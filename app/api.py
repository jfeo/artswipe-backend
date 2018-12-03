"""The APIs"""

import requests
import random
import json

from app.models import CultureItem


class Natmus():
    """Wrapper for the API of the National Museum."""

    def __init__(self):
        self.prefix = "natmus"
        self.url = "https://api.natmus.dk/search/public/raw"
        self.image_url = "http://cumulus.natmus.dk/CIP/preview/thumbnail/"

    def map_asset(self, hit):
        """Transform search result"""
        local_id = hit['_source']['id']
        collection = hit['_source']['collection']
        asset_id = f"{self.prefix}-{collection}-{local_id}"
        title = hit['_source']['text']['da-DK']['title']
        return CultureItem(local_id=asset_id, title=title)

    def fetch_image(self, asset_id):
        """Fetch an image."""
        collection = asset_id.split("-")[1]
        asset_id = asset_id.split("-")[2]
        rsp = requests.get(f"{self.image_url}{collection}/{id}")
        if rsp.status_code == 200:
            return rsp.content

    def fetch_assets(self, count):
        """Fetch assets from API."""
        es_data = {
            "size": count,
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
                                    "seed": random.randint(1, 2**32 - 1)
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
            self.url,
            data=json.dumps(es_data),
            headers={"Content-Type": "application/json"})
        results = req.json()
        return list(map(self.map_asset, results['hits']['hits']))


def get_culture_items(user, count):
    culture_items = []
    while len(culture_items) < count:
        count = count - len(culture_items)
        culture_items += Natmus().fetch_assets(count)
    return culture_items
