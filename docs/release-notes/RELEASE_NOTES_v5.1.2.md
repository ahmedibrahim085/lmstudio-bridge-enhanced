# Release Notes — v5.1.2

**Release Date**: 2026-10-13
**Branch**: `fix/14-no-global-nest-asyncio` → merged to `main`
**Tag**: `v5.1.2`
**Issue**: #14

---

## Summary

Patch release. On Python 3.14+ the server crashed at startup:

```
File ".../anyio/_backends/_asyncio.py", in wrapper
    task.set_name(get_callable_name(func))
AttributeError: 'NoneType' object has no attribute 'set_name'
```

`model_registry/registry.py` called `nest_asyncio.apply()` at import time, which patched every event loop. On Python
3.14+ the patched `run_until_complete` leaves `asyncio.current_task()` as `None` inside `anyio.run()`, which
`mcp.run(transport="stdio")` uses.

## Fix

- `model_registry/registry.py`: no global `nest_asyncio.apply()`. A private `_run_sync()` runs a coroutine with
  `asyncio.run()` when no loop is running, or on its own loop in a worker thread when one is. It is used by the two sync
  wrappers (`get_model_capabilities` auto-research, `refresh_registry_sync`).
- `requirements.txt`: `nest-asyncio` removed (no longer used).
- Tests: 17 call sites and `tests/conftest.py` used `asyncio.get_event_loop().run_until_complete(...)`, which only worked
  because of the global patch; they now use `asyncio.run(...)`.
- New: `tests/test_issue14_nest_asyncio.py` (importing the registry does not patch asyncio; the sync wrapper works with
  and without a running loop).

## Verification

Fresh venv, `pip install -r requirements.txt`, real `python main.py` over stdio with an MCP `initialize` request:

| Python | Before (v5.1.1) | After |
|---|---|---|
| 3.14 | exit 1, `AttributeError: 'NoneType' object has no attribute 'set_name'` | `initialize` answered |

CI unit gate on a fresh install: Python 3.13 and 3.14 both `2117 passed, 19 skipped`.
