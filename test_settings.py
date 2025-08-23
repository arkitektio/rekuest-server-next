from rekuest.settings import *
import os

# Override database to use SQLite for testing
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Disable Redis channels for testing
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
}

# Simple auth setup
AUTHENTIKATE = {
    "ISSUERS": []
}

# Static files
STATIC_ROOT = BASE_DIR / 'static_collected'
