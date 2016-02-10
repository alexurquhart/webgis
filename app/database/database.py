from sqlalchemy import create_engine, distinct, func, desc
from sqlalchemy.orm import sessionmaker
from geoalchemy2 import functions as geo_func
from datetime import datetime, timedelta
from app import config
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
        self.session = sessionmaker(bind=self.__engine)()

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
        for f in features:
            self.session.add(Division(f))
        self.session.commit()
        
    # Returns the division ID that the input geometry is contained by, or None
    def get_division(self, geom):
        div = self.session.query(Division).filter(Division.geom.ST_Contains(geom)).first()
        return div
        
    # Takes a list of hashtag entities and places them appropriately into the database Tweet object
    # First checks to see if the hashtag already exists, if so, then the existing name and ID is used
    # and an entry will be placed in the association table
    def extract_hashtags(self, hashtags, tweetClass):
        # Convert hashtags to lowercase and remove duplicates
        ht_text = set(map(lambda x: x["text"].lower(), hashtags))
        
        for ht in ht_text:
            new_ht = self.session.query(Hashtag).filter(Hashtag.text == ht).first()
            if new_ht == None:
                new_ht = Hashtag(text=ht)
            tweetClass.hashtags.append(new_ht)
    
    # Filter out tweets from blacklisted users            
    def filter(self, tweet):
        for name in config.BLACKLIST_SCREENNAMES_EQ:
            if tweet.screen_name[0] is name:
                return True

        for name in config.BLACKLIST_SCREENNAMES_STARTSWITH:
            if tweet.screen_name[0].lower().startswith(name):
                return True
                
        for name in config.BLACKLIST_SCREENNAMES_ENDSWITH:
            if tweet.screen_name[0].lower().endswith(name):
                return True
                
        return False
    
    # Takes a tweet object from the API and inserts it into the database
    def insert_tweet(self, tweet):
        db_tweet = Tweet(tweet)
        
        if self.filter(db_tweet):
            return
        
        # Return if the point does not lie inside one of our divisions
        div = self.get_division(db_tweet.geom)
        if div == None:
            return
        db_tweet.division_id = div.id

        if "hashtags" in tweet["entities"]:
            self.extract_hashtags(tweet["entities"]["hashtags"], db_tweet)
        
        # Add the tweet to the session
        self.session.add(db_tweet)
        self.session.commit()
        
        return db_tweet
        
    # Get Heatmap Geom
    # Returns geometry for all tweets recorded in the past 6 hours
    def get_heatmap_geom(self):
        hour_ago = datetime.utcnow() - timedelta(hours=6)
        q = self.session.query(geo_func.ST_Y(Tweet.geom), geo_func.ST_X(Tweet.geom)).filter(Tweet.created_at > hour_ago).all()
        return q
        
    # Get Last Tweets
    # Returns tweets from the past hour throughout the entire AOI
    def get_last_tweets(self):
        hour_ago = datetime.utcnow() - timedelta(hours=1)
        q = self.session.query(Tweet).filter(Tweet.created_at > hour_ago).all()
        return q

    # Returns a list of all division ids
    def get_division_ids(self):
        ids = self.session.query(Division.id).all()
        return map(lambda x: x[0], ids)

    '''
        Get Division Chloropleth
        
        The queries return an hourly list containing tweet activity throughout
        the entire hour, and for each division per hour. It's essentially:
        
        with hour_count as (
            select date_trunc('hour', created_at) as hour,
            count(*) over (partition by date_trunc('hour', created_at)) as count_all,
            division_id from tweets.tweets
            where created_at > now() - interval '1 week'
        ),
        select distinct
            hour,
            division_id,
            count_all,
            count(*) over (partition by division_id, hour) as div_count,
            from hour_count
            order by hour desc, division_id;
    '''
    def get_division_chloropleth(self):
        
        # Search back 1 week
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        # Truncate the hour
        hour_f = func.date_trunc('hour', Tweet.created_at)
        
        sq = self.session.query(
            hour_f.label('hour'),
            func.count('*').over(partition_by=hour_f).label('count_all'),
            Tweet.division_id).\
            filter(Tweet.created_at > week_ago).\
            subquery()
        
        # Use sq.c to access columns
        return self.session.query(
            sq.c.hour,
            sq.c.division_id,
            sq.c.count_all,
            func.count('*').over(partition_by=[sq.c.division_id, sq.c.hour]).label('div_count')).\
            order_by(sq.c.hour.desc(), sq.c.division_id).\
            distinct().all()

