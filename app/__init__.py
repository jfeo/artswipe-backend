from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from config import Config

APP = Flask(__name__)
APP.config.from_object(Config)
APP.config.from_envvar('ARTSWIPE_CONFIG', silent=True)

CORS(APP)
DB = SQLAlchemy(APP)
MIGRATE = Migrate(APP, DB)

from app import models, routes
