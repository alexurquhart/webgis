from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from app.database.base import Base
from app.database.schema import Tweet, Hashtag, Picture

class Database:
    
    def __init__(self, uri, debug=False):
        self.__debug = debug
        self.__engine = create_engine(uri, echo=debug, client_encoding='utf8')
        self.__base = Base
        
        # Drop all if debugging
        if self.__debug:
            self.__base.metadata.drop_all(self.__engine)
        
        self.__base.metadata.create_all(self.__engine)
        session = sessionmaker(bind=self.__engine)
        self.__session = session()
    
    # Takes a tweet object from the API and inserts it into the database
    def insert(self, tweet):
        session = self.__session
        
        coordinates = tweet["coordinates"]["coordinates"]
        
        db_tweet = Tweet(
            tweet_id=tweet['id_str'],
            text=tweet['text'],
            screen_name=tweet['user']['screen_name'],
            user_id=tweet['user']['id_str'],
            time=datetime.strptime(tweet["created_at"], "%a %b %d  %H:%M:%S +0000 %Y"),
            geom="SRID=4326;POINT({0} {1})".format(coordinates[0], coordinates[1]))
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