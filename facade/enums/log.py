from enum import Enum

import strawberry
from django.db.models import TextChoices


class LogLevelChoices(TextChoices):
    DEBUG = "DEBUG", "DEBUG Level"
    INFO = "INFO", "INFO Level"
    ERROR = "ERROR", "ERROR Level"
    WARN = "WARN", "WARN Level"


@strawberry.enum
class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    ERROR = "ERROR"
    WARN = "WARN"
    CRITICAL = "CRITICAL"
