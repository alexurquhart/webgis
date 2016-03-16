from app import config
from app.database import database
from app.database.schema import Tweet, Division, Hashtag, Picture
from datetime import datetime
import os, json

db = database.Database(config.DBURI)