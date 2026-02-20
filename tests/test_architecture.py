"""Architecture guard tests to prevent regressions."""

import ast
import os

import pytest


class TestNoDeadPackages:
    """Verify deleted packages stay deleted."""

    def test_adapters_directory_does_not_exist(self):
        """adapters/ was removed in B1 — must not be recreated."""
        assert not os.path.isdir("adapters"), "adapters/ directory should not exist (removed in B1)"

    def test_app_directory_does_not_exist(self):
        """app/ was removed in B1 — must not be recreated."""
        assert not os.path.isdir("app"), "app/ directory should not exist (removed in B1)"

    def test_domain_directory_does_not_exist(self):
        """domain/ was removed in B1 — must not be recreated."""
        assert not os.path.isdir("domain"), "domain/ directory should not exist (removed in B1)"


class TestNoDeprecatedAutonomous:
    """Verify deprecated autonomous.py stays removed."""

    def test_autonomous_py_does_not_exist(self):
        """tools/autonomous.py was removed in C1 — must not be recreated."""
        assert not os.path.exists("tools/autonomous.py"), (
            "tools/autonomous.py should not exist (deprecated, removed in C1)"
        )

    def test_no_autonomous_imports_in_main(self):
        """main.py must not import from tools.autonomous (removed in C1)."""
        with open("main.py", "r") as f:
            content = f.read()

        assert "from tools.autonomous" not in content, (
            "main.py still imports from tools.autonomous (should use dynamic_autonomous)"
        )

    def test_no_autonomous_in_tools_init(self):
        """tools/__init__.py must not reference autonomous module (removed in C1)."""
        with open("tools/__init__.py", "r") as f:
            content = f.read()

        assert "autonomous" not in content.lower() or "dynamic_autonomous" in content.lower(), (
            "tools/__init__.py still references deprecated autonomous module"
        )


class TestPhase2Invariants:
    """Guards for Phase 2 dedup and consolidation (OPP-05 through OPP-10)."""

    def test_no_autonomous_loop_multi_mcp(self):
        """_autonomous_loop_multi_mcp was unified into _autonomous_loop in OPP-05."""
        with open("tools/dynamic_autonomous.py", "r") as f:
            tree = ast.parse(f.read())
        method_names = [
            node.name for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        assert "_autonomous_loop_multi_mcp" not in method_names, (
            "_autonomous_loop_multi_mcp should not exist (unified in OPP-05)"
        )

    def test_preload_helper_exists(self):
        """_preload_and_validate_model was extracted in OPP-05."""
        with open("tools/dynamic_autonomous.py", "r") as f:
            tree = ast.parse(f.read())
        method_names = [
            node.name for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        assert "_preload_and_validate_model" in method_names, (
            "_preload_and_validate_model must exist (extracted in OPP-05)"
        )

    def test_single_ensure_model_loaded_call_site(self):
        """ensure_model_loaded_with_verification must appear exactly once in LLMClient (inside _ensure_model_loaded)."""
        with open("llm/llm_client.py", "r") as f:
            content = f.read()
        count = content.count("ensure_model_loaded_with_verification")
        assert count == 1, (
            f"ensure_model_loaded_with_verification appears {count} times, expected 1 "
            f"(should only be inside _ensure_model_loaded, OPP-09)"
        )

    def test_retry_logic_is_shim(self):
        """retry_logic.py was converted to deprecation shim in OPP-06."""
        with open("utils/retry_logic.py", "r") as f:
            content = f.read()
        assert "DEPRECATED" in content or "deprecated" in content, (
            "retry_logic.py should contain deprecation notice (OPP-06 shim)"
        )
        assert "from utils.error_handling import" in content or "from .error_handling import" in content, (
            "retry_logic.py should import from error_handling (OPP-06 shim)"
        )

    def test_no_stale_toolcalltracker_export(self):
        """ToolCallTracker was removed from message_manager.__all__ in OPP-09."""
        with open("llm/message_manager.py", "r") as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        if isinstance(node.value, ast.List):
                            exports = [
                                elt.value for elt in node.value.elts
                                if isinstance(elt, ast.Constant)
                            ]
                            assert "ToolCallTracker" not in exports, (
                                "ToolCallTracker must not be in __all__ (removed in OPP-09)"
                            )
                            return
        pytest.fail("Could not find __all__ in message_manager.py")

    def test_no_hardcoded_ttl_600_in_llm_client(self):
        """JIT guards must use constants, not magic number ttl=600 (fixed in OPP-09)."""
        with open("llm/llm_client.py", "r") as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.keyword) and node.arg == "ttl":
                if isinstance(node.value, ast.Constant) and node.value.value == 600:
                    pytest.fail(
                        "Found hardcoded ttl=600 in llm_client.py "
                        "(must use JIT_TTL_DEFAULT or JIT_TTL_EMBEDDING, OPP-09)"
                    )
