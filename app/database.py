from sqlalchemy import create_engine, distinct, func, desc
from sqlalchemy.orm import sessionmaker
from geoalchemy2 import functions as geo_func
from datetime import datetime, timedelta
import config
from base import Base
from schema import Tweet, Hashtag, Picture, Division
import codecs, json

class Database:
    def __init__(self, uri, debug=False, drop_all=config.TRUNCATE_TABLES, divisions_file="data/divisions.json"):
        self.__debug = debug
        self.__engine = create_engine(uri, echo=debug, client_encoding='utf8')
        self.__base = Base
        
        # Drop all if debugging
        if drop_all:
            self.__base.metadata.drop_all(self.__engine)
        
        self.__base.metadata.create_all(self.__engine)
        self.session = sessionmaker(bind=self.__engine)()

        # Load all divisions from GeoJSON if debugging, and all tables were dropped
        count = self.session.query(func.count(Division.id)).scalar()
        if count == 0:
            features = self.load_geojson(divisions_file)
            self.create_divisions(features)
        
    # Given a filename, opens the file and parses the GeoJSON,
    # returning the array of geojson feature objects
    def load_geojson(self, filename):
        with codecs.open(filename, 'r', "utf-8") as file:
            gj = file.read()
            file.close()
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
    
    def close(self):
        self.__engine.dispose()

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
            if tweet.screen_name[0].lower().startswith(name.lower()):
                return True
                
        for name in config.BLACKLIST_SCREENNAMES_ENDSWITH:
            if tweet.screen_name[0].lower().endswith(name.lower()):
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
    # Returns geometry for all tweets recorded in the past day
    def get_heatmap_geom(self):
        hour_ago = datetime.now() - timedelta(hours=24)
        q = self.session.query(geo_func.ST_Y(Tweet.geom), geo_func.ST_X(Tweet.geom)).filter(Tweet.created_at > hour_ago).all()
        return q
        
    # Get Last Tweets
    # Returns tweets from the past hour throughout the entire AOI
    def get_last_tweets(self):
        hour_ago = datetime.now() - timedelta(hours=1)
        q = self.session.query(Tweet).filter(Tweet.created_at > hour_ago).all()
        return q

    # Returns a list of all division ids
    def get_division_ids(self):
        ids = self.session.query(Division.id).all()
        return map(lambda x: x[0], ids)

    '''
    with series as (
        select * from generate_series(
        date_trunc('hour', now() - interval '1 week'),
        now(),
        interval '1 hour') time
    ), tw_count as (
        select distinct date_trunc('hour', created_at) as time,
        count(*) over (partition by date_trunc('hour', created_at))
        from tweets.tweets
        where created_at > now() - interval '1 week'
        and division_id = 77
    )
    select series.time,
    coalesce(tw_count.count, 0) as count
    from series
    left join tw_count on (tw_count.time = series.time);
    '''
    def get_tweet_counts_by_division(self, div_id=None):
        series = self.session.query(
            func.generate_series(
            func.date_trunc('hour', datetime.utcnow() - timedelta(hours=24)),
            datetime.utcnow(),
            timedelta(hours=1)).label('time')).subquery()
        tw_count = self.session.query(
            func.date_trunc('hour', Tweet.created_at).label('time'),
            func.count('*').over(partition_by=func.date_trunc('hour', Tweet.created_at)).label('count')).\
            filter(Tweet.created_at > datetime.utcnow() - timedelta(hours=24)).\
            distinct()

        if div_id != None:
            tw_count = tw_count.filter(Tweet.division_id == div_id)

        tw_count = tw_count.subquery()

        res = self.session.query(
            series.c.time,
            func.coalesce(tw_count.c.count, 0).label('count')).\
            select_from(series).\
            outerjoin(tw_count, tw_count.c.time == series.c.time).all()

        return map(lambda x: { "time": x[0].isoformat(), "count": x[1] }, res)

    # Get pictures in extent
    # Takes in lat/long bounding box and returns pictures that have been taken there in the past week
    def get_pictures_in_extent(self, sw_lat, sw_long, ne_lat, ne_long):
        wkt = "SRID=4326;POLYGON(({} {}, {} {}, {} {}, {} {}, {} {}))".format(ne_long, ne_lat, sw_long, ne_lat, sw_long, sw_lat, ne_long, sw_lat, ne_long, ne_lat)
        pics = self.session.query(Picture).join(Tweet).filter(geo_func.ST_Within(Tweet.geom, wkt)).order_by(Tweet.created_at.desc()).limit(10)
        return pics
        