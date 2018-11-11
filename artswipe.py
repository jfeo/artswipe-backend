from flask import Flask, request
import random
import json
import requests
import heapq
from flask_cors import CORS
app = Flask(__name__)
CORS(app)


def send_json(obj, status_code, headers={}):
    headers['Content-Type'] = 'application/json'
    return json.dumps(obj), status_code, headers


assets = {}
choices = {}
matches = {}
check_matches = {}

with open("assets.csv", "r", encoding="utf-8") as f:
    for line in f:
        try:
            (collection, asset, title) = line.split(",")
            assets[f"natmus-{collection}-{asset}"] = {
                "inst": "natmus",
                "collection": collection,
                "asset": asset,
                "title": title
            }
        except:
            pass


def get_swiped_culture(user, k=10):
    global choices
    if len([u for u in choices.keys() if u != user]) == 0:
        return None
    [other] = random.sample([u for u in choices.keys() if u != user], 1)
    [assetId] = random.sample(choices[other].keys(), 1)
    if user not in choices or len(choices[user]) == 0:
        return assetId
    while assetId in choices[user]:
        [other] = random.sample([u for u in choices.keys() if u != user], 1)
        [assetId] = random.sample(choices[other].keys(), 1)
        k -= 1
        if k == 0:
            return None
    return assetId


def get_random_culture(user):
    global assets, choices
    [assetId] = random.sample(assets.keys(), 1)
    if user not in choices or len(choices[user]) == 0:
        return assetId
    while assetId in choices[user]:
        [assetId] = random.sample(assets.keys(), 1)
    return assetId


@app.route('/culture', methods=['GET'])
def culture():
    user = request.args.get('user')
    if user is None:
        return send_json({"msg": "must log in"}, 401)
    if random.randint(0, 1) == 0:
        assetId = get_random_culture(user)
    else:
        assetId = get_swiped_culture(user)
        if assetId is None:
            assetId = get_random_culture(user)
    asset = assets[assetId]
    data = {}
    data['assetId'] = assetId
    data['title'] = asset['title']
    data['thumb'] = ("http://samlinger.natmus.dk/"
                     f"{asset['collection']}/asset/"
                     f"{asset['asset']}/thumbnail/500")
    return send_json(data, 200)


@app.route('/choose', methods=['GET'])
def choose():
    global choices
    user = request.args.get('user')
    assetId = request.args.get('assetId')
    choice = request.args.get('choice')
    if any(map(lambda arg: arg is None, [user, assetId, choice])):
        return send_json({"msg": "parameter missing"}, 401)
    if user not in choices:
        choices[user] = {}
    choices[user][assetId] = choice
    compute_matches(user, assetId, choice)
    return send_json({"msg": "choice made"}, 200)


def compute_matches(user, assetId, choice):
    global matches, choices
    for match in [u for u in choices.keys() if u != user]:
        if assetId not in choices[match]:
            continue
        matchChoice = choices[match][assetId]
        if user not in matches:
            matches[user] = {}
        if match not in matches[user]:
            matches[user][match] = {"same": 0, "not": 0}
        if match not in matches:
            matches[match] = {}
        if user not in matches[match]:
            matches[match][user] = {"same": 0, "not": 0}
        if choice == matchChoice:
            matches[user][match]["same"] += 1
            matches[match][user]["same"] += 1
        else:
            matches[user][match]["not"] += 1
            matches[match][user]["not"] += 1


@app.route('/match', methods=['GET'])
def match():
    global matches
    user = request.args.get('user')
    if user is None:
        return send_json({"msg": f"user missing"}, 401)
    if user not in matches:
        return send_json({
            "lost_matches": [],
            "new_matches": [],
            "all_matches": []
        }, 200)

    def sortkey(p):
        m, s = p
        return s["same"] - s["not"]

    ls = [(m, s) for (m, s) in matches[user].items()
          if s['same'] - s['not'] > 3]
    if user not in check_matches:
        check_matches[user] = []
    all_matches = list(map(lambda p: p[0], sorted(ls, key=sortkey)))
    new_matches = [m for m in all_matches if m not in check_matches[user]]
    lost_matches = [m for m in check_matches[user] if m not in all_matches]
    check_matches[user] = all_matches
    return send_json({
        "lost_matches": lost_matches,
        "new_matches": new_matches,
        "all_matches": all_matches
    }, 200)


@app.route('/suggest', methods=['GET'])
def suggest():
    user = request.args.get('user')
    match = request.args.get('match')
    if user is None or match is None:
        return send_json({"msg": "must have user and match"}, 401)
    return send_json({"msg": "not yet implemented"}, 500)


@app.route('/debug', methods=['GET'])
def debug():
    global choices, matches
    return send_json({'choices': choices, 'matches': matches}, 200)


@app.route('/clear', methods=['GET'])
def clear():
    global choices, matches
    matches = {}
    choices = {}
    return send_json({"msg": "Cleared"}, 200)


@app.route('/load', methods=['GET'])
def load():
    global choices, matches
    try:
        fname = request.args.get('fname') or 'dump.json'
        with open(fname, "r", encoding="utf-8") as f:
            dump = json.load(f)
            choices = dump['choices']
            matches = dump['matches']
            return send_json({"msg": f"loaded {fname}"}, 200)
    except:
        return send_json({"msg": f"could not load {fname}"}, 404)


@app.route('/save', methods=['GET'])
def save():
    global choices, matches
    fname = request.args.get('fname') or 'dump.json'
    with open(fname, 'w', encoding="utf-8") as f:
        json.dump({'choices': choices, 'matches': matches}, f)
    return send_json({"msg:": f"saved to '{fname}'"}, 200)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
