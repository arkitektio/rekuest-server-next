import os
import time

import boto3
import psycopg
import pytest
import pytest_asyncio
import redis as sync_redis
from moto import mock_aws

from authentikate.models import Client, Organization, User, Membership
from django.conf import settings
from kante.context import HttpContext, UniversalRequest
from strawberry.http.temporal_response import TemporalResponse
from dokker import local, testing

from channels.testing import WebsocketCommunicator
from facade.consumers.async_consumer import AgentConsumer


@pytest.fixture(scope="function")
def aws_credentials() -> None:
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture(scope="function")
def s3(aws_credentials):
    with mock_aws():
        yield boto3.client("s3", region_name="us-east-1")


@pytest.fixture
def create_bucket1(s3) -> None:
    s3.create_bucket(Bucket="babanana")


@pytest.fixture
def create_bucket2(s3) -> None:
    s3.create_bucket(Bucket="cabanana")


@pytest.fixture(scope="session")
def backend_stack():
    docker_compose_path = os.path.join(os.path.dirname(__file__), "integration", "docker-compose.yaml")

    with testing(docker_compose_path) as e:
        e.inspect()

        e.down()

        e.up()

        deadline = time.monotonic() + 30
        while True:
            try:
                with psycopg.connect(
                    dbname="testdb",
                    user="test",
                    password="test",
                    host="localhost",
                    port=5555,
                    connect_timeout=1,
                ) as connection:
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT 1")
                break
            except psycopg.OperationalError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(1)

        yield


@pytest.fixture(scope="session")
def django_db_modify_db_settings(backend_stack):
    """Start the backend services before pytest-django configures the test DB."""
    yield


@pytest.fixture(scope="function")
def authenticated_context(db, backend_stack):
    user, _ = User.objects.get_or_create(username="fart", password="123456789", sub="1")
    client, _ = Client.objects.get_or_create(client_id="oinsoins")
    org, _ = Organization.objects.get_or_create(slug="test-organization")
    membership, _ = Membership.objects.get_or_create(
        user=user,
        organization=org,
    )

    request = UniversalRequest(
        _extensions={"token": "test"},
        _client=client,  # type: ignore
        _user=user,  # type: ignore
        _organization=org,  # type: ignore
    )
    request.set_membership(membership)  # type: ignore

    return HttpContext(request=request, response=TemporalResponse(), headers={"Authorization": "Bearer test"}, type="http")


@pytest.fixture(scope="function")
def agent_ws_redis(backend_stack):
    """Start each agent test from a clean redis queue.

    The consumer now reads its redis endpoint from ``settings.AGENT_REDIS_HOST`` /
    ``AGENT_REDIS_PORT`` (overridden to the published ``localhost:6666`` port in
    ``settings_test``), so no factory monkeypatching is needed — we just flush the
    DB so broadcasts from a previous test can't leak.
    """
    client = sync_redis.Redis(host=settings.AGENT_REDIS_HOST, port=settings.AGENT_REDIS_PORT)
    client.flushdb()
    client.close()
    yield


@pytest_asyncio.fixture(scope="function")
async def agent_ws(agent_ws_redis):
    """Factory yielding connected ``WebsocketCommunicator``s, each disconnected on teardown.

    Disconnecting is mandatory: a registered agent spawns two long-lived background
    tasks (``listen_for_tasks`` and ``heartbeat``) that are only cancelled in
    ``disconnect``. Leaking them pollutes the async DB connections across tests.
    """
    created = []

    async def _connect():
        communicator = WebsocketCommunicator(AgentConsumer.as_asgi(), "/agi")
        connected, _ = await communicator.connect()
        assert connected, "WebsocketCommunicator failed to connect to AgentConsumer"
        created.append(communicator)
        return communicator

    yield _connect

    for communicator in created:
        await communicator.disconnect()


@pytest.fixture(scope="function")
def simple_api_context(db, backend_stack) -> HttpContext:
    user, _ = User.objects.get_or_create(username="fart", password="123456789", sub="1")
    client, _ = Client.objects.get_or_create(client_id="oinsoins")
    org, _ = Organization.objects.get_or_create(slug="test-organization")
    membership, _ = Membership.objects.get_or_create(
        user=user,
        organization=org,
    )

    request = UniversalRequest(
        _extensions={"token": "test"},
        _client=client,  # type: ignore
        _user=user,  # type: ignore
        _organization=org,  # type: ignore
    )
    request.set_membership(membership)  # type: ignore

    return HttpContext(request=request, response=TemporalResponse(), headers={"Authorization": "Bearer test"}, type="http")
