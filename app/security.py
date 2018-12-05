from flask import request, current_app
from flask_security import Security, SQLAlchemyUserDatastore, login_required
from flask_security.utils import get_token_status

from app.models import DB, User
from app.forms import ArtswipeRegisterForm
from graphql import GraphQLError
import graphene


USER_DATASTORE = SQLAlchemyUserDatastore(DB, User, None)
SECURITY = Security(register_form=ArtswipeRegisterForm,
                    confirm_register_form=ArtswipeRegisterForm)


class AuthError(graphene.ObjectType):
    message = graphene.String(required=True)


def get_user_or_error(token):
    expired, invalid, user = get_token_status(token, 'login', 'LOGIN')
    if expired:
        return AuthError(message='authentication token expired')
    if invalid:
        return AuthError(message='authentication token invalid')
    return user
