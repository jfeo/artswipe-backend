from flask_security import UserMixin

from datetime import datetime
from app import DB


class User(DB.Model, UserMixin):
    id = DB.Column(DB.Integer, primary_key=True)
    first = DB.Column(DB.String(64))
    last = DB.Column(DB.String(64))
    email = DB.Column(DB.String(255), unique=True, index=True)
    active = DB.Column(DB.Boolean, index=True)
    confirmed_at = DB.Column(DB.DateTime)
    swipes = DB.relationship('Swipe', backref='user', lazy='dynamic')

    def __repr__(self):
        return f"<User {self.id} {self.email}>"


class Asset(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    local_id = DB.Column(DB.String(128))
    title = DB.Column(DB.String(128))
    image = DB.Column(DB.LargeBinary)
    upvotes = DB.Column(DB.Integer)
    downvotes = DB.Column(DB.Integer)
    swipes = DB.relationship('Swipe', backref='asset', lazy='dynamic')

    def __repr__(self):
        return f"<Asset {self.id}>"


class Swipe(DB.Model):
    asset_id = DB.Column(
        DB.Integer, DB.ForeignKey('asset.id'), primary_key=True)
    user_id = DB.Column(DB.Integer, DB.ForeignKey('user.id'), primary_key=True)
    choice = DB.Column(DB.Boolean, index=True)
    timestamp = DB.Column(DB.DateTime, index=True, default=datetime.utcnow())

    def __repr__(self):
        return f"<Swipe {self.asset} {self.user} {self.choice}>"
