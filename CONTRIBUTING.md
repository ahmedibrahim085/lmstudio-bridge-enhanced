# Contributing to LM Studio Bridge Enhanced

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Documentation](#documentation)
- [Community](#community)

---

## Code of Conduct

### Our Standards

- **Be respectful**: Treat everyone with respect and kindness
- **Be inclusive**: Welcome contributors from all backgrounds
- **Be constructive**: Focus on solutions, not problems
- **Be collaborative**: Work together towards common goals

### Unacceptable Behavior

- Harassment, discrimination, or offensive comments
- Personal attacks or trolling
- Public or private harassment
- Publishing others' private information

---

## Getting Started

### Prerequisites

- **Python 3.9+**
- **Node.js 16+** (for MCP servers)
- **LM Studio v0.3.29+**
- **Git**

### Initial Setup

1. **Fork the repository** on GitHub

2. **Clone your fork**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/lmstudio-bridge-enhanced.git
   cd lmstudio-bridge-enhanced
   ```

3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/ORIGINAL_OWNER/lmstudio-bridge-enhanced.git
   ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Verify setup**:
   ```bash
   python3 test_lmstudio_integration.py
   ```

---

## Development Setup

### Environment Configuration

Create a test configuration:

```json
// ~/.lmstudio/mcp.json
{
  "mcpServers": {
    "lmstudio-bridge-dev": {
      "command": "python3",
      "args": ["/path/to/your/fork/lmstudio_bridge.py"],
      "env": {
        "LMSTUDIO_HOST": "localhost",
        "LMSTUDIO_PORT": "1234",
        "MCP_JSON_PATH": "/path/to/test/.mcp.json"
      }
    }
  }
}
```

### IDE Setup

**Recommended**: VS Code with:
- Python extension
- Pylance
- Black formatter
- Ruff linter

**Settings**:
```json
{
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "editor.formatOnSave": true
}
```

---

## Project Structure

```
lmstudio-bridge-enhanced/
├── lmstudio_bridge.py          # Main entry point
├── main.py                     # FastMCP server setup
├── config.py                   # Configuration
├── requirements.txt            # Dependencies
│
├── llm/                        # LLM client
│   ├── __init__.py
│   └── llm_client.py           # LM Studio API client
│
├── mcp_client/                 # MCP client functionality
│   ├── __init__.py
│   └── discovery.py            # Dynamic MCP discovery
│
├── tools/                      # Tool implementations
│   ├── __init__.py
│   ├── completions.py          # Core LM Studio tools
│   ├── dynamic_autonomous.py   # Dynamic autonomous agent
│   └── dynamic_autonomous_register.py  # Tool registration
│
├── tests/                      # Test files
│   ├── test_lmstudio_integration.py
│   ├── test_dynamic_discovery.py
│   ├── test_autonomous_tools.py
│   └── benchmark_hot_reload.py
│
└── docs/                       # Documentation
    ├── QUICKSTART.md
    ├── ARCHITECTURE.md
    ├── API_REFERENCE.md
    ├── TROUBLESHOOTING.md
    └── archive/
        └── DEVELOPMENT_NOTES.md
```

---

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# OR
git checkout -b fix/issue-number-description
```

**Branch naming**:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Test additions/changes

### 2. Make Changes

- Write clean, readable code
- Follow coding standards (see below)
- Add tests for new functionality
- Update documentation

### 3. Test Your Changes

```bash
# Run all tests
python3 test_lmstudio_integration.py
python3 test_dynamic_discovery.py
python3 test_autonomous_tools.py

# Run performance benchmarks
python3 benchmark_hot_reload.py
```

### 4. Commit Changes

```bash
git add .
git commit -m "feat: add new autonomous tool for X

- Implement X functionality
- Add tests for X
- Update documentation
"
```

**Commit message format**:
```
<type>: <subject>

<body>

<footer>
```

**Types**:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation only
- `refactor:` - Code refactoring
- `test:` - Adding tests
- `chore:` - Maintenance tasks

### 5. Push to Your Fork

```bash
git push origin feature/your-feature-name
```

### 6. Create Pull Request

- Go to GitHub
- Click "New Pull Request"
- Select your branch
- Fill in PR template
- Submit!

---

## Testing

### Running Tests

```bash
# Individual tests
python3 test_lmstudio_integration.py
python3 test_dynamic_discovery.py
python3 test_autonomous_tools.py

# With verbose output
python3 test_autonomous_tools.py -v
```

### Writing Tests

Place tests in `tests/` directory:

```python
# tests/test_your_feature.py
import asyncio
from tools.dynamic_autonomous import DynamicAutonomousAgent

async def test_your_feature():
    """Test your new feature."""
    agent = DynamicAutonomousAgent()

    result = await agent.your_method()

    assert "expected" in result
    print("✅ Test passed!")

if __name__ == "__main__":
    asyncio.run(test_your_feature())
```

### Test Guidelines

- ✅ Test happy path
- ✅ Test error cases
- ✅ Test edge cases
- ✅ Use meaningful assertions
- ✅ Add descriptive docstrings

---

## Pull Request Process

### Before Submitting

1. ✅ Tests pass locally
2. ✅ Code follows style guidelines
3. ✅ Documentation updated
4. ✅ Commit messages follow format
5. ✅ Branch is up to date with main

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring
- [ ] Other (describe)

## Testing
- [ ] Tests pass locally
- [ ] Added new tests (if applicable)
- [ ] Manual testing performed

## Documentation
- [ ] Documentation updated
- [ ] Examples added/updated
- [ ] CHANGELOG.md updated

## Related Issues
Closes #123
```

### Review Process

1. Automated checks run
2. Maintainers review code
3. Address review comments
4. Approval required before merge
5. Squash and merge to main

---

## Coding Standards

### Python Style

Follow **PEP 8** with these specifics:

```python
# Imports: standard library, third-party, local
import os
import sys

from fastmcp import FastMCP
from pydantic import Field

from llm.llm_client import LLMClient
from mcp_client.discovery import MCPDiscovery

# Class naming: PascalCase
class DynamicAutonomousAgent:
    """Agent for autonomous execution with dynamic MCPs."""

    def __init__(self, llm_client=None):
        """Initialize agent."""
        self.llm = llm_client or LLMClient()

    async def execute_task(self, task: str) -> str:
        """
        Execute task autonomously.

        Args:
            task: Task description

        Returns:
            Final answer from LLM
        """
        # Implementation
        return result

# Function naming: snake_case
async def register_tools(mcp, llm_client):
    """Register tools with FastMCP server."""
    # Implementation

# Constants: UPPER_CASE
DEFAULT_MAX_ROUNDS = 10000
DEFAULT_MAX_TOKENS = 8192
```

### Documentation Strings

```python
def function_name(param1: str, param2: int = 0) -> str:
    """
    Brief one-line description.

    Longer description if needed. Explain what the function does,
    not how it does it.

    Args:
        param1: Description of param1
        param2: Description of param2 (default: 0)

    Returns:
        Description of return value

    Raises:
        ValueError: When param1 is invalid

    Examples:
        >>> function_name("test", 5)
        "result"
    """
```

### Type Hints

Always use type hints:

```python
from typing import List, Dict, Optional, Union

async def connect_to_mcp(
    mcp_name: str,
    config: Dict[str, any]
) -> Optional[ClientSession]:
    """Connect to MCP server."""
    ...

def process_tools(
    tools: List[str],
    namespace: Optional[str] = None
) -> Dict[str, any]:
    """Process tool definitions."""
    ...
```

### Error Handling

```python
try:
    result = await operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    return f"Error: {str(e)}"
except Exception as e:
    logger.exception("Unexpected error")
    raise
```

---

## Documentation

### When to Update Docs

- Adding new features → Update API_REFERENCE.md
- Changing behavior → Update relevant docs
- Fixing bugs → Add to TROUBLESHOOTING.md if user-facing
- Architecture changes → Update ARCHITECTURE.md

### Documentation Style

- Use clear, concise language
- Include code examples
- Add screenshots when helpful
- Link related sections
- Keep examples up-to-date

---

## Community

### Getting Help

- **GitHub Discussions**: Ask questions, share ideas
- **GitHub Issues**: Report bugs, request features
- **Discord** (if available): Real-time chat

### Reporting Bugs

Use the bug report template:

```markdown
**Describe the bug**
Clear description of the issue

**To Reproduce**
Steps to reproduce:
1. Step 1
2. Step 2
3. See error

**Expected behavior**
What you expected to happen

**Environment**
- OS: [e.g., macOS 14]
- Python version: [e.g., 3.11]
- LM Studio version: [e.g., 0.3.29]

**Additional context**
Any other relevant information
```

### Feature Requests

Use the feature request template:

```markdown
**Is your feature request related to a problem?**
Description of the problem

**Describe the solution you'd like**
Clear description of desired functionality

**Describe alternatives you've considered**
Other approaches you've thought about

**Additional context**
Any other relevant information
```

---

## Development Tips

### Hot Reload During Development

1. Edit code
2. Save file
3. Test immediately (no restart needed after initial setup!)

### Debugging

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Add breakpoints
import pdb; pdb.set_trace()
```

### Performance Testing

```bash
# Benchmark hot reload
python3 benchmark_hot_reload.py

# Profile code
python3 -m cProfile -s cumtime your_script.py
```

---

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Credited in release notes
- Mentioned in project README

### Development Collaboration

This project was developed through a unique AI-powered workflow:

**Lead Developer**: Ahmed Maged

**AI Collaborators**:
- **Claude (Anthropic)** - Primary development assistant, architecture design, and documentation
- **Qwen3-Coder 30B** - Code generation, implementation support, and technical problem-solving
- **Qwen3-Think** - Deep analysis, architectural decisions, and strategic planning

This collaborative approach demonstrates the power of human-AI teamwork in modern software development, combining:
- Human vision and project leadership
- Claude's comprehensive documentation and best practices guidance
- Qwen3-Coder's efficient code generation and implementation
- Qwen3-Think's analytical depth for complex technical decisions

All AI contributions were guided, reviewed, and validated by the human developer to ensure quality, security, and alignment with project goals.

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

## Questions?

- Open a **GitHub Discussion** for questions
- Create an **issue** for bugs/features
- Reach out to maintainers for urgent matters

**Thank you for contributing!** 🎉
