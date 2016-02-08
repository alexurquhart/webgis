from flask import Flask
from database import database
from datetime import datetime
import os, json
application = Flask(__name__)

DBURI = os.environ["DBURI"]

db = database.Database(DBURI)

# Returns 100's of  
@application.route("/heatmap/")
def heatmap():
    return json.dumps(db.get_heatmap_geom())

@application.route("/last_tweets/")
def last_tweets():
    tweets = db.get_last_tweets()
    ser = map(lambda x: x.serialized, tweets)
    return json.dumps(ser)