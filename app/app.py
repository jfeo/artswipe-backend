from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from flask_security import Security, SQLAlchemyUserDatastore

from app.routes import ROUTES
from app.config import Config
from app.models import DB, User


def setup_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config.from_envvar('ARTSWIPE_CONFIG', silent=True)
    CORS(app)
    DB.init_app(app)
    app.register_blueprint(ROUTES)
    return app


def setup_migrate(app):
    return Migrate(app, DB)


def setup_security(app):
    user_datastore = SQLAlchemyUserDatastore(DB, User, None)
    return Security(app, user_datastore)
