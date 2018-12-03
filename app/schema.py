import graphene
from graphene import relay
from graphene_sqlalchemy import SQLAlchemyObjectType

from random import randint

import app.models as models
import app.api as api


class Match(graphene.ObjectType):
    id = graphene.NonNull(graphene.ID)
    author = graphene.NonNull(lambda: User)
    matchUser = graphene.NonNull(lambda: User)
    seen = graphene.NonNull(graphene.Boolean)
    read = graphene.NonNull(graphene.Boolean)
    createdAt = graphene.NonNull(graphene.Int)


class User(SQLAlchemyObjectType):
    class Meta:
        model = models.User


class CultureItem(SQLAlchemyObjectType):
    class Meta:
        model = models.CultureItem


class Swipe(SQLAlchemyObjectType):
    class Meta:
        model = models.Swipe


class SwipeCulture(graphene.Mutation):
    class Arguments:
        user = graphene.NonNull(graphene.ID)
        culture = graphene.NonNull(graphene.ID)
        choice = graphene.NonNull(graphene.Boolean)

    ok = graphene.Boolean()

    def mutate(self, info, user, culture, choice):
        swipe = models.Swipe(culture_item_id=culture,
                             user_id=user, choice=choice)
        models.DB.session.add(swipe)
        models.DB.session.commit()
        ok = True
        return SwipeCulture(ok=ok)


class Mutation(graphene.ObjectType):
    swipe_culture = SwipeCulture.Field()


class Query(graphene.ObjectType):
    user = graphene.Field(User, id=graphene.ID())
    matches = graphene.List(Match, author=graphene.ID())
    culture = graphene.List(
        CultureItem, user=graphene.ID(), count=graphene.Int())
    swipes = graphene.List(Swipe, user=graphene.ID())

    def resolve_user(self, info):
        query = User.get_query(info)
        return query.one()

    def resolve_culture(self, info, count=None, user=None):
        if count is None:
            count = 1
        swiped = CultureItem.get_query(info).join(models.Swipe).filter_by(
            user_id=user).limit(randint(0, count)).all()
        sampled = api.get_culture_items(user, count - len(swiped))
        models.DB.session.add_all(sampled)
        models.DB.session.commit()
        return swiped + sampled

    def resolve_matches(self, info):
        return []

    def resolve_swipes(self, info, user):
        return Swipe.get_query(info).filter_by(user_id=user).all()


SCHEMA = graphene.Schema(query=Query, mutation=Mutation)
