"""Tests for concurrent autonomous session safety (M17)."""

import threading
from config import get_config


class TestSingletonThreadSafety:
    """Verify singletons are safe under concurrent access."""

    def test_get_config_returns_same_instance(self):
        """get_config() should return the same instance from multiple threads."""
        results = []

        def get_config_instance():
            config = get_config()
            results.append(id(config))

        threads = [threading.Thread(target=get_config_instance) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All threads should get the same config instance
        assert len(set(results)) == 1, f"Expected 1 unique config instance, got {len(set(results))}"

    def test_get_registry_returns_same_instance(self):
        """get_registry() should return the same instance from multiple threads."""
        from model_registry.registry import get_registry

        results = []

        def get_registry_instance():
            registry = get_registry()
            results.append(id(registry))

        threads = [threading.Thread(target=get_registry_instance) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All threads should get the same registry instance
        assert len(set(results)) == 1, f"Expected 1 unique registry instance, got {len(set(results))}"
