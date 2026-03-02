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
        """ensure_model_loaded_with_verification must appear exactly once in jit_loader (the canonical location)."""
        with open("llm/jit_loader.py", "r") as f:
            content = f.read()
        count = content.count("ensure_model_loaded_with_verification")
        assert count == 1, (
            f"ensure_model_loaded_with_verification appears {count} times, expected 1 "
            f"(should only be inside jit_loader.ensure_model_loaded, OPP-09)"
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


class TestRoundAInvariants:
    """Guards for Round A features (OPP-11 through OPP-07)."""

    def test_anthropic_messages_method_exists(self):
        """OPP-11: LLMClient.anthropic_messages exists."""
        from llm.llm_client import LLMClient
        assert hasattr(LLMClient, 'anthropic_messages')

    def test_anthropic_constants_defined(self):
        """OPP-11: ANTHROPIC_MESSAGES_ENDPOINT in constants."""
        from config.constants import ANTHROPIC_MESSAGES_ENDPOINT
        assert ANTHROPIC_MESSAGES_ENDPOINT == "messages"

    def test_anthropic_tool_converters_exist(self):
        """OPP-13: 3 Anthropic tool static methods on LLMClient."""
        from llm.llm_client import LLMClient
        assert hasattr(LLMClient, 'convert_tools_to_anthropic_format')
        assert hasattr(LLMClient, 'extract_anthropic_tool_calls')
        assert hasattr(LLMClient, 'build_anthropic_tool_result')

    def test_native_mcp_detection_exists(self):
        """OPP-16: supports_native_mcp() method exists."""
        from llm.llm_client import LLMClient
        assert hasattr(LLMClient, 'supports_native_mcp')

    def test_compatibility_type_field(self):
        """OPP-05: ModelMetadata.compatibility_type field exists."""
        from model_registry.schemas import ModelMetadata
        import dataclasses
        field_names = [f.name for f in dataclasses.fields(ModelMetadata)]
        assert 'compatibility_type' in field_names

    def test_parallel_tools_parameter(self):
        """OPP-06: _autonomous_loop accepts parallel_tools."""
        import inspect
        from tools.dynamic_autonomous import DynamicAutonomousAgent
        sig = inspect.signature(DynamicAutonomousAgent._autonomous_loop)
        assert 'parallel_tools' in sig.parameters

    def test_loop_metrics_module(self):
        """OPP-07: tools/loop_metrics.py importable."""
        from tools.loop_metrics import LoopMetrics, RoundMetrics
        assert LoopMetrics is not None
        assert RoundMetrics is not None

    def test_no_hardcoded_anthropic_endpoint(self):
        """Scan ENTIRE codebase for raw '/v1/messages' not in constants/tests/docs."""
        import os
        for dirpath in ['llm/', 'tools/']:
            for root, dirs, files in os.walk(dirpath):
                for fname in files:
                    if fname.endswith('.py') and 'test_' not in fname:
                        filepath = os.path.join(root, fname)
                        with open(filepath) as f:
                            in_docstring = False
                            docstring_marker = None
                            for i, line in enumerate(f, 1):
                                stripped = line.lstrip()
                                # Track docstring state
                                if not in_docstring:
                                    for marker in ('"""', "'''"):
                                        if marker in stripped:
                                            # Count occurrences: odd number means we entered
                                            if stripped.count(marker) % 2 == 1:
                                                in_docstring = True
                                                docstring_marker = marker
                                            break
                                    if in_docstring:
                                        continue  # Opening docstring line — skip
                                else:
                                    # Inside a docstring — check for closing marker
                                    if docstring_marker in line:
                                        in_docstring = False
                                        docstring_marker = None
                                    continue  # Still inside docstring — skip entire line

                                if '/v1/messages' not in line:
                                    continue
                                if 'ANTHROPIC_MESSAGES_ENDPOINT' in line:
                                    continue
                                # Skip comment lines
                                if stripped.startswith('#'):
                                    continue
                                assert False, f"Hardcoded /v1/messages at {filepath}:{i}"

    def test_loop_returns_str_not_tuple(self):
        """OPP-07 uses instance attribute, NOT tuple return."""
        import inspect
        from tools.dynamic_autonomous import DynamicAutonomousAgent
        sig = inspect.signature(DynamicAutonomousAgent._autonomous_loop)
        ret = sig.return_annotation
        assert ret is inspect.Parameter.empty or ret == str or ret == 'str', \
            f"_autonomous_loop return type should be str, got {ret}"

class TestSingleSourceOfTruth:
    """Guards for DEFAULT_MAX_RETRIES consolidation — single source of truth."""

    def test_chat_client_does_not_define_local_default_max_retries(self):
        """chat_client.py must NOT define its own DEFAULT_MAX_RETRIES assignment."""
        with open("llm/chat_client.py", "r") as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "DEFAULT_MAX_RETRIES":
                        pytest.fail(
                            "chat_client.py defines its own DEFAULT_MAX_RETRIES — "
                            "must import from config.constants instead"
                        )

    def test_chat_client_imports_default_max_retries_from_constants(self):
        """chat_client.py must import DEFAULT_MAX_RETRIES from config.constants."""
        with open("llm/chat_client.py", "r") as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if "config" in module and "constants" in module:
                    names = [alias.name for alias in node.names]
                    if "DEFAULT_MAX_RETRIES" in names:
                        return  # Found the correct import
        pytest.fail(
            "chat_client.py does not import DEFAULT_MAX_RETRIES from config.constants"
        )

    def test_chat_client_no_plus_one_at_retry_call_sites(self):
        """Call sites must not pass DEFAULT_MAX_RETRIES + 1 — the constant already encodes 3 total."""
        with open("llm/chat_client.py", "r") as f:
            content = f.read()
        assert "DEFAULT_MAX_RETRIES + 1" not in content, (
            "chat_client.py still uses DEFAULT_MAX_RETRIES + 1 at call sites — "
            "after consolidation, pass DEFAULT_MAX_RETRIES directly (value=3 = total attempts)"
        )

    def test_constants_default_max_retries_equals_three(self):
        """config.constants.DEFAULT_MAX_RETRIES must equal 3 (total attempts for retry_with_backoff)."""
        from config.constants import DEFAULT_MAX_RETRIES
        assert DEFAULT_MAX_RETRIES == 3, (
            f"config.constants.DEFAULT_MAX_RETRIES should be 3 (total attempts), got {DEFAULT_MAX_RETRIES}"
        )
