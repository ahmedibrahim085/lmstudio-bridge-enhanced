# Delegation Guidelines: When to Use Local LLM vs Claude

## Overview

This document provides clear guidelines for deciding when to delegate tasks to your local LLM (via LM Studio) versus using Claude directly. The goal is to maximize efficiency, minimize costs, and leverage the strengths of each system.

## Quick Decision Matrix

| Task Type | Use Local LLM | Use Claude | Reason |
|-----------|--------------|------------|--------|
| **File Operations** | ✅ Yes | ❌ No | Local LLM has autonomous filesystem access |
| **Code Reviews** | ✅ Yes | ⚠️ For final sign-off | Local LLM can analyze code, Claude for critical decisions |
| **Documentation** | ✅ Yes | ❌ No | Local LLM can read/write/summarize docs autonomously |
| **Test Generation** | ✅ Yes | ❌ No | Local LLM can read code and create tests |
| **Architecture Decisions** | ❌ No | ✅ Yes | Claude excels at complex reasoning and trade-offs |
| **User Interaction** | ❌ No | ✅ Yes | Claude maintains conversation context and user preferences |
| **Multi-MCP Orchestration** | ❌ No | ✅ Yes | Claude can coordinate multiple MCP servers |
| **Complex Reasoning** | ⚠️ Simple tasks | ✅ Yes | Claude has superior reasoning for complex problems |

## Detailed Guidelines

### 1. Always Use Local LLM For:

#### A. File System Operations
**Examples:**
- Reading multiple files and creating summaries
- Searching for specific code patterns across files
- Generating reports from codebase analysis
- Creating or updating documentation files
- Organizing project structure

**Why:**
- FREE (no token costs)
- Has autonomous access to all 14 filesystem MCP tools
- Can work in parallel with Claude
- Fast local execution
- No API rate limits

**How to Delegate:**
```
Use the autonomous_filesystem_full tool to:
- "Read all Python files and create a summary document"
- "Search for TODO comments and list them in a file"
- "Analyze test coverage by reading test files"
```

#### B. Code Reviews and Analysis
**Examples:**
- Reviewing refactored code
- Analyzing code quality and patterns
- Identifying potential bugs or issues
- Checking code style and conventions
- Comparing implementations

**Why:**
- Can autonomously read all relevant files
- Provides objective analysis without token costs
- Fast iteration on multiple files
- Can create detailed review documents

**Success Example:**
- Local LLM successfully reviewed entire refactoring work
- Read 2 files autonomously (REFACTOR_COMPLETE.md + autonomous.py)
- Provided detailed feedback (8/10 rating with specific recommendations)
- Cost: $0.00

**How to Delegate:**
```
Use autonomous_filesystem_full to:
- "Review the code in tools/autonomous.py and provide feedback"
- "Analyze all files in src/ for code quality issues"
- "Compare old and new implementations and document differences"
```

#### C. Documentation Tasks
**Examples:**
- Writing README files
- Generating API documentation
- Creating code examples
- Summarizing changes
- Updating changelogs

**Why:**
- Can read source code autonomously
- Can write documentation files directly
- No token cost for lengthy documentation
- Can iterate quickly

**Token Efficiency Example:**
- Claude explaining refactoring: 4,200 tokens consumed
- Local LLM doing same task: 0 tokens (FREE)
- **Savings: 4,200 tokens per task**

**How to Delegate:**
```
Use autonomous_filesystem_full to:
- "Read all Python files and create API documentation in docs/API.md"
- "Update README.md with usage examples from the code"
- "Create a CHANGELOG.md from git commit history"
```

#### D. Test Generation
**Examples:**
- Creating unit tests
- Generating test data
- Writing integration test scenarios
- Creating test fixtures

**Why:**
- Can read implementation code
- Can create test files
- FREE execution
- Quick iterations

**How to Delegate:**
```
Use autonomous_filesystem_full to:
- "Read tools/autonomous.py and create comprehensive unit tests"
- "Generate test cases for all functions in llm/llm_client.py"
- "Create integration tests for MCP connection workflow"
```

#### E. Data Processing and Analysis
**Examples:**
- Parsing log files
- Analyzing metrics
- Processing CSV/JSON data
- Generating reports

**Why:**
- Can read multiple data files
- Can write processed results
- No token costs for large datasets
- Fast local processing

### 2. Always Use Claude For:

#### A. Complex Architecture Decisions
**Examples:**
- Choosing between design patterns
- Planning system architecture
- Evaluating trade-offs
- Making technology choices

**Why:**
- Superior reasoning for complex problems
- Considers multiple dimensions (performance, maintainability, scalability)
- Can explain trade-offs clearly
- Has broader knowledge of ecosystem

#### B. User Interaction and Conversation
**Examples:**
- Understanding user intent
- Asking clarifying questions
- Maintaining conversation context
- Adapting to user preferences

**Why:**
- Designed for natural conversation
- Understands context and nuance
- Can remember user preferences
- Better at ambiguity resolution

#### C. Multi-MCP Orchestration
**Examples:**
- Coordinating filesystem + github + memory MCPs
- Complex workflows across multiple tools
- Error recovery across systems

**Why:**
- Can manage multiple MCP connections
- Better error handling across systems
- Can make real-time decisions about tool usage

#### D. Critical Security and Quality Decisions
**Examples:**
- Final security audits
- Production deployment decisions
- Critical code review sign-offs
- Risk assessments

**Why:**
- Higher accuracy for critical decisions
- Can consider broader implications
- Better at identifying edge cases

### 3. Hybrid Approach (Use Both):

#### A. Research and Documentation Workflow
1. **Claude**: Plans research approach, identifies what needs to be found
2. **Local LLM**: Reads all relevant files, gathers information autonomously
3. **Local LLM**: Creates initial documentation draft
4. **Claude**: Reviews and refines for clarity and completeness

#### B. Feature Development Workflow
1. **Claude**: Designs feature architecture, makes key decisions
2. **Local LLM**: Reads existing codebase, identifies integration points
3. **Claude**: Writes critical core logic
4. **Local LLM**: Generates boilerplate, tests, documentation
5. **Local LLM**: Runs code review
6. **Claude**: Final quality check and user communication

#### C. Debugging Workflow
1. **Local LLM**: Searches codebase for error patterns
2. **Local LLM**: Gathers relevant code sections
3. **Claude**: Analyzes root cause
4. **Local LLM**: Generates test cases
5. **Claude**: Implements fix
6. **Local LLM**: Verifies fix across codebase

## Cost and Performance Considerations

### Token Efficiency

**Cost Comparison (Example: Documentation Task)**
- **Claude alone**: 4,200 tokens × $0.003/1K = $0.0126
- **Claude + Local LLM delegation**: 500 tokens × $0.003/1K = $0.0015
- **Savings**: 88% cost reduction

**Scaled Impact (100 documentation tasks)**
- **Claude alone**: $1.26
- **With delegation**: $0.15
- **Total savings**: $1.11

### Performance Considerations

**Local LLM Advantages:**
- No network latency
- No rate limits
- Parallel execution
- Free inference
- Privacy (data never leaves your machine)

**Claude Advantages:**
- Superior reasoning quality
- Better at complex tasks
- Maintains conversation state
- Integrated with Claude Code ecosystem

## Best Practices

### 1. Start with Local LLM, Escalate if Needed
```
❌ Bad: Ask Claude to read 10 files and summarize
✅ Good: Ask local LLM to read and summarize, Claude reviews summary
```

### 2. Use Local LLM for Iteration, Claude for Validation
```
❌ Bad: Have Claude generate 5 variations of documentation
✅ Good: Local LLM generates variations, Claude picks best one
```

### 3. Delegate File Operations Whenever Possible
```
❌ Bad: Claude reads file, explains content to user
✅ Good: Local LLM reads file, Claude discusses implications with user
```

### 4. Use Appropriate max_rounds for Task Complexity

**Simple Tasks** (max_rounds=10):
- Single file operations
- Simple searches
- Quick summaries

**Medium Tasks** (max_rounds=100, default):
- Multi-file analysis
- Documentation generation
- Code reviews

**Complex Tasks** (max_rounds=500+):
- Full codebase analysis
- Comprehensive refactoring reviews
- Large-scale documentation projects

**Very Complex Tasks** (max_rounds=1000+):
- Cross-repository analysis
- Architectural documentation
- Complete test suite generation

### 5. Configure Token Limits Based on Output Needs

**Short Outputs** (max_tokens=1024):
- Simple summaries
- File listings
- Quick searches

**Standard Outputs** (max_tokens=4096, default):
- Code reviews
- Documentation
- Test generation

**Long Outputs** (max_tokens=8192+):
- Comprehensive reports
- Full architectural documentation
- Detailed analysis documents

## Configuration Examples

### Example 1: Simple File Search
```python
autonomous_filesystem_full(
    task="Find all Python files containing 'async def'",
    max_rounds=10,
    max_tokens=1024
)
```

### Example 2: Code Review (Default Settings)
```python
autonomous_filesystem_full(
    task="Review all files in tools/ for code quality and provide feedback"
)
# Uses defaults: max_rounds=100, max_tokens=4096
```

### Example 3: Comprehensive Documentation
```python
autonomous_filesystem_full(
    task="Read entire codebase, analyze architecture, create comprehensive docs/ARCHITECTURE.md",
    max_rounds=500,
    max_tokens=8192
)
```

### Example 4: Cross-Project Analysis
```python
autonomous_filesystem_full(
    task="Compare implementations across all Python projects, document patterns",
    max_rounds=1000,
    max_tokens=8192
)
```

## Warning Signs You're Using the Wrong Tool

### Signs You Should Delegate to Local LLM:
- ⚠️ Claude is consuming 2,000+ tokens just reading files
- ⚠️ You're asking Claude to "read X and summarize" repeatedly
- ⚠️ Task involves reading/writing multiple files
- ⚠️ You need to iterate on documentation or tests
- ⚠️ Task is straightforward but time-consuming

### Signs You Should Use Claude:
- ⚠️ Local LLM is hitting max_rounds limit repeatedly
- ⚠️ Task requires understanding user intent or preferences
- ⚠️ Decision has security or architectural implications
- ⚠️ Multiple MCPs need to be coordinated
- ⚠️ Complex reasoning about trade-offs needed

## Measuring Success

### Key Metrics

**Token Efficiency:**
- Track Claude tokens used per session
- Compare before/after delegation
- Target: 70%+ reduction in routine tasks

**Task Completion Rate:**
- Monitor local LLM success rate
- Track which tasks need Claude intervention
- Optimize max_rounds based on patterns

**Time Efficiency:**
- Measure parallel execution gains
- Track end-to-end workflow time
- Compare sequential vs parallel approaches

### Success Criteria

✅ **Good Delegation Strategy:**
- 70%+ of file operations handled by local LLM
- Claude tokens primarily used for user interaction and complex decisions
- Tasks complete within configured max_rounds
- No truncated outputs due to token limits

❌ **Poor Delegation Strategy:**
- Claude reading/writing files directly
- Hitting max_rounds limits frequently
- Truncated outputs due to low max_tokens
- High token costs for routine tasks

## Real-World Examples

### Example 1: Refactoring Review (Successful)
**Task:** Review entire refactoring work (500+ lines of code)

**Approach:**
1. Claude: Identified review scope
2. Local LLM: Autonomously read REFACTOR_COMPLETE.md and autonomous.py
3. Local LLM: Analyzed code quality, rated 8/10, provided feedback
4. Claude: Discussed feedback with user, planned next steps

**Results:**
- Time: 2 minutes
- Claude tokens: ~500 (just planning and discussion)
- Local LLM cost: $0.00
- Quality: Comprehensive, actionable feedback

**Without Delegation:**
- Claude tokens: ~4,200 (reading files + analysis)
- Cost: 8.4x higher
- Time: Similar
- Quality: Similar

### Example 2: Documentation Generation (Hypothetical)
**Task:** Create comprehensive API documentation

**With Delegation:**
1. Claude: Plans documentation structure (100 tokens)
2. Local LLM: Reads all source files autonomously (max_rounds=200)
3. Local LLM: Generates docs/API.md (max_tokens=8192)
4. Claude: Reviews and approves (200 tokens)
- **Total Claude tokens: 300**
- **Cost: $0.0009**

**Without Delegation:**
1. Claude reads all files (2,000 tokens)
2. Claude generates documentation (3,000 tokens)
- **Total Claude tokens: 5,000**
- **Cost: $0.015**
- **Difference: 16.7x more expensive**

## Conclusion

The key to effective delegation is understanding the strengths of each system:

**Local LLM = Autonomous Worker**
- Handles file operations, analysis, documentation
- Works for free, in parallel, without limits
- Ideal for repetitive, well-defined tasks

**Claude = Strategic Thinker**
- Makes complex decisions, guides architecture
- Interacts with users, maintains context
- Ideal for ambiguous, high-stakes tasks

**Golden Rule:** If it involves reading/writing files or repetitive work, delegate to local LLM. If it requires judgment, creativity, or user interaction, use Claude.

---

**Document Version:** 1.0
**Last Updated:** October 30, 2025
**Related Documents:**
- README.md
- REFACTOR_COMPLETE.md
- tools/autonomous.py (implementation details)
