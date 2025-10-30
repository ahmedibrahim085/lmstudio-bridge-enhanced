# Review Cycle Framework

**Collaborative Review Process for Multi-Model Implementation**

---

## Overview

This framework defines the review process for implementing multi-model support in lmstudio-bridge-enhanced. It establishes clear roles, responsibilities, and checkpoints for collaboration between Claude Code and local LLMs.

---

## Team Members & Roles

### Claude Code (Primary Implementer)
**Responsibilities**:
- File creation and editing
- Code implementation
- Test execution
- Git operations
- Final integration

**Strengths**:
- Direct file system access
- Can execute tests
- Can use MCP tools
- Git integration

### Qwen3-Coder 30B (Code Review Specialist)
**Responsibilities**:
- Code quality review
- Implementation pattern validation
- Best practices enforcement
- Performance considerations
- Code-level design decisions

**Strengths**:
- Deep coding expertise
- Pattern recognition
- Code smell detection
- Performance optimization

### Qwen3-Thinking 4B (Architecture & Logic Specialist)
**Responsibilities**:
- Logical flow validation
- Task breakdown verification
- Completeness checks
- Process design review
- Integration logic

**Strengths**:
- Step-by-step reasoning
- Edge case identification
- Logical consistency
- Process optimization

### Magistral Small 2509 (Strategic Architecture Specialist)
**Responsibilities**:
- High-level architecture review
- Design pattern validation
- Strategic decision review
- Trade-off analysis
- Long-term implications

**Strengths**:
- Reasoning capability
- Strategic thinking
- Architecture patterns
- System design

---

## Review Types

### Type 1: Design Review (Before Implementation)

**When**: Before starting implementation of any component

**Process**:
1. **Implementer** (usually Claude) presents design/plan to **Reviewer** (appropriate LLM)
2. **Reviewer** evaluates:
   - Architecture soundness
   - Design patterns appropriateness
   - Edge cases coverage
   - Performance implications
   - Security considerations
   - Extensibility
3. **Reviewer** provides:
   - Approval + suggestions, OR
   - Rejection + required changes
4. **Implementer** addresses feedback and gets re-approval if needed

**Duration**: 10-20 minutes per component

**Example**:
```
Claude: "I'm about to implement ModelRouter. Here's my design:
[shares design details]
What do you think?"

Qwen3-Thinking: "The design looks good, but I see 3 issues:
1. Missing timeout handling in strategy chain
2. No consideration for concurrent requests
3. Cache invalidation not specified

Please address these before implementing."

Claude: "Good catches! Updated design:
[addresses issues]
Ready to proceed?"

Qwen3-Thinking: "Approved! Implementation can begin."
```

---

### Type 2: Implementation Review (After Coding)

**When**: After completing implementation of component/phase

**Process**:
1. **Implementer** shares completed code with **Reviewer**
2. **Reviewer** examines:
   - Code correctness
   - Error handling
   - Type safety
   - Test coverage
   - Documentation
   - Adherence to design
   - Best practices
3. **Reviewer** provides:
   - Approval, OR
   - Change requests with specific issues
4. **Implementer** fixes issues and requests re-review

**Duration**: 15-30 minutes per component

**Checklist for Reviewer**:
- [ ] Does code match design?
- [ ] Are all edge cases handled?
- [ ] Is error handling robust?
- [ ] Are type hints present and correct?
- [ ] Are tests comprehensive?
- [ ] Is documentation clear?
- [ ] Are there any code smells?
- [ ] Is performance acceptable?

**Example**:
```
Claude: "I've implemented ModelRouter. Code is in llm/model_router.py.
Please review."

Qwen3-Coder: "Reviewed. Issues found:
1. Line 45: Strategy chain doesn't handle NoSuitableModelError
2. Line 78: Missing type hint for _strategy_applies return
3. Line 102: No timeout on discovery.discover_models()
4. Tests: Missing test for concurrent route_request calls

Please fix these 4 issues."

Claude: "Fixed all 4 issues. Changes:
[describes fixes]
Ready for re-review?"

Qwen3-Coder: "Verified fixes. Approved! ✅"
```

---

### Type 3: Phase Completion Review (After Phase)

**When**: After completing all tasks in a phase

**Process**:
1. **Implementer** presents all phase deliverables
2. **All Reviewers** (all 3 LLMs) examine together:
   - Phase goals achieved
   - All tasks completed
   - Integration working
   - Tests passing
   - Documentation complete
3. **Reviewers** reach consensus:
   - Approve phase completion, OR
   - Request additional work
4. Sign-off before next phase begins

**Duration**: 20-30 minutes per phase

**Phase Completion Checklist**:
- [ ] All tasks in phase completed
- [ ] All files created/modified as planned
- [ ] All tests passing
- [ ] Documentation updated
- [ ] No regressions introduced
- [ ] Ready for next phase

**Example**:
```
Claude: "Phase 1 (Foundation) complete. Deliverables:
- llm/interfaces.py ✅
- llm/exceptions.py ✅
- llm/config.py ✅
- llm/metrics.py ✅
- docs/ARCHITECTURE_V2.md ✅
All tests passing. Ready for phase review."

Qwen3-Coder: "Code quality looks good. Exception hierarchy is solid."

Qwen3-Thinking: "Logical flow is sound. All interfaces complete."

Magistral: "Architecture is well-designed. Ready for Phase 2."

All: "Phase 1 APPROVED ✅"
```

---

### Type 4: Cross-Phase Integration Review

**When**: After integrating components from multiple phases

**Process**:
1. **Implementer** demonstrates integration
2. **Reviewers** validate:
   - Components work together
   - No integration bugs
   - Data flow correct
   - Error propagation works
3. **Reviewers** approve or request fixes

**Duration**: 15-25 minutes

**Example**:
```
Claude: "Integrated ModelRouter (Phase 2) with DynamicAutonomousAgent (Phase 4).
Testing shows all 3 autonomous methods now use router.
Run test_integration_v2.py - all pass."

Magistral: "Integration looks clean. Router integration is seamless."
```

---

### Type 5: Final Release Review

**When**: After all phases complete, before release

**Process**:
1. **Implementer** presents complete implementation
2. **All Reviewers** perform comprehensive review:
   - All requirements met
   - All tests passing
   - Performance acceptable
   - Documentation complete
   - No critical issues
   - Ready for production
3. **Reviewers** provide final sign-off

**Duration**: 30-45 minutes

**Final Release Checklist**:
- [ ] All phase completion reviews passed
- [ ] End-to-end tests passing
- [ ] Performance benchmarks met
- [ ] Documentation complete and accurate
- [ ] No known critical bugs
- [ ] Migration guide (if needed)
- [ ] CHANGELOG updated
- [ ] Version bumped

---

## Review Assignment Matrix

### Option A: Hardened MVP

| Phase | Task | Design Reviewer | Implementation Reviewer | Phase Reviewer |
|-------|------|-----------------|------------------------|----------------|
| **Phase 1: Validation Layer** | | | | |
| 1.1 | Exception Hierarchy | - | Qwen3-Coder | All 3 |
| 1.2 | Error Handling Utils | - | Qwen3-Thinking | All 3 |
| 1.3 | Model Validator | Magistral | Magistral | All 3 |
| 1.4 | Validation Tests | - | Qwen3-Thinking | All 3 |
| **Phase 2: Core Interface** | | | | |
| 2.1 | Update Agent Class | - | Qwen3-Coder | All 3 |
| 2.2 | Update Registration | - | Qwen3-Thinking | All 3 |
| 2.3 | Update LLMClient | - | Qwen3-Coder | All 3 |
| 2.4 | Integration Tests | - | Magistral | All 3 |
| **Phase 3: Documentation** | | | | |
| 3.1 | API Reference | - | Qwen3-Thinking | All 3 |
| 3.2 | README | - | Qwen3-Coder | All 3 |
| 3.3 | Multi-Model Guide | Magistral | Magistral | All 3 |
| 3.4 | Troubleshooting | - | Qwen3-Coder | All 3 |
| **Phase 4: Testing & Polish** | | | | |
| 4.1 | E2E Testing | - | Qwen3-Coder | All 3 |
| 4.2 | Benchmarking | Magistral | Magistral | All 3 |
| 4.3 | Doc Review | All 3 | - | All 3 |
| 4.4 | Final Polish | - | Qwen3-Coder | All 3 |

### Option C: Full Re-architecture

| Phase | Primary Reviewer | Phase Reviewer |
|-------|------------------|----------------|
| Phase 1: Foundation | Magistral | All 3 |
| Phase 2: Router | Qwen3-Coder | All 3 |
| Phase 3: Concurrency | Qwen3-Thinking | All 3 |
| Phase 4: Integration | Qwen3-Coder | All 3 |
| Phase 5: Advanced | Magistral | All 3 |
| Phase 6: Docs & Testing | All 3 | All 3 |

---

## Review Communication Protocol

### Requesting Review

**Template**:
```
REVIEW REQUEST

Type: [Design/Implementation/Phase Completion/Final]
Component: [Component name]
Reviewer: @[LLM name]

Context:
[Brief context about what needs review]

Deliverables:
- [List of files/designs]

Specific concerns:
- [Any specific areas to focus on]

Ready for review: [Yes/No]
```

### Providing Review

**Template**:
```
REVIEW RESPONSE

Component: [Component name]
Reviewer: [LLM name]
Status: [APPROVED / CHANGES REQUESTED]

Findings:
✅ [Things that are good]
⚠️  [Things that need attention]
❌ [Things that must be fixed]

Required Changes:
1. [Specific change with file/line if applicable]
2. [Specific change]

Optional Suggestions:
- [Nice-to-have improvements]

Next Steps:
[What implementer should do next]

[APPROVED] or [CHANGES REQUIRED]
```

---

## Review Criteria

### Code Quality
- **Correctness**: Does code do what it's supposed to do?
- **Clarity**: Is code easy to understand?
- **Consistency**: Does code follow project patterns?
- **Completeness**: Are all cases handled?

### Architecture
- **Separation of Concerns**: Are responsibilities well-divided?
- **Extensibility**: Can code be extended easily?
- **Maintainability**: Will code be easy to maintain?
- **Performance**: Are there performance issues?

### Testing
- **Coverage**: Are all code paths tested?
- **Quality**: Are tests meaningful?
- **Edge Cases**: Are edge cases covered?
- **Integration**: Do integration tests exist?

### Documentation
- **Completeness**: Is everything documented?
- **Clarity**: Is documentation clear?
- **Accuracy**: Is documentation correct?
- **Examples**: Are there good examples?

---

## Feedback Incorporation Process

### When Changes Requested

1. **Implementer** acknowledges feedback:
   ```
   "Received feedback. Working on fixes for:
   1. [Issue 1]
   2. [Issue 2]

   ETA: [time estimate]"
   ```

2. **Implementer** makes changes and documents:
   ```
   "Changes completed:

   Issue 1: [What was changed]
   - File: [filename:line]
   - Change: [description]

   Issue 2: [What was changed]
   - File: [filename:line]
   - Change: [description]

   Ready for re-review."
   ```

3. **Reviewer** verifies fixes:
   ```
   "Verified all changes. Status: [APPROVED/STILL NEEDS WORK]"
   ```

### When Approved

1. **Reviewer** gives explicit approval:
   ```
   "APPROVED ✅

   All criteria met. Ready to proceed to next task/phase."
   ```

2. **Implementer** proceeds and updates todo list

---

## Conflict Resolution

### If Reviewers Disagree

1. Present both viewpoints clearly
2. Discussbetween LLMs to reach consensus
3. If no consensus: Implementer makes decision with rationale
4. Document decision in code comments

**Example**:
```
Qwen3-Coder: "Should use Strategy pattern here"
Magistral: "Simple factory pattern is sufficient"

Discussion:
Qwen3-Coder: "Strategy provides more flexibility for future"
Magistral: "Factory is simpler and YAGNI applies here"

Decision: Use Factory pattern for MVP (Option A), Strategy for Option C
Rationale: Aligns with Option A goal of simplicity
```

---

## Quality Gates

### Must Pass Before Phase Completion

1. **All tasks completed**: Every task in phase done
2. **All tests passing**: No failing tests
3. **No critical issues**: All critical review comments addressed
4. **Documentation current**: Docs match implementation
5. **Reviewer approval**: All assigned reviewers approved

### Must Pass Before Release

1. **All phases complete**: Every phase approved
2. **End-to-end tests pass**: Full integration working
3. **Performance benchmarks met**: Performance acceptable
4. **Documentation complete**: All docs finished
5. **No known critical bugs**: Clean issue state
6. **Final review approved**: All 3 LLMs signed off

---

## Metrics & Tracking

### Track Per Review

- **Review duration**: How long did review take?
- **Issues found**: How many issues were found?
- **Approval rounds**: How many rounds to approval?
- **Issue categories**: What types of issues?

### Track Per Phase

- **Total review time**: All reviews in phase
- **Rework time**: Time spent on fixes
- **First-time approval rate**: % approved first time

### Track Overall

- **Total implementation time**
- **Total review time**
- **Issue density**: Issues per 100 lines
- **Quality score**: Based on final review

---

## Tools for Reviews

### For Claude Code (Implementer)

- Read tool: Share code with reviewers
- Write tool: Implement changes
- Edit tool: Fix specific issues
- Bash tool: Run tests

### For Local LLMs (Reviewers)

- lmstudio-bridge autonomous tools:
  - `autonomous_with_mcp("filesystem", "Review this file...")`
  - Can read files independently
  - Can analyze code structure
  - Can check patterns

### For Communication

- Clear @mentions for reviewers
- Structured templates
- Todo list for tracking
- Explicit approval/rejection

---

## Examples

### Example 1: Successful Design Review

```
Claude: "About to implement Exception Hierarchy.

Design:
- Base LLMError class with original_exception tracking
- 6 specific exception types
- Context support for structured logging
- to_dict() method for serialization

File: llm/exceptions.py (new)

@Qwen3-Coder: Ready for design review?"

Qwen3-Coder: "DESIGN REVIEW

Status: APPROVED ✅

Findings:
✅ Exception hierarchy is well-structured
✅ Context support is good practice
✅ to_dict() enables structured logging
✅ Clear separation of exception types

Suggestions:
- Consider adding __str__ override for better error messages
- Could add from_dict() for deserialization (optional)

Approved to implement with optional suggestions."

Claude: "Thanks! Implementing now with __str__ override.
Will add from_dict() if time permits."
```

### Example 2: Implementation Review with Changes

```
Claude: "Implemented ModelValidator in llm/model_validator.py

Key features:
- Fetches models from LM Studio API
- 60-second TTL cache
- Validates model existence
- Returns clear errors with available models

@Magistral: Ready for implementation review?"

Magistral: "IMPLEMENTATION REVIEW

Status: CHANGES REQUESTED ⚠️

Findings:
✅ Core logic is sound
✅ Caching implementation good
✅ Error messages are clear

Required Changes:
1. Line 45: _fetch_models() has no timeout on httpx.AsyncClient
   - Add timeout=10.0 parameter

2. Line 67: validate_model() doesn't handle None model
   - Should return True for None (means default)

3. Missing retry logic on API failures
   - Apply @retry_with_backoff decorator

4. Line 89: Cache TTL hardcoded
   - Should use config.router.cache_ttl_seconds

Please fix these 4 issues before approval."

Claude: "Fixed all 4 issues:

1. Added timeout=10.0 to AsyncClient
2. Added None check at start of validate_model()
3. Applied @retry_with_backoff(max_retries=3)
4. Changed to use config.router.cache_ttl_seconds

Changes in llm/model_validator.py lines 42-50, 65-68

@Magistral: Ready for re-review?"

Magistral: "REVIEW VERIFIED

Status: APPROVED ✅

All 4 issues resolved correctly. Code is production-ready.
Great work on the quick turnaround!"
```

### Example 3: Phase Completion Review

```
Claude: "Phase 1 (Validation Layer) complete!

Deliverables:
✅ llm/exceptions.py (6 exception classes)
✅ utils/error_handling.py (retry, fallback decorators)
✅ llm/model_validator.py (validator with caching)
✅ tests/test_exceptions.py (8 tests, all pass)
✅ tests/test_error_handling.py (9 tests, all pass)
✅ tests/test_model_validator.py (7 tests, all pass)

Test Results:
- 24 tests total
- 24 passed
- 0 failed
- 94% coverage

@All: Ready for Phase 1 completion review?"

Qwen3-Coder: "CODE REVIEW ✅
Exception hierarchy is solid, error handling utils are well-designed.
All code quality criteria met."

Qwen3-Thinking: "LOGIC REVIEW ✅
All edge cases covered, logical flow is sound.
Task breakdown complete."

Magistral: "ARCHITECTURE REVIEW ✅
Foundation is strong, design patterns appropriate.
Validation layer ready for use in Phase 2."

All LLMs: "PHASE 1 APPROVED ✅
Ready to proceed to Phase 2 (Core Interface Updates)"

Claude: "Excellent! Moving to Phase 2..."
```

---

## Success Metrics

### Review Effectiveness
- **Issue detection rate**: % of issues found before testing
- **Rework rate**: % of code that needed changes
- **Approval time**: Average time to approval

### Implementation Quality
- **Test coverage**: % of code covered
- **Bug density**: Bugs per 100 lines
- **Documentation completeness**: % of components documented

### Process Efficiency
- **Time per phase**: Actual vs estimated
- **Review overhead**: % of time in reviews
- **First-time approval rate**: % approved without changes

---

## Continuous Improvement

### After Each Phase
- Review what went well
- Identify improvement opportunities
- Adjust process if needed

### After Implementation
- Retrospective with all team members
- Document lessons learned
- Update framework for future projects

---

## Appendix: Quick Reference

### Review Type Cheat Sheet

| Type | When | Who | Duration | Outcome |
|------|------|-----|----------|---------|
| Design | Before coding | 1 LLM | 10-20min | Approve/Revise design |
| Implementation | After coding | 1 LLM | 15-30min | Approve/Request changes |
| Phase Completion | After phase | All 3 | 20-30min | Phase sign-off |
| Integration | After integration | 1-2 LLMs | 15-25min | Integration approval |
| Final Release | Before release | All 3 | 30-45min | Release sign-off |

### Reviewer Specializations

| Reviewer | Best For | Review Focus |
|----------|----------|--------------|
| Qwen3-Coder | Code implementation | Patterns, quality, performance |
| Qwen3-Thinking | Logic & process | Flow, completeness, edge cases |
| Magistral | Architecture | Design, patterns, strategy |

### Communication Templates

All templates available in this document, search for:
- "REVIEW REQUEST"
- "REVIEW RESPONSE"
- "Changes completed"
- "APPROVED ✅"

---

**Framework Version**: 1.0
**Created**: October 30, 2025
**Authors**: Claude Code + Qwen3-Coder + Qwen3-Thinking + Magistral
**Status**: Active
**Applies To**: Option A and Option C implementations
