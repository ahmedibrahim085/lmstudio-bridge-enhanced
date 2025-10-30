# Consolidation TODO: Detailed Task Breakdown

**Created**: October 30, 2025
**Goal**: Consolidate v1/v2 to single clean implementation
**Approach**: Phased, safe, Apple/Google style

---

## Quick Reference

### Timeline Options

**Conservative** (Recommended): 5 months
- Week 1: Phase 0-2 (Internal optimization)
- Months 2-4: Monitoring and deprecation
- Month 5: Cleanup

**Aggressive**: 8 weeks
- Weeks 1-2: Phase 0-2
- Week 4: Deprecation
- Week 8: Cleanup

---

## PHASE 0: Pre-Flight Checks (2-3 hours)

### 0.1 Code Inventory
- [ ] List all v1 function locations with line numbers
  - [ ] autonomous_filesystem_full: line ___
  - [ ] autonomous_memory_full: line ___
  - [ ] autonomous_fetch_full: line ___
  - [ ] autonomous_github_full: line ___

- [ ] List all v2 function locations with line numbers
  - [ ] autonomous_filesystem_full_v2: line ___
  - [ ] autonomous_memory_full_v2: line ___
  - [ ] autonomous_fetch_full_v2: line ___
  - [ ] autonomous_github_full_v2: line ___

- [ ] List FastMCP registrations (v1): lines ___
- [ ] List FastMCP registrations (v2): lines ___

### 0.2 Dependency Check
- [ ] Check if v1 functions call any v1-specific helpers
- [ ] Check if v2 functions call any v2-specific helpers
- [ ] Identify shared code between v1 and v2
- [ ] List private methods used by implementations

### 0.3 Test Inventory
- [ ] List all v1 test files:
  - [ ] test_autonomous_v2_comparison.py (uses both)
  - [ ] Other: ___

- [ ] List all v2 test files:
  - [ ] test_phase3_all_v2_functions.py
  - [ ] Other: ___

- [ ] Identify tests that need updating

### 0.4 Compatibility Verification
- [ ] Run all v1 tests - record results:
  - [ ] autonomous_filesystem_full: ___
  - [ ] autonomous_memory_full: ___
  - [ ] autonomous_fetch_full: ___
  - [ ] autonomous_github_full: ___

- [ ] Run all v2 tests - record results:
  - [ ] autonomous_filesystem_full_v2: ___
  - [ ] autonomous_memory_full_v2: ___
  - [ ] autonomous_fetch_full_v2: ___
  - [ ] autonomous_github_full_v2: ___

- [ ] Compare outputs (should be identical)
- [ ] Document any differences found

### 0.5 Documentation Check
- [ ] List all docs mentioning v1 or v2:
  - [ ] README.md
  - [ ] MIGRATION_GUIDE.md
  - [ ] Other: ___

- [ ] Note sections that need updating

### 0.6 Go/No-Go Decision
- [ ] All tests passing? (Required)
- [ ] V1 and V2 produce identical outputs? (Required)
- [ ] No known compatibility issues? (Required)
- [ ] Test coverage adequate (>80%)? (Recommended)

**Decision**: [ ] GO / [ ] NO-GO

**If NO-GO**: Document blockers: ___

---

## PHASE 1: Internal Implementation Swap (1 day)

### 1.1 Create Private Helper Methods

#### 1.1.1 Extract Stateful Implementation
- [ ] Create `_execute_autonomous_stateful()` method in tools/autonomous.py
- [ ] Move core v2 logic to this method
- [ ] Parameters:
  - [ ] task: str
  - [ ] mcp_connection: MCPConnection
  - [ ] max_rounds: int
  - [ ] max_tokens: Union[int, str]
- [ ] Return type: str
- [ ] Add comprehensive docstring
- [ ] Test method works

```python
async def _execute_autonomous_stateful(
    self,
    task: str,
    mcp_connection: MCPConnection,
    max_rounds: int,
    max_tokens: Union[int, str]
) -> str:
    """
    Execute autonomous task using stateful /v1/responses API.

    This is the optimized implementation with constant token usage.
    """
    # Implementation here
```

#### 1.1.2 Extract Stateless Implementation (for fallback)
- [ ] Create `_execute_autonomous_stateless()` method
- [ ] Move core v1 logic to this method
- [ ] Same parameters as stateful version
- [ ] Add docstring noting it's legacy/fallback
- [ ] Test method works

### 1.2 Create Connection Helper Methods

#### 1.2.1 Filesystem Connection Helper
- [ ] Create `_create_filesystem_connection()` method
- [ ] Parameters: working_directory
- [ ] Returns: MCPConnection
- [ ] Test connection creation

#### 1.2.2 Memory Connection Helper
- [ ] Create `_create_memory_connection()` method
- [ ] Returns: MCPConnection
- [ ] Test connection creation

#### 1.2.3 Fetch Connection Helper
- [ ] Create `_create_fetch_connection()` method
- [ ] Returns: MCPConnection
- [ ] Test connection creation

#### 1.2.4 GitHub Connection Helper
- [ ] Create `_create_github_connection()` method
- [ ] Parameters: github_token
- [ ] Returns: MCPConnection
- [ ] Test connection creation

### 1.3 Update V1 Functions to Use Helpers

#### 1.3.1 Update autonomous_filesystem_full
```python
- [ ] Remove old implementation code
- [ ] Call _create_filesystem_connection()
- [ ] Call _execute_autonomous_stateful()
- [ ] Update docstring (remove warning, add "optimized" note)
- [ ] Test function works
- [ ] Verify token usage is now optimized
```

#### 1.3.2 Update autonomous_memory_full
```python
- [ ] Remove old implementation code
- [ ] Call _create_memory_connection()
- [ ] Call _execute_autonomous_stateful()
- [ ] Update docstring
- [ ] Test function works
- [ ] Verify token usage is now optimized
```

#### 1.3.3 Update autonomous_fetch_full
```python
- [ ] Remove old implementation code
- [ ] Call _create_fetch_connection()
- [ ] Call _execute_autonomous_stateful()
- [ ] Update docstring
- [ ] Test function works
- [ ] Verify token usage is now optimized
```

#### 1.3.4 Update autonomous_github_full
```python
- [ ] Remove old implementation code
- [ ] Call _create_github_connection()
- [ ] Call _execute_autonomous_stateful()
- [ ] Update docstring
- [ ] Test function works
- [ ] Verify token usage is now optimized
```

### 1.4 Update V2 Functions to Use Helpers

#### 1.4.1 Update autonomous_filesystem_full_v2
```python
- [ ] Update to use same helpers as v1
- [ ] Should now be very thin wrapper
- [ ] Add docstring note: "Identical to v1 now"
- [ ] Test function works
```

#### 1.4.2 Update autonomous_memory_full_v2
```python
- [ ] Update to use same helpers
- [ ] Add docstring note
- [ ] Test function works
```

#### 1.4.3 Update autonomous_fetch_full_v2
```python
- [ ] Update to use same helpers
- [ ] Add docstring note
- [ ] Test function works
```

#### 1.4.4 Update autonomous_github_full_v2
```python
- [ ] Update to use same helpers
- [ ] Add docstring note
- [ ] Test function works
```

### 1.5 Testing Phase 1

#### 1.5.1 Unit Tests
- [ ] Test _execute_autonomous_stateful() directly
- [ ] Test _execute_autonomous_stateless() directly
- [ ] Test all connection helpers
- [ ] All unit tests passing?

#### 1.5.2 Integration Tests - V1 Functions
- [ ] Run test_autonomous_v2_comparison.py (v1 part)
- [ ] Test autonomous_filesystem_full with real MCP
- [ ] Test autonomous_memory_full with real MCP
- [ ] Test autonomous_fetch_full with real MCP
- [ ] Test autonomous_github_full with real MCP
- [ ] All v1 integration tests passing?

#### 1.5.3 Integration Tests - V2 Functions
- [ ] Run test_phase3_all_v2_functions.py
- [ ] Test all v2 functions still work
- [ ] All v2 integration tests passing?

#### 1.5.4 Comparison Tests
- [ ] Compare v1 and v2 outputs (should be identical)
- [ ] filesystem: v1 output == v2 output?
- [ ] memory: v1 output == v2 output?
- [ ] fetch: v1 output == v2 output?
- [ ] github: v1 output == v2 output?

#### 1.5.5 Performance Verification
- [ ] Measure v1 token usage (should be optimized now!)
  - [ ] filesystem: ~3K tokens at round 100?
  - [ ] memory: ~2K tokens at round 100?
  - [ ] fetch: ~500 tokens at round 100?
  - [ ] github: ~7.5K tokens at round 100?
- [ ] Compare with old v1 measurements
- [ ] Verify 97% savings achieved

### 1.6 Documentation Updates

#### 1.6.1 Update V1 Docstrings
- [ ] Remove ⚠️ warnings from all v1 functions
- [ ] Add "Now optimized with /v1/responses API" notes
- [ ] Update examples if needed
- [ ] Mention 97% token savings

#### 1.6.2 Update V2 Docstrings
- [ ] Add note: "Now identical to v1 (both optimized)"
- [ ] Mention v2 suffix is now redundant
- [ ] Point to consolidation plan

#### 1.6.3 Update README.md
- [ ] Update "Recommended: V2 Functions" section
- [ ] Add note that v1 is now optimized too
- [ ] Mention both versions use same implementation
- [ ] Update performance section

#### 1.6.4 Update MIGRATION_GUIDE.md
- [ ] Add section about Phase 1 completion
- [ ] Note that v1 is now optimized automatically
- [ ] Update recommendation (both work equally well now)

#### 1.6.5 Create Phase 1 Summary Doc
- [ ] Create PHASE1_INTERNAL_SWAP_COMPLETE.md
- [ ] Document what was changed
- [ ] Show before/after comparison
- [ ] Include test results
- [ ] List next steps

### 1.7 Git Commit
- [ ] Review all changes
- [ ] Run full test suite one more time
- [ ] Stage changes: `git add -A`
- [ ] Commit with message:
```
refactor: Phase 1 - Make v1 functions use optimized implementation internally

All autonomous functions now use the stateful /v1/responses API by default:
- Created private helper methods for implementations
- V1 functions now call optimized stateful implementation
- V2 functions now identical to v1 (both use same implementation)
- 97% token savings now automatic for all users

Breaking changes: NONE (backwards compatible)
Performance: V1 functions now as fast as v2

Tests: All passing ✅
Token usage: Verified optimized for v1 ✅
```

**Phase 1 Complete!** ✅

---

## PHASE 2: Add Optional Fallback (4 hours)

### 2.1 Add Parameter to V1 Functions

#### 2.1.1 Update autonomous_filesystem_full signature
```python
- [ ] Add parameter: use_stateful_api: bool = True
- [ ] Update type hints
- [ ] Add to docstring Args section
- [ ] Explain parameter purpose
```

#### 2.1.2 Update autonomous_memory_full signature
```python
- [ ] Add use_stateful_api parameter
- [ ] Update documentation
```

#### 2.1.3 Update autonomous_fetch_full signature
```python
- [ ] Add use_stateful_api parameter
- [ ] Update documentation
```

#### 2.1.4 Update autonomous_github_full signature
```python
- [ ] Add use_stateful_api parameter
- [ ] Update documentation
```

### 2.2 Implement Conditional Logic

#### 2.2.1 Update each function implementation
```python
if use_stateful_api:
    return await self._execute_autonomous_stateful(...)
else:
    return await self._execute_autonomous_stateless(...)
```

- [ ] filesystem: Add conditional logic
- [ ] memory: Add conditional logic
- [ ] fetch: Add conditional logic
- [ ] github: Add conditional logic

### 2.3 Update FastMCP Registrations

#### 2.3.1 Add parameter to tool definitions
- [ ] filesystem tool: Add use_stateful_api parameter
- [ ] memory tool: Add use_stateful_api parameter
- [ ] fetch tool: Add use_stateful_api parameter
- [ ] github tool: Add use_stateful_api parameter

#### 2.3.2 Update Pydantic Field definitions
```python
use_stateful_api: Annotated[
    bool,
    Field(
        default=True,
        description="Use optimized stateful API (recommended). Set False for legacy behavior."
    )
] = True
```

- [ ] Add Field annotation for each parameter
- [ ] Test Pydantic validation

### 2.4 Testing Phase 2

#### 2.4.1 Test with use_stateful_api=True (default)
- [ ] filesystem: Test default behavior
- [ ] memory: Test default behavior
- [ ] fetch: Test default behavior
- [ ] github: Test default behavior
- [ ] Verify uses stateful implementation

#### 2.4.2 Test with use_stateful_api=False (legacy)
- [ ] filesystem: Test legacy behavior
- [ ] memory: Test legacy behavior
- [ ] fetch: Test legacy behavior
- [ ] github: Test legacy behavior
- [ ] Verify uses stateless implementation
- [ ] Verify token usage is higher (expected)

#### 2.4.3 Parameter Validation
- [ ] Test with True (should work)
- [ ] Test with False (should work)
- [ ] Test with no value (should default to True)
- [ ] Test with invalid value (should fail validation)

### 2.5 Documentation

#### 2.5.1 Update docstrings
- [ ] Document new parameter in all 4 functions
- [ ] Explain when to use False (rare cases)
- [ ] Add examples showing both modes

#### 2.5.2 Update README
- [ ] Add section about fallback option
- [ ] Explain it's rarely needed
- [ ] Show example usage

#### 2.5.3 Update MIGRATION_GUIDE
- [ ] Document fallback parameter
- [ ] Explain use cases
- [ ] Add troubleshooting section

### 2.6 Git Commit
```
feat: Add optional fallback to legacy stateless API

Added use_stateful_api parameter (default=True) to all autonomous functions:
- Allows opt-in to legacy /v1/chat/completions if needed
- Default behavior unchanged (uses optimized stateful API)
- Backwards compatible

Use case: Edge cases where stateful API might have issues

Breaking changes: NONE
Default behavior: Optimized (stateful API)
```

**Phase 2 Complete!** ✅

---

## PHASE 3: Deprecate V2 Suffix (2 hours)

**Wait**: 2-4 weeks after Phase 2 before starting

### 3.1 Add Deprecation Warnings

#### 3.1.1 Import warnings module
- [ ] Add `import warnings` to tools/autonomous.py

#### 3.1.2 Add warning to autonomous_filesystem_full_v2
```python
warnings.warn(
    "autonomous_filesystem_full_v2() is deprecated. "
    "Use autonomous_filesystem_full() instead - it now uses "
    "the optimized implementation by default. "
    "The _v2 suffix will be removed in version 3.0.0.",
    DeprecationWarning,
    stacklevel=2
)
```

- [ ] Add warning at start of function
- [ ] Update docstring with [DEPRECATED] tag
- [ ] Add removal timeline

#### 3.1.3 Add warning to autonomous_memory_full_v2
- [ ] Add deprecation warning
- [ ] Update docstring

#### 3.1.4 Add warning to autonomous_fetch_full_v2
- [ ] Add deprecation warning
- [ ] Update docstring

#### 3.1.5 Add warning to autonomous_github_full_v2
- [ ] Add deprecation warning
- [ ] Update docstring

### 3.2 Update Implementations to Redirect

#### 3.2.1 Make v2 functions call v1
```python
async def autonomous_filesystem_full_v2(...):
    warnings.warn(...)
    return await self.autonomous_filesystem_full(
        task=task,
        working_directory=working_directory,
        max_rounds=max_rounds,
        max_tokens=max_tokens
    )
```

- [ ] filesystem_v2: Redirect to v1
- [ ] memory_v2: Redirect to v1
- [ ] fetch_v2: Redirect to v1
- [ ] github_v2: Redirect to v1

### 3.3 Testing

#### 3.3.1 Test warnings appear
- [ ] Call each _v2 function
- [ ] Verify DeprecationWarning is shown
- [ ] Verify warning message is clear
- [ ] Verify stacklevel is correct (points to caller)

#### 3.3.2 Test functionality unchanged
- [ ] filesystem_v2 still works correctly
- [ ] memory_v2 still works correctly
- [ ] fetch_v2 still works correctly
- [ ] github_v2 still works correctly

### 3.4 Documentation

#### 3.4.1 Update README
- [ ] Mark _v2 functions as [DEPRECATED]
- [ ] Add deprecation notice
- [ ] Show migration path (remove _v2)
- [ ] Add timeline for removal

#### 3.4.2 Update MIGRATION_GUIDE
- [ ] Add deprecation section
- [ ] Explain why _v2 is no longer needed
- [ ] Show how to migrate (trivial: remove _v2)
- [ ] Add FAQ about deprecation

#### 3.4.3 Create changelog entry
```markdown
## [2.2.0] - 2025-XX-XX

### Deprecated
- `autonomous_filesystem_full_v2()` - Use `autonomous_filesystem_full()` instead
- `autonomous_memory_full_v2()` - Use `autonomous_memory_full()` instead
- `autonomous_fetch_full_v2()` - Use `autonomous_fetch_full()` instead
- `autonomous_github_full_v2()` - Use `autonomous_github_full()` instead

The _v2 suffix is no longer needed as all functions now use the optimized
implementation by default. These functions will be removed in version 3.0.0.
```

### 3.5 Communication

#### 3.5.1 Draft announcement
- [ ] Write deprecation announcement
- [ ] Explain reasoning
- [ ] Provide migration instructions
- [ ] Set removal timeline
- [ ] Answer anticipated questions

#### 3.5.2 Update release notes
- [ ] Add to v2.2.0 release notes
- [ ] Highlight deprecation prominently
- [ ] Link to migration guide

### 3.6 Git Commit
```
deprecate: Mark _v2 suffix functions as deprecated

All _v2 functions now show DeprecationWarning:
- autonomous_filesystem_full_v2()
- autonomous_memory_full_v2()
- autonomous_fetch_full_v2()
- autonomous_github_full_v2()

Reason: Base functions now use optimized implementation by default,
making _v2 suffix redundant.

Migration: Simply remove _v2 from function names.

Removal planned for: Version 3.0.0 (Month 5)

Breaking changes: NONE (warnings only)
```

**Phase 3 Complete!** ✅

---

## PHASE 4: Remove V2 Functions (3 hours)

**Wait**: 2-3 months after Phase 3 before starting

### 4.1 Pre-Removal Checks
- [ ] Phase 3 has been active for at least 2 months
- [ ] No critical user issues reported
- [ ] No requests to keep _v2 suffix
- [ ] Users have had time to migrate
- [ ] All internal code updated (no _v2 usage)

**Decision**: [ ] GO AHEAD WITH REMOVAL / [ ] DELAY

**If delaying**: Reason: ___

### 4.2 Remove V2 Functions

#### 4.2.1 Delete implementations
- [ ] Delete autonomous_filesystem_full_v2() (entire function)
- [ ] Delete autonomous_memory_full_v2() (entire function)
- [ ] Delete autonomous_fetch_full_v2() (entire function)
- [ ] Delete autonomous_github_full_v2() (entire function)

#### 4.2.2 Remove FastMCP registrations
- [ ] Delete autonomous_filesystem_full_v2 tool registration
- [ ] Delete autonomous_memory_full_v2 tool registration
- [ ] Delete autonomous_fetch_full_v2 tool registration
- [ ] Delete autonomous_github_full_v2 tool registration

#### 4.2.3 Clean up imports
- [ ] Remove any v2-specific imports
- [ ] Clean up warnings import if no longer needed elsewhere

### 4.3 Update Tests

#### 4.3.1 Remove v2-specific tests
- [ ] Review test_phase3_all_v2_functions.py
- [ ] Decide: Delete or rename to remove v2 references
- [ ] Update test_autonomous_v2_comparison.py
  - [ ] Remove v2 comparison part or keep for history

#### 4.3.2 Update test references
- [ ] Search for _v2 in all test files
- [ ] Update or remove references
- [ ] Ensure all tests still pass

### 4.4 Documentation Cleanup

#### 4.4.1 Update README
- [ ] Remove all _v2 function mentions
- [ ] Remove "Recommended" vs "Legacy" sections
- [ ] Simplify to single function list
- [ ] Update function count (4 autonomous, not 8)

#### 4.4.2 Update MIGRATION_GUIDE
- [ ] Add note that v2 has been removed
- [ ] Keep historical context for reference
- [ ] Or archive entire guide if no longer relevant

#### 4.4.3 Clean up other docs
- [ ] Search all .md files for _v2 references
- [ ] Update or remove as appropriate
- [ ] Keep historical docs in archive if desired

#### 4.4.4 Create changelog entry
```markdown
## [3.0.0] - 2025-XX-XX

### BREAKING CHANGES
- Removed deprecated `_v2` suffix functions
  - `autonomous_filesystem_full_v2()` → Use `autonomous_filesystem_full()`
  - `autonomous_memory_full_v2()` → Use `autonomous_memory_full()`
  - `autonomous_fetch_full_v2()` → Use `autonomous_fetch_full()`
  - `autonomous_github_full_v2()` → Use `autonomous_github_full()`

Migration: Remove the `_v2` suffix from function names. All functions now
use the optimized implementation by default.
```

### 4.5 Version Management

#### 4.5.1 Update version numbers
- [ ] Update setup.py: version="3.0.0"
- [ ] Update __version__ in __init__.py if exists
- [ ] Update any other version references

#### 4.5.2 Create git tag
- [ ] Commit all changes
- [ ] Tag release: `git tag -a v3.0.0 -m "Version 3.0.0 - Simplified API"`
- [ ] Push tag: `git push origin v3.0.0`

### 4.6 Testing Phase 4

#### 4.6.1 Verify v2 functions don't exist
- [ ] Try importing _v2 functions (should fail)
- [ ] Check FastMCP tool list (no _v2 tools)
- [ ] Verify 4 functions total, not 8

#### 4.6.2 Test remaining functions
- [ ] Test autonomous_filesystem_full
- [ ] Test autonomous_memory_full
- [ ] Test autonomous_fetch_full
- [ ] Test autonomous_github_full
- [ ] All tests passing with v3.0.0?

#### 4.6.3 Integration testing
- [ ] Test with real MCP servers
- [ ] Test all use cases
- [ ] Verify performance still optimal
- [ ] No regressions?

### 4.7 Release

#### 4.7.1 Prepare release notes
- [ ] Highlight breaking changes
- [ ] Provide migration instructions
- [ ] Link to documentation
- [ ] Announce simplification

#### 4.7.2 Publish
- [ ] Build package: `python setup.py sdist bdist_wheel`
- [ ] Upload to PyPI: `twine upload dist/*`
- [ ] Verify package is available

#### 4.7.3 Communicate
- [ ] Post release announcement
- [ ] Update project status
- [ ] Notify users

### 4.8 Git Commit
```
BREAKING: Remove deprecated _v2 suffix functions (v3.0.0)

Removed:
- autonomous_filesystem_full_v2()
- autonomous_memory_full_v2()
- autonomous_fetch_full_v2()
- autonomous_github_full_v2()

These functions were deprecated in v2.2.0 and are now removed.

Migration: Use base functions without _v2 suffix (they're already optimized).

Version: 3.0.0
Breaking changes: YES (removed deprecated functions)
```

**Phase 4 Complete!** ✅

---

## PHASE 5: Optional - Remove Fallback (2 hours)

**OPTIONAL**: Only if confident fallback is not needed

**Wait**: 3-6 months after Phase 4, then decide

### 5.1 Analysis
- [ ] Check if anyone is using `use_stateful_api=False`
- [ ] Review any issues related to stateful API
- [ ] Evaluate necessity of fallback
- [ ] Make decision: Keep or remove?

**Decision**: [ ] KEEP FALLBACK / [ ] REMOVE FALLBACK

**Reasoning**: ___

### 5.2 If Removing Fallback

#### 5.2.1 Remove parameter
- [ ] Remove `use_stateful_api` from all 4 functions
- [ ] Remove from docstrings
- [ ] Remove from FastMCP registrations

#### 5.2.2 Remove stateless implementation
- [ ] Delete `_execute_autonomous_stateless()` method
- [ ] Clean up any stateless-specific helpers
- [ ] Keep only optimized implementation

#### 5.2.3 Simplify code
- [ ] Remove conditional logic
- [ ] Direct call to stateful implementation only
- [ ] Clean up unnecessary complexity

#### 5.2.4 Testing
- [ ] Test all functions still work
- [ ] Verify no regressions
- [ ] Performance check

#### 5.2.5 Documentation
- [ ] Remove fallback parameter docs
- [ ] Simplify examples
- [ ] Update function signatures

#### 5.2.6 Version bump
- [ ] Version 4.0.0 (breaking change)
- [ ] Changelog entry
- [ ] Release notes

### 5.3 If Keeping Fallback

#### 5.3.1 Document decision
- [ ] Create doc explaining why keeping fallback
- [ ] Document use cases for `use_stateful_api=False`
- [ ] Add to FAQ

#### 5.3.2 Monitor usage
- [ ] Add telemetry (optional)
- [ ] Track how often fallback is used
- [ ] Review periodically

**Phase 5 Complete!** ✅ or [ ] Skipped

---

## Progress Tracking

### Overall Status

- [ ] Phase 0: Pre-Flight Checks
- [ ] Phase 1: Internal Swap
- [ ] Phase 2: Add Fallback
- [ ] Phase 3: Deprecate V2
- [ ] Phase 4: Remove V2
- [ ] Phase 5: Remove Fallback (Optional)

### Current Phase: _____

### Time Tracking

- Phase 0: Started ___ | Completed ___
- Phase 1: Started ___ | Completed ___
- Phase 2: Started ___ | Completed ___
- Phase 3: Started ___ | Completed ___
- Phase 4: Started ___ | Completed ___
- Phase 5: Started ___ | Completed ___

### Blockers / Issues

1. ___
2. ___
3. ___

---

## Quick Commands Reference

### Testing
```bash
# Run all tests
python3 test_autonomous_v2_comparison.py
python3 test_phase3_all_v2_functions.py

# Run specific test
python3 -c "from tools.autonomous import AutonomousExecutionTools; import asyncio; asyncio.run(test())"
```

### Git
```bash
# Check status
git status

# Stage changes
git add -A

# Commit
git commit -m "message"

# Tag release
git tag -a v3.0.0 -m "Version 3.0.0"
```

### Version bump
```bash
# Update setup.py version
# Update CHANGELOG.md
# Tag and push
```

---

**TODO Created**: October 30, 2025
**Ready to execute**: Phase 0 onwards
**Estimated completion**: 1-5 months depending on timeline
