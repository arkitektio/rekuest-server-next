from django.core.management.base import BaseCommand
from django.conf import settings
from facade.models import Agent, Registry
from rekuest_core.inputs import models
from facade.unique import calculate_action_hash, infer_action_scope
from facade.creation import create_implementation_from_definition
from authentikate.models import App
from django.contrib.auth import get_user_model
from facade.inputs import CreateImplementationInputModel
from pydantic import BaseModel
from typing import Optional
from facade.persist_backend import persist_backend


class Command(BaseCommand):
    help = "Creates all of the reactive actions"

    def handle(self, *args, **kwargs):
        persist_backend.on_reinit()
