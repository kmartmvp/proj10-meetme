import flask
from pymongo import MongoClient

import logging
import sys

import config

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

CONFIG = config.configuration()

# Need to edit configuration file. This will be accessed from main - don't worry
MONGO_CLIENT_URL = "mongodb://{}:{}@{}:{}/{}".format(
    CONFIG.DB_USER,
    CONFIG.DB_USER_PW,
    CONFIG.DB_HOST, 
    CONFIG.DB_PORT, 
    CONFIG.DB)

try:
    # Collection will be defined per meeting (as each meeting is represented by a collection)
    dbclient = MongoClient(MONGO_CLIENT_URL)
    dbase = getattr(dbclient, CONFIG.DB)
except:
    # If database can't be reached, exit program
    print("Failure opening database.")
    sys.exit(1)


def new_meeting(name):
    """Creates collection within MLab on call.
    Docs: https://api.mongodb.com/python/current/api/index.html
    
    [description]
    """
    # Create new DB collection in app's Mongo DB
    dbase.create_collection(name)
    
    
    