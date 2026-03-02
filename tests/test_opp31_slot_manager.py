"""Tests for OPP-31 Phase 4: AgentSlotManager concurrent slot lifecycle.

Covers:
  - create_slot creates a named slot with resolved config
  - get_slot retrieves a slot by name
  - list_slots returns all active slots
  - remove_slot removes a slot cleanly
  - Thread safety via threading.Lock
  - Error handling for duplicate names and missing slots

Test categories (Req 07):
- Happy: Tests 1-8 — create, get, list, remove, multi-slot
- Negative: Tests 9-12 — duplicate name, missing slot, remove missing
- Edge: Tests 13-15 — same role different slots, re-create after remove
- Boundary: Tests 16-18 — concurrent create/remove, 10+ slots, empty manager
"""

import os
import sys
import threading

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
def manager(resolver):
    """Create an AgentSlotManager with resolver."""
    from config.slot_manager import AgentSlotManager

    return AgentSlotManager(resolver=resolver)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class TestSlotCreation:
    """Happy: create_slot creates named slots with resolved config."""

    @pytest.mark.unit
    def test_create_slot_returns_resolved_config(self, manager):
        """create_slot returns a ResolvedConfig."""
        from config.resolved_config import ResolvedConfig

        config = manager.create_slot(
            name="my-coder", role="coder", model_id="qwen2.5-coder-7b",
        )
        assert isinstance(config, ResolvedConfig)

    @pytest.mark.unit
    def test_create_slot_preserves_name(self, manager):
        """Created slot uses the given name."""
        config = manager.create_slot(
            name="my-coder", role="coder", model_id="qwen2.5-coder-7b",
        )
        assert config.role_name == "coder"
        assert config.model_id == "qwen2.5-coder-7b"

    @pytest.mark.unit
    def test_create_slot_with_overrides(self, manager):
        """create_slot passes user overrides to resolver."""
        config = manager.create_slot(
            name="hot-writer",
            role="writer",
            model_id="llama-3.3-70b",
            overrides={"temperature": 0.9},
        )
        assert config.temperature == 0.9


class TestSlotRetrieval:
    """Happy: get_slot and list_slots work correctly."""

    @pytest.mark.unit
    def test_get_slot_retrieves_by_name(self, manager):
        """get_slot returns the config for a named slot."""
        manager.create_slot(name="my-coder", role="coder", model_id="qwen2.5-coder-7b")
        config = manager.get_slot("my-coder")
        assert config.role_name == "coder"

    @pytest.mark.unit
    def test_list_slots_returns_all(self, manager):
        """list_slots returns info for all active slots."""
        manager.create_slot(name="coder-1", role="coder", model_id="qwen2.5-coder-7b")
        manager.create_slot(name="tester-1", role="tester", model_id="phi-4")
        slots = manager.list_slots()
        assert len(slots) == 2
        names = {s["name"] for s in slots}
        assert names == {"coder-1", "tester-1"}

    @pytest.mark.unit
    def test_list_slots_empty_manager(self, manager):
        """list_slots returns empty list when no slots exist."""
        slots = manager.list_slots()
        assert slots == []

    @pytest.mark.unit
    def test_list_slots_includes_role_and_model(self, manager):
        """list_slots entries include role and model info."""
        manager.create_slot(name="my-coder", role="coder", model_id="qwen2.5-coder-7b")
        slots = manager.list_slots()
        assert slots[0]["role"] == "coder"
        assert slots[0]["model_id"] == "qwen2.5-coder-7b"


class TestSlotRemoval:
    """Happy: remove_slot removes slots cleanly."""

    @pytest.mark.unit
    def test_remove_slot_removes_by_name(self, manager):
        """remove_slot removes the named slot."""
        manager.create_slot(name="my-coder", role="coder", model_id="qwen2.5-coder-7b")
        manager.remove_slot("my-coder")
        assert manager.list_slots() == []

    @pytest.mark.unit
    def test_remove_slot_does_not_affect_others(self, manager):
        """Removing one slot leaves others intact."""
        manager.create_slot(name="coder-1", role="coder", model_id="qwen2.5-coder-7b")
        manager.create_slot(name="tester-1", role="tester", model_id="phi-4")
        manager.remove_slot("coder-1")
        slots = manager.list_slots()
        assert len(slots) == 1
        assert slots[0]["name"] == "tester-1"


# ---------------------------------------------------------------------------
# Negative
# ---------------------------------------------------------------------------

class TestSlotManagerNegative:
    """Negative: error handling for bad inputs."""

    @pytest.mark.unit
    def test_duplicate_name_raises(self, manager):
        """Creating a slot with existing name raises ValueError."""
        manager.create_slot(name="my-coder", role="coder", model_id="qwen2.5-coder-7b")
        with pytest.raises(ValueError, match="my-coder"):
            manager.create_slot(name="my-coder", role="coder", model_id="phi-4")

    @pytest.mark.unit
    def test_get_missing_slot_raises(self, manager):
        """Getting a nonexistent slot raises KeyError."""
        with pytest.raises(KeyError, match="nonexistent"):
            manager.get_slot("nonexistent")

    @pytest.mark.unit
    def test_remove_missing_slot_raises(self, manager):
        """Removing a nonexistent slot raises KeyError."""
        with pytest.raises(KeyError, match="nonexistent"):
            manager.remove_slot("nonexistent")

    @pytest.mark.unit
    def test_create_with_unknown_role_raises(self, manager):
        """Creating a slot with unknown role propagates KeyError from resolver."""
        with pytest.raises(KeyError):
            manager.create_slot(name="bad", role="nonexistent_role", model_id="any")


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestSlotManagerEdge:
    """Edge: same role multi-slot, re-create after remove."""

    @pytest.mark.unit
    def test_same_role_different_slots(self, manager):
        """Two slots can use the same role with different models."""
        config1 = manager.create_slot(
            name="coder-qwen", role="coder", model_id="qwen2.5-coder-7b",
        )
        config2 = manager.create_slot(
            name="coder-llama", role="coder", model_id="llama-3.3-70b",
        )
        assert config1.family == "qwen"
        assert config2.family == "llama"

    @pytest.mark.unit
    def test_recreate_after_remove(self, manager):
        """Slot name can be reused after removal."""
        manager.create_slot(name="my-coder", role="coder", model_id="qwen2.5-coder-7b")
        manager.remove_slot("my-coder")
        config = manager.create_slot(
            name="my-coder", role="writer", model_id="llama-3.3-70b",
        )
        assert config.role_name == "writer"

    @pytest.mark.unit
    def test_slot_config_is_immutable(self, manager):
        """Slot configs are frozen — modifying doesn't affect manager."""
        manager.create_slot(name="my-coder", role="coder", model_id="qwen2.5-coder-7b")
        config = manager.get_slot("my-coder")
        with pytest.raises(AttributeError):
            config.temperature = 999.0


# ---------------------------------------------------------------------------
# Boundary
# ---------------------------------------------------------------------------

class TestSlotManagerBoundary:
    """Boundary: concurrent access, many slots, thread safety."""

    @pytest.mark.unit
    def test_ten_concurrent_slots(self, manager):
        """Manager handles 10+ simultaneous slots."""
        for i in range(10):
            manager.create_slot(
                name=f"slot-{i}", role="coder", model_id="qwen2.5-coder-7b",
            )
        assert len(manager.list_slots()) == 10

    @pytest.mark.unit
    def test_thread_safe_create(self, manager):
        """Concurrent slot creation is thread-safe (no lost slots)."""
        errors = []

        def create_slot(idx):
            try:
                manager.create_slot(
                    name=f"thread-slot-{idx}",
                    role="coder",
                    model_id="qwen2.5-coder-7b",
                )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=create_slot, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors during concurrent create: {errors}"
        assert len(manager.list_slots()) == 20

    @pytest.mark.unit
    def test_thread_safe_create_and_remove(self, manager):
        """Concurrent create and remove operations don't corrupt state."""
        # Pre-create slots to remove
        for i in range(10):
            manager.create_slot(
                name=f"pre-slot-{i}", role="coder", model_id="qwen2.5-coder-7b",
            )
        errors = []

        def remove_slot(idx):
            try:
                manager.remove_slot(f"pre-slot-{idx}")
            except Exception as e:
                errors.append(e)

        def create_slot(idx):
            try:
                manager.create_slot(
                    name=f"new-slot-{idx}",
                    role="tester",
                    model_id="phi-4",
                )
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(10):
            threads.append(threading.Thread(target=remove_slot, args=(i,)))
            threads.append(threading.Thread(target=create_slot, args=(i,)))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors during concurrent ops: {errors}"
        # All pre-slots removed, all new-slots created
        names = {s["name"] for s in manager.list_slots()}
        assert all(f"new-slot-{i}" in names for i in range(10))
        assert all(f"pre-slot-{i}" not in names for i in range(10))
