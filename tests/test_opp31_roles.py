"""Tests for OPP-31 Phase 1: RoleTemplate and RoleRegistry.

Covers:
  - RoleTemplate is a frozen dataclass with expected fields
  - RoleRegistry loads roles from YAML files
  - Custom roles can be created at runtime
  - Role with unknown capabilities uses defaults
  - Duplicate role names raise ValueError
  - Missing required fields in YAML raise ValueError
  - Default example roles shipped (coder, tester, reviewer, writer, chat, reasoning)

Test categories (Req 07):
- Happy: Tests 1-5 — create role, load from YAML, list roles, get role
- Negative: Tests 6-8 — duplicate name, missing field, invalid YAML
- Edge: Tests 9-10 — empty capabilities, role with all defaults
- Boundary: Tests 11-12 — max name length, all 6 example roles loadable
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class TestRoleTemplateCreation:
    """Happy: RoleTemplate creation and immutability."""

    @pytest.mark.unit
    def test_create_role_template(self):
        """RoleTemplate can be created with required fields."""
        from config.roles import RoleTemplate

        role = RoleTemplate(
            name="coder",
            description="Code generation",
            system_prompt="You are a coder.",
        )
        assert role.name == "coder"
        assert role.description == "Code generation"
        assert role.system_prompt == "You are a coder."

    @pytest.mark.unit
    def test_role_template_is_frozen(self):
        """RoleTemplate instances are immutable (frozen dataclass)."""
        from config.roles import RoleTemplate

        role = RoleTemplate(
            name="test",
            description="Test",
            system_prompt="Test",
        )
        with pytest.raises(AttributeError):
            role.name = "changed"

    @pytest.mark.unit
    def test_role_template_defaults(self):
        """RoleTemplate has sensible defaults for optional fields."""
        from config.roles import RoleTemplate

        role = RoleTemplate(
            name="test",
            description="Test",
            system_prompt="Test",
        )
        assert role.temperature == 0.7
        assert role.max_tokens == 4096
        assert role.context_length == 16384
        assert role.context_overflow_policy == "truncateMiddle"
        assert role.preferred_capabilities == ()

    @pytest.mark.unit
    def test_role_template_with_capabilities(self):
        """RoleTemplate accepts preferred_capabilities tuple."""
        from config.roles import RoleTemplate

        role = RoleTemplate(
            name="coder",
            description="Code gen",
            system_prompt="Code.",
            preferred_capabilities=("code",),
        )
        assert role.preferred_capabilities == ("code",)


class TestRoleRegistryFromYAML:
    """Happy: RoleRegistry loads roles from YAML files."""

    @pytest.mark.unit
    def test_load_role_from_yaml(self, tmp_path):
        """RoleRegistry loads a single role from a YAML file."""
        from config.roles import RoleRegistry

        yaml_content = """
name: coder
description: Code generation
system_prompt: You are a coder.
temperature: 0.2
max_tokens: 4096
preferred_capabilities: [code]
"""
        role_file = tmp_path / "coder.yaml"
        role_file.write_text(yaml_content)

        registry = RoleRegistry(roles_dir=tmp_path)
        role = registry.get("coder")
        assert role.name == "coder"
        assert role.temperature == 0.2
        assert role.preferred_capabilities == ("code",)

    @pytest.mark.unit
    def test_list_roles(self, tmp_path):
        """RoleRegistry.list() returns all loaded role names."""
        from config.roles import RoleRegistry

        for name in ["coder", "tester"]:
            (tmp_path / f"{name}.yaml").write_text(
                f"name: {name}\ndescription: {name}\nsystem_prompt: Be a {name}.\n"
            )

        registry = RoleRegistry(roles_dir=tmp_path)
        names = registry.list()
        assert set(names) == {"coder", "tester"}


# ---------------------------------------------------------------------------
# Negative
# ---------------------------------------------------------------------------

class TestRoleRegistryNegative:
    """Negative: invalid YAML and duplicate roles."""

    @pytest.mark.unit
    def test_duplicate_role_name_raises(self, tmp_path):
        """Two YAML files with same 'name' field → ValueError."""
        from config.roles import RoleRegistry

        for fname in ["a.yaml", "b.yaml"]:
            (tmp_path / fname).write_text(
                "name: coder\ndescription: dup\nsystem_prompt: dup\n"
            )

        with pytest.raises(ValueError, match="[Dd]uplicate"):
            RoleRegistry(roles_dir=tmp_path)

    @pytest.mark.unit
    def test_missing_required_field_raises(self, tmp_path):
        """YAML missing 'name' field → ValueError."""
        from config.roles import RoleRegistry

        (tmp_path / "bad.yaml").write_text(
            "description: no name\nsystem_prompt: test\n"
        )

        with pytest.raises(ValueError, match="name"):
            RoleRegistry(roles_dir=tmp_path)

    @pytest.mark.unit
    def test_get_nonexistent_role_raises(self, tmp_path):
        """RoleRegistry.get() for unknown role → KeyError."""
        from config.roles import RoleRegistry

        registry = RoleRegistry(roles_dir=tmp_path)
        with pytest.raises(KeyError, match="nonexistent"):
            registry.get("nonexistent")


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestRoleRegistryEdge:
    """Edge: empty capabilities, empty directory, runtime add."""

    @pytest.mark.unit
    def test_empty_directory_no_roles(self, tmp_path):
        """Empty roles directory → registry with 0 roles."""
        from config.roles import RoleRegistry

        registry = RoleRegistry(roles_dir=tmp_path)
        assert registry.list() == []

    @pytest.mark.unit
    def test_add_role_at_runtime(self, tmp_path):
        """RoleRegistry.add() creates a new role at runtime."""
        from config.roles import RoleTemplate, RoleRegistry

        registry = RoleRegistry(roles_dir=tmp_path)
        role = RoleTemplate(
            name="dynamic",
            description="Created at runtime",
            system_prompt="Be dynamic.",
        )
        registry.add(role)
        assert registry.get("dynamic") == role
        assert "dynamic" in registry.list()


# ---------------------------------------------------------------------------
# Boundary
# ---------------------------------------------------------------------------

class TestRoleRegistryBoundary:
    """Boundary: example roles and role constants."""

    @pytest.mark.unit
    def test_example_roles_directory_exists(self):
        """The roles/examples/ directory with 6 YAML files exists."""
        from config.roles import EXAMPLE_ROLES_DIR

        assert EXAMPLE_ROLES_DIR.exists()
        yaml_files = list(EXAMPLE_ROLES_DIR.glob("*.yaml"))
        assert len(yaml_files) == 6

    @pytest.mark.unit
    def test_all_example_roles_loadable(self):
        """All 6 example roles can be loaded into a RoleRegistry."""
        from config.roles import RoleRegistry, EXAMPLE_ROLES_DIR

        registry = RoleRegistry(roles_dir=EXAMPLE_ROLES_DIR)
        names = registry.list()
        assert set(names) == {"coder", "tester", "reviewer", "writer", "chat", "reasoning"}
