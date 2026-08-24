"""UI-component model tests: Blok and Dashboard creation."""

import pytest

from facade.models import Blok, Dashboard


def _org(slug="test-org-scope"):
    """Protocol / StateDefinition / Blok / Dashboard are organization-scoped; any org will do here."""
    from authentikate.models import Organization

    return Organization.objects.get_or_create(slug=slug)[0]



@pytest.mark.django_db(transaction=True)
class TestUIModels:
    """Test suite for the Blok / Dashboard UI models."""

    def test_blok_creation(self):
        """Test creating a Blok model instance."""
        # Create a test user for creator
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create(username="testuser", email="test@example.com")

        blok = Blok.objects.create(name="Test Blok", description="A test UI blok", creator=user, organization=_org())

        assert blok.name == "Test Blok"
        assert blok.description == "A test UI blok"
        assert blok.creator == user
        assert blok.components == []
        assert blok.demo_state == {}

    def test_dashboard_creation(self):
        """Test creating a Dashboard model instance."""
        dashboard = Dashboard.objects.create(name="Test Dashboard", organization=_org())

        assert dashboard.name == "Test Dashboard"
        assert dashboard.ui_tree is None  # Default null
