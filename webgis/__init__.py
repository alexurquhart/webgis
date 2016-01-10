from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from webgis import twitter.Base
import os

debug = False
if os.getenv("DEBUG"):
    debug = True

engine = create_engine(os.getenv("DBURL"), echo=debug, client_encoding='utf8')
Session = sessionmaker(bind=engine)

if debug:
    Base.metadata.drop_all(engine)

Base.metadata.create_all(engine)
