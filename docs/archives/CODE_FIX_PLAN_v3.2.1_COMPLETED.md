# 🔧 Code Fix Implementation Plan
**Project**: lmstudio-bridge-enhanced
**Created**: 2025-11-27
**Methodology**: Semantic code search + Deep impact analysis
**Risk Order**: LEAST Destructive → MOST Destructive

---

## 📋 **PRE-EXECUTION CHECKLIST**

### 1. Initial State Capture
```bash
# Create baseline commit
git add -A
git commit -m "chore: baseline before code fixes (pre-Phase 1)"
git tag baseline-before-fixes

# Create feature branch
git checkout -b fix/code-quality-improvements
```

### 2. Verification Requirements
- ✅ All tests passing: `pytest`
- ✅ No uncommitted changes: `git status`
- ✅ Code search index current: Check `.code-search-index/`

---

## 🎯 **EXECUTION STRATEGY**

**Ordering Principle**: Start with LEAST risky changes (additive) → End with MOST risky (refactoring)

```
Phase 1: Config Validation (ADDITIVE - Low Risk)
Phase 2: Test Refactoring (ISOLATED - Low Risk)
Phase 3: HTTP Pooling (ISOLATED - Medium Risk)
Phase 4: Logger Consolidation (IMPORT CHANGES - Medium-High Risk)
Phase 5: Exception Merge (WIDESPREAD CHANGES - HIGH Risk)
```

**After EACH phase**:
1. Commit changes
2. Run full test suite
3. Re-index changed files
4. Tag the phase
5. **STOP if tests fail** - investigate before proceeding

---

# 📦 **PHASE 1: Add Config Validation with Pydantic**

**Risk Level**: 🟢 LOW (Additive, no breaking changes)
**Estimated Time**: 30 minutes
**Test Impact**: NEW tests only

## Impact Analysis

### Files to Modify
| File | Lines | Changes | Test Impact |
|------|-------|---------|-------------|
| `config_main.py` | 26-187 | Add Pydantic models | None (backward compatible) |
| `config_main.py` | 214-226 | Add validation in `__init__` | None |
| `config_main.py` | 228-238 | Add try/except in `from_env` | None |

### Files to Create
| File | Purpose | Lines (est.) |
|------|---------|--------------|
| `tests/test_config_validation.py` | Test validation logic | ~200 |

### Dependencies to Add
```toml
# pyproject.toml or requirements.txt
pydantic>=2.0.0
```

## Task Breakdown

### Task 1.1: Add Pydantic Dependency
**File**: `pyproject.toml` or `requirements.txt`

```bash
# If using pyproject.toml
# Add to [project.dependencies]:
pydantic = ">=2.0.0"

# If using requirements.txt:
echo "pydantic>=2.0.0" >> requirements.txt

# Install
pip install pydantic
```

**Commit**:
```bash
git add pyproject.toml  # or requirements.txt
git commit -m "feat(config): add Pydantic dependency for validation"
```

---

### Task 1.2: Add Validation to LMStudioConfig
**File**: `config_main.py:26-187`

**Current code** (dataclass):
```python
@dataclass
class LMStudioConfig:
    host: str = "127.0.0.1"
    port: int = 1234
    # ... more fields
```

**Changes needed**:
```python
from pydantic import BaseModel, Field, validator

class LMStudioConfig(BaseModel):
    host: str = Field(default="127.0.0.1", description="LM Studio host")
    port: int = Field(default=1234, ge=1, le=65535, description="Port number")

    @validator('port')
    def validate_port(cls, v):
        if not (1 <= v <= 65535):
            raise ValueError(f"Port must be between 1-65535, got {v}")
        return v

    @validator('host')
    def validate_host(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("Host must be a non-empty string")
        return v
```

**Lines affected**: 26-187 (entire LMStudioConfig class)

**Manual Testing**:
```python
# Test valid config
config = LMStudioConfig(host="localhost", port=8080)
assert config.port == 8080

# Test invalid port
try:
    config = LMStudioConfig(port=99999)  # Should raise ValueError
    assert False, "Should have raised"
except ValueError:
    pass
```

---

### Task 1.3: Add Validation to MCPConfig
**File**: `config_main.py:190-208`

**Changes needed**: Same pattern as Task 1.2

---

### Task 1.4: Update Config.from_env() Error Handling
**File**: `config_main.py:228-238`

**Current code**:
```python
@classmethod
def from_env(cls) -> "Config":
    lmstudio_host = os.getenv("LMSTUDIO_HOST", "127.0.0.1")
    lmstudio_port = int(os.getenv("LMSTUDIO_PORT", "1234"))
    # ...
```

**Changes needed**:
```python
@classmethod
def from_env(cls) -> "Config":
    try:
        lmstudio_port = int(os.getenv("LMSTUDIO_PORT", "1234"))
    except ValueError as e:
        raise ConfigurationError(f"Invalid LMSTUDIO_PORT: {e}")

    try:
        lmstudio_config = LMStudioConfig(
            host=os.getenv("LMSTUDIO_HOST", "127.0.0.1"),
            port=lmstudio_port
        )
    except Exception as e:
        raise ConfigurationError(f"Invalid LMStudio config: {e}")
    # ...
```

**Import needed**:
```python
from utils.errors import ConfigurationError
```

---

### Task 1.5: Create Comprehensive Tests
**File**: `tests/test_config_validation.py` (NEW FILE)

**Content** (~200 lines):
```python
import pytest
import os
from config_main import Config, LMStudioConfig
from utils.errors import ConfigurationError


class TestLMStudioConfigValidation:
    def test_valid_config(self):
        config = LMStudioConfig(host="localhost", port=8080)
        assert config.host == "localhost"
        assert config.port == 8080

    def test_invalid_port_too_high(self):
        with pytest.raises(ValueError, match="Port must be"):
            LMStudioConfig(port=99999)

    def test_invalid_port_too_low(self):
        with pytest.raises(ValueError, match="Port must be"):
            LMStudioConfig(port=0)

    def test_invalid_port_negative(self):
        with pytest.raises(ValueError):
            LMStudioConfig(port=-1)

    def test_empty_host(self):
        with pytest.raises(ValueError, match="Host must be"):
            LMStudioConfig(host="")

    def test_none_host(self):
        with pytest.raises(ValueError):
            LMStudioConfig(host=None)


class TestConfigFromEnv:
    def test_valid_env_vars(self, monkeypatch):
        monkeypatch.setenv("LMSTUDIO_PORT", "8080")
        monkeypatch.setenv("LMSTUDIO_HOST", "192.168.1.1")

        config = Config.from_env()
        assert config.lmstudio.port == 8080
        assert config.lmstudio.host == "192.168.1.1"

    def test_invalid_port_env_var(self, monkeypatch):
        monkeypatch.setenv("LMSTUDIO_PORT", "not_a_number")

        with pytest.raises(ConfigurationError, match="Invalid LMSTUDIO_PORT"):
            Config.from_env()

    def test_port_out_of_range_env_var(self, monkeypatch):
        monkeypatch.setenv("LMSTUDIO_PORT", "70000")

        with pytest.raises(ConfigurationError, match="Invalid LMStudio config"):
            Config.from_env()
```

**Manual Testing**:
```bash
# Test with valid env vars
export LMSTUDIO_PORT=8080
python -c "from config_main import Config; c = Config.from_env(); print(c.lmstudio.port)"

# Test with invalid env vars
export LMSTUDIO_PORT=invalid
python -c "from config_main import Config; Config.from_env()"  # Should raise error
```

---

### Task 1.6: Run Tests
```bash
# Run new tests
pytest tests/test_config_validation.py -v

# Run full test suite
pytest

# Expected: All pass
```

---

### Task 1.7: Re-index Changed Files
```bash
# Re-index to update search index
# (This will be done via MCP tool after changes)
```

**In Claude Code**:
```
Re-index these files: config_main.py, tests/test_config_validation.py
```

---

### Task 1.8: Commit Phase 1
```bash
git add config_main.py tests/test_config_validation.py
git commit -m "feat(config): add Pydantic validation for configuration

- Add Pydantic BaseModel validation to LMStudioConfig
- Add port range validation (1-65535)
- Add host non-empty validation
- Add error handling in Config.from_env()
- Add comprehensive test coverage

BREAKING: None (backward compatible)
RISK: LOW
TESTS: Added test_config_validation.py"

git tag phase-1-config-validation
```

---

# 📦 **PHASE 2: Refactor Test Runner Duplication**

**Risk Level**: 🟢 LOW (Test code only, no production impact)
**Estimated Time**: 45 minutes
**Test Impact**: Refactored tests, same coverage

## Impact Analysis

### Files with Duplication
| File | Lines | Duplicate Pattern | Test Impact |
|------|-------|-------------------|-------------|
| `tests/standalone/test_retry_logic.py` | 276-319 | `run_all_tests()` | Refactor |
| `tests/standalone/test_lmstudio_api_integration.py` | 405-504 | `run_all_tests()` | Refactor |
| `tests/standalone/test_lmstudio_api_integration_v2.py` | 554-667 | `run_all_tests()` | Refactor |
| `tests/standalone/test_lms_cli_mcp_tools.py` | 429-449 | `run_all_tests()` | Refactor |

### Duplicate Helper Functions
| File | Function | Lines |
|------|----------|-------|
| `tests/standalone/test_sqlite_autonomous.py` | `print_section()` | 42-46 |
| `tests/standalone/test_reasoning_integration.py` | `print_section()` | 28-32 |
| `tests/standalone/test_retry_logic.py` | `print_section()` | 27-31 |
| `scripts/extensive_real_testing.py` | `print_section()` | 26-30 |

### File to Create
| File | Purpose | Lines (est.) |
|------|---------|--------------|
| `tests/standalone/test_runner_base.py` | Base class for test runners | ~150 |

## Task Breakdown

### Task 2.1: Create Base Test Runner Class
**File**: `tests/standalone/test_runner_base.py` (NEW)

**Content** (~150 lines):
```python
"""Base class for standalone test runners.

Provides common functionality for test orchestration:
- Test result tracking
- Section headers
- Summary printing
- Pass/fail tracking
"""
from typing import List, Tuple, Callable
import sys


class TestRunner:
    """Base class for standalone test runners."""

    def __init__(self, test_name: str):
        self.test_name = test_name
        self.results: List[Tuple[str, bool, str]] = []
        self.total_tests = 0
        self.passed_tests = 0

    def print_section(self, title: str) -> None:
        """Print a section header."""
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}\n")

    def run_test(self, test_name: str, test_func: Callable) -> bool:
        """Run a single test and track results."""
        self.total_tests += 1
        try:
            test_func()
            self.passed_tests += 1
            self.results.append((test_name, True, ""))
            print(f"✓ {test_name}")
            return True
        except Exception as e:
            self.results.append((test_name, False, str(e)))
            print(f"✗ {test_name}: {e}")
            return False

    async def run_test_async(self, test_name: str, test_func: Callable) -> bool:
        """Run a single async test and track results."""
        self.total_tests += 1
        try:
            await test_func()
            self.passed_tests += 1
            self.results.append((test_name, True, ""))
            print(f"✓ {test_name}")
            return True
        except Exception as e:
            self.results.append((test_name, False, str(e)))
            print(f"✗ {test_name}: {e}")
            return False

    def print_summary(self) -> None:
        """Print test summary."""
        self.print_section(f"{self.test_name} - Summary")
        print(f"Total: {self.total_tests}")
        print(f"Passed: {self.passed_tests}")
        print(f"Failed: {self.total_tests - self.passed_tests}")
        print(f"Success Rate: {(self.passed_tests/self.total_tests*100):.1f}%")

        if self.total_tests - self.passed_tests > 0:
            print("\nFailed Tests:")
            for name, passed, error in self.results:
                if not passed:
                    print(f"  - {name}: {error}")

    def exit_with_status(self) -> None:
        """Exit with appropriate status code."""
        sys.exit(0 if self.passed_tests == self.total_tests else 1)


# Standalone helper function (for backward compatibility)
def print_section(title: str) -> None:
    """Print a section header (standalone function)."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")
```

**Commit**:
```bash
git add tests/standalone/test_runner_base.py
git commit -m "test: add base TestRunner class for test orchestration

- Centralize test running logic
- Provide print_section helper
- Track pass/fail results
- Print summaries

RISK: NONE (test infrastructure only)"
```

---

### Task 2.2: Refactor test_retry_logic.py
**File**: `tests/standalone/test_retry_logic.py`

**Changes needed**:
- Lines 27-31: DELETE `print_section()` function
- Line 1: ADD `from test_runner_base import TestRunner, print_section`
- Lines 276-319: REPLACE `run_all_tests()` with TestRunner usage

**Before** (lines 276-319):
```python
def run_all_tests(self):
    total = 0
    passed = 0
    # ... manual tracking
```

**After**:
```python
def run_all_tests(self):
    runner = TestRunner("Retry Logic Tests")

    runner.print_section("Basic Retry Tests")
    runner.run_test("test_retry_success", self.test_retry_success)
    runner.run_test("test_retry_with_backoff", self.test_retry_with_backoff)
    # ... etc

    runner.print_summary()
    runner.exit_with_status()
```

**Manual Testing**:
```bash
python tests/standalone/test_retry_logic.py
# Should show same output but cleaner code
```

---

### Task 2.3: Refactor test_lmstudio_api_integration.py
**File**: `tests/standalone/test_lmstudio_api_integration.py`

**Changes**: Same pattern as Task 2.2
**Lines affected**: 405-504

---

### Task 2.4: Refactor test_lmstudio_api_integration_v2.py
**File**: `tests/standalone/test_lmstudio_api_integration_v2.py`

**Changes**: Same pattern, but ASYNC variant
**Lines affected**: 554-667

**After**:
```python
async def run_all_tests(self):
    runner = TestRunner("LM Studio API Integration V2")

    runner.print_section("Health Checks")
    await runner.run_test_async("test_health_check", self.test_health_check)
    # ... etc
```

---

### Task 2.5: Refactor Other Files
**Files**:
- `tests/standalone/test_lms_cli_mcp_tools.py:429-449`
- `tests/standalone/test_sqlite_autonomous.py:42-46`
- `tests/standalone/test_reasoning_integration.py:28-32`
- `scripts/extensive_real_testing.py:26-30`

**Changes**: Replace `print_section()` with import from `test_runner_base`

---

### Task 2.6: Run Tests
```bash
# Run each refactored test individually
python tests/standalone/test_retry_logic.py
python tests/standalone/test_lmstudio_api_integration.py
python tests/standalone/test_lmstudio_api_integration_v2.py

# Run full pytest suite
pytest

# Expected: All pass, same output
```

---

### Task 2.7: Re-index Changed Files
```
Re-index: tests/standalone/*.py
```

---

### Task 2.8: Commit Phase 2
```bash
git add tests/standalone/
git commit -m "refactor(tests): consolidate test runner duplication

- Refactor run_all_tests() methods to use TestRunner
- Consolidate print_section() helper functions
- Remove ~300 lines of duplicate code
- Maintain identical test behavior

Files refactored:
- test_retry_logic.py
- test_lmstudio_api_integration.py
- test_lmstudio_api_integration_v2.py
- test_lms_cli_mcp_tools.py
- test_sqlite_autonomous.py
- test_reasoning_integration.py

BREAKING: None
RISK: LOW (test code only)
TESTS: All existing tests still run"

git tag phase-2-test-refactoring
```

---

# 📦 **PHASE 3: Add HTTP Connection Pooling**

**Risk Level**: 🟡 MEDIUM (Changes client behavior)
**Estimated Time**: 1 hour
**Test Impact**: Existing tests should pass, add performance tests

## Impact Analysis

### Files Using HTTP Requests
| File | Lines | Current Pattern | Change Needed |
|------|-------|----------------|---------------|
| `llm/llm_client.py` | 54-120, 739-754 | `requests` per-call | Add session |
| `utils/lms_helper.py` | Unknown | `requests` | Add session |
| `llm/model_validator.py` | Unknown | `requests` | Add session |
| `utils/image_utils.py` | Unknown | `requests` | Add session |

### New Dependencies
```toml
requests[security]>=2.31.0  # Already exists, verify version
```

## Task Breakdown

### Task 3.1: Research Current requests Usage
```bash
# Find all requests.get/post calls
grep -n "requests\\.get\\|requests\\.post" llm/llm_client.py utils/lms_helper.py
```

**Document findings** before proceeding.

---

### Task 3.2: Add Session to LLMClient
**File**: `llm/llm_client.py:129-138`

**Current __init__**:
```python
def __init__(self, api_base: Optional[str] = None, model: Optional[str] = None):
    self.api_base = api_base or f"http://{config.lmstudio.host}:{config.lmstudio.port}"
    self.model = model
```

**Changes needed**:
```python
import requests

def __init__(self, api_base: Optional[str] = None, model: Optional[str] = None):
    self.api_base = api_base or f"http://{config.lmstudio.host}:{config.lmstudio.port}"
    self.model = model

    # Create persistent session for connection pooling
    self.session = requests.Session()
    self.session.headers.update({
        "Content-Type": "application/json"
    })

    # Configure connection pooling
    adapter = requests.adapters.HTTPAdapter(
        pool_connections=10,
        pool_maxsize=20,
        max_retries=3
    )
    self.session.mount("http://", adapter)
    self.session.mount("https://", adapter)

def __del__(self):
    """Cleanup session on deletion."""
    if hasattr(self, 'session'):
        self.session.close()
```

---

### Task 3.3: Replace requests.* with self.session.*
**File**: `llm/llm_client.py` (multiple locations)

**Find and replace**:
```python
# Before
response = requests.post(url, json=data, timeout=30)

# After
response = self.session.post(url, json=data, timeout=30)
```

**Lines to check**: Search for all `requests.get`, `requests.post` in file

---

### Task 3.4: Create Performance Tests
**File**: `tests/test_http_pooling.py` (NEW)

**Content** (~100 lines):
```python
import pytest
import time
from llm.llm_client import LLMClient


class TestHTTPPooling:
    """Test HTTP connection pooling performance."""

    @pytest.mark.benchmark
    def test_session_reuse(self):
        """Verify session is reused across requests."""
        client = LLMClient()

        # Session should exist
        assert hasattr(client, 'session')
        assert client.session is not None

        # Session should be the same instance
        session1 = client.session
        session2 = client.session
        assert session1 is session2

    @pytest.mark.benchmark
    def test_connection_pooling_performance(self):
        """Verify connection pooling improves performance."""
        client = LLMClient()

        # Make multiple requests
        start = time.time()
        for _ in range(10):
            try:
                client.health_check()
            except:
                pass  # Ignore errors, just testing pooling
        elapsed = time.time() - start

        # With pooling, 10 requests should be fast
        assert elapsed < 5.0, f"Connection pooling slow: {elapsed}s"
```

**Manual Testing**:
```bash
# Test that session is created
python -c "from llm.llm_client import LLMClient; c = LLMClient(); print(hasattr(c, 'session'))"

# Expected: True
```

---

### Task 3.5: Update Other Files (lms_helper, model_validator, image_utils)
**Same pattern as 3.2-3.3** for each file.

**Priority**: Start with `llm/llm_client.py` only, commit, then do others.

---

### Task 3.6: Run Tests
```bash
# Run new tests
pytest tests/test_http_pooling.py -v

# Run existing tests (should still pass)
pytest tests/test_llm_client.py -v

# Run full suite
pytest
```

---

### Task 3.7: Re-index
```
Re-index: llm/llm_client.py, utils/lms_helper.py, tests/test_http_pooling.py
```

---

### Task 3.8: Commit Phase 3
```bash
git add llm/llm_client.py utils/lms_helper.py tests/test_http_pooling.py
git commit -m "perf(http): add connection pooling for HTTP requests

- Add persistent requests.Session to LLMClient
- Configure connection pool (10 connections, 20 max)
- Add retry adapter (3 retries)
- Replace per-request calls with session
- Add cleanup in __del__
- Add performance tests

BREAKING: None (implementation detail)
RISK: MEDIUM (changes HTTP behavior)
TESTS: Added test_http_pooling.py
PERF: Reduced connection overhead for repeated requests"

git tag phase-3-http-pooling
```

---

# 📦 **PHASE 4: Consolidate StructuredLogger Classes**

**Risk Level**: 🟠 MEDIUM-HIGH (Import changes, backward compatibility needed)
**Estimated Time**: 1.5 hours
**Test Impact**: Update imports, verify logging works

## Impact Analysis

### Duplicate Classes
| File | Lines | Features | Used By |
|------|-------|----------|---------|
| `utils/custom_logging.py` | 22-104 | Basic logging (debug/info/warn/error) | `main.py`, `tools/dynamic_autonomous.py` |
| `utils/observability.py` | 277-384 | Advanced (model_operation, metrics) | Potentially other files |

### Files Importing Logger
| File | Import Statement | Lines |
|------|------------------|-------|
| `main.py` | `from utils import get_logger` | ~32 |
| `tools/dynamic_autonomous.py` | `from utils import get_logger` | Unknown |

### Decision: Keep Which One?
**KEEP**: `utils/observability.py` version (has more features)
**DEPRECATE**: `utils/custom_logging.py`
**REASON**: Observability version has `log_model_operation()` which is useful

## Task Breakdown

### Task 4.1: Analyze Features of Both Loggers
**Research step**: Read both files completely

**utils/custom_logging.py features**:
- `debug()`, `info()`, `warning()`, `error()`, `critical()`
- `_log()` helper
- `get_logger()` factory function
- Helper functions: `log_info()`, `log_error()`, `log_debug()`

**utils/observability.py features**:
- Same basic methods as custom_logging
- PLUS: `log_model_operation()` (lines 293-327)
- PLUS: `log_error()` with structured context (lines 362-384)

**Decision**: Merge best of both into `utils/observability.py`

---

### Task 4.2: Enhance utils/observability.py StructuredLogger
**File**: `utils/observability.py:277-384`

**Add missing methods from custom_logging**:
```python
# After line 384, ADD:

def debug(self, message: str, **context) -> None:
    """Log debug message."""
    self.log("debug", message, **context)

def info(self, message: str, **context) -> None:
    """Log info message."""
    self.log("info", message, **context)

def warning(self, message: str, **context) -> None:
    """Log warning message."""
    self.log("warning", message, **context)

def error(self, message: str, **context) -> None:
    """Log error message."""
    self.log("error", message, **context)

def critical(self, message: str, **context) -> None:
    """Log critical message."""
    self.log("critical", message, **context)
```

**Add get_logger factory** (if not exists):
```python
# At end of file, ADD:

def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance."""
    return StructuredLogger(name)
```

---

### Task 4.3: Add Deprecation Warning to custom_logging.py
**File**: `utils/custom_logging.py:111-123`

**Modify get_logger()**:
```python
import warnings
from utils.observability import get_logger as _new_get_logger

def get_logger(name: str, level: int = INFO) -> StructuredLogger:
    """DEPRECATED: Use utils.observability.get_logger instead.

    This function will be removed in v4.0.0.
    """
    warnings.warn(
        "utils.custom_logging.get_logger is deprecated, "
        "use utils.observability.get_logger instead",
        DeprecationWarning,
        stacklevel=2
    )
    return _new_get_logger(name)
```

**Commit deprecation first**:
```bash
git add utils/custom_logging.py utils/observability.py
git commit -m "refactor(logging): deprecate custom_logging, enhance observability

- Add basic logging methods to observability.StructuredLogger
- Add get_logger() factory to observability
- Add deprecation warning to custom_logging.get_logger()

BREAKING: None (backward compatible via deprecation)
RISK: MEDIUM
NEXT: Update imports in Phase 4 part 2"
```

---

### Task 4.4: Update Import in main.py
**File**: `main.py:32`

**Before**:
```python
from utils import get_logger, log_info
```

**After**:
```python
from utils.observability import get_logger
from utils import log_info  # Keep this if it exists
```

**Verify**: Run `python main.py --help` (should work)

---

### Task 4.5: Update Import in tools/dynamic_autonomous.py
**Same pattern as 4.4**

---

### Task 4.6: Search for ANY Other Imports
```bash
# Find all imports of custom_logging
grep -r "from utils.custom_logging" --include="*.py"
grep -r "from utils import.*get_logger" --include="*.py"
```

**Update each found file** with new import.

---

### Task 4.7: Create Migration Test
**File**: `tests/test_logger_migration.py` (NEW)

**Content** (~80 lines):
```python
import pytest
import warnings
from utils.observability import get_logger as new_get_logger
from utils.custom_logging import get_logger as old_get_logger


class TestLoggerMigration:
    """Test logger consolidation and backward compatibility."""

    def test_new_logger_has_all_methods(self):
        """Verify observability logger has all required methods."""
        logger = new_get_logger("test")

        assert hasattr(logger, 'debug')
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'warning')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'critical')
        assert hasattr(logger, 'log_model_operation')

    def test_old_logger_shows_deprecation_warning(self):
        """Verify deprecation warning is shown."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            logger = old_get_logger("test")

            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "deprecated" in str(w[0].message).lower()

    def test_both_loggers_work_identically(self):
        """Verify both loggers produce same output."""
        new_logger = new_get_logger("test")

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            old_logger = old_get_logger("test")

        # Both should have same methods
        assert type(new_logger).__name__ == type(old_logger).__name__
```

**Manual Testing**:
```python
# Test new logger
from utils.observability import get_logger
logger = get_logger("test")
logger.info("Test message", key="value")

# Test old logger (should show warning)
from utils.custom_logging import get_logger as old_logger
logger = old_logger("test")  # Should show deprecation warning
```

---

### Task 4.8: Run Tests
```bash
# Run migration tests
pytest tests/test_logger_migration.py -v

# Run main.py to verify
python main.py --help

# Run full suite
pytest
```

---

### Task 4.9: Re-index
```
Re-index: utils/observability.py, utils/custom_logging.py, main.py, tools/dynamic_autonomous.py
```

---

### Task 4.10: Commit Phase 4
```bash
git add main.py tools/ tests/test_logger_migration.py
git commit -m "refactor(logging): migrate to observability.StructuredLogger

- Update main.py to use observability.get_logger
- Update tools/dynamic_autonomous.py imports
- Add backward compatibility tests
- Verify deprecation warnings work

BREAKING: None (deprecated functions still work)
RISK: MEDIUM-HIGH (import changes)
TESTS: Added test_logger_migration.py
MIGRATION: custom_logging → observability (Phase 4 of 5 complete)"

git tag phase-4-logger-consolidation
```

---

# 📦 **PHASE 5: Merge Exception Hierarchies**

**Risk Level**: 🔴 HIGH (Widespread import changes, refactoring)
**Estimated Time**: 2-3 hours
**Test Impact**: Update all exception handling, update tests

## Impact Analysis

### Current Exception Hierarchies

**llm/exceptions.py**:
```
Exception
└── LLMError (lines 17-37)
    ├── LLMTimeoutError (lines 40-49)
    ├── LLMRateLimitError (lines 52-58)
    ├── LLMValidationError (lines 61-67)
    ├── LLMConnectionError (lines 70-80)
    ├── LLMResponseError (lines 83-89)
    ├── ModelMemoryError (lines 92-125)
    └── ModelNotFoundError (lines 128-...)
```

**utils/errors.py**:
```
Exception
└── LMStudioBridgeError (lines 9-27)
    ├── ConfigurationError (lines 30-32)
    ├── LLMClientError (lines 35-37)
    ├── MCPConnectionError (lines 40-42)
    ├── MCPToolExecutionError (lines 45-47)
    ├── ToolDiscoveryError (lines 50-52)
    ├── AutonomousExecutionError (lines 55-57)
    └── SchemaConversionError (lines 60-62)
```

### Strategy: Merge into LMStudioBridgeError

**Reason**: `LMStudioBridgeError` is more domain-specific and already used in utils/errors.py

**New Hierarchy**:
```
Exception
└── LMStudioBridgeError (utils/errors.py)
    ├── ConfigurationError
    ├── LLMError (migrated from llm/exceptions.py)
    │   ├── LLMTimeoutError
    │   ├── LLMRateLimitError
    │   ├── LLMValidationError
    │   │   └── ModelNotFoundError
    │   ├── LLMConnectionError
    │   ├── LLMResponseError
    │   └── ModelMemoryError
    ├── MCPConnectionError
    ├── MCPToolExecutionError
    ├── ToolDiscoveryError
    ├── AutonomousExecutionError
    └── SchemaConversionError
```

### Files That Import LLMError
| File | Import | Lines | Usage |
|------|--------|-------|-------|
| `llm/llm_client.py` | `from llm.exceptions import ...` | ~54-120 | Raises LLMConnectionError, etc |
| `tests/test_exceptions.py` | `from llm.exceptions import LLMError` | Multiple | Tests inheritance |
| **Potentially more files** | Search needed | Unknown | TBD |

## Task Breakdown

### Task 5.1: Search for ALL Exception Imports
```bash
# Find all imports from llm.exceptions
grep -r "from llm.exceptions import" --include="*.py"

# Find all imports from utils.errors
grep -r "from utils.errors import" --include="*.py"

# Find all raises of these exceptions
grep -r "raise LLMError\\|raise LLM.*Error\\|raise LMStudioBridgeError" --include="*.py"
```

**Document ALL findings** in a checklist before proceeding.

---

### Task 5.2: Create New Unified Exception File
**Strategy**: Create NEW file, then migrate imports

**File**: `utils/exceptions.py` (NEW)

**Content** (~300 lines):
```python
"""Unified exception hierarchy for lmstudio-bridge-enhanced.

All exceptions inherit from LMStudioBridgeError.
This module consolidates llm/exceptions.py and utils/errors.py.

Migration from v3.2.x:
- llm.exceptions.LLMError → utils.exceptions.LLMError (now inherits from LMStudioBridgeError)
- utils.errors.LMStudioBridgeError → utils.exceptions.LMStudioBridgeError (same)
"""

from typing import Optional, Any
from datetime import datetime


# ============================================================================
# BASE EXCEPTION
# ============================================================================

class LMStudioBridgeError(Exception):
    """Base exception for all lmstudio-bridge errors.

    All custom exceptions in this project inherit from this class.
    Provides:
    - Error message
    - Optional details (any JSON-serializable data)
    - Timestamp
    - Original exception tracking
    """

    def __init__(
        self,
        message: str,
        details: Optional[Any] = None,
        original_exception: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.details = details
        self.timestamp = datetime.now()
        self.original_exception = original_exception

    def __str__(self) -> str:
        base = f"{self.__class__.__name__}: {self.message}"
        if self.details:
            base += f" (details: {self.details})"
        return base


# ============================================================================
# CONFIGURATION ERRORS
# ============================================================================

class ConfigurationError(LMStudioBridgeError):
    """Configuration validation or loading error."""
    pass


# ============================================================================
# LLM ERRORS (migrated from llm/exceptions.py)
# ============================================================================

class LLMError(LMStudioBridgeError):
    """Base exception for LLM-related errors.

    All LLM-specific exceptions inherit from this class.
    NOW INHERITS FROM LMStudioBridgeError for unified hierarchy.
    """
    pass


class LLMTimeoutError(LLMError):
    """LLM request timeout."""
    pass


class LLMRateLimitError(LLMError):
    """LLM rate limit exceeded."""
    pass


class LLMValidationError(LLMError):
    """LLM response validation failed."""
    pass


class LLMConnectionError(LLMError):
    """LLM connection failed."""
    pass


class LLMResponseError(LLMError):
    """LLM response format invalid."""
    pass


class ModelMemoryError(LLMError):
    """Model cannot be loaded due to insufficient memory."""

    def __init__(
        self,
        model_name: str,
        required_memory: str = None,
        original_exception: Exception = None
    ):
        message = f"Model '{model_name}' requires more memory than available"
        if required_memory:
            message += f" (requires: {required_memory})"

        super().__init__(
            message=message,
            details={"model": model_name, "required_memory": required_memory},
            original_exception=original_exception
        )
        self.model_name = model_name
        self.required_memory = required_memory


class ModelNotFoundError(LLMValidationError):
    """Requested model not available."""
    pass


# ============================================================================
# MCP ERRORS
# ============================================================================

class LLMClientError(LMStudioBridgeError):
    """LLM client operation error."""
    pass


class MCPConnectionError(LMStudioBridgeError):
    """MCP connection failed."""
    pass


class MCPToolExecutionError(LMStudioBridgeError):
    """MCP tool execution error."""
    pass


class ToolDiscoveryError(LMStudioBridgeError):
    """MCP tool discovery failed."""
    pass


class AutonomousExecutionError(LMStudioBridgeError):
    """Autonomous execution failed."""
    pass


class SchemaConversionError(LMStudioBridgeError):
    """Schema conversion failed."""
    pass


# ============================================================================
# ERROR HANDLING UTILITIES
# ============================================================================

def handle_error(error: Exception, context: Optional[str] = None) -> str:
    """Format error for logging/display."""
    if isinstance(error, LMStudioBridgeError):
        msg = str(error)
        if context:
            msg = f"{context}: {msg}"
        return msg
    else:
        return f"{context}: {type(error).__name__}: {error}" if context else str(error)
```

**Commit NEW file first**:
```bash
git add utils/exceptions.py
git commit -m "feat(exceptions): create unified exception hierarchy

- Create utils/exceptions.py with all exceptions
- LLMError now inherits from LMStudioBridgeError
- Consolidate features from both hierarchies
- Add comprehensive docstrings

BREAKING: None yet (new file, no imports changed)
RISK: NONE (preparation step)
NEXT: Migrate imports in Phase 5 part 2"
```

---

### Task 5.3: Add Backward Compatibility Shims
**File**: `llm/exceptions.py`

**Replace entire file with**:
```python
"""DEPRECATED: Use utils.exceptions instead.

This module is deprecated and will be removed in v4.0.0.
All exceptions have been moved to utils.exceptions.

Migration guide:
  from llm.exceptions import LLMError
  # Change to:
  from utils.exceptions import LLMError
"""

import warnings

# Re-export all exceptions for backward compatibility
from utils.exceptions import (
    LLMError,
    LLMTimeoutError,
    LLMRateLimitError,
    LLMValidationError,
    LLMConnectionError,
    LLMResponseError,
    ModelMemoryError,
    ModelNotFoundError,
)

# Show deprecation warning
warnings.warn(
    "llm.exceptions is deprecated, use utils.exceptions instead. "
    "This module will be removed in v4.0.0.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = [
    "LLMError",
    "LLMTimeoutError",
    "LLMRateLimitError",
    "LLMValidationError",
    "LLMConnectionError",
    "LLMResponseError",
    "ModelMemoryError",
    "ModelNotFoundError",
]
```

**File**: `utils/errors.py`

**Replace with**:
```python
"""DEPRECATED: Use utils.exceptions instead.

This module is deprecated and will be removed in v4.0.0.
"""

import warnings
from utils.exceptions import *

warnings.warn(
    "utils.errors is deprecated, use utils.exceptions instead",
    DeprecationWarning,
    stacklevel=2
)
```

**Commit compatibility layer**:
```bash
git add llm/exceptions.py utils/errors.py
git commit -m "refactor(exceptions): add backward compatibility shims

- Make llm/exceptions.py re-export from utils.exceptions
- Make utils/errors.py re-export from utils.exceptions
- Add deprecation warnings
- ALL existing code still works!

BREAKING: None (backward compatible)
RISK: LOW (shim layer)
TESTS: Should all pass without changes"
```

---

### Task 5.4: Run Tests WITHOUT Changing Imports
```bash
# Tests should still pass with shims
pytest -v

# Verify deprecation warnings show
pytest tests/test_exceptions.py -v -W default::DeprecationWarning
```

**If tests pass**, proceed. **If tests fail**, investigate before continuing.

---

### Task 5.5: Migrate Imports (One File at a Time)

**Priority order** (least risky first):
1. Test files (isolated)
2. Utils files
3. Tools files
4. Core LLM files

**File**: `tests/test_exceptions.py`

**Before**:
```python
from llm.exceptions import LLMError, LLMTimeoutError
```

**After**:
```python
from utils.exceptions import LLMError, LLMTimeoutError
```

**Test after EACH file**:
```bash
pytest tests/test_exceptions.py -v
```

**Commit each file or small batch**:
```bash
git add tests/test_exceptions.py
git commit -m "refactor(tests): migrate test_exceptions to utils.exceptions"
```

---

### Task 5.6: Find and Migrate ALL Other Files
```bash
# List all files that need migration
grep -l "from llm.exceptions import" --include="*.py" -r .
grep -l "from utils.errors import" --include="*.py" -r .
```

**For EACH file**:
1. Update import
2. Run tests
3. Commit

---

### Task 5.7: Create Migration Verification Test
**File**: `tests/test_exception_hierarchy.py` (NEW)

**Content** (~150 lines):
```python
import pytest
from utils.exceptions import (
    LMStudioBridgeError,
    LLMError,
    LLMTimeoutError,
    LLMValidationError,
    ModelNotFoundError,
    ConfigurationError,
    MCPConnectionError,
)


class TestUnifiedExceptionHierarchy:
    """Test unified exception hierarchy."""

    def test_all_exceptions_inherit_from_base(self):
        """All exceptions should inherit from LMStudioBridgeError."""
        exceptions = [
            LLMError,
            LLMTimeoutError,
            LLMValidationError,
            ModelNotFoundError,
            ConfigurationError,
            MCPConnectionError,
        ]

        for exc_class in exceptions:
            assert issubclass(exc_class, LMStudioBridgeError)

    def test_llm_errors_inherit_from_llm_error(self):
        """LLM-specific exceptions should inherit from LLMError."""
        llm_exceptions = [
            LLMTimeoutError,
            LLMValidationError,
            ModelNotFoundError,
        ]

        for exc_class in llm_exceptions:
            assert issubclass(exc_class, LLMError)

    def test_catch_with_base_exception(self):
        """Should be able to catch all with base exception."""
        with pytest.raises(LMStudioBridgeError):
            raise LLMTimeoutError("test")

        with pytest.raises(LMStudioBridgeError):
            raise ConfigurationError("test")

    def test_catch_llm_errors_specifically(self):
        """Should be able to catch LLM errors specifically."""
        with pytest.raises(LLMError):
            raise LLMTimeoutError("test")

        # But not catch non-LLM errors
        with pytest.raises(ConfigurationError):
            try:
                raise ConfigurationError("test")
            except LLMError:
                pytest.fail("Should not catch ConfigurationError as LLMError")

    def test_backward_compatibility_imports(self):
        """Old imports should still work with deprecation warning."""
        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            from llm.exceptions import LLMError as OldLLMError

            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "deprecated" in str(w[0].message).lower()

        # But it should be the same class
        assert OldLLMError is LLMError
```

---

### Task 5.8: Final Full Test Run
```bash
# Run ALL tests
pytest -v

# Run with coverage
pytest --cov=. --cov-report=term-missing

# Expected: All pass, no import errors
```

---

### Task 5.9: Re-index ALL Modified Files
```
Re-index: utils/exceptions.py, llm/exceptions.py, utils/errors.py, all migrated files
```

---

### Task 5.10: Commit Phase 5
```bash
git add .
git commit -m "refactor(exceptions): complete exception hierarchy merge

- Migrated all imports to utils.exceptions
- Unified LLMError under LMStudioBridgeError
- Maintained backward compatibility via shims
- All tests passing

Files migrated:
- llm/llm_client.py
- tests/test_exceptions.py
- [list all other files]

BREAKING: None (deprecated modules still work)
RISK: HIGH (widespread changes) - mitigated by compatibility layer
TESTS: All pass, added test_exception_hierarchy.py
CONSOLIDATION: Phase 5 of 5 COMPLETE ✓"

git tag phase-5-exception-hierarchy
```

---

# 🎯 **POST-EXECUTION**

## Final Verification

### 1. Run Full Test Suite
```bash
pytest -v --tb=short
pytest --cov=. --cov-report=html
```

### 2. Verify All Tags
```bash
git tag | grep phase
# Should show:
# phase-1-config-validation
# phase-2-test-refactoring
# phase-3-http-pooling
# phase-4-logger-consolidation
# phase-5-exception-hierarchy
```

### 3. Check Deprecation Warnings
```bash
pytest -W default::DeprecationWarning
# Should show warnings for:
# - utils.custom_logging.get_logger
# - llm.exceptions imports
# - utils.errors imports
```

### 4. Re-index Entire Codebase
```
Re-index the entire project to update search index
```

---

## Merge to Main

```bash
# Review all changes
git log --oneline main..fix/code-quality-improvements

# Merge to main
git checkout main
git merge fix/code-quality-improvements --no-ff -m "feat: code quality improvements (Phases 1-5)

Summary of changes:
- Phase 1: Config validation with Pydantic
- Phase 2: Test runner consolidation (-300 LOC)
- Phase 3: HTTP connection pooling
- Phase 4: Logger consolidation
- Phase 5: Exception hierarchy unification

All phases backward compatible via deprecation.
All tests passing.
Full code review completed."

# Tag release
git tag v3.3.0-rc1
git push origin main --tags
```

---

# 📊 **IMPACT SUMMARY**

## Lines Changed (Estimated)
| Phase | Added | Removed | Modified | Net Change |
|-------|-------|---------|----------|------------|
| Phase 1 | ~250 | ~0 | ~50 | +250 |
| Phase 2 | ~150 | ~300 | ~100 | -150 |
| Phase 3 | ~150 | ~0 | ~80 | +150 |
| Phase 4 | ~100 | ~0 | ~50 | +100 |
| Phase 5 | ~400 | ~200 | ~150 | +200 |
| **TOTAL** | **~1050** | **~500** | **~430** | **+550** |

## Risk Mitigation
- ✅ Backward compatibility via deprecation warnings
- ✅ Tests run after EACH phase
- ✅ Git tags for easy rollback
- ✅ Code search re-indexing after changes
- ✅ Ordered from LEAST to MOST destructive

## Testing Strategy
- ~600 new test lines added
- All existing tests must pass
- Performance tests added (Phase 3)
- Migration tests added (Phase 4, Phase 5)

---

**END OF PLAN**

---

# 🔍 **APPENDIX: Search Results**

## Exception Imports Found
```
Files importing from llm.exceptions:
- llm/llm_client.py:54-120 (_handle_request_exception)
- tests/test_exceptions.py (multiple)

Files importing from utils.errors:
- [To be determined in Task 5.1]
```

## Logger Imports Found
```
Files importing get_logger:
- main.py:32
- tools/dynamic_autonomous.py
```

## HTTP Usage Found
```
Files using requests library:
- llm/llm_client.py
- utils/lms_helper.py
- llm/model_validator.py
- utils/image_utils.py
- [+ test files]
```

---

**This plan is ready for execution. Proceed phase by phase, stopping at any test failure.**
