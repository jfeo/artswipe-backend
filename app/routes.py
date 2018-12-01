"""artswipe backend
author: jfeo
email: jensfeodor@gmail.com
"""
import random
import pymysql

from flask import jsonify, request

from app import APP
from app import api

CONNECTION = None

APIS = {"natmus": api.Natmus()}


def get_connection():
    """Get a connection to the database."""
    global CONNECTION
    if not CONNECTION:
        CONNECTION = pymysql.connect(
            host='db',
            user='asadmin',
            password='asrocks',
            charset='utf8',
            database="artswipe",
            autocommit=True)
    CONNECTION.ping(reconnect=True)
    return CONNECTION


def get_swiped_culture(user):
    """Get a culture item that has been swiped already by another user."""
    with get_connection().cursor() as cur:
        cur.execute(
            "SELECT a.id, a.title FROM `assets` a "
            "RIGHT JOIN `swipes` s ON s.asset_id = a.id "
            "GROUP BY a.`id`, a.title HAVING SUM(s.user_uuid = %s) = 0 "
            "ORDER BY rand() LIMIT 1", user)
        result = cur.fetchone()
        if result is not None:
            return {"asset_id": result[0], "title": result[1]}
        return None


def user_has_asset(user, asset_id):
    """Check if the given user has the given asset."""
    with get_connection().cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM swipes "
            "WHERE user_uuid = %s AND asset_id = %s LIMIT 1", (user, asset_id))
        [count] = cur.fetchone()
        return count > 0


def get_asset(asset_id):
    """Get the asset."""
    with get_connection().cursor() as cur:
        cur.execute("SELECT * FROM assets WHERE id = %s LIMIT 1", (asset_id))
        asset = cur.fetchone()
        return {"asset_id": asset[0], "title": asset[1]}


def get_random_culture():
    """Get a culture item by random sampling."""
    with get_connection().cursor() as cur:
        result = None
        while result is None:
            cur.execute("SELECT a.* FROM assets a "
                        "LEFT JOIN swipes s ON a.id = s.asset_id "
                        "WHERE s.asset_id IS NULL ORDER BY rand() LIMIT 1")
            result = cur.fetchone()
            if result is None:
                [api] = random.sample(list(APIS.values()), 1)
                api.fetch_assets()
            else:
                return {"asset_id": result[0], "title": result[1]}


@APP.route('/culture', methods=['GET'])
def route_culture():
    """Get a culture."""
    user = request.args.get('user')
    if user is None:
        return jsonify({"msg": "must log in"}), 401
    count = request.args.get('count')
    if count is None:
        count = 1
    else:
        count = int(count)
    assets = []
    for _ in range(count):
        if random.randint(0, 1) == 0:
            asset = get_random_culture()
        else:
            asset = get_swiped_culture(user)
            if asset is None:
                asset = get_random_culture()
        assets.append(asset)
    return jsonify(assets), 200


@APP.route('/choose', methods=['GET'])
def route_choose():
    """The user makes a choice on an asset."""
    user = request.args.get('user')
    asset_id = request.args.get('asset_id')
    choice = request.args.get('choice')
    if any(map(lambda arg: arg is None, [user, asset_id, choice])):
        return jsonify({"msg": "parameter missing"}), 401
    try:
        get_asset(asset_id)
    except ValueError:
        return jsonify({"msg": "invalid asset_id"}), 401
    with get_connection().cursor() as cur:
        cur.execute(
            "INSERT INTO `swipes` (user_uuid, asset_id, choice)"
            "VALUES (%s, %s, %s)", (user, asset_id, choice))
        if choice == "true":
            cur.execute(
                "UPDATE assets SET upvotes = upvotes + 1 "
                "WHERE id = %s", (asset_id))
        else:
            cur.execute(
                "UPDATE assets SET downvotes = downvotes + 1 "
                "WHERE id = %s", (asset_id))
    return jsonify({"msg": "choice made"}), 200


@APP.route('/match', methods=['GET'])
def route_match():
    """Match route"""
    user = request.args.get('user')
    if user is None:
        return jsonify({"msg": f"user missing"}), 401
    with get_connection().cursor() as cur:
        cur.execute(
            "SELECT s2.user_uuid FROM swipes s1 "
            "JOIN swipes s2 ON s1.asset_id = s2.asset_id "
            "WHERE s1.user_uuid = %s AND s2.user_uuid != %s "
            "GROUP BY s2.user_uuid "
            "HAVING SUM(s1.choice = s2.choice) - "
            "SUM(s1.choice != s2.choice) > 2 "
            "ORDER BY SUM(s1.choice = s2.choice) - "
            "SUM(s1.choice != s2.choice)", (user, user))
        matches = list(map(lambda val: val[0], cur.fetchall()))
        return jsonify(matches), 200


@APP.route('/image', methods=['GET'])
def route_image():
    asset_id = request.args.get('asset_id')
    if asset_id is None:
        return jsonify({"msg": "missing asset_id"}), 200
    with get_connection().cursor() as cur:
        cur.execute(
            "SELECT image FROM assets "
            "WHERE id = %s AND image IS NOT NULL LIMIT 1", (asset_id))
        result = cur.fetchone()
        if result is None:
            APIS[(asset_id).split("-")[0]].fetch_image(asset_id)
            cur.execute(
                "SELECT image FROM assets "
                "WHERE id = %s AND image is NOT NULL LIMIT 1", (asset_id))
            result = cur.fetchone()
        image = result[0]
        return image, 200, {"Content-Type": "image/jpeg"}


@APP.route('/suggest', methods=['GET'])
def route_suggest():
    """Get a suggestion based on a match."""
    user = request.args.get('user')
    match = request.args.get('match')
    if user is None or match is None:
        return jsonify({"msg": "must have user and match"}), 401
    return jsonify({"msg": "not yet implemented"}), 500


@APP.errorhandler(500)
def internal_server_error():
    """Send json on status 500."""
    return jsonify({"msg": f"an internal server error happened. sorry!"}), 500
