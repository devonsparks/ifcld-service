import json
from pyld import jsonld
from collections import defaultdict



Sentinel = "-"
Separator = ";"

def getcontext(path):
    with open(path) as f:
        return json.loads(f.read())["@context"]


def doc(aDoc = {}):
    return defaultdict(lambda: doc(), aDoc)


