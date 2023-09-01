import strawberry
import hashlib
import json
import dataclasses


def hash_input(input: dataclasses.dataclass):
    hash = hashlib.sha256(
            json.dumps(strawberry.asdict(input), sort_keys=True).encode()
        ).hexdigest()
    return hash