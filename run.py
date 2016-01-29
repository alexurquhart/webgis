from app.app import application
import os

if __name__ == "__main__":
    debug = False
    if "DEBUG" in os.environ and int(os.environ["DEBUG"]):
        debug = True
    
    application.config['DEBUG'] = debug
    application.run(host='0.0.0.0', port=6060)