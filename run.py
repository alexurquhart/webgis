from app import config
from app.database import Database
from flask import Flask, abort
from datetime import datetime
import os, json
application = Flask(__name__)

db = Database(config.DBURI)

# Returns 100's of  
@application.route("/tweets/heatmap")
def heatmap():
    return json.dumps(db.get_heatmap_geom())

@application.route("/tweets/latest")
def last_tweets():
    tweets = db.get_last_tweets()
    ser = map(lambda x: x.serialized, tweets)
    return json.dumps(ser)
    
@application.route("/division/all/histogram")
def div_histogram_all():
    res = db.get_tweet_counts_by_division()        
    return json.dumps(res)
    
@application.route("/division/<int:div_id>/histogram")
def div_histogram(div_id):
    div_ids = db.get_division_ids()
    
    if div_id not in div_ids:
        abort(400)
    else:
        res = db.get_tweet_counts_by_division(div_id)        
        return json.dumps(res)

@application.route("/division/<int:div_id>/users")
def div_users(div_id):
    div_ids = db.get_division_ids()
    
    if div_id not in div_ids:
        abort(400)
    else:
        res = db.get_active_users_by_division(div_id)        
        return json.dumps(res)
        
@application.route("/pictures/<sw_long>,<sw_lat>,<ne_long>,<ne_lat>")
def pictures_in_extent(sw_lat, sw_long, ne_lat, ne_long):
    try:
        sw_lat = float(sw_lat)
        sw_long = float(sw_long)
        ne_lat = float(ne_lat)
        ne_long = float(ne_long)
    except ValueError:
        abort(400)

    res = db.get_pictures_in_extent(sw_lat, sw_long, ne_lat, ne_long)
    ser = ser = map(lambda x: x.tweet.serialized, res)
    return json.dumps(ser)

if __name__ == "__main__":
    application.config['DEBUG'] = config.DEBUG
    application.run(host='0.0.0.0', port=6060)