from enum import Enum

import strawberry
from django.db.models import TextChoices


class RetentionPolicyChoices(TextChoices):
    KEEP_ALL = "KEEP_ALL", "Keep all patches and snapshots for this state"
    KEEP_LAST_10 = "KEEP_LAST_10", "Keep only the last 10 patches and snapshots for this state"
    KEEP_LAST_100 = "KEEP_LAST_100", "Keep only the last 100 patches and snapshots for this state"
    KEEP_LAST_1000 = "KEEP_LAST_1000", "Keep only the last 1000 patches and snapshots for this state"
    KEEP_LAST_10000 = "KEEP_LAST_10000", "Keep only the last 10000 patches and snapshots for this state"
    KEEP_LAST_100000 = "KEEP_LAST_100000", "Keep only the last 100000 patches and snapshots for this state"


@strawberry.enum
class JSONPatchOperation(str, Enum):
    add = "add"
    remove = "remove"
    replace = "replace"
    move = "move"
    copy = "copy"
    test = "test"
