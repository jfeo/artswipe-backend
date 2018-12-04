"""artswipe backend
author: jfeo
email: jensfeodor@gmail.com
"""
from flask import request, Blueprint, jsonify
from flask_security import auth_token_required

from .schema import SCHEMA

ROUTES = Blueprint('routes', __name__)


@ROUTES.errorhandler(500)
def internal_server_error(error):
    """Send json on status 500."""
    return jsonify({"msg": str(error), "error": str(type(error))}), 500
