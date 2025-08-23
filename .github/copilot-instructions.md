# Rekuest Server Next - Development Instructions

**Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.**

Rekuest Server Next is a Django-based GraphQL API server built with Python 3.12+ that serves as a core service in the Arkitekt ecosystem. It manages connected applications and their provided functionality (Actions), handles task routing between apps, and provides a central GraphQL API for interaction.

## Working Effectively

### Bootstrap and Setup
- **Install uv package manager**: `pip install uv` (required for dependency management)
- **Install dependencies**: `uv sync` - takes 30-60 seconds on first run, <1 second on subsequent runs. NEVER CANCEL. Set timeout to 120+ seconds.
- **Create test configuration**: Use SQLite for local development instead of PostgreSQL
- **Basic setup validation**: `uv run python manage.py check` - takes 2-3 seconds

### Database Operations
- **Run migrations**: `DJANGO_SETTINGS_MODULE=test_settings uv run python manage.py migrate` - takes 2-3 seconds. NEVER CANCEL.
- **Create superuser**: `DJANGO_SETTINGS_MODULE=test_settings uv run python manage.py createsuperuser --noinput --username admin --email admin@test.com`
- **Show migration status**: `DJANGO_SETTINGS_MODULE=test_settings uv run python manage.py showmigrations`

### Static Files
- **Collect static files**: `DJANGO_SETTINGS_MODULE=test_settings uv run python manage.py collectstatic --noinput` - takes ~1 second

### Development Server
- **Start development server**: `DJANGO_SETTINGS_MODULE=test_settings uv run python manage.py runserver 0.0.0.0:8000`
- **Start production server**: `DJANGO_SETTINGS_MODULE=test_settings uv run daphne -b 0.0.0.0 -p 8000 rekuest.asgi:application`
- **Server startup time**: 1-2 seconds
- **Health check endpoint**: `http://localhost:8000/ht`
- **GraphQL endpoint**: `http://localhost:8000/graphql`

### Quality Control
- **Type checking**: `uv run --group dev mypy .` - takes 10-15 seconds. NEVER CANCEL. Set timeout to 30+ seconds.
- **Run tests**: `DJANGO_SETTINGS_MODULE=test_settings uv run python manage.py test` - takes 1-2 seconds (currently no tests exist)

### Docker (Network Dependent)
- **Build Docker image**: `docker build -t rekuest-server .` - may fail due to certificate issues in sandboxed environments
- The Dockerfile uses `uv sync --locked` which requires internet access

## Test Configuration Setup

Create a `test_settings.py` file in the project root with the following content for local development:

```python
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
```

## Validation

### Manual Testing Steps
1. **ALWAYS run the bootstrap steps first before making any code changes**
2. **Test GraphQL API**: Send a query to `http://localhost:8000/graphql` with:
   ```json
   {"query":"query { __schema { queryType { name } } }"}
   ```
   Expected response: `{"data": {"__schema": {"queryType": {"name": "Query"}}}}`
3. **Verify health endpoint**: Check `http://localhost:8000/ht` returns HTTP 200 with HTML status page
4. **Test database operations**: Run migrations, create users, verify data persistence

### Complete Validation Workflow
After making changes, always run this complete validation sequence:
```bash
# 1. Install/update dependencies
uv sync

# 2. Check Django configuration
uv run python manage.py check

# 3. Run migrations
DJANGO_SETTINGS_MODULE=test_settings uv run python manage.py migrate

# 4. Collect static files
DJANGO_SETTINGS_MODULE=test_settings uv run python manage.py collectstatic --noinput

# 5. Start server (in background)
DJANGO_SETTINGS_MODULE=test_settings uv run python manage.py runserver 0.0.0.0:8000 &

# 6. Test GraphQL API
curl -s http://localhost:8000/graphql -H "Content-Type: application/json" -d '{"query":"query { __schema { queryType { name } } }"}'

# 7. Test health endpoint
curl -I http://localhost:8000/ht

# 8. Stop server and run type checking
kill %1
uv run --group dev mypy .
```

### Critical Testing Scenarios
- **After any model changes**: Run `uv run python manage.py makemigrations` then `uv run python manage.py migrate`
- **After dependency changes**: Run `uv sync` to update lock file
- **Before committing**: Run type checking with `uv run --group dev mypy .`

## Build Times and Timeouts

### NEVER CANCEL these operations - Always set appropriate timeouts:
- **Dependency sync (`uv sync`)**: 30-60 seconds on first run, <1 second on subsequent runs - Set timeout to 120+ seconds
- **Type checking (`mypy`)**: 10-15 seconds - Set timeout to 30+ seconds  
- **Database migrations**: 2-3 seconds - Set timeout to 30+ seconds
- **Docker builds**: 5-30 minutes depending on network - Set timeout to 60+ minutes

### Fast operations (under 5 seconds):
- `python manage.py check` (2-3 seconds)
- `python manage.py collectstatic` (~1 second)
- `python manage.py test` (~2 seconds)
- Server startup (1-2 seconds)

## Common Issues and Solutions

### Missing `ensureadmin` Command
The `run.sh` and `run-debug.sh` scripts reference `uv run python manage.py ensureadmin` but this command does not exist. Skip this step or create a custom management command if needed.

### Database Connection Issues
- Use `test_settings.py` with SQLite instead of PostgreSQL for local development
- The main `config.yaml` expects external services (PostgreSQL, Redis, RabbitMQ)

### Network/Certificate Issues
- Docker builds may fail in sandboxed environments due to certificate validation
- External service dependencies may not be available for testing

### Dependencies
- Uses `uv` for package management (not pip or poetry)
- Dev dependencies are separate: use `uv run --group dev <command>` for dev tools
- Main dependencies: Django 5.2+, GraphQL (Strawberry), PostgreSQL driver (psycopg), Daphne ASGI server

## Key Project Structure

### Repository Root
```
├── README.md               # Project documentation
├── pyproject.toml         # Package configuration with uv
├── uv.lock               # Locked dependencies
├── config.yaml           # Production configuration (requires external services)
├── Dockerfile            # Container build (requires network access)
├── docker-compose.yaml   # Multi-service stack
├── manage.py             # Django management
├── run.sh / run-debug.sh # Production/debug startup scripts
├── facade/               # Main Django application
│   ├── models.py        # Database models
│   ├── mutations/       # GraphQL mutations
│   ├── queries/         # GraphQL queries
│   ├── types.py         # GraphQL types
│   └── schema.py        # GraphQL schema definition
├── rekuest/             # Django project settings
│   ├── settings.py      # Main settings (requires external services)
│   ├── settings_test.py # Test settings (broken - missing koherent)
│   └── urls.py          # URL routing
└── rekuest_core/        # Core functionality
```

### Frequently Modified Files
- `facade/models.py` - Database schema changes
- `facade/mutations/` - API endpoint logic  
- `facade/types.py` - GraphQL type definitions
- `rekuest/settings.py` - Configuration changes

Always validate changes by running the complete bootstrap sequence and testing the GraphQL API functionality after modifications.