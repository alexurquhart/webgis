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
    
@application.route("/division/histogram/all")
def div_histogram_all():
    res = db.get_division_temporal_histogram()
    
    # Cast datetimes to strings
    for item in res["data"]:
        item.update((k, str(v)) for k, v in item.iteritems() if k is 'hour')
        
    return json.dumps(res)
    
@application.route("/division/histogram/<int:div_id>")
def div_histogram(div_id):
    div_ids = db.get_division_ids()
    
    if div_id not in div_ids:
        abort(400)
    else:
        return str(div_id)
        
    

if __name__ == "__main__":
    application.config['DEBUG'] = config.DEBUG
    application.run(host='0.0.0.0', port=6060)