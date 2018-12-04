from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from flask_security import Security, SQLAlchemyUserDatastore, login_required
from flask_security.decorators import auth_token_required
from flask_graphql import GraphQLView

from app.routes import ROUTES
from app.config import Config
from app.models import DB, User
from app.schema import SCHEMA
from app.forms import ArtswipeRegisterForm


def setup_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config.from_envvar('ARTSWIPE_CONFIG', silent=True)
    app.template_folder = app.config.get('TEMPLATE_FOLDER')
    graphql_view = GraphQLView.as_view('graphql',
                                       schema=SCHEMA,
                                       graphiql=False)
    app.add_url_rule('/graphql', view_func=auth_token_required(graphql_view))
    graphiql_view = GraphQLView.as_view('graphqli',
                                        schema=SCHEMA,
                                        graphiql=True)
    app.add_url_rule('/graphiql', view_func=login_required(graphiql_view))
    CORS(app)
    DB.init_app(app)
    app.register_blueprint(ROUTES)
    return app


def setup_migrate(app):
    return Migrate(app, DB)


def setup_security(app):
    user_datastore = SQLAlchemyUserDatastore(DB, User, None)
    security = Security(app, user_datastore,
                        register_form=ArtswipeRegisterForm,
                        confirm_register_form=ArtswipeRegisterForm)
    return security
