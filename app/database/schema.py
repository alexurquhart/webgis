from sqlalchemy import Table, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from datetime import datetime
from app.database.base import Base
import os

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
    text = Column(String, nullable=False, unique=True, index=True)
    tweets = relationship("Tweet", secondary=hashtags_tweets, back_populates="hashtags")
    
    # For analysis purposes all hashtags will be lower case
    def __init__(self, text):
        self.text = text.lower()