"""artswipe backend
author: jfeo
email: jensfeodor@gmail.com
"""
from flask_graphql import GraphQLView
from flask import Blueprint, jsonify

from .schema import SCHEMA

ROUTES = Blueprint('routes', __name__)


#@ROUTES.route('/graphql')
#def route_graphql():
#    return GraphQLView.as_view('graphql', schema=SCHEMA, graphiql=True)


@ROUTES.errorhandler(500)
def internal_server_error(error):
    """Send json on status 500."""
    return jsonify({"msg": str(error), "error": str(type(error))}), 500
