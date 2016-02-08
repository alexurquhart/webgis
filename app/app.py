from flask import Flask
from database import database
from datetime import datetime
import os, json, config
application = Flask(__name__)

db = database.Database(config.DBURI)

# Returns 100's of  
@application.route("/heatmap/")
def heatmap():
    return json.dumps(db.get_heatmap_geom())

@application.route("/last_tweets/")
def last_tweets():
    tweets = db.get_last_tweets()
    ser = map(lambda x: x.serialized, tweets)
    return json.dumps(ser)