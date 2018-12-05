import graphene
from graphene_sqlalchemy import SQLAlchemyObjectType
from sqlalchemy import and_
from flask_security.forms import LoginForm
from werkzeug.datastructures import MultiDict
from graphql.error import GraphQLError
from flask_login import current_user
from flask import current_app

from random import randint

import app.models as models
import app.api as api
from app.security import USER_DATASTORE, AuthError, get_user_or_error


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


class AuthorizedSwipe(graphene.Union):
    class Meta:
        types = [Swipe, AuthError]


class SwipeCulture(graphene.Mutation):
    class Arguments:
        token = graphene.NonNull(graphene.String)
        culture = graphene.NonNull(graphene.ID)
        choice = graphene.NonNull(graphene.Boolean)

    Output = AuthorizedSwipe

    def mutate(self, info, token, culture, choice):
        auth = get_user_or_error(token)
        if isinstance(auth, AuthError):
            return auth
        user = auth
        swipe = models.Swipe(culture_item_id=culture,
                             user_id=user.id, choice=choice)
        models.DB.session.add(swipe)
        models.DB.session.commit()
        return swipe


class CreateUserError(graphene.ObjectType):
    message = graphene.String(required=True)


class CreateUserResult(graphene.Union):
    class Meta:
        types = [User, CreateUserError]


class CreateUser(graphene.Mutation):
    class Arguments:
        first_name = graphene.NonNull(graphene.String)
        last_name = graphene.NonNull(graphene.String)
        email = graphene.NonNull(graphene.String)
        password = graphene.NonNull(graphene.String)

    Output = CreateUserResult

    def mutate(self, info, first_name, last_name, email, password):
        try:
            user = USER_DATASTORE.create_user(email=email,
                                              password=password,
                                              first_name=first_name,
                                              last_name=last_name)
            models.DB.session.commit()
            return user
        except:
            return CreateUserError(message="Could not create user")


class AuthToken(graphene.ObjectType):
    value = graphene.String(required=True)


class AuthorizedUser(graphene.Union):
    class Meta:
        types = [User, AuthError]


class AuthorizedToken(graphene.Union):
    class Meta:
        types = [AuthToken, AuthError]


class MatchList(graphene.ObjectType):
    matches = graphene.List(Match)


class SwipeList(graphene.ObjectType):
    swipes = graphene.List(Swipe)


class CultureList(graphene.ObjectType):
    items = graphene.List(CultureItem, required=True)


class AuthorizedMatches(graphene.Union):
    class Meta:
        types = [MatchList, AuthError]


class AuthorizedCultureItems(graphene.Union):
    class Meta:
        types = [CultureList, AuthError]


class AuthorizedSwipes(graphene.Union):
    class Meta:
        types = [SwipeList, AuthError]


class ObtainToken(graphene.Mutation):
    class Arguments:
        email = graphene.String(required=True)
        password = graphene.String(required=True)

    Output = AuthorizedToken

    def mutate(self, info, email, password):
        form = LoginForm(formdata=MultiDict(
            [('email', email), ('password', password)]))
        if form.validate():
            token = current_app.extensions.get(
                'security').login_serializer.dumps([str(form.user.id)])
            return AuthToken(value=token)
        else:
            raise AuthError(message="Authorization failed")


class Mutation(graphene.ObjectType):
    swipe_culture = SwipeCulture.Field()
    create_user = CreateUser.Field()
    obtain_token = ObtainToken.Field()


class Query(graphene.ObjectType):
    user = graphene.Field(AuthorizedUser, token=graphene.String(required=True))
    matches = graphene.Field(
        AuthorizedMatches, token=graphene.String(required=True))
    culture = graphene.Field(AuthorizedCultureItems, count=graphene.Int(
    ), token=graphene.String(required=True))
    swipes = graphene.Field(
        AuthorizedSwipes, token=graphene.String(required=True))

    def resolve_user(self, info, token=None):
        query = User.get_query(info)
        return query.one()

    def resolve_culture(self, info, count=None, token=None):
        if count is None:
            count = 1
        auth = get_user_or_error(token)
        if isinstance(auth, AuthError):
            return auth
        user = auth
        q = CultureItem.get_query(info)
        q = q.join(models.Swipe)
        q = q.filter_by(user_id=user.id)
        q = q.limit(randint(0, count))
        swiped = q.all()
        sampled = api.get_culture_items(user, count - len(swiped))
        models.DB.session.add_all(sampled)
        models.DB.session.commit()
        return CultureList(items=swiped+sampled)

    def resolve_matches(self, info, author, token=None):
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
        return MatchList(matches=matches)

    def resolve_swipes(self, info, token=None):
        return SwipeList(swipes=Swipe.get_query(info).all())


SCHEMA = graphene.Schema(query=Query, mutation=Mutation)
