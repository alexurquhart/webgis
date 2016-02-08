from app import config
from app.app import application
import os

if __name__ == "__main__":
    application.config['DEBUG'] = config.DEBUG
    application.run(host='0.0.0.0', port=6060)