from flask_sqlalchemy import SQLAlchemy
from flask_security import UserMixin

from datetime import datetime


DB = SQLAlchemy()


class Swipe(DB.Model):
    culture_item_id = DB.Column(
        DB.Integer, DB.ForeignKey('culture_item.id'), primary_key=True)
    user_id = DB.Column(DB.Integer, DB.ForeignKey('user.id'), primary_key=True)
    choice = DB.Column(DB.Boolean, index=True)
    timestamp = DB.Column(DB.DateTime, index=True, default=datetime.utcnow())
    user = DB.relationship('User', back_populates='swipes')
    culture_item = DB.relationship('CultureItem', back_populates='swipes')

    def __repr__(self):
        return f"<Swipe {self.culture_item} {self.user} {self.choice}>"


class User(DB.Model, UserMixin):
    id = DB.Column(DB.Integer, primary_key=True)
    first_name = DB.Column(DB.String(64))
    last_name = DB.Column(DB.String(64))
    email = DB.Column(DB.String(255), unique=True, index=True)
    facebook_linked = DB.Column(DB.Boolean)
    google_linked = DB.Column(DB.Boolean)
    avatar_url = DB.Column(DB.String(255))
    swipes = DB.relationship('Swipe', back_populates='user')

    def __repr__(self):
        return f"<User {self.id} {self.email}>"


class CultureItem(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    local_id = DB.Column(DB.String(128))
    title = DB.Column(DB.String(128))
    image = DB.Column(DB.LargeBinary)
    upvotes = DB.Column(DB.Integer)
    downvotes = DB.Column(DB.Integer)
    swipes = DB.relationship('Swipe', back_populates='culture_item')

    def __repr__(self):
        return f"<Asset {self.id}>"
