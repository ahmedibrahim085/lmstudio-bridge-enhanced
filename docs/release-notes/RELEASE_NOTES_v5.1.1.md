# Release Notes — v5.1.1

**Release Date**: 2026-10-12
**Branch**: `fix/28-pin-mcp-v1` → merged to `main`
**Tag**: `v5.1.1`
**Issue**: #28

---

## Summary

Patch release. A fresh install of v5.1.0 could not start the server: `requirements.txt` did not cap the `mcp`
dependency, so `pip` now resolves `mcp` 2.x, which renamed `FastMCP`:

```
python -c "import main"
ModuleNotFoundError: No module named 'mcp.server.fastmcp'. This is mcp 2.x, where FastMCP was renamed to MCPServer ...
```

## Fix

- `requirements.txt`: `mcp[cli]>=1.0.0` → `mcp[cli]>=1.0.0,<2`

`pip install .` is not covered: it builds from `pyproject.toml`, whose `[project]` table declares no dependencies, so
`setup.py`'s `install_requires` is ignored and `pip install .` installs no dependencies at all. That is a separate gap,
recorded in #22.

No code change. Migrating to mcp 2.x is a separate decision, recorded in #28.

## Verification

Fresh venv (Python 3.13), `pip install -r requirements.txt`: `mcp` resolves to a 1.x release, `python -c "import main"`
exits 0, and the CI unit gate passes. Before the fix the same gate failed 6 tests on two machines (#28).
