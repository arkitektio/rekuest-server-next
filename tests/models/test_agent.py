"""Agent model tests: creation, defaults, registry relationship and constraints."""

import pytest
from django.db import IntegrityError

from facade.models import Agent

from tests.factories import create_agent_for_registry, create_registry_bundle


@pytest.mark.django_db(transaction=True)
class TestAgentModels:
    """Test suite for the Agent model."""

    def test_agent_creation(self):
        """Test creating an Agent model instance."""
        user, _, org, registry = create_registry_bundle("agent-creation")

        agent = create_agent_for_registry(
            registry=registry,
            user=user,
            organization=org,
            prefix="agent-creation",
            name="Test Agent",
        )

        assert agent.name == "Test Agent"
        assert agent.registry == registry
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

    def test_registry_relationship(self):
        """Each registry owns exactly one agent; different registries are independent."""
        user1, _, org1, registry1 = create_registry_bundle("registry-relationship-1")
        user2, _, org2, registry2 = create_registry_bundle("registry-relationship-2")

        agent1 = create_agent_for_registry(
            registry=registry1,
            user=user1,
            organization=org1,
            prefix="registry-relationship-1",
            name="Agent 1",
        )

        agent2 = create_agent_for_registry(
            registry=registry2,
            user=user2,
            organization=org2,
            prefix="registry-relationship-2",
            name="Agent 2",
        )

        # Each registry resolves to its own single agent.
        assert Agent.objects.filter(registry=registry1).count() == 1
        assert Agent.objects.filter(registry=registry2).count() == 1
        assert list(Agent.objects.filter(registry=registry1)) == [agent1]
        assert list(Agent.objects.filter(registry=registry2)) == [agent2]

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

        # Only one agent is allowed per registry.
        create_agent_for_registry(
            registry=registry,
            user=user,
            organization=org,
            prefix="meta-1",
        )

        # Creating a second agent for the same registry should fail.
        with pytest.raises(IntegrityError):
            create_agent_for_registry(
                registry=registry,
                user=user,
                organization=org,
                prefix="meta-2",
            )
