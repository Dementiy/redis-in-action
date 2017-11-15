from urllib.parse import urlparse
from urllib.parse import parse_qs
import time

def extract_item_id(request):
    parsed = urlparse(request)
    query = parse_qs(parsed.query)
    return (query.get('item') or [None])[0]


def is_dynamic(request):
    parsed = urlparse(request)
    query = parse_qs(parsed.query)
    return '_' in query


def hash_request(request):
    return str(hash(request))


class Inventory:

    def __init__(self, id):
        self.id = id

    @classmethod
    def get(cls, id):
        return Inventory(id)

    def to_dict(self):
        return {
            'id': self.id,
            'data': 'data to cache...',
            'cached': time.time()
        }

