"""artswipe backend
author: jfeo
email: jensfeodor@gmail.com
"""
import random
import json
import requests

from flask import Flask, request
from flask_cors import CORS
APP = Flask(__name__)
CORS(APP)

NATMUS_API_SEARCH = "https://api.natmus.dk/search/public/raw"

QUEUE = []
ASSETS = {}
CHOICES = {}
MATCHES = {}
CHECK_MATCHES = {}


def send_json(obj, status_code, headers={}):
    """Create the response tuple with, automatically dumping the given object
    to a json string, and setting the Content-Type header appropriately.
    """
    headers['Content-Type'] = 'application/json'
    return json.dumps(obj), status_code, headers


def get_swiped_culture(user, k=10):
    """Get a culture item that has been swiped already by another user."""
    if not [u for u in CHOICES.keys() if u != user]:
        return None

    [other] = random.sample([u for u in CHOICES.keys() if u != user], 1)
    [asset_id] = random.sample(CHOICES[other].keys(), 1)
    if user not in CHOICES or not CHOICES[user]:
        return ASSETS[asset_id]
    while asset_id in CHOICES[user]:
        [other] = random.sample([u for u in CHOICES.keys() if u != user], 1)
        [asset_id] = random.sample(CHOICES[other].keys(), 1)
        k -= 1
        if k == 0:
            return None
    return ASSETS[asset_id]


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
    asset = {}
    asset['id'] = hit['_source']['id']
    asset['collection'] = hit['_source']['collection']
    asset['asset_id'] = f"natmus-{asset['collection']}-{asset['id']}"
    asset['title'] = hit['_source']['text']['da-DK']['title']
    asset['thumb'] = (f"http://samlinger.natmus.dk/{asset['collection']}"
                      f"/asset/{asset['id']}/thumbnail/500")
    return asset


def fill_queue():
    """Fill the asset queue with randomly sampled assets."""
    global QUEUE
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
    QUEUE.extend(map(lambda asset: asset['asset_id'], assets))
    tmpdict = {asset['asset_id']: asset for asset in assets}
    ASSETS.update(tmpdict)


def get_random_culture(user):
    """Get a culture item by random sampling."""
    if not QUEUE:
        fill_queue()
    asset_id = QUEUE.pop()
    if user not in CHOICES or not CHOICES[user]:
        return ASSETS[asset_id]
    while asset_id in CHOICES[user]:
        if not QUEUE:
            fill_queue()
        asset_id = QUEUE.pop()
    return ASSETS[asset_id]


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
    if asset_id not in ASSETS:
        return send_json({"msg": "invalid asset_id"}, 401)
    if user not in CHOICES:
        CHOICES[user] = {}
    CHOICES[user][asset_id] = choice
    update_matches(user, asset_id, choice)
    return send_json({"msg": "choice made"}, 200)


def update_matches(user, asset_id, choice):
    """Update the matches, given a choice on an asset by a user."""
    for match in [u for u in CHOICES.keys() if u != user]:
        if asset_id not in CHOICES[match]:
            continue
        match_choice = CHOICES[match][asset_id]
        if user not in MATCHES:
            MATCHES[user] = {}
        if match not in MATCHES[user]:
            MATCHES[user][match] = {"same": 0, "not": 0}
        if match not in MATCHES:
            MATCHES[match] = {}
        if user not in MATCHES[match]:
            MATCHES[match][user] = {"same": 0, "not": 0}
        if choice == match_choice:
            MATCHES[user][match]["same"] += 1
            MATCHES[match][user]["same"] += 1
        else:
            MATCHES[user][match]["not"] += 1
            MATCHES[match][user]["not"] += 1


@APP.route('/match', methods=['GET'])
def route_match():
    """Match route"""
    user = request.args.get('user')
    if user is None:
        return send_json({"msg": f"user missing"}, 401)
    if user not in MATCHES:
        return send_json({
            "lost_matches": [],
            "new_matches": [],
            "all_matches": []
        }, 200)

    def sortkey(key_value):
        score = key_value[1]
        return score["same"] - score["not"]

    valids = [(match, score) for (match, score) in MATCHES[user].items()
              if score['same'] - score['not'] > 3]
    if user not in CHECK_MATCHES:
        CHECK_MATCHES[user] = []
    all_matches = list(map(lambda p: p[0], sorted(valids, key=sortkey)))
    new_matches = [m for m in all_matches if m not in CHECK_MATCHES[user]]
    lost_matches = [m for m in CHECK_MATCHES[user] if m not in all_matches]
    CHECK_MATCHES[user] = all_matches
    return send_json({
        "lost_matches": lost_matches,
        "new_matches": new_matches,
        "all_matches": all_matches
    }, 200)


@APP.route('/matchInfo', methods=['GET'])
def route_match_info():
    """Get detailed information about the match between a user and the matched user."""
    user = request.args.get('user')
    match = request.args.get('match')
    if user is None or match is None:
        return send_json({"msg": "must have user and match"}, 401)
    if user not in MATCHES or match not in MATCHES[user]:
        return send_json({
            "msg": f"no match between '{user}' and '{match}'"
        }, 401)
    info = {'same': {}, 'not': {}}
    for asset_id in CHOICES[user]:
        if asset_id not in CHOICES[match]:
            continue
        user_choice = CHOICES[user][asset_id]
        match_choice = CHOICES[match][asset_id]
        if user_choice == match_choice:
            if user_choice not in info['same']:
                info['same'][user_choice] = []
            info['same'][user_choice].append(asset_id)
        else:
            info['not'][asset_id] = {
                'user': user_choice,
                'match': match_choice
            }
    return send_json(info, 200)


@APP.route('/suggest', methods=['GET'])
def route_suggest():
    """Get a suggestion based on a match."""
    user = request.args.get('user')
    match = request.args.get('match')
    if user is None or match is None:
        return send_json({"msg": "must have user and match"}, 401)
    return send_json({"msg": "not yet implemented"}, 500)


@APP.route('/debug', methods=['GET'])
def route_debug():
    """Get server state for debugging."""
    return send_json({'CHOICES': CHOICES, 'MATCHES': MATCHES}, 200)


@APP.route('/clear', methods=['GET'])
def route_clear():
    """Clear server state."""
    global CHOICES, MATCHES
    MATCHES = {}
    CHOICES = {}
    return send_json({"msg": "Cleared"}, 200)


@APP.route('/load', methods=['GET'])
def route_load():
    """Route for loading a dump file."""
    global CHOICES, MATCHES
    try:
        fname = request.args.get('fname') or 'dump.json'
        with open(fname, "r", encoding="utf-8") as file:
            dump = json.load(file)
            CHOICES = dump['CHOICES']
            MATCHES = dump['MATCHES']
            return send_json({"msg": f"loaded {fname}"}, 200)
    except IOError:
        return send_json({"msg": f"could not load {fname}"}, 404)


@APP.route('/save', methods=['GET'])
def route_save():
    """Route for saving state to a dump file."""
    fname = request.args.get('fname') or 'dump.json'
    with open(fname, 'w', encoding="utf-8") as file:
        json.dump({'CHOICES': CHOICES, 'MATCHES': MATCHES}, file)
    return send_json({"msg:": f"saved to '{fname}'"}, 200)


@APP.errorhandler(500)
def internal_server_error():
    """Send json on status 500."""
    return send_json({
        "msg": f"an internal server error happened. sorry!"
    }, 500)


if __name__ == '__main__':
    APP.run(debug=True, host='0.0.0.0')
