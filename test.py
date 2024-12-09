# Initialiaze django

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rekuest.settings")

django.setup()

# Import the models
from facade import models
from pydantic import BaseModel, Field
