from sqlalchemy import Table, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from datetime import datetime
import os

Base = declarative_base()

if "SCHEMA" in os.environ:

# Hashtag-Tweet association table for many-many relationship
hashtags_tweets = Table(
    "hashtags_tweets", 
    Base.metadata,
    Column("hashtag_id", ForeignKey("tweets.hashtags.id"), primary_key=True),
    Column("tweet_id", ForeignKey("tweets.tweets.id"), primary_key=True),
    schema="tweets"
)

class Tweet(Base):
    __tablename__ = 'tweets'
    __table_args__ = {'schema': 'tweets'}
    
    id = Column(Integer, primary_key=True)
    tweet_id = Column(String, nullable=False)
    text = Column(String(convert_unicode=True))
    screen_name = Column(String)
    user_id = Column(String)
    time = Column(DateTime)
    geom = Column(Geometry("POINT", 4326))
    pictures = relationship("Picture", back_populates="tweet")
    hashtags = relationship("Hashtag", secondary=hashtags_tweets, back_populates="tweets")

class Picture(Base):
    __tablename__ = "pictures"
    __table_args__ = {'schema': 'tweets'}
    
    id = Column(Integer, primary_key=True)
    tweet_id = Column(Integer, ForeignKey('tweets.tweets.id'))
    tweet = relationship("Tweet", back_populates="pictures")
    source = Column(String, nullable=False)
    img_url = Column(String, nullable=False)
    
class Hashtag(Base):
    __tablename__ = "hashtags"
    __table_args__ = {'schema': 'tweets'}
    
    id = Column(Integer, primary_key=True)
    text = Column(String, nullable=False, unique=True)
    tweets = relationship("Tweet", secondary=hashtags_tweets, back_populates="hashtags")
    
    # For analysis purposes all hashtags will be lower case
    def __init__(self, text):
        self.text = text.lower()

def setup(debug, schema):
    

# Takes a raw tweet dict and adds it to the databse
def add_to_database(tweet, session):
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
            if url["display_url"].startswith("instagr.am"):
                db_tweet.pictures.append(Picture(source="instagram", img_url=url["expanded_url"] + "media/"))
    
    session.commit()