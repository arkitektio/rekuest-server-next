"""
Unit tests for Django models in the Rekuest application.

This module tests the model functionality, including creation,
validation, relationships, and custom methods.
"""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from facade.models import Agent, Registry, Action, Protocol, Blok, Dashboard
from authentikate.models import User, Client, Organization
import uuid


@pytest.mark.django_db(transaction=True)
class TestModels:
    """Test suite for Django model functionality."""

    def test_agent_creation(self):
        """Test creating an Agent model instance."""
        user = User.objects.create(username="testuser", password="testpass")
        client = Client.objects.create(client_id="test-client")
        org = Organization.objects.create(slug="test-org")

        registry = Registry.objects.create(client=client, user=user, organization=org)

        agent = Agent.objects.create(name="Test Agent", instance_id="test-instance", registry=registry, extensions=["ext1", "ext2"])

        assert agent.name == "Test Agent"
        assert agent.instance_id == "test-instance"
        assert agent.registry == registry
        assert agent.extensions == ["ext1", "ext2"]
        assert agent.unique is not None  # Should have auto-generated UUID

    def test_agent_default_values(self):
        """Test Agent model default values."""
        user = User.objects.create(username="testuser2", password="testpass")
        client = Client.objects.create(client_id="test-client-2")
        org = Organization.objects.create(slug="test-org-2")

        registry = Registry.objects.create(client=client, user=user, organization=org)

        agent = Agent.objects.create(registry=registry)

        assert agent.name == "Nana"  # Default name
        assert agent.instance_id == "main"  # Default instance_id
        assert agent.extensions == []  # Default empty list
        assert agent.health_check_interval == 300  # 5 minutes in seconds
        assert agent.on_instance == "all"

    def test_agent_str_representation(self):
        """Test Agent model string representation."""
        user = User.objects.create(username="testuser3", password="testpass")
        client = Client.objects.create(client_id="test-client-3")
        org = Organization.objects.create(slug="test-org-3")

        registry = Registry.objects.create(client=client, user=user, organization=org)

        agent = Agent.objects.create(name="Test Agent Display", registry=registry)

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

        action = Action.objects.create(name="Test Action", description="A test action", hash="test-hash-123", organization=org)

        assert action.name == "Test Action"
        assert action.description == "A test action"
        assert action.hash == "test-hash-123"

    def test_state_schema_creation(self):
        """Test creating a StateSchema model instance."""
        ports_data = {"input": {"type": "string", "description": "Input port"}, "output": {"type": "string", "description": "Output port"}}

        state_schema = StateSchema.objects.create(name="Test State Schema", hash="state-hash-123", ports=ports_data, description="A test state schema")

        assert state_schema.name == "Test State Schema"
        assert state_schema.hash == "state-hash-123"
        assert state_schema.ports == ports_data
        assert state_schema.description == "A test state schema"

    def test_state_schema_unique_hash_constraint(self):
        """Test that StateSchema hash must be unique."""
        StateSchema.objects.create(name="First Schema", hash="unique-hash-456", description="First schema")

        # Attempting to create another schema with the same hash should fail
        with pytest.raises(IntegrityError):
            StateSchema.objects.create(name="Second Schema", hash="unique-hash-456", description="Second schema with same hash")

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
        assert blok.action_demands == []
        assert blok.state_demands == []

    def test_dashboard_creation(self):
        """Test creating a Dashboard model instance."""
        dashboard = Dashboard.objects.create(name="Test Dashboard")

        assert dashboard.name == "Test Dashboard"
        assert dashboard.structure is None  # Default null
        assert dashboard.ui_tree is None  # Default null

    def test_registry_relationship(self):
        """Test the relationship between Registry and Agent."""
        user = User.objects.create(username="reltest", password="testpass")
        client = Client.objects.create(client_id="rel-client")
        org = Organization.objects.create(slug="rel-org")

        registry = Registry.objects.create(client=client, user=user, organization=org)

        # Create multiple agents for the same registry
        agent1 = Agent.objects.create(name="Agent 1", instance_id="agent-1", registry=registry)

        agent2 = Agent.objects.create(name="Agent 2", instance_id="agent-2", registry=registry)

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
        action1 = Action.objects.create(name="Action 1", hash="action1-hash", organization=org)
        action1.protocols.add(protocol)

        action2 = Action.objects.create(name="Action 2", hash="action2-hash", organization=org)
        action2.protocols.add(protocol)

        # Test relationship
        protocol_actions = Action.objects.filter(protocols=protocol)
        assert action1 in protocol_actions
        assert action2 in protocol_actions
        assert protocol_actions.count() == 2

    def test_agent_cascade_delete(self):
        """Test that deleting registry cascades to agents."""
        user = User.objects.create(username="cascade", password="testpass")
        client = Client.objects.create(client_id="cascade-client")
        org = Organization.objects.create(slug="cascade-org")

        registry = Registry.objects.create(client=client, user=user, organization=org)

        agent = Agent.objects.create(name="To Be Deleted", registry=registry)

        agent_pk = agent.pk

        # Delete the registry
        registry.delete()

        # Agent should also be deleted due to CASCADE
        assert not Agent.objects.filter(pk=agent_pk).exists()

    def test_model_meta_options(self):
        """Test model meta options and constraints."""
        # Test that certain fields have expected database constraints
        user = User.objects.create(username="meta", password="testpass")
        client = Client.objects.create(client_id="meta-client")
        org = Organization.objects.create(slug="meta-org")

        registry = Registry.objects.create(client=client, user=user, organization=org)

        # Test that unique fields enforce uniqueness at model level
        agent1 = Agent.objects.create(instance_id="unique-instance", registry=registry)

        # Creating another agent with same instance_id and registry should fail
        with pytest.raises(IntegrityError):
            Agent.objects.create(instance_id="unique-instance", registry=registry)
