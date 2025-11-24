# Release Notes - v3.2.1

**Release Date**: November 24, 2025
**Version**: 3.2.1
**Previous Version**: 3.2.0
**Status**: **PRODUCTION READY**
**Commits**: 27 commits since v3.2.0

---

## Release Summary

This is a **patch release** focused on bug fixes, test reliability improvements, and code quality enhancements. No new features or breaking changes.

**Key Improvements**:
1. **Test Reliability** - Automatic retry for flaky tests handling transient LM Studio HTTP 500 errors
2. **Bug Fixes** - Fixed critical bugs in model detection, duplicate loading, and async execution
3. **Code Quality** - Refactored project structure, removed dead code, improved error handling
4. **Infrastructure** - Added pre-commit hooks, improved test isolation

---

## What's Fixed

### Critical Bug Fixes

| Issue | Commit | Description |
|-------|--------|-------------|
| **Model detection failure** | `089330b` | Fixed `config_main.py` calling wrong method `get_loaded_models()` instead of `list_loaded_models()` |
| **Response.__bool__ bug** | `c2dc1c4` | Fixed bug where HTTP error codes showed as `None` due to incorrect boolean evaluation |
| **MCP connection failures** | `3ac8870` | Prevented MCP connection failures during LLM calls using `asyncio.to_thread` |
| **Duplicate model loading** | `661fff8`, `e5c55c8` | Prevented duplicate model loading in `load_model()` via base name matching |
| **Asyncio context errors** | `2cd8558` | Fixed `asyncio.run` in async contexts with `nest_asyncio` in model registry |

### Test Improvements

| Improvement | Commit | Description |
|-------------|--------|-------------|
| **Automatic test retry** | `c7f3443` | Added `pytest-rerunfailures` to handle flaky tests (2 retries, 5s delay) |
| **Memory leak test** | `9d08a95` | Improved robustness with GC control and absolute thresholds |
| **Persistent session test** | `bb5e236`, `d7bffc1` | Marked as model-dependent skip, improved assertions |
| **Test isolation** | `5c5fc7a` | Added `reset_mcp_discovery` for better test isolation |
| **Fixture error fix** | `b642a87` | Renamed helper function to avoid pytest fixture collision |

### Code Quality Enhancements

| Enhancement | Commit | Description |
|-------------|--------|-------------|
| **Pre-commit hooks** | `63a6c91` | Added pre-commit config and `pyproject.toml` for code quality |
| **Project organization** | `ccb23fe`, `8e542c0` | Reorganized scripts/examples/tests into subdirectories |
| **Remove dead code** | `1ce0e1e` | Removed unused `_execute_autonomous_stateful` method |
| **Shared logging** | `169dabc` | Refactored tools to use shared logging from `utils.custom_logging` |
| **Better error handling** | `5386ad4` | Replaced bare `except` with explicit `Exception` |
| **Deprecation warnings** | `cced517` | Added deprecation warning for old `lmstudio_bridge.py` |

### Security & Validation

| Security Fix | Commit | Description |
|--------------|--------|-------------|
| **Input validation** | `5d9730d` | Added MCP and model name validation for security |
| **Constants standardization** | `40244ea` | Standardized `max_rounds` to use `DEFAULT_MAX_ROUNDS` constant |

### Shell Script Fixes

| Fix | Commit | Description |
|-----|--------|-------------|
| **Portable shebang** | `0edf708` | Use portable shebang for cross-platform compatibility |
| **Read command flags** | `67f8734` | Added `-r` flag to read commands |
| **Directory structure** | `79c05f6` | Updated test runner for new directory structure |

---

## Test Configuration

### New: Automatic Test Retry

**File**: `pytest.ini`

```ini
# Automatic retry for flaky tests (e.g., transient LM Studio HTTP 500 errors)
# Failed tests will be retried up to 2 times with a 5 second delay between attempts
# This helps distinguish transient failures from real bugs
addopts = --reruns 2 --reruns-delay 5
```

**Rationale**: Some LLM models (e.g., deepseek-r1-0528-qwen3-8b) have ~40% failure rate with transient HTTP 500 errors. Automatic retry distinguishes real bugs from infrastructure flakiness.

**File**: `requirements.txt`
```
pytest-rerunfailures>=12.0  # Automatic retry for flaky tests
```

---

## Breaking Changes

**NONE** - This release is 100% backward compatible.

---

## Migration Guide

### From v3.2.0 to v3.2.1

**No changes required!** Just update and restart:

```bash
cd /path/to/lmstudio-bridge-enhanced
git pull
git checkout v3.2.1

# Restart Claude Code to load updated MCP
```

---

## Files Modified

### Core Files
- `config/constants.py` - Version bump to 3.2.1
- `setup.py` - Version bump to 3.2.1
- `config_main.py` - Fixed model detection method call

### Configuration Files
- `pytest.ini` - Added automatic retry configuration
- `requirements.txt` - Added `pytest-rerunfailures>=12.0`
- `pyproject.toml` - Added project metadata (NEW)
- `.pre-commit-config.yaml` - Added pre-commit hooks (NEW)

### Bug Fixes
- `llm/llm_client.py` - Fixed Response.__bool__ bug
- `utils/lms_helper.py` - Prevented duplicate model loading, improved logging
- `model_registry/registry.py` - Fixed asyncio context issues
- `tools/dynamic_autonomous.py` - Prevent MCP connection failures

### Refactoring
- `tools/` - Standardized logging, sys.path patterns, constants usage
- `scripts/` - Moved to `scripts/development/`
- `examples/` - Moved to `examples/usage/`
- `tests/` - Moved standalone tests to `tests/standalone/`

---

## Statistics

| Metric | Value |
|--------|-------|
| **Commits** | 27 |
| **Bug Fixes** | 16 |
| **Test Improvements** | 5 |
| **Refactoring** | 8 |
| **Security Enhancements** | 2 |
| **Files Modified** | 20+ |
| **Lines Added** | ~500 |
| **Lines Removed** | ~300 (dead code cleanup) |

---

## Commit Log

<details>
<summary>Click to expand full commit history</summary>

```
c7f3443 test: add automatic retry for flaky tests with pytest-rerunfailures
089330b fix(config): use correct LMSHelper method for model detection
bb5e236 fix(test): mark test_persistent_session as model-dependent skip
d7bffc1 fix(test): improve test_persistent_session robustness with proper assertions
9d08a95 fix: improve memory leak test robustness with GC control and absolute thresholds
3ac8870 fix: prevent MCP connection failures during LLM calls with asyncio.to_thread
661fff8 fix(lms_helper): prevent duplicate model loading in load_model()
b642a87 fix(test): rename helper function to avoid pytest fixture error
c2dc1c4 fix: Response.__bool__ bug causing HTTP error codes to show as None
1f02bd4 fix(lms_helper): update log message to include processingprompt state
e5c55c8 fix(lms_helper): prevent duplicate model loading via base name matching
63a6c91 chore(infra): add pre-commit config and pyproject.toml
ccb23fe refactor(project): organize scripts and examples into subdirectories
8e542c0 refactor(tests): move standalone tests to tests/standalone/
79c05f6 fix(scripts): update test runner for new directory structure
357bf37 docs: update file references for upcoming reorganization
cced517 deprecate(bridge): add deprecation warning for lmstudio_bridge.py
2cd8558 fix(registry): handle asyncio.run in async contexts with nest_asyncio
40244ea fix(tools): standardize max_rounds to use DEFAULT_MAX_ROUNDS constant
169dabc refactor(tools): use shared logging from utils.custom_logging
5d9730d feat(security): add MCP and model name validation
5c5fc7a refactor(mcp): add reset_mcp_discovery for test isolation
9ef771d refactor(tools): standardize sys.path.insert pattern
1ce0e1e refactor(tools): remove unused _execute_autonomous_stateful method
67f8734 fix(shell): add -r flag to read commands
0edf708 fix(shell): use portable shebang
5386ad4 fix(bridge): replace bare except with explicit Exception
47e3b08 fix(config): correct VERSION constant to 3.2.0
```

</details>

---

## Contributors

- **Ahmed Maged** - Primary Developer
- **Claude Code** - AI Collaboration Partner

---

## What's Next (v3.3.0 Roadmap)

### Planned Features
- Enhanced error recovery mechanisms
- Performance optimizations for large-scale autonomous tasks
- Extended model compatibility testing
- Improved documentation and examples

---

## Summary

**v3.2.1 is a stability and reliability release** that addresses:

- **16 bug fixes** including critical model detection and async execution issues
- **5 test improvements** with automatic retry for flaky tests
- **8 refactoring changes** improving code quality and organization
- **2 security enhancements** with input validation

All changes are backward compatible. No breaking changes.

---

**Release**: v3.2.1
**Date**: November 24, 2025
**Status**: **PRODUCTION READY**

**Full Changelog**: v3.2.0...v3.2.1
