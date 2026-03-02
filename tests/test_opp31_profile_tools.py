"""Tests for OPP-31 Phase 5: MCP tools for agent slot management.

Covers:
  - ProfileTools class exposes create_agent, list_agents, remove_agent,
    list_roles, create_role methods
  - register_profile_tools function wires tools to MCP server
  - JSON output for MCP protocol compliance
  - Error handling returns structured error messages

Test categories (Req 07):
- Happy: Tests 1-7 — create agent, list agents, remove agent, list/create roles
- Negative: Tests 8-10 — duplicate agent, unknown role, remove missing
- Edge: Tests 11-12 — create role at runtime then use in agent
- Boundary: Test 13 — register_profile_tools callable
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def profile_tools():
    """Create ProfileTools with example roles."""
    from config.roles import RoleRegistry, EXAMPLE_ROLES_DIR
    from config.resolver import DynamicResolver
    from config.slot_manager import AgentSlotManager
    from tools.profiles import ProfileTools

    registry = RoleRegistry(roles_dir=EXAMPLE_ROLES_DIR)
    resolver = DynamicResolver(role_registry=registry)
    manager = AgentSlotManager(resolver=resolver)
    return ProfileTools(slot_manager=manager, role_registry=registry)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class TestCreateAgent:
    """Happy: create_agent creates slots and returns JSON."""

    @pytest.mark.unit
    def test_create_agent_returns_json(self, profile_tools):
        """create_agent returns valid JSON string."""
        result = profile_tools.create_agent(
            name="my-coder", role="coder", model="qwen2.5-coder-7b",
        )
        data = json.loads(result)
        assert data["name"] == "my-coder"
        assert data["role"] == "coder"
        assert data["model_id"] == "qwen2.5-coder-7b"

    @pytest.mark.unit
    def test_create_agent_with_overrides(self, profile_tools):
        """create_agent passes temperature override."""
        result = profile_tools.create_agent(
            name="hot-writer", role="writer", model="llama-3.3-70b",
            temperature=0.9,
        )
        data = json.loads(result)
        assert data["temperature"] == 0.9


class TestListAgents:
    """Happy: list_agents returns all active slots."""

    @pytest.mark.unit
    def test_list_agents_empty(self, profile_tools):
        """list_agents returns empty list JSON when no agents."""
        result = profile_tools.list_agents()
        data = json.loads(result)
        assert data["agents"] == []

    @pytest.mark.unit
    def test_list_agents_after_create(self, profile_tools):
        """list_agents includes created agents."""
        profile_tools.create_agent(name="c1", role="coder", model="qwen2.5-coder-7b")
        profile_tools.create_agent(name="t1", role="tester", model="phi-4")
        result = profile_tools.list_agents()
        data = json.loads(result)
        assert len(data["agents"]) == 2


class TestRemoveAgent:
    """Happy: remove_agent removes a slot."""

    @pytest.mark.unit
    def test_remove_agent_returns_confirmation(self, profile_tools):
        """remove_agent returns success JSON."""
        profile_tools.create_agent(name="my-coder", role="coder", model="qwen2.5-coder-7b")
        result = profile_tools.remove_agent(name="my-coder")
        data = json.loads(result)
        assert data["removed"] == "my-coder"


class TestListRoles:
    """Happy: list_roles returns available role templates."""

    @pytest.mark.unit
    def test_list_roles_includes_examples(self, profile_tools):
        """list_roles returns at least the 6 example roles."""
        result = profile_tools.list_roles()
        data = json.loads(result)
        names = {r["name"] for r in data["roles"]}
        assert "coder" in names
        assert "tester" in names
        assert "chat" in names


class TestCreateRole:
    """Happy: create_role adds a runtime role."""

    @pytest.mark.unit
    def test_create_role_returns_confirmation(self, profile_tools):
        """create_role returns success JSON with role details."""
        result = profile_tools.create_role(
            name="my-custom",
            description="A custom role",
            system_prompt="Be helpful.",
        )
        data = json.loads(result)
        assert data["name"] == "my-custom"
        assert data["created"] is True


# ---------------------------------------------------------------------------
# Negative
# ---------------------------------------------------------------------------

class TestProfileToolsNegative:
    """Negative: error handling returns structured errors."""

    @pytest.mark.unit
    def test_duplicate_agent_returns_error(self, profile_tools):
        """Creating duplicate agent returns error JSON, not exception."""
        profile_tools.create_agent(name="my-coder", role="coder", model="qwen2.5-coder-7b")
        result = profile_tools.create_agent(name="my-coder", role="coder", model="phi-4")
        data = json.loads(result)
        assert "error" in data

    @pytest.mark.unit
    def test_unknown_role_returns_error(self, profile_tools):
        """Using unknown role returns error JSON."""
        result = profile_tools.create_agent(
            name="bad", role="nonexistent_role", model="any",
        )
        data = json.loads(result)
        assert "error" in data

    @pytest.mark.unit
    def test_remove_missing_returns_error(self, profile_tools):
        """Removing nonexistent agent returns error JSON."""
        result = profile_tools.remove_agent(name="ghost")
        data = json.loads(result)
        assert "error" in data


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestProfileToolsEdge:
    """Edge: runtime role creation then use in agent."""

    @pytest.mark.unit
    def test_create_role_then_use_in_agent(self, profile_tools):
        """Runtime-created role can be used to create an agent."""
        profile_tools.create_role(
            name="security-auditor",
            description="Security analysis",
            system_prompt="Audit code for vulnerabilities.",
            temperature=0.1,
        )
        result = profile_tools.create_agent(
            name="sec-1", role="security-auditor", model="deepseek-v3",
        )
        data = json.loads(result)
        assert data["role"] == "security-auditor"

    @pytest.mark.unit
    def test_duplicate_role_returns_error(self, profile_tools):
        """Creating a role with existing name returns error JSON."""
        result = profile_tools.create_role(
            name="coder",
            description="Duplicate",
            system_prompt="Test.",
        )
        data = json.loads(result)
        assert "error" in data


# ---------------------------------------------------------------------------
# Boundary
# ---------------------------------------------------------------------------

class TestProfileToolsBoundary:
    """Boundary: register function exists and is callable."""

    @pytest.mark.unit
    def test_register_function_exists(self):
        """register_profile_tools is importable and callable."""
        from tools.profiles import register_profile_tools

        assert callable(register_profile_tools)
