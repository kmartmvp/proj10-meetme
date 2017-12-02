import flask
import arrow

import logging

# Referenced this for best practice on logging in flask (app.logger or Python's own logging?)
#   https://stackoverflow.com/questions/29325259/call-logger-from-multiple-modules-in-flask-app
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def free(range_lst, range_start, range_end, user_start, user_end):
    """Calculates free times for user based on time range, start time of events and end times of events
    by removing range [user_start, user_end] from range [range_start, range_end].
    
    Takes a range list that is iterated upon in flask_main. This list is updated via index deletion and
    returned. Only to be used in flask_main.
    
    Arguments:
        range_lst {list} -- [description]
        range_start {dateTime} -- [description]
        range_end {dateTime} -- [description]
        user_start {dateTime} -- [description]
        user_end {dateTime} -- [description]
    """
    
    # Attempt to calculate range to subtract times from
    minute_range = []
    # range_start = arrow.get(range_start, "MM/DD/YYYY hh:mm A")
    # range_start_format = range_start.format("MM/DD/YYYY hh:mm A")
    # range_end   = arrow.get(range_end, "MM/DD/YYYY hh:mm A")
    # range_end_format = range_end.format("MM/DD/YYYY hh:mm A")

    # Calculate range of minutes between potential start and end given by event creator
    minute_range = []
    for r in arrow.Arrow.range("minute", range_start, range_end):
        minute_range.append(r)

    # Attempt to calculate user range of busy times
    try:
        user_start = arrow.get(user_start, "MM/DD/YYYY hh:mm A")
        user_end = arrow.get(user_end, "MM/DD/YYYY hh:mm A")

        user_range = arrow.Arrow.range("minute", user_start, user_end)
    except:
        logger.info("MODULE 'free_times' FUNCTION 'free' -- Can't calculate USER range using {} - {}".format(user_start, user_end))
        # Return empty list on fail
        return []

    # Subtract times from user_range from the general minute_range
    for time in user_range:
        if time in minute_range:
            index = minute_range.index(time)
            # None type will be used to generate range in flask_main find_busy_times
            minute_range[index] = None
        
    return minute_range


    