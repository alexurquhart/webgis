from app import config
from app.database import Database
from app.schema import Tweet, Division, Hashtag, Picture
from geoalchemy2 import functions as func
from datetime import datetime, timedelta
from time import sleep
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

db = Database(config.DBURI, False, True)
duration = timedelta(days=7)
interval = timedelta(minutes=60)
now = datetime.now()
centroid = func.ST_Centroid(Division.geom)
for row in db.session.query(func.ST_X(centroid), func.ST_Y(centroid)).all():
	# Create 1 tweet per hour per division for the past 7 days
	for i in range(0, int(duration.total_seconds()) + 60, 3600):
		new_tweet = TEST_TWEET.copy()
		new_tweet["coordinates"]["coordinates"] = list(row)
		new_tweet["created_at"] = now - timedelta(seconds=i)
		db.insert_tweet(new_tweet)

ps = PubSub()

while True:
	for row in db.session.query(func.ST_X(centroid), func.ST_Y(centroid)).all():
        if "coordinates" in item and item["coordinates"] is not None:
			new_tweet = TEST_TWEET.copy()
			new_tweet["coordinates"]["coordinates"] = list(row)
            tweet = db.insert_tweet(new_tweet)
            if tweet is not None:
				ps.publish(tweet)
				sleep(250)