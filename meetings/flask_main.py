import flask
from flask import render_template
from flask import request
from flask import url_for
import uuid

import json
import logging

# Date handling 
import arrow # Replacement for datetime, based on moment.js
# import datetime # But we still need time
from dateutil import tz  # For interpreting local times


# OAuth2  - Google library implementation for convenience
from oauth2client import client
import httplib2   # used in oauth2 flow

# Google API for services 
from apiclient import discovery

# For use to calculate free times
from free_times import free

# Calculate final meeting range
from calc_avail import final_time

# Database essentials
from pymongo import MongoClient
import db

###
# Globals
###
import config
if __name__ == "__main__":
    CONFIG = config.configuration()
else:
    CONFIG = config.configuration(proxied=True)

app = flask.Flask(__name__)
app.debug=CONFIG.DEBUG
app.logger.setLevel(logging.DEBUG)
app.secret_key=CONFIG.SECRET_KEY

SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
CLIENT_SECRET_FILE = CONFIG.GOOGLE_KEY_FILE  ## You'll need this
APPLICATION_NAME = 'MeetMe class project'

#############################
#
#  Pages (routed from URLs)
#
#############################

# @app.route("/index")
# def index():
#   app.logger.debug("Entering index")
#   if 'begin_date' not in flask.session:
#     init_session_values()
#   return render_template('index.html')

@app.route("/choose")
def choose():
    ## We'll need authorization to list calendars 
    ## I wanted to put what follows into a function, but had
    ## to pull it back here because the redirect has to be a
    ## 'return' 
    app.logger.debug("Checking credentials for Google calendar access")
    credentials = valid_credentials()
    if not credentials:
      app.logger.debug("Redirecting to authorization")
      return flask.redirect(flask.url_for('oauth2callback'))

    gcal_service = get_gcal_service(credentials)
    app.logger.debug("Returned from get_gcal_service")
    flask.g.calendars = list_calendars(gcal_service)
    return render_template('index.html')


@app.route("/find_busy_times")
def find_busy_times():
    # Get IDs of selected calendars
    id_list = flask.request.args.get("idList")
    id_list_split = id_list.split("+")

    # Retrieve selected datetime from session and split into start and end
    date_time_split = flask.session["daterange"].split(" - ")
    date_time_start = date_time_split[0]
    date_time_end = date_time_split[1]
    
    # MUST format according to RFC3339 format for timeMin and timeMax in service object
    # Format received from: https://github.com/crsmithdev/arrow/issues/180
    start_arrow = arrow.get(date_time_start, "MM/DD/YYYY hh:mm A")
    start_format = start_arrow.format("YYYY-MM-DDTHH:mm:ssZZ")
    end_arrow = arrow.get(date_time_end, "MM/DD/YYYY hh:mm A")
    end_format = end_arrow.format("YYYY-MM-DDTHH:mm:ssZZ")

    # Use current Calendar service
    credentials = valid_credentials()
    service = get_gcal_service(credentials)

    # Iterate through each calendar
    for cal in id_list_split:
        # While we still have calendars to iterate through, check for events
        # in selected range (held in session variable daterange)
        #   CalendarID: id of a user's calendar
        #   timeMin: Minimum date to start looking for
        #   timeMax: Maximum date to start looking for
        #   pageToken: Used to iterate though elist of events
        #   singleEvents: Make recurring events only be considered once
        page_token = None
        while True:
            events = service.events().list(
                calendarId = cal, 
                timeMin = start_format,
                timeMax = end_format,
                pageToken = page_token,
                singleEvents = True).execute()
            
            free_times = []
            for event in events['items']:
                try:
                    ev_start = event["start"]["dateTime"]
                    ev_end = event["end"]["dateTime"]

                    start_time = arrow.get(ev_start, "YYYY-MM-DDTHH:mm:ssZZ")
                    start_time_format = start_time.format("MM/DD/YYYY hh:mm A")

                    end_time = arrow.get(ev_end, "YYYY-MM-DDTHH:mm:ssZZ")
                    end_time_format = end_time.format("MM/DD/YYYY hh:mm A")

                    summary = event["summary"]

                    # Send busy times to free_times module to calculate free times for DB
                    free_times = free(
                        free_times, start_arrow, end_arrow, start_time_format, end_time_format)

                    # Flash busy times for user to see if NOT all-day event (ie dateTime key is accessible)
                    flask.flash("Busy on {} - {}: {}".format(
                        start_time_format, end_time_format, summary))
                except:
                    ev_start = event["start"]["date"]
                    ev_end = event["end"]["date"]

                    start_time = arrow.get(ev_start, "YYYY-MM-DD")
                    start_time_format = start_time.format("MM/DD/YYYY hh:mm A")

                    end_time = arrow.get(ev_end, "YYYY-MM-DD")
                    end_time_format = end_time.format("MM/DD/YYYY hh:mm A")

                    summary = event["summary"]

                    # Flash busy times for user to see if IS all-day event (ie dateTime key is NOT accessible)
                    flask.flash("Busy on {} - {}: {}".format(
                        start_time_format, end_time_format, summary))
                    
                    app.logger.info("%s is all-day event - no dateTime.", summary)
                
            # Create list of ranges to be passed to DB
                avail_times = []
                last = None
                time1 = None
                time2 = None
                # Find free times according to ranges
                # None indicates the end of a range - create ranges according to a beginning up to a Nonetype
                for i in range(len(free_times)):
                    nxt = None
                    if i != len(free_times) - 1:
                        nxt = free_times[i+1]

                    if free_times[i] == None:
                        last = None
                    elif last == None:
                        time1 = free_times[i]
                        last = free_times[i]
                    elif nxt == None:
                        time2 = free_times[i]
                        avail_times.append([time1, time2])
                
                for r in avail_times:
                    # Flash busy times for user to see if NOT all-day event (ie dateTime key is accessible)
                    flask.flash("Available on {} - {}".format(
                        r[0], r[1]))
                    
                    # Create new object in database
                    collection = db.dbase.get_collection(flask.session["db_name"])
                    collection.insert_one({
                        "type": "availability",
                        "start": str(r[0]),
                        "end": str(r[1])
                    })

            page_token = events.get("nextPageToken")

            if not page_token:
                break

    # Empty response, but JQuery uses response to indicate redirect
    return flask.jsonify({})


@app.route("/")
@app.route("/entry")
def entry():
    # Entry point - it is automatically the "create meeting" page
    return render_template("create.html")


@app.route("/create_meeting")
def create_meeting():
    """Routes application to create page. Is default page.
    
    [description]
    
    Decorators:
        app
    
    Returns:
        [type] -- [description]
    """
    # Maybe initialize session vairables here and combine index with this? I think yes.
    # Will need to edit intialize session and set range for dateTime ranges
    # See how datetimepicker is used. This format will be sent to new user page.
    #   SO, setrange is used for create page now and not user page (old index and busy times)

    # Retrieve selected datetime from session and split into start and end
    date_time_split = flask.session["daterange"].split(" - ")
    date_time_start = date_time_split[0]
    date_time_end = date_time_split[1]

    # Generate ID for both URL and name of collection in DB that represents the meeting
    name = str(uuid.uuid4())
    flask.session["db_name"] = name

    # Find collection with respective name defined in parameters
    collection = db.dbase.get_collection(flask.session["db_name"])

    # Create new collection (a new meeting)
    db.new_meeting(flask.session["db_name"])

    # Add date range to collection
    collection.insert_one({
        "type": "meetingRange",
        "start": date_time_start,
        "end": date_time_end
    })

    # Flash url to bootstrap in create.html
    # flask.flash("Append to back of URL: " + name)

    msg = {"name": name}

    return flask.jsonify(result=msg)


@app.route("/<meeting>")
def user_page(meeting):
    # Reference on routing to variable URL:
    # http://exploreflask.com/en/latest/views.html

    # Will need to give "choose" render_template parameters

    # Similar to entry point at index, this is the entry point for someone
    # receiving an invitation to the meeting. If so, we must initialize session
    # values.
    if 'begin_date' not in flask.session:
        app.logger.debug("User entering upon invitation")
        init_session_values()

    # Update with user provided URL (meeting) so that we reference the correct collection
    # in route choose
    flask.session["db_name"] = meeting

    ## STARTER CODE - originally from original index route
    ## We'll need authorization to list calendars 
    ## I wanted to put what follows into a function, but had
    ## to pull it back here because the redirect has to be a
    ## 'return' 
    app.logger.debug("Checking credentials for Google calendar access")
    credentials = valid_credentials()
    if not credentials:
      app.logger.debug("Redirecting to authorization")
      return flask.redirect(flask.url_for('oauth2callback'))

    gcal_service = get_gcal_service(credentials)
    app.logger.debug("Returned from get_gcal_service")
    flask.g.calendars = list_calendars(gcal_service)

    return render_template("index.html")


@app.route("/get_range", methods=["GET"])
def get_range():
    # Retrieves date range from meeting
    # Meeting is already saved in session variable "db_name"

    collection = db.dbase.get_collection(str(flask.session["db_name"]))
    
    print(collection)
    # Returns cursor object for iterating over item in collection
    item = collection.find_one({"type": "meetingRange"})
    print(item)
    
    # Correct start and end based on indices for meetingRange type
    #   [0] - oID
    #   [1] - type ("meetingRange")
    #   [2] - start
    #   [3] - end
    start = item["start"]
    end = item["end"]
    print("\n" + start)
    print("\n" + end)

    rng = "{} - {}".format(start, end)
    app.logger.debug("METHOD: get_range -- Can't connect to collection.")


    rslt = {"rng": rng}
    return flask.jsonify(result=rslt)

@app.route("/final", methods=["GET"])
def final():
    # Calculate the final meeting time for creator
    
    # Get the final calculation on aggregated free times via calc_avail
    fr = final_time(flask.session["db_name"])

    rslt = {"range": fr}
    
    return flask.jsonify(result=rslt)


####
#
#  Google calendar authorization:
#      Returns us to the main /choose screen after inserting
#      the calendar_service object in the session state.  May
#      redirect to OAuth server first, and may take multiple
#      trips through the oauth2 callback function.
#
#  Protocol for use ON EACH REQUEST: 
#     First, check for valid credentials
#     If we don't have valid credentials
#         Get credentials (jump to the oauth2 protocol)
#         (redirects back to /choose, this time with credentials)
#     If we do have valid credentials
#         Get the service object
#
#  The final result of successful authorization is a 'service'
#  object.  We use a 'service' object to actually retrieve data
#  from the Google services. Service objects are NOT serializable ---
#  we can't stash one in a cookie.  Instead, on each request we
#  get a fresh serivce object from our credentials, which are
#  serializable. 
#
#  Note that after authorization we always redirect to /choose;
#  If this is unsatisfactory, we'll need a session variable to use
#  as a 'continuation' or 'return address' to use instead. 
#
####

def valid_credentials():
    """
    Returns OAuth2 credentials if we have valid
    credentials in the session.  This is a 'truthy' value.
    Return None if we don't have credentials, or if they
    have expired or are otherwise invalid.  This is a 'falsy' value. 
    """
    if 'credentials' not in flask.session:
      return None

    credentials = client.OAuth2Credentials.from_json(
        flask.session['credentials'])

    if (credentials.invalid or
        credentials.access_token_expired):
      return None
    return credentials


def get_gcal_service(credentials):
  """
  We need a Google calendar 'service' object to obtain
  list of calendars, busy times, etc.  This requires
  authorization. If authorization is already in effect,
  we'll just return with the authorization. Otherwise,
  control flow will be interrupted by authorization, and we'll
  end up redirected back to /choose *without a service object*.
  Then the second call will succeed without additional authorization.
  """
  app.logger.debug("Entering get_gcal_service")
  http_auth = credentials.authorize(httplib2.Http())
  service = discovery.build('calendar', 'v3', http=http_auth)
  app.logger.debug("Returning service")
  return service

@app.route('/oauth2callback')
def oauth2callback():
  """
  The 'flow' has this one place to call back to.  We'll enter here
  more than once as steps in the flow are completed, and need to keep
  track of how far we've gotten. The first time we'll do the first
  step, the second time we'll skip the first step and do the second,
  and so on.
  """
  app.logger.debug("Entering oauth2callback")
  flow =  client.flow_from_clientsecrets(
      CLIENT_SECRET_FILE,
      scope= SCOPES,
      redirect_uri=flask.url_for('oauth2callback', _external=True))
  ## Note we are *not* redirecting above.  We are noting *where*
  ## we will redirect to, which is this function. 
  
  ## The *second* time we enter here, it's a callback 
  ## with 'code' set in the URL parameter.  If we don't
  ## see that, it must be the first time through, so we
  ## need to do step 1. 
  app.logger.debug("Got flow")
  if 'code' not in flask.request.args:
    app.logger.debug("Code not in flask.request.args")
    auth_uri = flow.step1_get_authorize_url()
    return flask.redirect(auth_uri)
    ## This will redirect back here, but the second time through
    ## we'll have the 'code' parameter set
  else:
    ## It's the second time through ... we can tell because
    ## we got the 'code' argument in the URL.
    app.logger.debug("Code was in flask.request.args")
    auth_code = flask.request.args.get('code')
    credentials = flow.step2_exchange(auth_code)
    flask.session['credentials'] = credentials.to_json()
    ## Now I can build the service and execute the query,
    ## but for the moment I'll just log it and go back to
    ## the main screen
    app.logger.debug("Got credentials")
    return flask.redirect(flask.url_for('choose'))

#####
#
#  Option setting:  Buttons or forms that add some
#     information into session state.  Don't do the
#     computation here; use of the information might
#     depend on what other information we have.
#   Setting an option sends us back to the main display
#      page, where we may put the new information to use. 
#
#####

@app.route('/setrange', methods=['POST'])
def setrange():
    """
    User chose a date range with the bootstrap daterange
    widget.
    """
    app.logger.debug("Entering setrange")  
    flask.flash("Setrange gave us '{}'".format(
      request.form.get('daterange')))
    daterange = request.form.get('daterange')
    flask.session['daterange'] = daterange
    daterange_parts = daterange.split(" - ")
    flask.session['begin_date'] = interpret_date(daterange_parts[0])
    flask.session['end_date'] = interpret_date(daterange_parts[1])
    app.logger.debug("Setrange parsed {} - {}  dates as {} - {}".format(
      daterange_parts[0], daterange_parts[1], 
      flask.session['begin_date'], flask.session['end_date']))
    return flask.redirect(flask.url_for("choose"))


####
#
#   Initialize session variables 
#
####

def init_session_values():
    """
    Start with some reasonable defaults for date and time ranges.
    Note this must be run in app context ... can't call from main. 
    """
    # Default date span = tomorrow to 1 week from now
    now = arrow.now('local')     # We really should be using tz from browser
    tomorrow = now.replace(days=+1)
    nextweek = now.replace(days=+7)
    flask.session["begin_date"] = tomorrow.floor('day').isoformat()
    flask.session["end_date"] = nextweek.ceil('day').isoformat()
    flask.session["daterange"] = "{} - {}".format(
        tomorrow.format("MM/DD/YYYY hh:mm A"),
        nextweek.format("MM/DD/YYYY hh:mm A"))
    # Default time span each day, 8 to 5
    flask.session["begintime"] = interpret_time("9am")
    flask.session["endtime"] = interpret_time("5pm")

    # Initialize database session info
    flask.session["db_name"] = "No collections defined"

def interpret_time( text ):
    """
    Read time in a human-compatible format and
    interpret as ISO format with local timezone.
    May throw exception if time can't be interpreted. In that
    case it will also flash a message explaining accepted formats.
    """
    app.logger.debug("Decoding time '{}'".format(text))
    time_formats = ["ha", "h:mma",  "h:mm a", "H:mm"]
    try: 
        as_arrow = arrow.get(text, time_formats).replace(tzinfo=tz.tzlocal())
        as_arrow = as_arrow.replace(year=2016) #HACK see below
        app.logger.debug("Succeeded interpreting time")
    except:
        app.logger.debug("Failed to interpret time")
        flask.flash("Time '{}' didn't match accepted formats 13:30 or 1:30pm"
              .format(text))
        raise
    return as_arrow.isoformat()
    #HACK #Workaround
    # isoformat() on raspberry Pi does not work for some dates
    # far from now.  It will fail with an overflow from time stamp out
    # of range while checking for daylight savings time.  Workaround is
    # to force the date-time combination into the year 2016, which seems to
    # get the timestamp into a reasonable range. This workaround should be
    # removed when Arrow or Dateutil.tz is fixed.
    # FIXME: Remove the workaround when arrow is fixed (but only after testing
    # on raspberry Pi --- failure is likely due to 32-bit integers on that platform)


def interpret_date( text ):
    """
    Convert text of date to ISO format used internally,
    with the local time zone.
    """
    try:
      as_arrow = arrow.get(text, "MM/DD/YYYY hh:mm A").replace(
          tzinfo=tz.tzlocal())
    except:
        flask.flash("Date '{}' didn't fit expected format 12/31/2001")
        raise
    return as_arrow.isoformat()

def next_day(isotext):
    """
    ISO date + 1 day (used in query to Google calendar)
    """
    as_arrow = arrow.get(isotext)
    return as_arrow.replace(days=+1).isoformat()

####
#
#  Functions (NOT pages) that return some information
#
####
  
def list_calendars(service):
    """
    Given a google 'service' object, return a list of
    calendars.  Each calendar is represented by a dict.
    The returned list is sorted to have
    the primary calendar first, and selected (that is, displayed in
    Google Calendars web app) calendars before unselected calendars.
    """
    app.logger.debug("Entering list_calendars")  
    calendar_list = service.calendarList().list().execute()["items"]
    result = [ ]
    for cal in calendar_list:
        kind = cal["kind"]
        identification = cal["id"]
        if "description" in cal: 
            desc = cal["description"]
        else:
            desc = "(no description)"
        summary = cal["summary"]
        # Optional binary attributes with False as default
        selected = ("selected" in cal) and cal["selected"]
        primary = ("primary" in cal) and cal["primary"]

        result.append(
          { "kind": kind,
            "id": identification,
            "summary": summary,
            "selected": selected,
            "primary": primary
            })
    return sorted(result, key=cal_sort_key)


def cal_sort_key( cal ):
    """
    Sort key for the list of calendars:  primary calendar first,
    then other selected calendars, then unselected calendars.
    (" " sorts before "X", and tuples are compared piecewise)
    """
    if cal["selected"]:
       selected_key = " "
    else:
       selected_key = "X"
    if cal["primary"]:
       primary_key = " "
    else:
       primary_key = "X"
    return (primary_key, selected_key, cal["summary"])


#################
#
# Functions used within the templates
#
#################

@app.template_filter( 'fmtdate' )
def format_arrow_date( date ):
    try: 
        normal = arrow.get( date )
        return normal.format("ddd MM/DD/YYYY")
    except:
        return "(bad date)"

@app.template_filter( 'fmttime' )
def format_arrow_time( time ):
    try:
        normal = arrow.get( time )
        return normal.format("HH:mm")
    except:
        return "(bad time)"
    
#############


if __name__ == "__main__":
  # App is created above so that it will
  # exist whether this is 'main' or not
  # (e.g., if we are running under green unicorn)
  app.run(port=CONFIG.PORT,host="0.0.0.0")
    
