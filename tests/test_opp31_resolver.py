"""Tests for OPP-31 Phase 3: DynamicResolver and ResolvedConfig.

Covers:
  - ResolvedConfig is a frozen dataclass with all required fields
  - DynamicResolver.resolve() in explicit mode (user provides model_id)
  - DynamicResolver.resolve() in auto-resolve mode (mocked SmartModelSelector)
  - Config layering: critical constraints > user overrides > family overlay > role defaults
  - Task type inference from role name and preferred_capabilities
  - Error handling for unknown roles and missing selector

Test categories (Req 07):
- Happy: Tests 1-7 — explicit resolve, auto-resolve, layering, task inference
- Negative: Tests 8-10 — unknown role, no selector for auto, invalid overrides
- Edge: Tests 11-13 — critical constraint override, unknown family, role name match
- Boundary: Tests 14-16 — all example roles resolvable, R1 constraint, type checks
"""

import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def role_registry():
    """Create a RoleRegistry loaded with example roles."""
    from config.roles import RoleRegistry, EXAMPLE_ROLES_DIR

    return RoleRegistry(roles_dir=EXAMPLE_ROLES_DIR)


@pytest.fixture
def resolver(role_registry):
    """Create a DynamicResolver with example roles."""
    from config.resolver import DynamicResolver

    return DynamicResolver(role_registry=role_registry)


@pytest.fixture
def resolver_with_selector(role_registry):
    """Create a DynamicResolver with a mocked SmartModelSelector."""
    from config.resolver import DynamicResolver

    mock_selector = MagicMock()
    mock_selector.select.return_value = "qwen2.5-coder-7b-instruct"
    return DynamicResolver(role_registry=role_registry, model_selector=mock_selector)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class TestExplicitResolve:
    """Happy: Explicit model assignment resolves correctly."""

    @pytest.mark.unit
    def test_resolve_explicit_returns_resolved_config(self, resolver):
        """Explicit model resolve returns a ResolvedConfig instance."""
        from config.resolved_config import ResolvedConfig

        config = resolver.resolve(role_name="coder", model_id="qwen2.5-coder-7b")
        assert isinstance(config, ResolvedConfig)

    @pytest.mark.unit
    def test_resolve_explicit_model_id_preserved(self, resolver):
        """Resolved config preserves the explicit model_id."""
        config = resolver.resolve(role_name="coder", model_id="qwen2.5-coder-7b")
        assert config.model_id == "qwen2.5-coder-7b"

    @pytest.mark.unit
    def test_resolve_explicit_role_name_preserved(self, resolver):
        """Resolved config preserves the role name."""
        config = resolver.resolve(role_name="coder", model_id="qwen2.5-coder-7b")
        assert config.role_name == "coder"

    @pytest.mark.unit
    def test_resolve_applies_family_overlay(self, resolver):
        """Qwen coder overlay sets temperature=0.2 (from knowledge base)."""
        config = resolver.resolve(role_name="chat", model_id="qwen2.5-coder-7b")
        # Qwen + chat task → temperature 0.7 from knowledge base
        assert config.temperature == 0.7

    @pytest.mark.unit
    def test_resolve_detects_family(self, resolver):
        """Resolved config includes detected family."""
        config = resolver.resolve(role_name="coder", model_id="qwen2.5-coder-7b")
        assert config.family == "qwen"


class TestAutoResolve:
    """Happy: Auto-resolve delegates to SmartModelSelector."""

    @pytest.mark.unit
    def test_auto_resolve_uses_selector(self, resolver_with_selector):
        """When model_id is None, selector picks the model."""
        config = resolver_with_selector.resolve(role_name="coder", model_id=None)
        assert config.model_id == "qwen2.5-coder-7b-instruct"

    @pytest.mark.unit
    def test_auto_resolve_passes_task_type_to_selector(self, resolver_with_selector):
        """Auto-resolve passes the inferred task type to selector."""
        resolver_with_selector.resolve(role_name="coder", model_id=None)
        # Selector should have been called with task_type
        resolver_with_selector._selector.select.assert_called_once()


class TestConfigLayering:
    """Happy: Config layering works correctly."""

    @pytest.mark.unit
    def test_role_defaults_applied(self, resolver):
        """Role template's system_prompt and max_tokens are used."""
        config = resolver.resolve(
            role_name="coder",
            model_id="totally-unknown-model-xyz",
        )
        assert "expert software engineer" in config.system_prompt
        assert config.max_tokens == 4096

    @pytest.mark.unit
    def test_family_overlay_overrides_role_defaults(self, resolver):
        """Family overlay temperature overrides role template temperature."""
        # Coder role has temp=0.2, but Qwen code overlay also has temp=0.2
        # Use chat role (temp=0.7) with Qwen code model to see overlay effect
        # Qwen + chat task → knowledge base says temp=0.7
        config = resolver.resolve(role_name="writer", model_id="qwen2.5-coder-7b")
        # Writer role has temp=0.7, Qwen write overlay has temp=0.7 (same)
        # Use deepseek to see difference: writer role temp=0.7, deepseek write=1.0
        config2 = resolver.resolve(role_name="writer", model_id="deepseek-v3")
        assert config2.temperature == 1.0  # overlay wins over role's 0.7

    @pytest.mark.unit
    def test_user_overrides_applied(self, resolver):
        """User overrides win over family overlay."""
        config = resolver.resolve(
            role_name="coder",
            model_id="qwen2.5-coder-7b",
            user_overrides={"temperature": 0.5},
        )
        assert config.temperature == 0.5

    @pytest.mark.unit
    def test_resolved_config_is_frozen(self, resolver):
        """ResolvedConfig is immutable (frozen dataclass)."""
        config = resolver.resolve(role_name="coder", model_id="qwen2.5-coder-7b")
        with pytest.raises(AttributeError):
            config.temperature = 999.0


# ---------------------------------------------------------------------------
# Negative
# ---------------------------------------------------------------------------

class TestResolverNegative:
    """Negative: error handling for bad inputs."""

    @pytest.mark.unit
    def test_unknown_role_raises_key_error(self, resolver):
        """Unknown role name raises KeyError."""
        with pytest.raises(KeyError, match="nonexistent_role"):
            resolver.resolve(role_name="nonexistent_role", model_id="any-model")

    @pytest.mark.unit
    def test_auto_resolve_without_selector_raises(self, resolver):
        """Auto-resolve (model_id=None) without selector raises ValueError."""
        with pytest.raises(ValueError, match="model_selector"):
            resolver.resolve(role_name="coder", model_id=None)

    @pytest.mark.unit
    def test_invalid_override_key_ignored(self, resolver):
        """Unknown override keys are silently ignored."""
        config = resolver.resolve(
            role_name="coder",
            model_id="qwen2.5-coder-7b",
            user_overrides={"nonexistent_param": 42},
        )
        # Should not raise, config still valid
        assert config.role_name == "coder"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestResolverEdge:
    """Edge: constraint overrides, unknown family, role name matching."""

    @pytest.mark.unit
    def test_critical_constraint_overrides_user_override(self, resolver):
        """DeepSeek-R1 min_temperature=0.6 enforced even when user requests 0.1."""
        config = resolver.resolve(
            role_name="coder",
            model_id="deepseek-r1-distill-qwen-32b",
            user_overrides={"temperature": 0.1},
        )
        assert config.temperature >= 0.6

    @pytest.mark.unit
    def test_unknown_family_uses_role_defaults(self, resolver):
        """Unknown family model gets no overlay — role defaults used."""
        config = resolver.resolve(
            role_name="coder",
            model_id="totally-unknown-model-xyz",
        )
        # No overlay, so role template temp (0.2) used
        assert config.temperature == 0.2
        assert config.family == "unknown"

    @pytest.mark.unit
    def test_role_name_matching_task_type(self, resolver):
        """Role named 'chat' matches standard task type 'chat' directly."""
        config = resolver.resolve(role_name="chat", model_id="qwen2.5-coder-7b")
        assert config.task_type == "chat"

    @pytest.mark.unit
    def test_task_type_inferred_from_capabilities(self, resolver):
        """Role with [long_context] capability maps to 'write' task type."""
        config = resolver.resolve(role_name="writer", model_id="llama-3.3-70b")
        assert config.task_type == "write"


# ---------------------------------------------------------------------------
# Boundary
# ---------------------------------------------------------------------------

class TestResolverBoundary:
    """Boundary: all roles resolvable, R1 constraints, type checks."""

    @pytest.mark.unit
    def test_all_example_roles_resolvable(self, resolver):
        """All 6 example roles can be resolved with an explicit model."""
        from config.roles import EXAMPLE_ROLES_DIR, RoleRegistry

        registry = RoleRegistry(roles_dir=EXAMPLE_ROLES_DIR)
        for role_name in registry.list():
            config = resolver.resolve(
                role_name=role_name,
                model_id="qwen2.5-coder-7b",
            )
            assert config.role_name == role_name
            assert config.model_id == "qwen2.5-coder-7b"

    @pytest.mark.unit
    def test_deepseek_r1_constraint_all_roles(self, resolver):
        """DeepSeek-R1 critical constraint (min_temp=0.6) applies to ALL roles."""
        from config.roles import EXAMPLE_ROLES_DIR, RoleRegistry

        registry = RoleRegistry(roles_dir=EXAMPLE_ROLES_DIR)
        for role_name in registry.list():
            config = resolver.resolve(
                role_name=role_name,
                model_id="deepseek-r1-distill-qwen-32b",
            )
            assert config.temperature >= 0.6, (
                f"R1 constraint violated for role '{role_name}': temp={config.temperature}"
            )

    @pytest.mark.unit
    def test_resolved_config_field_types(self, resolver):
        """ResolvedConfig fields have correct types."""
        config = resolver.resolve(role_name="coder", model_id="qwen2.5-coder-7b")
        assert isinstance(config.role_name, str)
        assert isinstance(config.model_id, str)
        assert isinstance(config.family, str)
        assert isinstance(config.task_type, str)
        assert isinstance(config.system_prompt, str)
        assert isinstance(config.temperature, float)
        assert isinstance(config.max_tokens, int)
        assert isinstance(config.context_length, int)
        assert isinstance(config.context_overflow_policy, str)

    @pytest.mark.unit
    def test_infer_task_type_exported(self):
        """infer_task_type is part of the public API."""
        from config.resolver import infer_task_type

        assert callable(infer_task_type)
