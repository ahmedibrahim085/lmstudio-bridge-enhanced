"""Tests for e2e timeout configuration enforcement.

Verifies that ALL @pytest.mark.e2e test methods:
1. Have @pytest.mark.timeout(LONG_TEST_TIMEOUT) to prevent indefinite hangs
2. Use max_rounds <= E2E_TEST_MAX_ROUNDS to keep within timeout budget

Budget math: E2E_TEST_MAX_ROUNDS(5) × DEFAULT_LLM_TIMEOUT(58s) = 290s < LONG_TEST_TIMEOUT(300s)

RED phase: These tests FAIL because:
- 0 of 8 e2e methods have @pytest.mark.timeout
- Several methods use max_rounds > E2E_TEST_MAX_ROUNDS (10, 15, 20, 30)
"""

from __future__ import annotations

import ast
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.test_constants import E2E_TEST_MAX_ROUNDS

# Path to the e2e test file under inspection
E2E_TEST_FILE = os.path.join(os.path.dirname(__file__), "test_e2e_multi_model.py")


def _parse_e2e_test_file() -> ast.Module:
    """Parse the e2e test file into an AST."""
    with open(E2E_TEST_FILE) as f:
        return ast.parse(f.read(), filename=E2E_TEST_FILE)


def _get_e2e_methods(tree: ast.Module) -> list[ast.AsyncFunctionDef | ast.FunctionDef]:
    """Find all methods decorated with @pytest.mark.e2e."""
    methods: list[ast.AsyncFunctionDef | ast.FunctionDef] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            for decorator in node.decorator_list:
                if _is_pytest_mark(decorator, "e2e"):
                    methods.append(node)
                    break
    return methods


def _is_pytest_mark(node: ast.expr, mark_name: str) -> bool:
    """Check if a decorator is @pytest.mark.<mark_name> or @pytest.mark.<mark_name>(...)."""
    # @pytest.mark.e2e (Attribute form)
    if isinstance(node, ast.Attribute) and node.attr == mark_name:
        if isinstance(node.value, ast.Attribute) and node.value.attr == "mark":
            if isinstance(node.value.value, ast.Name) and node.value.value.id == "pytest":
                return True
    # @pytest.mark.e2e(...) (Call form)
    if isinstance(node, ast.Call):
        return _is_pytest_mark(node.func, mark_name)
    return False


def _has_timeout_marker(method: ast.AsyncFunctionDef | ast.FunctionDef) -> bool:
    """Check if method has @pytest.mark.timeout decorator."""
    for decorator in method.decorator_list:
        if _is_pytest_mark(decorator, "timeout"):
            return True
    return False


def _get_max_rounds_literals(method: ast.AsyncFunctionDef | ast.FunctionDef) -> list[int]:
    """Extract all literal max_rounds=N values from method body."""
    values: list[int] = []
    for node in ast.walk(method):
        if isinstance(node, ast.keyword) and node.arg == "max_rounds":
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, int):
                values.append(node.value.value)
    return values


@pytest.mark.unit
class TestE2ETimeoutConfig:
    """Verify e2e tests have proper timeout and max_rounds configuration."""

    def test_all_e2e_methods_have_timeout_marker(self):
        """Every @pytest.mark.e2e method must also have @pytest.mark.timeout(LONG_TEST_TIMEOUT).

        Without timeout markers, e2e tests can hang indefinitely when LM Studio
        is slow or unresponsive. The timeout budget is LONG_TEST_TIMEOUT (300s).
        """
        tree = _parse_e2e_test_file()
        e2e_methods = _get_e2e_methods(tree)

        assert len(e2e_methods) > 0, "Should find at least 1 e2e method"

        missing_timeout = [
            m.name for m in e2e_methods if not _has_timeout_marker(m)
        ]

        assert missing_timeout == [], (
            f"{len(missing_timeout)} e2e methods missing @pytest.mark.timeout: "
            f"{missing_timeout}"
        )

    def test_no_e2e_method_uses_excessive_max_rounds(self):
        """No e2e method should use literal max_rounds > E2E_TEST_MAX_ROUNDS.

        Budget: E2E_TEST_MAX_ROUNDS(5) × DEFAULT_LLM_TIMEOUT(58s) = 290s
        This must fit within LONG_TEST_TIMEOUT(300s).

        Methods using named constants (SHORT_MAX_ROUNDS, etc.) are allowed
        as long as their value is <= E2E_TEST_MAX_ROUNDS. This test only
        catches hardcoded literals that exceed the budget.
        """
        tree = _parse_e2e_test_file()
        e2e_methods = _get_e2e_methods(tree)

        violations: list[tuple[str, int]] = []
        for method in e2e_methods:
            for value in _get_max_rounds_literals(method):
                if value > E2E_TEST_MAX_ROUNDS:
                    violations.append((method.name, value))

        assert violations == [], (
            f"E2E methods with max_rounds > {E2E_TEST_MAX_ROUNDS}: "
            + ", ".join(f"{name}(max_rounds={v})" for name, v in violations)
        )
