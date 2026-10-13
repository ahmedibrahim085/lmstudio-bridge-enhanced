#!/usr/bin/env python3
"""
Issue #14: model_registry must not patch asyncio globally with nest_asyncio.

nest_asyncio.apply() at import time patched every event loop. On Python 3.14+
the patched run_until_complete leaves asyncio.current_task() as None inside
anyio.run(), so mcp.run(transport="stdio") crashed with
AttributeError: 'NoneType' object has no attribute 'set_name'.

Each check runs in a fresh interpreter: a patch applied anywhere else in the
pytest process would otherwise mask the result.
"""

import os
import subprocess
import sys
import textwrap

ROOT = os.path.join(os.path.dirname(__file__), "..")


def _run(code: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_importing_registry_does_not_patch_asyncio():
    proc = _run(
        """
        import asyncio
        import model_registry.registry  # noqa: F401
        print(getattr(asyncio, "_nest_patched", False))
        """
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "False"


def test_refresh_registry_sync_works_inside_running_loop():
    # A sync caller inside a running event loop (e.g. a sync tool called from
    # an async server) must still get the result, without nest_asyncio.
    proc = _run(
        """
        import asyncio
        from model_registry.registry import ModelRegistry

        async def fake_refresh(self, models=None, force_all=False, remove_unavailable=True):
            return {"ok": True, "has_task": asyncio.current_task() is not None}

        ModelRegistry.refresh_registry = fake_refresh
        reg = ModelRegistry.__new__(ModelRegistry)

        async def main():
            return reg.refresh_registry_sync()

        print(asyncio.run(main()))
        """
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "{'ok': True, 'has_task': True}"


def test_refresh_registry_sync_works_without_running_loop():
    proc = _run(
        """
        import asyncio
        from model_registry.registry import ModelRegistry

        async def fake_refresh(self, models=None, force_all=False, remove_unavailable=True):
            return {"ok": True}

        ModelRegistry.refresh_registry = fake_refresh
        print(ModelRegistry.__new__(ModelRegistry).refresh_registry_sync())
        """
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "{'ok': True}"
