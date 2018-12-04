import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    SECRET_KEY = 'super-secret'
    SECURITY_REGISTERABLE = True
    SECURITY_SEND_REGISTER_EMAIL = False
    SECURITY_CONFIRMABLE = False
    SECURITY_TOKEN_AUTHENTICATION_KEY = 'token'
    SECURITY_PASSWORD_SALT = 'bla'
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'ARTSWIPE_DB_URL') or 'sqlite:///' + os.path.join(basedir, 'db.sqlite3')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TEMPLATE_FOLDER = 'templates'
