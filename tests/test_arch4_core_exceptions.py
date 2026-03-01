"""Tests for ARCH-4: core.exceptions import paths and hierarchy.

Verifies that exceptions moved from llm/exceptions.py to core/exceptions.py
preserve the hierarchy, remain importable from both paths, and fix the
upward dependency from utils/ → llm/.

Test categories (Req 07):
- Happy: Tests 1, 2, 3 — import from core.exceptions and llm.exceptions both work
- Negative: Test 4 — non-existent exception raises ImportError
- Edge: Test 5 — hierarchy preserved (isinstance checks)
- Boundary: Test 6 — every __all__ entry importable from both paths
- Edge: Test 7 — production files import from core, not llm
"""

import ast
import importlib
import pathlib

import pytest


EXPECTED_ALL = [
    "LLMError",
    "LLMTimeoutError",
    "LLMRateLimitError",
    "LLMValidationError",
    "LLMConnectionError",
    "LLMResponseError",
    "ModelNotFoundError",
    "ModelMemoryError",
    "get_error_type",
]


class TestCoreExceptionsImport:
    """Happy: Import from core.exceptions works."""

    def test_import_from_core(self) -> None:
        from core.exceptions import LLMError, ModelNotFoundError

        assert issubclass(ModelNotFoundError, LLMError)

    def test_import_get_error_type_from_core(self) -> None:
        from core.exceptions import LLMError, get_error_type

        err = LLMError("test")
        assert get_error_type(err) == "LLMError"


class TestLlmExceptionsBackwardCompat:
    """Happy: Import from llm.exceptions still works (re-export shim)."""

    def test_import_from_llm_still_works(self) -> None:
        from llm.exceptions import LLMError, ModelNotFoundError

        assert issubclass(ModelNotFoundError, LLMError)

    def test_same_class_from_both_paths(self) -> None:
        from core.exceptions import LLMError as CoreLLMError
        from llm.exceptions import LLMError as LlmLLMError

        assert CoreLLMError is LlmLLMError


class TestNonexistentRaises:
    """Negative: Non-existent exception raises ImportError."""

    def test_nonexistent_from_core(self) -> None:
        with pytest.raises(ImportError):
            from core.exceptions import NonExistentError  # noqa: F401


class TestHierarchyPreserved:
    """Edge: Full exception hierarchy preserved after move."""

    def test_hierarchy(self) -> None:
        from core.exceptions import (
            LLMConnectionError,
            LLMError,
            LLMRateLimitError,
            LLMResponseError,
            LLMTimeoutError,
            LLMValidationError,
            ModelMemoryError,
            ModelNotFoundError,
        )

        # Direct subclasses of LLMError
        assert issubclass(LLMTimeoutError, LLMError)
        assert issubclass(LLMRateLimitError, LLMError)
        assert issubclass(LLMValidationError, LLMError)
        assert issubclass(LLMConnectionError, LLMError)
        assert issubclass(LLMResponseError, LLMError)
        assert issubclass(ModelMemoryError, LLMError)

        # ModelNotFoundError inherits from LLMValidationError
        assert issubclass(ModelNotFoundError, LLMValidationError)
        assert issubclass(ModelNotFoundError, LLMError)

    def test_isinstance_works(self) -> None:
        from core.exceptions import LLMError, LLMTimeoutError

        err = LLMTimeoutError("timeout")
        assert isinstance(err, LLMError)
        assert isinstance(err, LLMTimeoutError)
        assert isinstance(err, Exception)


class TestAllConsistency:
    """Boundary: Every __all__ entry importable from both core and llm paths."""

    def test_all_importable_from_core(self) -> None:
        mod = importlib.import_module("core.exceptions")
        all_names = getattr(mod, "__all__", [])
        assert set(all_names) == set(EXPECTED_ALL)
        for name in all_names:
            assert hasattr(mod, name), f"{name} in __all__ but not accessible"

    def test_all_importable_from_llm(self) -> None:
        mod = importlib.import_module("llm.exceptions")
        all_names = getattr(mod, "__all__", [])
        assert set(all_names) == set(EXPECTED_ALL)
        for name in all_names:
            assert hasattr(mod, name), f"{name} in __all__ but not accessible"


class TestProductionImportsFromCore:
    """Edge: utils/ and tools/ import from core.exceptions, not llm.exceptions."""

    def test_utils_lms_helper_imports_from_core(self) -> None:
        source = pathlib.Path("utils/lms_helper.py").read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and "llm.exceptions" in node.module:
                    pytest.fail(
                        f"utils/lms_helper.py still imports from llm.exceptions "
                        f"(line {node.lineno}): should use core.exceptions"
                    )

    def test_tools_dynamic_autonomous_imports_from_core(self) -> None:
        source = pathlib.Path("tools/dynamic_autonomous.py").read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and "llm.exceptions" in node.module:
                    pytest.fail(
                        f"tools/dynamic_autonomous.py still imports from llm.exceptions "
                        f"(line {node.lineno}): should use core.exceptions"
                    )

    def test_tools_completions_imports_from_core(self) -> None:
        source = pathlib.Path("tools/completions.py").read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and "llm.exceptions" in node.module:
                    pytest.fail(
                        f"tools/completions.py still imports from llm.exceptions "
                        f"(line {node.lineno}): should use core.exceptions"
                    )
