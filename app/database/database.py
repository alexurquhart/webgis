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

    # Takes a tweet object from the API and inserts it into the database
    def insert(self, tweet):
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
        
        div = self.get_division(db_tweet.geom)
        if div is not None:
            db_tweet.division_id = div.id

        # Add the tweet to the session
        session.add(db_tweet)
    
        # Loop through hashtags
        # If there isn't an instance of the hashtag already in the database
        # then create a new one and insert. Otherwise use the one that exists
        # Must also detect duplicate hashtags in the raw tweet and remove them
        if "hashtags" in tweet["entities"]:
            for ht in tweet["entities"]["hashtags"]:
                new_ht = session.query(Hashtag).filter(Hashtag.text == ht["text"].lower()).first()
                if new_ht == None:
                    new_ht = Hashtag(ht["text"])
                db_tweet.hashtags.append(new_ht)
                session.commit()
        
        # Insert any pictures from twitter
        if "media" in tweet["entities"]:
            for media in tweet["entities"]["media"]:
                if media["type"] == "photo":
                    db_tweet.pictures.append(Picture(source="twitter", img_url=media["media_url_https"]))
                
        # Extract instagram pictures
        if "urls" in tweet["entities"]:
            for url in tweet["entities"]["urls"]:
                if url["display_url"].startswith("instagram.com/p/"):
                    db_tweet.pictures.append(Picture(source="instagram", img_url=url["expanded_url"] + "media/"))
        
        session.commit()