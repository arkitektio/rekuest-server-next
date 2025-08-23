import pytest
import boto3
import moto
from moto import mock_aws
import os
import django
from django.conf import settings


# Configure Django settings for tests
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rekuest.settings_test')
    django.setup()


from django.contrib.auth import get_user_model
from authentikate.models import Client, Organization, User
from facade.schema import schema
from guardian.shortcuts import get_perms
from asgiref.sync import sync_to_async
from kante.context import HttpContext, UniversalRequest


@pytest.fixture(scope="function")
def aws_credentials():
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
def create_bucket1(s3):
    s3.create_bucket(Bucket="babanana")


@pytest.fixture
def create_bucket2(s3):
    s3.create_bucket(Bucket="cabanana")


@pytest.fixture
def authenticated_context(db):
    user = User.objects.create(username="fart", password="123456789", sub="1")
    client = Client.objects.create(client_id="oinsoins")
    org = Organization.objects.create(slug="test-organization")

    return HttpContext(
            request=UniversalRequest(
                _extensions={"token": "token"},
                _client=client,  # type: ignore
                _user=user, # type: ignore
                _organization=org, #type: ignore
            ),
            headers={"Authorization": "Bearer token"},
            type="http"
        )
    
