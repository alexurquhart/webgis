import os

SCHEMA = "tweets"
if "SCHEMA" in os.environ:
    SCHEMA = os.environ["SCHEMA"]