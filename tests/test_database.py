import unittest, json, os
from datetime import datetime
os.environ["SCHEMA"] = "testing"
from app.database.database import Database
from app.database.schema import Tweet, Hashtag, Picture, Division

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

# Setup database - creates all tables and inserts divisions geometry
def setUpModule():
    global db
    db = Database(os.environ["DBURI"], True)
    
class TestDatabase(unittest.TestCase):
    def setUp(self):
        coordinates = TEST_TWEET["coordinates"]["coordinates"]
        time = datetime.strptime(TEST_TWEET["created_at"], "%a %b %d  %H:%M:%S +0000 %Y")
        
        self.tweet = Tweet(
            tweet_id=TEST_TWEET['id_str'],
            text=TEST_TWEET['text'],
            screen_name=TEST_TWEET['user']['screen_name'],
            user_id=TEST_TWEET['user']['id_str'],
            time=time,
            geom="SRID=4326;POINT({0} {1})".format(coordinates[0], coordinates[1]))
    
    def test_get_division(self):
        self.assertIsNotNone(db.get_division(self.tweet.geom))
        self.tweet.geom = "SRID=4326;POINT({0} {1})".format(-1, -1)
        self.assertIsNone(db.get_division(self.tweet.geom))
        
    def test_extract_hashtags(self):
        db.extract_hashtags(TEST_TWEET["entities"]["hashtags"], self.tweet)
        self.assertEqual(len(self.tweet.hashtags), 2)
        
    def test_extract_twitter_images(self):
        db.extract_twitter_images(TEST_TWEET["entities"]["media"], self.tweet)
        self.assertEqual(len(self.tweet.pictures), 1)
        self.assertEqual(self.tweet.pictures[0].img_url, "https://twitter.com")
        
    def test_extract_instagram_images(self):
        db.extract_instagram_images(TEST_TWEET["entities"]["urls"], self.tweet)
        self.assertEqual(len(self.tweet.pictures), 1)
        self.assertEqual(self.tweet.pictures[0].img_url, "instagram.com/media/")
    
if __name__ == '__main__':
    unittest.main()