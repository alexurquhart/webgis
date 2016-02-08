from sqlalchemy import Table, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from datetime import datetime
from app.database import SCHEMA
from app.database.base import Base

# Hashtag-Tweet association table for many-many relationship
hashtags_tweets = Table(
    "hashtags_tweets", 
    Base.metadata,
    Column("hashtag_id", ForeignKey(SCHEMA + ".hashtags.id"), primary_key=True),
    Column("tweet_id", ForeignKey(SCHEMA + ".tweets.id"), primary_key=True),
    schema=SCHEMA
)

class Tweet(Base):
    __tablename__ = "tweets"
    __table_args__ = {"schema": SCHEMA}
    
    id = Column(Integer, primary_key=True)
    tweet_id = Column(String, nullable=False)
    text = Column(String(convert_unicode=True))
    screen_name = Column(String)
    user_id = Column(String)
    created_at = Column(DateTime)
    coordinates = None
    geom = Column(Geometry("POINT", 4326))
    division_id = Column(Integer, ForeignKey(SCHEMA + ".divisions.id"))
    pictures = relationship("Picture", backref="tweet")
    hashtags = relationship("Hashtag", secondary=hashtags_tweets, back_populates="tweets")
    
    def __init__(self, tweet):
        time = datetime.now()
        coordinates = tweet["coordinates"]["coordinates"]
        
        self.tweet_id = tweet['id_str'],
        self.text = tweet['text'],
        self.screen_name = tweet['user']['screen_name'],
        self.user_id = tweet['user']['id_str'],
        self.created_at = time,
        self.coordinates = [coordinates[0], coordinates[1]]
        self.geom = "SRID=4326;POINT({0} {1})".format(coordinates[0], coordinates[1])
        
        # Insert any pictures from twitter
        if "media" in tweet["entities"]:
            self.extract_twitter_images(tweet["entities"]["media"])

        # Extract instagram pictures
        if "urls" in tweet["entities"]:
            self.extract_instagram_images(tweet["entities"]["urls"])
    
    # Extracts images out of the twitter media entities
    def extract_twitter_images(self, media):
        for img in media:
            if img["type"] == "photo":
                self.pictures.append(Picture(source="twitter", img_url=img["media_url_https"]))

    # Extracts instagram image URL's out of the twitter URL entities
    def extract_instagram_images(self, urls):
        for url in urls:
            if url["display_url"].startswith("instagram.com/p/"):
                self.pictures.append(Picture(source="instagram", img_url=url["expanded_url"] + "media/"))

    @property
    def serialized(self):
        return {
            "tweet_id": self.tweet_id,
            "text": self.text,
            "screen_name": self.screen_name,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "coordinates": self.coordinates,
            "division_id": self.division_id,
            "pictures": [pic.serialized for pic in self.pictures],
            "hashtags": [ht.text for ht in self.hashtags],
        }

class Picture(Base):
    __tablename__ = "pictures"
    __table_args__ = {"schema": SCHEMA}
    
    id = Column(Integer, primary_key=True)
    tweet_id = Column(Integer, ForeignKey(SCHEMA + ".tweets.id"))
    source = Column(String, nullable=False)
    img_url = Column(String, nullable=False)
    
    @property
    def serialized(self):
        return {
            "source": self.source,
            "img_url": self.img_url
        }
    
class Hashtag(Base):
    __tablename__ = "hashtags"
    __table_args__ = {"schema": SCHEMA}
    
    id = Column(Integer, primary_key=True)
    text = Column(String, nullable=False, unique=True, index=True)
    tweets = relationship("Tweet", secondary=hashtags_tweets, back_populates="hashtags")

class Division(Base):
    __tablename__ = "divisions"
    __table_args__ = {"schema": SCHEMA}

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