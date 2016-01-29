from flask import Flask
from database import database
from datetime import datetime
import os, json
application = Flask(__name__)

DBURI = os.environ["DBURI"]

db = database.Database(DBURI)

@application.route("/hashtags/")
def hashtags():
    return "<h1 style='color:blue'>Hello There!</h1>"
   
# Returns 100's of  
@application.route("/heatmap/")
def heatmap():
    return json.dumps(db.get_heatmap_geom())