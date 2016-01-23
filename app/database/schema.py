from sqlalchemy import Table, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from datetime import datetime
from app.database.base import Base

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
    division_id = Column(Integer, ForeignKey('tweets.divisions.id'))
    pictures = relationship("Picture", backref="tweet")
    hashtags = relationship("Hashtag", secondary=hashtags_tweets, back_populates="tweets")

class Picture(Base):
    __tablename__ = "pictures"
    __table_args__ = {'schema': 'tweets'}
    
    id = Column(Integer, primary_key=True)
    tweet_id = Column(Integer, ForeignKey('tweets.tweets.id'))
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

class Division(Base):
    __tablename__ = "divisions"
    __table_args__ = {'schema': 'tweets'}

    id = Column(Integer, primary_key=True)
    name = Column(String(convert_unicode=True))
    geom = Column(Geometry("POLYGON", 4326))
    tweets = relationship("Tweet", backref="division")
    
    # Takes a single GeoJSON polygon feature and extracts the geometry, name, and ID fields
    def __init__(self, feature):
        self.id = feature["properties"]["id"]
        self.name = feature["properties"]["name"]
        
        geom_list = []
        
        # Convert feature coordinates array to WKT
        for coord in feature["geometry"]["coordinates"][0]:
            geom_list.append("{:.15f} {:.15f}".format(coord[0], coord[1]))

        # Create the WKT string
        geom_text = ", ".join(geom_list)
        self.geom = "SRID=4326;POLYGON((" + geom_text + "))"