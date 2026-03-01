#!/usr/bin/env python3
"""Tests for silent error catch prevention across ALL tool modules.

Two layers of defense:
1. Every tool module with except blocks must have a module-level logger
2. Every `except Exception` block must contain a logger.* call OR an explicit
   # noqa suppression comment (for intentional catch-and-ignore patterns)

This is an architectural guard — it uses AST parsing to structurally enforce
that no one can add a silent catch block without the test suite catching it.
"""

import ast
import importlib
from pathlib import Path

import pytest


TOOLS_DIR = Path(__file__).parent.parent / "tools"

# All tool modules that contain except blocks must have loggers
TOOL_MODULES = [
    "tools.completions",
    "tools.embeddings",
    "tools.health",
    "tools.vision",
    "tools.dynamic_autonomous",
    "tools.dynamic_autonomous_register",
]

# All tool files to scan for silent catches (every .py except __init__)
TOOL_FILES = [
    "completions.py",
    "dynamic_autonomous.py",
    "dynamic_autonomous_register.py",
    "embeddings.py",
    "health.py",
    "vision.py",
]


class TestToolModulesHaveLoggers:
    """Every tool module that catches exceptions must have a module-level logger."""

    @pytest.mark.parametrize("module_name", TOOL_MODULES)
    def test_module_has_logger_attribute(self, module_name):
        """Module must have a 'logger' attribute at module level."""
        mod = importlib.import_module(module_name)
        assert hasattr(mod, "logger"), (
            f"{module_name} is missing module-level 'logger = logging.getLogger(__name__)'"
        )

    @pytest.mark.parametrize("module_name", TOOL_MODULES)
    def test_logger_uses_getlogger(self, module_name):
        """Logger must be created via logging.getLogger (not a bare Logger)."""
        import logging

        mod = importlib.import_module(module_name)
        log = getattr(mod, "logger", None)
        assert isinstance(log, logging.Logger), (
            f"{module_name}.logger is not a logging.Logger instance"
        )


class TestNoSilentCatchesAllModules:
    """AST guard: every except Exception block in ANY tool module must log.

    Scans every tool file for `except Exception` handlers and verifies
    that each one contains a logging call OR an explicit `# noqa`
    suppression comment (for intentional catch-and-ignore patterns like
    metrics collection that must never break the autonomous loop).

    Recognized logging patterns:
    - logger.error/warning/debug/info (standard logging module)
    - log_error/log_info/log_warning (custom_logging helpers)
    """

    # Patterns that count as "logging" inside an except block
    LOGGING_PATTERNS = ("logger.", "log_error", "log_info", "log_warning")

    @staticmethod
    def _get_except_exception_blocks(filename):
        """Parse a tool file and return all except Exception handler nodes."""
        source = (TOOLS_DIR / filename).read_text()
        tree = ast.parse(source)
        blocks = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if (
                    node.type
                    and isinstance(node.type, ast.Name)
                    and node.type.id == "Exception"
                ):
                    blocks.append(node)
        return blocks, source

    @pytest.mark.parametrize("filename", TOOL_FILES)
    def test_except_exception_blocks_have_logging_or_noqa(self, filename):
        """Every except Exception block must contain a logging call or # noqa."""
        blocks, source = self._get_except_exception_blocks(filename)

        # Get the raw source lines for noqa comment checking
        source_lines = source.splitlines()

        violations = []
        for handler in blocks:
            body_source = ast.get_source_segment(source, handler)
            if body_source is None:
                continue

            # Check 1: any recognized logging pattern in the except block body
            has_logging = any(pat in body_source for pat in self.LOGGING_PATTERNS)

            # Check 2: noqa comment on the except line itself
            except_line = source_lines[handler.lineno - 1] if handler.lineno <= len(source_lines) else ""
            has_noqa = "# noqa" in except_line

            if not has_logging and not has_noqa:
                violations.append(
                    f"  Line {handler.lineno}: except Exception block — no logging call, no # noqa"
                )

        assert not violations, (
            f"\n{filename}: silent except Exception blocks found:\n"
            + "\n".join(violations)
            + "\n\nFix: add logger.error/warning/debug call, or # noqa: S110 if intentional"
        )

    @pytest.mark.parametrize("filename", TOOL_FILES)
    def test_no_bare_except(self, filename):
        """No bare `except:` (without exception type) allowed in any tool module."""
        source = (TOOLS_DIR / filename).read_text()
        tree = ast.parse(source)

        bare_excepts = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                bare_excepts.append(f"  Line {node.lineno}: bare except:")

        assert not bare_excepts, (
            f"\n{filename}: bare except blocks found (use except Exception instead):\n"
            + "\n".join(bare_excepts)
        )


class TestNoSilentCatchesInHealth:
    """health.py: specific log message guards for critical error paths."""

    def test_health_check_logs_error(self):
        source = (TOOLS_DIR / "health.py").read_text()
        assert "logger.error" in source or "logger.debug" in source, (
            "health.py has no logger.error or logger.debug calls"
        )

    def test_detect_type_logs_on_parse_failure(self):
        source = (TOOLS_DIR / "health.py").read_text()
        assert "Failed to parse server type" in source, (
            "health.py _detect_type_from_response should log parse failures"
        )

    def test_models_probe_logs_failure(self):
        source = (TOOLS_DIR / "health.py").read_text()
        assert "Models endpoint probe failed" in source, (
            "health.py check_server_type should log models endpoint probe failure"
        )


class TestNoSilentCatchesInEmbeddings:
    """embeddings.py: the single except block must log."""

    def test_generate_embeddings_logs_error(self):
        source = (TOOLS_DIR / "embeddings.py").read_text()
        assert 'logger.error("Failed to generate embeddings' in source, (
            "embeddings.py generate_embeddings should log errors"
        )


class TestNoSilentCatchesInDynamicAutonomousRegister:
    """dynamic_autonomous_register.py: list_mcps except block must log."""

    def test_list_mcps_logs_error(self):
        source = (TOOLS_DIR / "dynamic_autonomous_register.py").read_text()
        assert 'logger.error("Error listing MCPs' in source, (
            "dynamic_autonomous_register.py list_mcps should log errors"
        )
