import hashlib
import json


def hash_graph(graph_hash) -> str:
    """MD5 hash of a dictionary."""
    dhash = hashlib.md5()
    # We need to sort arguments so {'a': 1, 'b': 2} is
    # the same as {'b': 2, 'a': 1}
    encoded = json.dumps(graph_hash, sort_keys=True).encode()
    dhash.update(encoded)
    return dhash.hexdigest()
