import graphene
from graphene import relay
from graphene_sqlalchemy import SQLAlchemyObjectType

import app.models as models


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


class Query(graphene.ObjectType):
    user = graphene.Field(User, id=graphene.ID())
    matches = graphene.List(Match, author=graphene.ID())
    culture = graphene.List(CultureItem, count=graphene.Int())

    def resolve_user(self, info):
        query = User.get_query(info)
        return query.one()

    def resolve_culture(self, info, count=None):
        if count is None:
            return CultureItem.get_query(info).first()
        else:
            query = CultureItem.get_query(info).limit(count)
            return query.all()

    def resolve_matches(self, info):
        return []


SCHEMA = graphene.Schema(query=Query)
