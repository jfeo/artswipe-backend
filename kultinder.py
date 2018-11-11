from flask import Flask, request
import random
import json
import requests
import heapq
from flask_cors import CORS
app = Flask(__name__)
CORS(app)

titles = {}


def parse_assets(l):
    try:
        (collection, asset, title) = l.split(",")
        titles[f"{collection}-{asset}"] = title
        return collection, int(asset.rstrip())
    except:
        return None


def send_json(obj, status_code, headers={}):
    headers['Content-Type'] = 'application/json'
    return json.dumps(obj), status_code, headers


assets = []
with open("assets.csv", "r", encoding="utf-8") as f:
    assets = [parse_assets(l) for l in f if parse_assets(l) is not None]

choices = {}
matches = {}
check_matches = {}


def get_swiped_culture(user, k=10):
    global choices, titles
    if len([u for u in choices.keys() if u != user]) == 0:
        return None
    [other] = random.sample([u for u in choices.keys() if u != user], 1)
    [collection] = random.sample(choices[other].keys(), 1)
    [asset] = random.sample(choices[other][collection].keys(), 1)
    if user not in choices or len(choices[user]) == 0:
        return collection, asset
    while collection in choices[user].keys(
    ) and asset in choices[user][collection].keys():
        [other] = random.sample([u for u in choices.keys() if u != user], 1)
        [collection] = random.sample(choices[other].keys(), 1)
        [asset] = random.sample(choices[other][collection].keys(), 1)
        k -= 1
        if k == 0:
            return None
    return collection, asset


def get_random_culture(user):
    global choices
    [(collection, asset)] = random.sample(assets, 1)
    if user not in choices or len(choices[user]) == 0:
        return collection, asset
    while collection in choices[user] and asset in choices[user][collection]:
        [(collection, asset)] = random.sample(assets, 1)
    return collection, asset


@app.route('/culture', methods=['GET'])
def culture():
    user = request.args.get('user')
    if user is None:
        return send_json({"msg": "must log in"}, 401)
    if random.randint(0, 1) == 0:
        collection, asset = get_random_culture(user)
        print("Selecting random")
    else:
        tup = get_swiped_culture(user)
        print("Selecting from swiped")
        if tup is None:
            print("Falling back to random culture")
            collection, asset = get_random_culture(user)
        else:
            collection, asset = tup
    #r = requests.get(
    #    f"http://samlinger.natmus.dk/{collection}/asset/{asset}/json")
    text = "Beskrivelse"
    title = titles.get(f"{collection}-{asset}")
    #if r.status_code == 200:
    #   data = r.json()
    #  text = data['text']['da-DK']['description']
    # title = data['text']['da-DK']['title']
    data = {
        'collection': collection,
        'asset': asset,
        'title': title,
        'text': text
    }
    return send_json(data, 200)


@app.route('/choose', methods=['GET'])
def choose():
    global choices
    args = ["user", "collection", "asset", "choice"]
    if any([arg not in request.args for arg in args]):
        return json.dumps({
            "msg": "parameter missing"
        }), 401, {
            'Content-Type': 'application/json'
        }
    user = request.args.get('user')
    collection = request.args.get('collection')
    try:
        asset = int(request.args.get('asset'))
    except Exception:
        return send_json({"msg": "asset id malformed"}, 401)
    choice = request.args.get('choice')
    if user not in choices:
        choices[user] = {}
    if collection not in choices[user]:
        choices[user][collection] = {}
    choices[user][collection][asset] = choice
    compute_matches(user, collection, asset, choice)
    return send_json({"msg": "choice made"}, 200)


def compute_matches(user, collection, asset, choice):
    global matches, choices
    for match in [u for u in choices.keys() if u != user]:
        if collection not in choices[match].keys():
            continue
        if asset not in choices[match][collection].keys():
            continue
        match_choice = choices[match][collection][asset]
        if user not in matches:
            matches[user] = {}
        if match not in matches[user]:
            matches[user][match] = {"same": 0, "not": 0}
        if match not in matches:
            matches[match] = {}
        if user not in matches[match]:
            matches[match][user] = {"same": 0, "not": 0}
        if choice == match_choice:
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
        return send_json([], 200)

    def sortkey(p):
        m, s = p
        return s["same"] - s["not"]

    ls = [(m, s) for (m, s) in matches[user].items()
          if s['same'] - s['not'] > 3]
    print(ls)
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
