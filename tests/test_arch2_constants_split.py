"""Tests for ARCH-2: config/constants domain-split package.

Verifies that the flat config/constants.py → config/constants/ package
conversion preserves all 205 constants, backward compatibility, and
domain isolation.

Test categories (Req 07):
- Happy: Tests 1, 3, 6, 7, 8 — normal import paths work
- Negative: Test 5 — invalid import raises correctly
- Edge: Test 10 — os import isolation
- Boundary: Test 2 — exact 205 count, no extras, no missing
"""

import ast
import importlib
import pathlib
import types

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DOMAIN_MODULES = [
    "version",
    "server",
    "api",
    "timeouts",
    "models",
    "errors",
    "limits",
    "sampling",
    "streaming",
    "thinking",
    "security",
    "images",
    "mcp",
    "selection",
    "testing",
    "tool_config",
]

EXPECTED_COUNT = 249


def _get_domain_all(module_name: str) -> list[str]:
    """Import a domain module and return its __all__."""
    mod = importlib.import_module(f"config.constants.{module_name}")
    return list(getattr(mod, "__all__", []))


# ---------------------------------------------------------------------------
# Test 1: All 205 constants importable from config.constants
# ---------------------------------------------------------------------------


class TestAllImportable:
    """Happy path — every __all__ entry is importable from the package."""

    def test_all_205_importable(self) -> None:
        import config.constants as cc

        all_names = cc.__all__
        assert len(all_names) == EXPECTED_COUNT, (
            f"Expected {EXPECTED_COUNT} exports, got {len(all_names)}"
        )
        for name in all_names:
            obj = getattr(cc, name, _SENTINEL := object())
            assert obj is not _SENTINEL, f"{name!r} listed in __all__ but not accessible"


# ---------------------------------------------------------------------------
# Test 2: Package __all__ == union of all domain __all__s
# ---------------------------------------------------------------------------


class TestAllConsistency:
    """Boundary — exact count, no extras, no missing."""

    def test_all_consistency(self) -> None:
        import config.constants as cc

        package_all = set(cc.__all__)

        union_all: set[str] = set()
        for domain in DOMAIN_MODULES:
            union_all.update(_get_domain_all(domain))

        missing = union_all - package_all
        extra = package_all - union_all
        assert not missing, f"In domain __all__ but missing from package: {missing}"
        assert not extra, f"In package __all__ but missing from domains: {extra}"
        assert len(package_all) == EXPECTED_COUNT


# ---------------------------------------------------------------------------
# Test 3: Direct domain import works
# ---------------------------------------------------------------------------


class TestDomainDirectImport:
    """Happy path — direct imports from domain sub-modules."""

    def test_domain_direct_import(self) -> None:
        from config.constants.api import CHAT_COMPLETIONS_ENDPOINT

        assert CHAT_COMPLETIONS_ENDPOINT == "/v1/chat/completions"

        from config.constants.server import DEFAULT_LMSTUDIO_PORT

        assert DEFAULT_LMSTUDIO_PORT == 1234

        from config.constants.version import VERSION

        assert isinstance(VERSION, str)


# ---------------------------------------------------------------------------
# Test 4: No cross-domain imports
# ---------------------------------------------------------------------------


class TestNoCrossDomainImports:
    """Edge — domain files must not import from each other."""

    def test_no_cross_domain_imports(self) -> None:
        pkg_dir = pathlib.Path(__file__).resolve().parent.parent / "config" / "constants"
        assert pkg_dir.is_dir(), f"Package directory not found: {pkg_dir}"

        for domain in DOMAIN_MODULES:
            source = (pkg_dir / f"{domain}.py").read_text()
            tree = ast.parse(source, filename=f"{domain}.py")
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and node.level == 1:
                        # Relative import from another domain file
                        assert False, (
                            f"{domain}.py has cross-domain import: "
                            f"from .{node.module} import ..."
                        )


# ---------------------------------------------------------------------------
# Test 5: Non-existent constant raises ImportError
# ---------------------------------------------------------------------------


class TestNonexistentRaises:
    """Negative — importing a non-existent name fails."""

    def test_nonexistent_raises(self) -> None:
        with pytest.raises(ImportError):
            from config.constants import NONEXISTENT_CONSTANT_XYZ  # noqa: F401


# ---------------------------------------------------------------------------
# Test 6: Cross-references preserved
# ---------------------------------------------------------------------------


class TestCrossRefsPreserved:
    """Happy path — intra-file cross-references still resolve."""

    def test_cross_refs_preserved(self) -> None:
        from config.constants import (
            DEFAULT_AUTONOMOUS_FORMAT,
            DEFAULT_VISION_DETAIL,
            FORMAT_RESPONSES,
            MULTIMODAL_DETAIL_DEFAULT,
            SUPPORTED_API_FORMATS,
        )

        assert MULTIMODAL_DETAIL_DEFAULT == DEFAULT_VISION_DETAIL
        assert DEFAULT_AUTONOMOUS_FORMAT == FORMAT_RESPONSES
        assert FORMAT_RESPONSES in SUPPORTED_API_FORMATS


# ---------------------------------------------------------------------------
# Test 7: config package re-export
# ---------------------------------------------------------------------------


class TestConfigPackageReexport:
    """Happy path — from config import VERSION still works."""

    def test_config_package_reexport(self) -> None:
        from config import VERSION

        assert isinstance(VERSION, str)
        assert VERSION == "5.0.0"


# ---------------------------------------------------------------------------
# Test 8: Aliased import
# ---------------------------------------------------------------------------


class TestAliasedImport:
    """Happy path — import config.constants as cc; cc.VERSION."""

    def test_aliased_import(self) -> None:
        import config.constants as cc

        assert hasattr(cc, "VERSION")
        assert hasattr(cc, "DEFAULT_LMSTUDIO_HOST")
        assert hasattr(cc, "CHAT_COMPLETIONS_ENDPOINT")
        assert isinstance(cc, types.ModuleType)


# ---------------------------------------------------------------------------
# Test 9: Type preservation
# ---------------------------------------------------------------------------


class TestTypePreservation:
    """Boundary — constants keep their original types after split."""

    def test_type_preservation(self) -> None:
        from config.constants import (
            BLOCKED_IP_RANGES_172,
            DEFAULT_LMSTUDIO_PORT,
            DEFAULT_TEMPERATURE,
            IMAGE_EXTENSION_MAP,
            MCP_PACKAGES,
            MODEL_ROLE_KEYWORDS,
            REVIEW_MODELS,
            SUPPORTED_IMAGE_TYPES,
            VERSION,
        )

        assert isinstance(VERSION, str)
        assert isinstance(DEFAULT_LMSTUDIO_PORT, int)
        assert isinstance(DEFAULT_TEMPERATURE, float)
        assert isinstance(SUPPORTED_IMAGE_TYPES, list)
        assert isinstance(IMAGE_EXTENSION_MAP, dict)
        assert isinstance(MCP_PACKAGES, dict)
        assert isinstance(REVIEW_MODELS, list)
        assert isinstance(MODEL_ROLE_KEYWORDS, dict)
        assert isinstance(BLOCKED_IP_RANGES_172, range)


# ---------------------------------------------------------------------------
# Test 10: `import os` only in mcp.py
# ---------------------------------------------------------------------------


class TestOsOnlyInMcp:
    """Edge — only mcp.py should have `import os`."""

    def test_os_only_in_mcp(self) -> None:
        pkg_dir = pathlib.Path(__file__).resolve().parent.parent / "config" / "constants"
        assert pkg_dir.is_dir(), f"Package directory not found: {pkg_dir}"

        os_importers = []
        for domain in DOMAIN_MODULES:
            source = (pkg_dir / f"{domain}.py").read_text()
            tree = ast.parse(source, filename=f"{domain}.py")
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "os":
                            os_importers.append(domain)
                elif isinstance(node, ast.ImportFrom):
                    if node.module == "os":
                        os_importers.append(domain)

        assert os_importers == ["mcp"], (
            f"Expected only mcp.py to import os, got: {os_importers}"
        )
