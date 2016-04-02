from app import config
from app.database import Database
from app.schema import Tweet, Division, Hashtag, Picture
from geoalchemy2 import functions as func
from datetime import datetime, timedelta
import os, json

# Test tweet dicts
TEST_TWEET = {
    "id_str": "1234",
    "text": "This tweet is from the middle of lake ontario",
    "user": {
        "screen_name": "test_user",
        "id_str": "5678"
    },
    "created_at": "Wed Aug 27 13:08:45 +0000 2008",
    "coordinates": {
        "coordinates": [-77.8, 43.5]   
    },
    "entities": {
        "hashtags": [
            {
                "text": "yolo"   
            },
            {
                "text": "yolo"   
            },
            {
                "text": "YoLo"   
            },
            {
                "text": "Test"   
            }
        ],
        "urls": [
            {
                "display_url": "instagram.com/p/1234",
                "expanded_url": "instagram.com/"
            },
            {
                "display_url": "test.com",
                "expanded_url": "test.com"
            }
        ],
        "media": [
            {
                "type": "photo",
                "media_url_https": "https://twitter.com"
            }
        ]
    }
}

db = Database(config.DBURI, True)
duration = timedelta(days=30)
interval = timedelta(minutes=1)
now = datetime.now()
for row in db.session.query(func.ST_Centroid(Division.geom)).all():
	# Create 1 tweet per minute per division for the past 30 days
	for 