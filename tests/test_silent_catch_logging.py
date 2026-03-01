#!/usr/bin/env python3
"""Tests for H-error: All tool modules must have module-level loggers.

Verifies that every module under tools/ that catches exceptions also
has a module-level logger configured via logging.getLogger(__name__).
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


class TestNoSilentCatchesInVision:
    """vision.py: every except Exception block must call logger before return."""

    def _get_except_blocks(self):
        source = (TOOLS_DIR / "vision.py").read_text()
        tree = ast.parse(source)
        blocks = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type and isinstance(node.type, ast.Name) and node.type.id == "Exception":
                    blocks.append(node)
        return blocks, source

    def test_all_except_blocks_have_logger_call(self):
        """Every except Exception block in vision.py must contain a logger call."""
        blocks, source = self._get_except_blocks()
        assert len(blocks) >= 6, f"Expected >=6 except Exception blocks, found {len(blocks)}"

        for handler in blocks:
            body_source = ast.get_source_segment(source, handler)
            assert body_source is not None
            assert "logger." in body_source, (
                f"Line {handler.lineno}: except Exception block has no logger call"
            )


class TestNoSilentCatchesInHealth:
    """health.py: except blocks returning errors must log first."""

    def test_health_check_logs_error(self):
        source = (TOOLS_DIR / "health.py").read_text()
        # The health_check method's except block should log
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
