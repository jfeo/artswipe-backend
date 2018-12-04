import graphene
from graphene_sqlalchemy import SQLAlchemyObjectType
from sqlalchemy import and_
from flask_security.forms import LoginForm
from werkzeug.datastructures import MultiDict

from random import randint

import app.models as models
import app.api as api
from app.security import USER_DATASTORE, AuthError


class Match(graphene.ObjectType):
    author = graphene.NonNull(lambda: User)
    match_user = graphene.NonNull(lambda: User)
    seen = graphene.NonNull(graphene.Boolean)
    read = graphene.NonNull(graphene.Boolean)
    created_at = graphene.NonNull(graphene.Int)


class User(SQLAlchemyObjectType):
    class Meta:
        model = models.User
        exclude_fields = ['password']


class CultureItem(SQLAlchemyObjectType):
    class Meta:
        model = models.CultureItem


class Swipe(SQLAlchemyObjectType):
    class Meta:
        model = models.Swipe
        exclude_fields = ['culture_item_id', 'user_id']


class SwipeCulture(graphene.Mutation):
    class Arguments:
        user = graphene.NonNull(graphene.ID)
        culture = graphene.NonNull(graphene.ID)
        choice = graphene.NonNull(graphene.Boolean)

    Output = Swipe

    def mutate(self, info, user, culture, choice):
        swipe = models.Swipe(culture_item_id=culture,
                             user_id=user, choice=choice)
        models.DB.session.add(swipe)
        models.DB.session.commit()
        return swipe


class CreateUser(graphene.Mutation):
    class Arguments:
        first_name = graphene.NonNull(graphene.String)
        last_name = graphene.NonNull(graphene.String)
        email = graphene.NonNull(graphene.String)
        password = graphene.NonNull(graphene.String)

    Output = User

    def mutate(self, info, first_name, last_name, email, password):
        user = USER_DATASTORE.create_user(email=email,
                                          password=password,
                                          first_name=first_name,
                                          last_name=last_name)
        models.DB.session.commit()
        return user


auth_unions = {}


def auth_error_union(*types_):
    _types = list(types_) + [AuthError]

    name = "Union"
    for t in _types:
        if hasattr(t, '_meta'):
            name += t._meta.name
        else:
            name += t.__class__.__name__

    if name in auth_unions:
        return auth_unions[name]

    class _Union(graphene.Union):
        class Meta:
            types = _types

    _Union.__name__ = name
    auth_unions[name] = _Union
    return _Union


class AuthToken(graphene.ObjectType):
    value = graphene.String(required=True)


class AuthTokenError(graphene.Union):
    class Meta:
        types = [AuthToken, AuthError]


class ObtainToken(graphene.Mutation):
    class Arguments:
        email = graphene.String(required=True)
        password = graphene.String(required=True)

    Output = AuthTokenError

    def mutate(self, info, email, password):
        form = LoginForm(formdata=MultiDict(
            [('email', email), ('password', password)]))
        if form.validate():
            return AuthToken(value=form.user.get_auth_token())
        else:
            raise AuthError(message="Could not authorize")


class VerifyToken(graphene.Mutation):
    class Arguments:
        token = graphene.String(required=True)

    Output = auth_error_union(AuthToken)

    def mutate(self, info, token):
        return AuthError(message="Not authorized")


class RefreshToken(graphene.Mutation):
    class Arguments:
        auth_token = graphene.String(required=True)

    Output = auth_error_union(AuthToken)

    def mutate(self, info, token):
        return AuthError(message="Not authorized")


class Mutation(graphene.ObjectType):
    swipe_culture = SwipeCulture.Field()
    create_user = CreateUser.Field()
    obtain_token = ObtainToken.Field()
    verify_token = VerifyToken.Field()
    refresh_token = RefreshToken.Field()


class Query(graphene.ObjectType):
    user = auth_error_union(User)
    matches = auth_error_union(graphene.List(Match))
    culture = auth_error_union(graphene.List(
        CultureItem, count=graphene.Int()))
    swipes = auth_error_union(graphene.List(
        Swipe, user=graphene.ID()))

    def resolve_user(self, info):
        query = User.get_query(info)
        return query.one()

    def resolve_culture(self, info, count=None, user=None):
        if count is None:
            count = 1
        q = CultureItem.get_query(info)
        q = q.join(models.Swipe)
        q = q.filter_by(user_id=user)
        q = q.limit(randint(0, count))
        swiped = q.all()
        sampled = api.get_culture_items(user, count - len(swiped))
        models.DB.session.add_all(sampled)
        models.DB.session.commit()
        return swiped + sampled

    def resolve_matches(self, info, author):
        swipe = models.DB.aliased(models.Swipe)
        other_swipe = models.DB.aliased(models.Swipe)
        user = models.DB.aliased(models.User)
        other_user = models.DB.aliased(models.User)
        q = models.DB.session.query(swipe, other_user)
        q = q.join(other_swipe, swipe.culture_item_id ==
                   other_swipe.culture_item_id)
        q = q.join(user, swipe.user_id == user.id)
        q = q.join(other_user, other_swipe.user_id == other_user.id)
        q = q.filter(and_(user.id == author, other_user.id != user.id))
        q = q.group_by(other_swipe.user_id)
        agree = models.DB.func.sum(swipe.choice == other_swipe.choice)
        disagree = models.DB.func.sum(swipe.choice != other_swipe.choice)
        q = q.order_by(agree - disagree)
        matches = [Match(author=swipe.user, match_user=match_user, read=False,
                         seen=False, created_at=0) for (swipe, match_user) in q.all()]
        return matches

    def resolve_swipes(self, info, user):
        return Swipe.get_query(info).filter_by(user_id=user).all()


SCHEMA = graphene.Schema(query=Query)
