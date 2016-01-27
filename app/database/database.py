from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from app.database.base import Base
from app.database.schema import Tweet, Hashtag, Picture, Division
import codecs, json

class Database:
    
    def __init__(self, uri, debug=False, divisions_file="data/divisions.json"):
        self.__debug = debug
        self.__engine = create_engine(uri, echo=debug, client_encoding='utf8')
        self.__base = Base
        
        # Drop all if debugging
        if self.__debug:
            self.__base.metadata.drop_all(self.__engine)
        
        self.__base.metadata.create_all(self.__engine)
        session = sessionmaker(bind=self.__engine)
        self.__session = session()
        
        # Load all divisions from GeoJSON if debugging
        if self.__debug:
            features = self.load_geojson(divisions_file)
            self.create_divisions(features)
    
    # Given a filename, opens the file and parses the GeoJSON,
    # returning the array of geojson feature objects
    def load_geojson(self, filename):
        with codecs.open(filename, 'r', "utf-8") as file:
            gj = file.read()
        parsed = json.loads(gj)
        return parsed["features"]
        
    # Given a list of GeoJSON features, create divison objects and insert them
    def create_divisions(self, features):
        session = self.__session
        for f in features:
            session.add(Division(f))
        session.commit()
        
    # Returns the division ID that the input geometry is contained by, or None
    def get_division(self, geom):
        div = self.__session.query(Division).filter(Division.geom.ST_Contains(geom)).first()
        return div
        
    # Takes a list of hashtag entities and places them appropriately into the database Tweet object
    # First checks to see if the hashtag already exists, if so, then the existing name and ID is used
    # and an entry will be placed in the association table
    def extract_hashtags(self, hashtags, tweetClass):
        # Convert hashtags to lowercase and remove duplicates
        ht_text = set(map(lambda x: x["text"].lower(), hashtags))
        
        for ht in ht_text:
            new_ht = self.__session.query(Hashtag).filter(Hashtag.text == ht).first()
            if new_ht == None:
                new_ht = Hashtag(text=ht)
            tweetClass.hashtags.append(new_ht)
    
    # Extracts images out of the twitter media entities
    def extract_twitter_images(self, media, tweetClass):
        for img in media:
            if img["type"] == "photo":
                tweetClass.pictures.append(Picture(source="twitter", img_url=img["media_url_https"]))

    # Extracts instagram image URL's out of the twitter URL entities
    def extract_instagram_images(self, urls, tweetClass):
        for url in urls:
            if url["display_url"].startswith("instagram.com/p/"):
                tweetClass.pictures.append(Picture(source="instagram", img_url=url["expanded_url"] + "media/"))

    # Takes a tweet object from the API and inserts it into the database
    def insert_tweet(self, tweet):
        session = self.__session
        
        coordinates = tweet["coordinates"]["coordinates"]
        time = datetime.strptime(tweet["created_at"], "%a %b %d  %H:%M:%S +0000 %Y")
        
        db_tweet = Tweet(
            tweet_id=tweet['id_str'],
            text=tweet['text'],
            screen_name=tweet['user']['screen_name'],
            user_id=tweet['user']['id_str'],
            time=time,
            geom="SRID=4326;POINT({0} {1})".format(coordinates[0], coordinates[1]))
        
        # If return if the point does not lie inside one of our divisions
        div = self.get_division(db_tweet.geom)
        if div == None:
            return
        db_tweet.division_id = div.id

        if "hashtags" in tweet["entities"]:
            self.extract_hashtags(tweet["entities"]["hashtags"], db_tweet)
        
        # Insert any pictures from twitter
        if "media" in tweet["entities"]:
            self.extract_twitter_images(tweet["entities"]["media"], db_tweet)

        # Extract instagram pictures
        if "urls" in tweet["entities"]:
            self.extract_instagram_images(tweet["entities"]["urls"], db_tweet)
        
        # Add the tweet to the session
        session.add(db_tweet)
        session.commit()