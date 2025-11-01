# COMPLETE RENAMING IMPACT ANALYSIS
## From "AUTONOMOUS" to "LLM" Unified Naming Convention

**Generated:** 2025-01-11
**Scope:** Complete codebase transformation
**Estimated Impact:** 40 files, 150+ references

---

## PHASE 1: FILE RENAMES

### Core Implementation Files

| Current Name | New Name | Reason |
|--------------|----------|--------|
| `tools/autonomous.py` | `tools/llm_execution.py` | Core LLM execution logic |
| `tools/dynamic_autonomous.py` | `tools/llm_dynamic_execution.py` | Dynamic LLM execution |
| `tools/dynamic_autonomous_register.py` | `tools/llm_dynamic_register.py` | Tool registration |

### Test Files (Following "llm_" prefix convention)

| Current Name | New Name | Impact |
|--------------|----------|--------|
| `test_autonomous_tools.py` | `test_llm_execution_tools.py` | Main test file |
| `test_dynamic_mcp_discovery.py` | Keep as-is | No autonomous reference |
| `test_integration_real.py` | Keep as-is | Import updates only |
| `proper_extensive_testing.py` | `llm_extensive_testing.py` | Follows llm_ prefix |
| `extensive_real_testing.py` | `llm_real_testing.py` | Follows llm_ prefix |
| `test_truncation_real.py` | `test_llm_truncation.py` | Follows llm_ prefix |
| `test_reasoning_integration.py` | `test_llm_reasoning.py` | Follows llm_ prefix |
| `test_corner_cases_extensive.py` | `test_llm_corner_cases.py` | Follows llm_ prefix |
| `test_option_4a_comprehensive.py` | `test_llm_option_4a.py` | Follows llm_ prefix |
| `test_persistent_session_working.py` | `test_llm_persistent_session.py` | Follows llm_ prefix |
| `test_tool_execution_debug.py` | `test_llm_tool_execution_debug.py` | Follows llm_ prefix |

**Total Files to Rename:** 14 files

---

## PHASE 2: CONSTANT RENAMES

### In `config/constants.py`

| Line | Current Name | New Name | Usage Count |
|------|--------------|----------|-------------|
| 53 | `DEFAULT_AUTONOMOUS_TIMEOUT` | `DEFAULT_LLM_EXECUTION_TIMEOUT` | 1 reference |
| 128 | `DEFAULT_AUTONOMOUS_MODEL` | `DEFAULT_LLM_MODEL` | 5 references |

### In `llm/llm_client.py`

| Line | Current Name | New Name | Usage Count |
|------|--------------|----------|-------------|
| 40 | `DEFAULT_AUTONOMOUS_ROUNDS` | `DEFAULT_LLM_MAX_ROUNDS` | 2 references |

**Total Constants to Rename:** 3 constants, 8 references

---

## PHASE 3: CLASS RENAMES

### In `tools/autonomous.py` (→ `tools/llm_execution.py`)

| Current Name | New Name | References |
|--------------|----------|------------|
| `AutonomousExecutionTools` | `LLMExecutionTools` | 89 references |

### In `tools/dynamic_autonomous.py` (→ `tools/llm_dynamic_execution.py`)

| Current Name | New Name | References |
|--------------|----------|------------|
| `DynamicAutonomousAgent` | `DynamicLLMAgent` | Included in 89 above |

**Total Classes to Rename:** 2 classes, 89 total references

---

## PHASE 4: FUNCTION RENAMES

### Public API Functions (tools/autonomous.py)

| Line Range | Current Name | New Name |
|------------|--------------|----------|
| ~100-200 | `autonomous_filesystem_full()` | `llm_execution_with_filesystem()` |
| ~250-350 | `autonomous_memory_full()` | `llm_execution_with_memory()` |
| ~400-500 | `autonomous_fetch_full()` | `llm_execution_with_fetch()` |
| ~550-650 | `autonomous_github_full()` | `llm_execution_with_github()` |

### Public API Functions (tools/dynamic_autonomous.py)

| Line Range | Current Name | New Name |
|------------|--------------|----------|
| ~90-150 | `autonomous_with_mcp()` | `llm_execution_with_mcp()` |
| ~180-250 | `autonomous_with_multiple_mcps()` | `llm_execution_with_multiple_mcps()` |
| ~280-350 | `autonomous_persistent_session()` | `llm_persistent_execution()` |
| ~380-450 | `autonomous_discover_and_execute()` | `llm_discover_and_execute()` |

### Registered Tool Functions (tools/dynamic_autonomous_register.py)

| Line Range | Current Name | New Name |
|------------|--------------|----------|
| ~25-100 | `autonomous_with_mcp` (FastMCP tool) | `llm_execution_with_mcp` |
| ~105-180 | `autonomous_with_multiple_mcps` | `llm_execution_with_multiple_mcps` |
| ~185-260 | `autonomous_persistent_session` | `llm_persistent_execution` |
| ~265-340 | `autonomous_discover_and_execute` | `llm_discover_and_execute` |
| ~345-420 | `list_available_mcps` | Keep as-is (no autonomous ref) |

**Total Functions to Rename:** 12 functions

---

## PHASE 5: IMPORT STATEMENT UPDATES

### Files with `from tools.autonomous import`

| File | Line | Current Import | New Import |
|------|------|----------------|------------|
| `extensive_real_testing.py` | 22 | `from tools.autonomous import AutonomousExecutionTools` | `from tools.llm_execution import LLMExecutionTools` |
| `main.py` | 22 | `from tools.autonomous import AutonomousExecutionTools` | `from tools.llm_execution import LLMExecutionTools` |
| `proper_extensive_testing.py` | 18 | `from tools.autonomous import AutonomousExecutionTools` | `from tools.llm_execution import LLMExecutionTools` |
| `test_autonomous_tools.py` | 19 | `from tools.autonomous import AutonomousExecutionTools` | `from tools.llm_execution import LLMExecutionTools` |
| `test_comprehensive_coverage.py` | 39, 134, 217 | Multiple imports | Update all |
| `test_corner_cases_extensive.py` | 24 | `from tools.autonomous import AutonomousExecutionTools` | `from tools.llm_execution import LLMExecutionTools` |
| `test_lmstudio_api_integration.py` | 25 | `from tools.autonomous import AutonomousExecutionTools` | `from tools.llm_execution import LLMExecutionTools` |
| `test_lmstudio_api_integration_v2.py` | 29 | `from tools.autonomous import AutonomousExecutionTools` | `from tools.llm_execution import LLMExecutionTools` |
| `test_option_4a_comprehensive.py` | 30, 75, 112, 147 | Multiple imports | Update all |
| `test_persistent_session_working.py` | 21 | `from tools.autonomous import AutonomousExecutionTools` | `from tools.llm_execution import LLMExecutionTools` |
| `test_reasoning_integration.py` | 24 | `from tools.autonomous import AutonomousExecutionTools` | `from tools.llm_execution import LLMExecutionTools` |
| `test_tool_execution_debug.py` | 25 | `from tools.autonomous import AutonomousExecutionTools` | `from tools.llm_execution import LLMExecutionTools` |
| `test_truncation_real.py` | 18 | `from tools.autonomous import AutonomousExecutionTools` | `from tools.llm_execution import LLMExecutionTools` |

**Total: 13 files, 18+ import lines**

### Files with `from tools.dynamic_autonomous import`

| File | Line | Current Import | New Import |
|------|------|----------------|------------|
| `main.py` | 23 | `from tools.dynamic_autonomous import DynamicAutonomousAgent` | `from tools.llm_dynamic_execution import DynamicLLMAgent` |
| `test_dynamic_mcp_discovery.py` | 16 | `from tools.dynamic_autonomous import DynamicAutonomousAgent` | `from tools.llm_dynamic_execution import DynamicLLMAgent` |
| `test_integration_real.py` | 24 | `from tools.dynamic_autonomous import DynamicAutonomousAgent` | `from tools.llm_dynamic_execution import DynamicLLMAgent` |
| `tests/benchmark_multi_model.py` | 24 | `from tools.dynamic_autonomous import DynamicAutonomousAgent` | `from tools.llm_dynamic_execution import DynamicLLMAgent` |
| `tests/test_e2e_multi_model.py` | 26 | `from tools.dynamic_autonomous import DynamicAutonomousAgent` | `from tools.llm_dynamic_execution import DynamicLLMAgent` |
| `tests/test_multi_model_integration.py` | 21 | `from tools.dynamic_autonomous import DynamicAutonomousAgent` | `from tools.llm_dynamic_execution import DynamicLLMAgent` |
| `tools/dynamic_autonomous_register.py` | 11 | `from tools.dynamic_autonomous import DynamicAutonomousAgent` | `from tools.llm_dynamic_execution import DynamicLLMAgent` |

**Total: 7 files, 7 import lines**

---

## PHASE 6: CONSTANT USAGE UPDATES

### DEFAULT_AUTONOMOUS_MODEL References

| File | Lines | Context |
|------|-------|---------|
| `config/constants.py` | 128 | Definition |
| `tools/dynamic_autonomous.py` | 126, 130, 265, 437 | Import and usage |
| `lmstudio_bridge.py` | 427, 432 | Import and usage |

**Update to:** `DEFAULT_LLM_MODEL`

### DEFAULT_AUTONOMOUS_TIMEOUT References

| File | Lines | Context |
|------|-------|---------|
| `config/constants.py` | 53 | Definition |

**Update to:** `DEFAULT_LLM_EXECUTION_TIMEOUT`

### DEFAULT_AUTONOMOUS_ROUNDS References

| File | Lines | Context |
|------|-------|---------|
| `llm/llm_client.py` | 40, 621 | Definition and usage |

**Update to:** `DEFAULT_LLM_MAX_ROUNDS`

---

## PHASE 7: FUNCTION CALL UPDATES

### Files Calling Autonomous Functions

**Files calling `autonomous_filesystem_full()`:**
- `extensive_real_testing.py`
- `proper_extensive_testing.py`
- `test_autonomous_tools.py`
- `test_lmstudio_api_integration.py`
- `test_lmstudio_api_integration_v2.py`
- `test_option_4a_comprehensive.py`
- `test_reasoning_integration.py`

**Files calling `autonomous_with_mcp()`:**
- `test_comprehensive_coverage.py`
- `test_dynamic_mcp_discovery.py`
- `tests/benchmark_multi_model.py`
- `tests/test_e2e_multi_model.py`
- `tests/test_multi_model_integration.py`

**Files calling `autonomous_with_multiple_mcps()`:**
- `test_comprehensive_coverage.py`
- `test_option_4a_comprehensive.py`

**Files calling `autonomous_persistent_session()`:**
- `test_persistent_session_working.py`
- `test_phase2_2.py`
- `test_phase2_2_manual.py`

**Files calling `autonomous_discover_and_execute()`:**
- `test_comprehensive_coverage.py`
- `test_tool_execution_debug.py`

---

## PHASE 8: DOCSTRING AND COMMENT UPDATES

### Files with "autonomous" in Docstrings/Comments

All renamed files will need docstring updates:
- Function docstrings mentioning "autonomous execution"
- Class docstrings mentioning "autonomous agent"
- Inline comments mentioning "autonomous loop"
- Example code in docstrings

**Estimated:** 50+ docstrings/comments

---

## PHASE 9: VARIABLE NAME UPDATES

### Internal Variable Names

Files may have internal variables like:
- `autonomous_result`
- `autonomous_agent`
- `autonomous_tools`
- `agent` (context-dependent)

**Strategy:** Update only where "autonomous" is explicitly in the variable name

---

## PHASE 10: TEST DISCOVERY PATTERNS

### Pytest Discovery

Current pattern: `test_autonomous_*.py`
New pattern: `test_llm_*.py`

**Impact:** Test runners should still discover renamed files (pytest finds all `test_*.py`)

---

## SUMMARY

| Category | Count | Complexity |
|----------|-------|------------|
| **Files to rename** | 14 | Medium |
| **Constants to rename** | 3 (8 refs) | Low |
| **Classes to rename** | 2 (89 refs) | High |
| **Functions to rename** | 12 | High |
| **Import statements** | 20 files, 25+ lines | Medium |
| **Function calls** | 19 files, 40+ calls | High |
| **Docstrings/Comments** | 50+ | Medium |
| **Variable names** | ~10-20 | Low |

**TOTAL ESTIMATED IMPACT:**
- **40+ files** to modify
- **150+ specific line changes**
- **High risk** if not done systematically

---

## RECOMMENDED EXECUTION ORDER

1. ✅ Run full test suite (baseline)
2. ✅ Rename constants in `config/constants.py`
3. ✅ Update constant imports (9 files)
4. ✅ Run tests (verify constants work)
5. ✅ Rename class definitions
6. ✅ Update class imports (20 files)
7. ✅ Run tests (verify classes work)
8. ✅ Rename function definitions
9. ✅ Update function calls (19 files)
10. ✅ Run tests (verify functions work)
11. ✅ Rename files
12. ✅ Update all import paths
13. ✅ Run tests (verify imports work)
14. ✅ Update docstrings and comments
15. ✅ Final full test suite run
16. ✅ Git commit with detailed message

---

## RISK MITIGATION

### High-Risk Areas

1. **Circular imports** - Renaming files might break import order
2. **Dynamic imports** - Code using `importlib` or `__import__`
3. **String references** - Tool names in FastMCP decorators
4. **External references** - If other projects import these modules

### Safety Measures

1. ✅ Use find-and-replace with regex
2. ✅ Run tests after EACH phase
3. ✅ Git commit after each successful phase
4. ✅ Keep backup of original code
5. ✅ Use IDE refactoring tools (if available)

---

## TESTING STRATEGY

### Before Renaming

```bash
# Run full suite, save output
pytest tests/ -v > test_output_before.txt 2>&1

# Count passing tests
grep "PASSED" test_output_before.txt | wc -l

# Run specific test files
pytest test_autonomous_tools.py -v
pytest test_dynamic_mcp_discovery.py -v
pytest tests/test_multi_model_integration.py -v
```

### After Each Phase

```bash
# Run same tests
pytest tests/ -v

# Compare with baseline
# ALL tests that passed before MUST pass after
```

### After Complete Renaming

```bash
# Run full suite again
pytest tests/ -v > test_output_after.txt 2>&1

# Diff the results
diff test_output_before.txt test_output_after.txt

# Should be IDENTICAL (except file name references)
```

---

## AUTOMATION SCRIPT (Recommended)

```bash
#!/bin/bash
# rename_autonomous_to_llm.sh

set -e  # Exit on error

echo "Phase 1: Renaming constants..."
# Use sed or similar for safe replacements

echo "Phase 2: Running tests..."
pytest tests/ -v || { echo "Tests failed!"; exit 1; }

echo "Phase 3: Renaming classes..."
# More replacements

echo "Phase 4: Running tests..."
pytest tests/ -v || { echo "Tests failed!"; exit 1; }

# ... continue for all phases
```

---

**END OF ANALYSIS**
