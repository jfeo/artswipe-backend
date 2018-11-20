"""artswipe backend
author: jfeo
email: jensfeodor@gmail.com
"""
import random
import json
import requests
import pymysql

from flask import Flask, request
from flask_cors import CORS
APP = Flask(__name__)
CORS(APP)

class NatmusAPI(object):

    def __init__(self):
        self.url = "https://api.natmus.dk/search/public/raw"


connection = pymysql.connect(
    host='localhost',
    user='asadmin',
    password='asrocks',
    charset='utf8',
    database="artswipe",
    autocommit=True)


def get_connection():
    connection.ping(reconnect=True)
    return connection


def send_json(obj, status_code, headers={}):
    """Create the response tuple with, automatically dumping the given object
    to a json string, and setting the Content-Type header appropriately.
    """
    headers['Content-Type'] = 'application/json'
    return json.dumps(obj), status_code, headers


def get_swiped_culture(user, k=10):
    """Get a culture item that has been swiped already by another user."""
    with get_connection().cursor() as cur:
        cur.execute(
            "SELECT a.* FROM `swipes` s "
            "LEFT JOIN assets a ON s.asset_id = a.id "
            "GROUP BY s.`asset_id` HAVING SUM(s.user_uuid = %s) = 0 "
            "ORDER BY rand() LIMIT 1", user)
        result = cur.fetchone()
        if result is not None:
            return {
                "asset_id": result[0],
                "title": result[1],
                "thumb": result[2]
            }
        else:
            return None


def get_asset_info(asset_id):
    """Get asset information"""
    _id = asset_id[6:]
    es_data = {
        "query": {
            "constant_score": {
                "filter": {
                    "bool": {
                        "must": [{
                            "term": {
                                "_id": _id
                            }
                        }, {
                            "term": {
                                "type": "asset"
                            }
                        }]
                    }
                }
            }
        }
    }
    req = requests.post(
        NATMUS_API_SEARCH,
        data=json.dumps(es_data),
        headers={"Content-Type": "application/json"})
    result = req.json()
    return result['hits']['hits'][0]['_source']


def natmus_transform_result(hit):
    """Transform search result"""
    asset = {}
    asset['id'] = hit['_source']['id']
    asset['collection'] = hit['_source']['collection']
    asset['asset_id'] = f"natmus-{asset['collection']}-{asset['id']}"
    asset['title'] = hit['_source']['text']['da-DK']['title']
    asset['thumb'] = (f"http://samlinger.natmus.dk/{asset['collection']}"
                      f"/asset/{asset['id']}/thumbnail/500")
    return asset


def fetch_assets():
    """Fill the asset queue with randomly sampled assets."""
    es_data = {
        "size": 100,
        "query": {
            "bool": {
                "filter": {
                    "term": {
                        "type": "asset"
                    }
                },
                "should": {
                    "function_score": {
                        "functions": [{
                            "random_score": {
                                "seed": random.randint(1, 2 ^ 32 - 1)
                            }
                        }],
                        "score_mode":
                        "sum"
                    }
                }
            }
        }
    }
    req = requests.post(
        NATMUS_API_SEARCH,
        data=json.dumps(es_data),
        headers={"Content-Type": "application/json"})
    results = req.json()
    assets = list(map(natmus_transform_result, results['hits']['hits']))
    with get_connection().cursor() as cur:
        cur.executemany(
            "INSERT IGNORE INTO assets (id, title, thumb) "
            "VALUES (%(asset_id)s, %(title)s, %(thumb)s)", assets)


def user_has_asset(user, asset_id):
    with get_connection().cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM swipes "
            "WHERE user_uuid = %s AND asset_id = %s LIMIT 1", (user, asset_id))
        [count] = cur.fetchone()
        return count > 0


def get_asset(asset_id):
    with get_connection().cursor() as cur:
        print(asset_id, flush=True)
        cur.execute("SELECT * FROM assets WHERE id = %s LIMIT 1", (asset_id))
        asset = cur.fetchone()
        return {"asset_id": asset[0], "title": asset[1], "thumb": asset[2]}


def get_random_culture(user):
    """Get a culture item by random sampling."""
    with get_connection().cursor() as cur:
        result = None
        while result is None:
            cur.execute("SELECT a.* FROM assets a "
                        "LEFT JOIN swipes s ON a.id = s.asset_id "
                        "WHERE s.asset_id IS NULL ORDER BY rand() LIMIT 1")
            result = cur.fetchone()
            if result is None:
                fetch_assets()
            else:
                return {
                    "asset_id": result[0],
                    "title": result[1],
                    "thumb": result[2]
                }


@APP.route('/culture', methods=['GET'])
def route_culture():
    """Get a culture."""
    user = request.args.get('user')
    if user is None:
        return send_json({"msg": "must log in"}, 401)
    count = request.args.get('count')
    if count is None:
        count = 1
    else:
        count = int(count)
    assets = []
    for _ in range(count):
        if random.randint(0, 1) == 0:
            asset = get_random_culture(user)
        else:
            asset = get_swiped_culture(user)
            if asset is None:
                asset = get_random_culture(user)
        assets.append(asset)
    return send_json(assets, 200)


@APP.route('/choose', methods=['GET'])
def route_choose():
    """The user makes a choice on an asset."""
    user = request.args.get('user')
    asset_id = request.args.get('asset_id')
    choice = request.args.get('choice')
    if any(map(lambda arg: arg is None, [user, asset_id, choice])):
        return send_json({"msg": "parameter missing"}, 401)
    try:
        get_asset(asset_id)
    except ValueError:
        return send_json({"msg": "invalid asset_id"}, 401)
    with get_connection().cursor() as cur:
        ret = cur.execute(
            "INSERT INTO `swipes` (user_uuid, asset_id, choice)"
            "VALUES (%s, %s, %s)", (user, asset_id, choice))
    return send_json({"msg": "choice made"}, 200)


@APP.route('/match', methods=['GET'])
def route_match():
    """Match route"""
    user = request.args.get('user')
    if user is None:
        return send_json({"msg": f"user missing"}, 401)
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
        return send_json(matches, 200)


@APP.route('/suggest', methods=['GET'])
def route_suggest():
    """Get a suggestion based on a match."""
    user = request.args.get('user')
    match = request.args.get('match')
    if user is None or match is None:
        return send_json({"msg": "must have user and match"}, 401)
    return send_json({"msg": "not yet implemented"}, 500)


@APP.errorhandler(500)
def internal_server_error():
    """Send json on status 500."""
    return send_json({
        "msg": f"an internal server error happened. sorry!"
    }, 500)


if __name__ == '__main__':
    APP.run(debug=True, host='0.0.0.0')
