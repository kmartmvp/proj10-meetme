import flask
import pymongo
import arrow
import db

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Pull all ranges from collection in DB
# Expand ranges, get intersection. Returns a time for available for all users
def final_time(db_name):
    # DB name corresponding to meeting
    collection = db.dbase.get_collection(db_name)

    time_set = set()
    time_list = []
    for r in collection.find({"type": "availability"}):
        # Handles conversions to correct format and arrow object here
        start = arrow.get(r["start"], "YYYY-MM-DDTHH:mm:ssZZ")
        end = arrow.get(r["end"], "YYYY-MM-DDTHH:mm:ssZZ")
        start_format = start.format("MM/DD/YYYY hh:mm A")
        end_format = end.format("MM/DD/YYYY hh:mm A")

        for t in arrow.Arrow.range("minute", start, end):
            time_list.append(t)
    
    time_list_sort = sorted(time_list)
    for t in time_list_sort:
        time_set.add(t)

    # Sinc sets don't support indexing, convert to list
    time_set_conversion = list(time_set)
    
    if len(time_set_conversion) != 0:
        range1 = time_set_conversion[0]
        range2 = time_set_conversion[-1]

        return "{} - {}".format(range1, range2)
    else:
        return "No one has replied yet."
