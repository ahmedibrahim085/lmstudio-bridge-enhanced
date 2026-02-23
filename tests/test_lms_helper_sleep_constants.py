#!/usr/bin/env python3
"""
TDD tests for F-06: Extract hardcoded sleep durations to constants in lms_helper.py

RED phase: These tests are written FIRST and must fail before implementation.
GREEN phase: Apply changes to constants.py and lms_helper.py to make them pass.
"""

import ast
import re
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

LMS_HELPER_PATH = Path(__file__).parent.parent / "utils" / "lms_helper.py"
CONSTANTS_PATH = Path(__file__).parent.parent / "config" / "constants.py"


def _read_source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Constants exist and have correct values
# ---------------------------------------------------------------------------


class TestConstantsExist:
    """MODEL_REACTIVATION_DELAY and MODEL_LOADING_DELAY must exist in constants."""

    def test_model_reactivation_delay_exists(self):
        """config.constants must export MODEL_REACTIVATION_DELAY."""
        from config import constants

        assert hasattr(constants, "MODEL_REACTIVATION_DELAY"), (
            "MODEL_REACTIVATION_DELAY not found in config.constants"
        )

    def test_model_reactivation_delay_value(self):
        """MODEL_REACTIVATION_DELAY must equal 1 (seconds)."""
        from config.constants import MODEL_REACTIVATION_DELAY

        assert MODEL_REACTIVATION_DELAY == 1, (
            f"Expected MODEL_REACTIVATION_DELAY == 1, got {MODEL_REACTIVATION_DELAY}"
        )

    def test_model_loading_delay_exists(self):
        """config.constants must export MODEL_LOADING_DELAY."""
        from config import constants

        assert hasattr(constants, "MODEL_LOADING_DELAY"), (
            "MODEL_LOADING_DELAY not found in config.constants"
        )

    def test_model_loading_delay_value(self):
        """MODEL_LOADING_DELAY must equal 2 (seconds)."""
        from config.constants import MODEL_LOADING_DELAY

        assert MODEL_LOADING_DELAY == 2, (
            f"Expected MODEL_LOADING_DELAY == 2, got {MODEL_LOADING_DELAY}"
        )


# ---------------------------------------------------------------------------
# 2. lms_helper.py imports the constants at module level
# ---------------------------------------------------------------------------


class TestLmsHelperImportsConstants:
    """lms_helper.py must import both constants from config.constants."""

    def test_imports_model_reactivation_delay(self):
        """lms_helper.py source must import MODEL_REACTIVATION_DELAY from config.constants."""
        source = _read_source(LMS_HELPER_PATH)
        assert "MODEL_REACTIVATION_DELAY" in source, (
            "MODEL_REACTIVATION_DELAY not imported in utils/lms_helper.py"
        )

    def test_imports_model_loading_delay(self):
        """lms_helper.py source must import MODEL_LOADING_DELAY from config.constants."""
        source = _read_source(LMS_HELPER_PATH)
        assert "MODEL_LOADING_DELAY" in source, (
            "MODEL_LOADING_DELAY not imported in utils/lms_helper.py"
        )

    def test_import_is_from_config_constants(self):
        """The import statement must be 'from config.constants import ...'."""
        source = _read_source(LMS_HELPER_PATH)
        # Look for a from-import line that covers both constants
        assert re.search(
            r"from config\.constants import[^\n]*MODEL_REACTIVATION_DELAY",
            source,
        ) or re.search(
            r"from config\.constants import[^\n]*MODEL_LOADING_DELAY",
            source,
        ), (
            "Expected 'from config.constants import MODEL_REACTIVATION_DELAY / MODEL_LOADING_DELAY' "
            "in utils/lms_helper.py"
        )


# ---------------------------------------------------------------------------
# 3. No inline `import time` inside methods/functions (via AST inspection)
# ---------------------------------------------------------------------------


class TestNoInlineImportTime:
    """lms_helper.py must NOT contain inline `import time` inside any function/method body."""

    def _collect_inline_imports(self) -> list[tuple[int, str]]:
        """Return list of (line_no, enclosing_scope) for every `import time` inside a scope."""
        source = _read_source(LMS_HELPER_PATH)
        tree = ast.parse(source, filename=str(LMS_HELPER_PATH))

        violations: list[tuple[int, str]] = []

        for node in ast.walk(tree):
            # Any function or method body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for child in ast.walk(node):
                    if isinstance(child, ast.Import):
                        for alias in child.names:
                            if alias.name == "time":
                                violations.append((child.lineno, node.name))

        return violations

    def test_no_inline_import_time_in_methods(self):
        """There must be zero `import time` statements inside function/method bodies."""
        violations = self._collect_inline_imports()
        assert violations == [], (
            f"Found inline 'import time' inside methods at lines "
            f"{[(ln, scope) for ln, scope in violations]} in utils/lms_helper.py. "
            "Move 'import time' to module level."
        )


# ---------------------------------------------------------------------------
# 4. time.sleep calls use the constants (not raw literals)
# ---------------------------------------------------------------------------


class TestSleepCallsUseConstants:
    """time.sleep() must be called with MODEL_REACTIVATION_DELAY / MODEL_LOADING_DELAY, not literals."""

    def test_no_time_sleep_with_literal_1(self):
        """time.sleep(1) literal must not appear in lms_helper.py."""
        source = _read_source(LMS_HELPER_PATH)
        # Match time.sleep(1) — allow whitespace, reject if literal int argument
        matches = re.findall(r"time\.sleep\(\s*1\s*\)", source)
        assert matches == [], (
            f"Found {len(matches)} occurrence(s) of time.sleep(1) literal in "
            "utils/lms_helper.py. Use time.sleep(MODEL_REACTIVATION_DELAY) instead."
        )

    def test_no_time_sleep_with_literal_2(self):
        """time.sleep(2) literal must not appear in lms_helper.py."""
        source = _read_source(LMS_HELPER_PATH)
        matches = re.findall(r"time\.sleep\(\s*2\s*\)", source)
        assert matches == [], (
            f"Found {len(matches)} occurrence(s) of time.sleep(2) literal in "
            "utils/lms_helper.py. Use time.sleep(MODEL_LOADING_DELAY) instead."
        )

    def test_sleep_uses_model_reactivation_delay(self):
        """time.sleep(MODEL_REACTIVATION_DELAY) must appear at least once in lms_helper.py."""
        source = _read_source(LMS_HELPER_PATH)
        assert "time.sleep(MODEL_REACTIVATION_DELAY)" in source, (
            "Expected time.sleep(MODEL_REACTIVATION_DELAY) in utils/lms_helper.py"
        )

    def test_sleep_uses_model_loading_delay(self):
        """time.sleep(MODEL_LOADING_DELAY) must appear at least twice in lms_helper.py."""
        source = _read_source(LMS_HELPER_PATH)
        count = source.count("time.sleep(MODEL_LOADING_DELAY)")
        assert count >= 2, (
            f"Expected at least 2 occurrences of time.sleep(MODEL_LOADING_DELAY) "
            f"in utils/lms_helper.py, found {count}"
        )


# ---------------------------------------------------------------------------
# 5. `import time` appears at module level
# ---------------------------------------------------------------------------


class TestModuleLevelImportTime:
    """lms_helper.py must import `time` at module level (not only inside methods)."""

    def test_module_level_import_time(self):
        """Top-level `import time` must exist in lms_helper.py."""
        source = _read_source(LMS_HELPER_PATH)
        tree = ast.parse(source, filename=str(LMS_HELPER_PATH))

        top_level_time_imports = [
            node
            for node in ast.iter_child_nodes(tree)
            if isinstance(node, ast.Import)
            and any(alias.name == "time" for alias in node.names)
        ]

        assert top_level_time_imports, (
            "No module-level 'import time' found in utils/lms_helper.py. "
            "Add 'import time' at the top of the file."
        )
