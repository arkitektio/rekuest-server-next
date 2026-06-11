"""
Unit tests for Django models in the Rekuest application.

This module tests the model functionality, including creation,
validation, relationships, and custom methods.
"""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from authentikate.models import App, Client, Device, Organization, Release, User
from facade.models import Action, Agent, Blok, Dashboard, Protocol, Registry, StateDefinition
import uuid


def create_registry_bundle(prefix: str) -> tuple[User, Client, Organization, Registry]:
    user = User.objects.create(username=f"{prefix}-user", password="testpass")
    client = Client.objects.create(client_id=f"{prefix}-client")
    org = Organization.objects.create(slug=f"{prefix}-org")
    registry = Registry.objects.create(client=client, user=user, organization=org)
    return user, client, org, registry


def create_agent_for_registry(registry: Registry, user: User, organization: Organization, prefix: str, **overrides) -> Agent:
    app = App.objects.create(identifier=f"{prefix}-app")
    release = Release.objects.create(app=app, version="1.0.0")
    device = Device.objects.create(device_id=f"{prefix}-device")

    agent_data = {
        "app": app,
        "hash": f"{prefix}-hash",
        "release": release,
        "device": device,
        "user": user,
        "registry": registry,
        "organization": organization,
    }
    agent_data.update(overrides)

    return Agent.objects.create(**agent_data)


def create_action_for_organization(organization: Organization, prefix: str, **overrides) -> Action:
    app = App.objects.create(identifier=f"{prefix}-app")
    action_data = {
        "app": app,
        "key": f"{prefix}-key",
        "version": "1.0.0",
        "name": f"{prefix} action",
        "description": f"{prefix} description",
        "hash": f"{prefix}-hash",
        "organization": organization,
    }
    action_data.update(overrides)

    return Action.objects.create(**action_data)


@pytest.mark.django_db(transaction=True)
class TestModels:
    """Test suite for Django model functionality."""

    def test_agent_creation(self):
        """Test creating an Agent model instance."""
        user, _, org, registry = create_registry_bundle("agent-creation")

        agent = create_agent_for_registry(
            registry=registry,
            user=user,
            organization=org,
            prefix="agent-creation",
            name="Test Agent",
            instance_id="test-instance",
            extensions=["ext1", "ext2"],
        )

        assert agent.name == "Test Agent"
        assert agent.instance_id == "test-instance"
        assert agent.registry == registry
        assert agent.extensions == ["ext1", "ext2"]
        assert agent.unique is not None  # Should have auto-generated UUID

    def test_agent_default_values(self):
        """Test Agent model default values."""
        user, _, org, registry = create_registry_bundle("agent-defaults")

        agent = create_agent_for_registry(
            registry=registry,
            user=user,
            organization=org,
            prefix="agent-defaults",
        )

        assert agent.name == "Nana"  # Default name
        assert agent.instance_id == "main"  # Default instance_id
        assert agent.extensions == []  # Default empty list
        assert agent.health_check_interval == 300  # 5 minutes in seconds
        assert agent.on_instance == "all"

    def test_agent_str_representation(self):
        """Test Agent model string representation."""
        user, _, org, registry = create_registry_bundle("agent-str")

        agent = create_agent_for_registry(
            registry=registry,
            user=user,
            organization=org,
            prefix="agent-str",
            name="Test Agent Display",
        )

        # String representation should include name and registry info
        str_repr = str(agent)
        assert "Test Agent Display" in str_repr

    def test_protocol_creation(self):
        """Test creating a Protocol model instance."""
        protocol = Protocol.objects.create(name="Test Protocol", description="A test protocol for unit testing")

        assert protocol.name == "Test Protocol"
        assert protocol.description == "A test protocol for unit testing"

    def test_protocol_unique_name_constraint(self):
        """Test that Protocol names must be unique."""
        Protocol.objects.create(name="Unique Protocol", description="First protocol")

        # Attempting to create another protocol with the same name should fail
        with pytest.raises(IntegrityError):
            Protocol.objects.create(name="Unique Protocol", description="Second protocol with same name")

    def test_action_creation(self):
        """Test creating an Action model instance."""
        org = Organization.objects.create(slug="test-org-3")

        action = create_action_for_organization(
            organization=org,
            prefix="action-creation",
            name="Test Action",
            description="A test action",
            hash="test-hash-123",
        )

        assert action.name == "Test Action"
        assert action.description == "A test action"
        assert action.hash == "test-hash-123"

    def test_state_schema_creation(self):
        """Test creating a StateDefinition model instance."""
        ports_data = {"input": {"type": "string", "description": "Input port"}, "output": {"type": "string", "description": "Output port"}}

        state_schema = StateDefinition.objects.create(name="Test State Schema", hash="state-hash-123", ports=ports_data, description="A test state schema")

        assert state_schema.name == "Test State Schema"
        assert state_schema.hash == "state-hash-123"
        assert state_schema.ports == ports_data
        assert state_schema.description == "A test state schema"

    def test_state_schema_unique_hash_constraint(self):
        """Test that StateDefinition hash must be unique."""
        StateDefinition.objects.create(name="First Schema", hash="unique-hash-456", description="First schema")

        # Attempting to create another schema with the same hash should fail
        with pytest.raises(IntegrityError):
            StateDefinition.objects.create(name="Second Schema", hash="unique-hash-456", description="Second schema with same hash")

    def test_blok_creation(self):
        """Test creating a Blok model instance."""
        # Create a test user for creator
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create(username="testuser", email="test@example.com")

        blok = Blok.objects.create(name="Test Blok", description="A test UI blok", creator=user)

        assert blok.name == "Test Blok"
        assert blok.description == "A test UI blok"
        assert blok.creator == user
        assert blok.components == []
        assert blok.demo_state == {}

    def test_dashboard_creation(self):
        """Test creating a Dashboard model instance."""
        dashboard = Dashboard.objects.create(name="Test Dashboard")

        assert dashboard.name == "Test Dashboard"
        assert dashboard.structure is None  # Default null
        assert dashboard.ui_tree is None  # Default null

    def test_registry_relationship(self):
        """Test the relationship between Registry and Agent."""
        user, _, org, registry = create_registry_bundle("registry-relationship")

        # Create multiple agents for the same registry
        agent1 = create_agent_for_registry(
            registry=registry,
            user=user,
            organization=org,
            prefix="registry-relationship-1",
            name="Agent 1",
            instance_id="agent-1",
        )

        agent2 = create_agent_for_registry(
            registry=registry,
            user=user,
            organization=org,
            prefix="registry-relationship-2",
            name="Agent 2",
            instance_id="agent-2",
        )

        # Test relationship through direct queries
        agent_count = Agent.objects.filter(registry=registry).count()
        assert agent_count == 2

        agents_for_registry = Agent.objects.filter(registry=registry)
        assert agent1 in agents_for_registry
        assert agent2 in agents_for_registry

    def test_protocol_action_relationship(self):
        """Test the relationship between Protocol and Action."""
        protocol = Protocol.objects.create(name="Relationship Test Protocol", description="Testing protocol-action relationship")

        org = Organization.objects.create(slug="test-org-3")

        # Create multiple actions and associate them with the protocol
        action1 = create_action_for_organization(
            organization=org,
            prefix="protocol-action-1",
            name="Action 1",
            hash="action1-hash",
        )
        action1.protocols.add(protocol)

        action2 = create_action_for_organization(
            organization=org,
            prefix="protocol-action-2",
            name="Action 2",
            hash="action2-hash",
        )
        action2.protocols.add(protocol)

        # Test relationship
        protocol_actions = Action.objects.filter(protocols=protocol)
        assert action1 in protocol_actions
        assert action2 in protocol_actions
        assert protocol_actions.count() == 2

    def test_agent_cascade_delete(self):
        """Test that deleting registry cascades to agents."""
        user, _, org, registry = create_registry_bundle("agent-cascade")

        agent = create_agent_for_registry(
            registry=registry,
            user=user,
            organization=org,
            prefix="agent-cascade",
            name="To Be Deleted",
        )

        agent_pk = agent.pk

        # Delete the registry
        registry.delete()

        # Agent should also be deleted due to CASCADE
        assert not Agent.objects.filter(pk=agent_pk).exists()

    def test_model_meta_options(self):
        """Test model meta options and constraints."""
        # Test that certain fields have expected database constraints
        user, _, org, registry = create_registry_bundle("meta")

        # Test that unique fields enforce uniqueness at model level
        create_agent_for_registry(
            registry=registry,
            user=user,
            organization=org,
            prefix="meta-1",
            instance_id="unique-instance",
        )

        # Creating another agent with same instance_id and registry should fail
        with pytest.raises(IntegrityError):
            create_agent_for_registry(
                registry=registry,
                user=user,
                organization=org,
                prefix="meta-2",
                instance_id="unique-instance",
            )
