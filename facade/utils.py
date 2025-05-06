import hashlib
import json
import dataclasses
from pydantic import BaseModel


def hash_input(input: BaseModel) -> str:
    """ Generate a hash for the input data."""
    hash = hashlib.sha256(json.dumps(input.dict(), sort_keys=True).encode()).hexdigest()
    return hash
