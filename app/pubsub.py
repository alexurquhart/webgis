from redis_conn import Redis as R
from sys import stdout
import json, time

class PubSub:
    def __init__(self, channel="tweets"):
        self.__P = R.pubsub(ignore_subscribe_messages=True)
        self.__channel = channel
    
    # Publish tweet to subscribers
    def publish(self, tweet):
        ser = tweet.serialized
        ser["online_count"] = R.execute_command("PUBSUB", "NUMSUB", self.__channel)
        data = json.dumps(ser, ensure_ascii=False)
        R.publish(self.__channel, data)
    
    # Listen for incoming data and print to stdout
    # Pause is the time between attempts to retreive messages
    def listen(self, pause=0.1):
        self.__P.subscribe(self.__channel)
        while True:
            message = self.__P.get_message()
            if message:
                print message["data"]
                stdout.flush()
            time.sleep(pause)