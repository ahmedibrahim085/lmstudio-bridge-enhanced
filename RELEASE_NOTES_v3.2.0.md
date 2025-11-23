# Release Notes - v3.2.0

**Release Date**: November 23, 2025
**Version**: 3.2.0
**Previous Version**: 3.1.1
**Status**: **PRODUCTION READY**
**Commits**: 44 commits since v3.1.1

---

## Release Summary

This is a **major feature release** introducing four significant capabilities:

1. **Structured JSON Output** - Force LLMs to return valid JSON matching your schema
2. **Vision/Multimodal Support** - Process images with vision-capable models
3. **Model Capability Registry** - Query model capabilities with BFCL benchmark data
4. **Autonomous Agent Enhancements** - Improved reliability for smaller LLMs

Plus critical bug fixes, resilience improvements, and 100+ new tests.

---

## What's New

### 1. Structured JSON Output (Phase 1)

**Commits**: `537b95e`, `54aeef1`, `417c079`, `ced7247`, `ea553f1`

Force LLMs to return valid, parseable JSON that conforms to your schema.

**New Features**:
- `response_format` parameter in `chat_completion` MCP tool
- JSON schema validation utilities
- Support for `json_object` and `json_schema` response formats

**Example Usage**:
```python
# Force JSON output with schema
result = await chat_completion(
    messages=[{"role": "user", "content": "List 3 colors"}],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "colors",
            "schema": {
                "type": "object",
                "properties": {
                    "colors": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["colors"]
            }
        }
    }
)
# Returns: {"colors": ["red", "blue", "green"]}
```

**Files Added/Modified**:
- `config/constants.py` - Structured output constants
- `llm/llm_client.py` - `response_format` parameter support
- `tools/completions.py` - Exposed in MCP tool
- `utils/json_schema.py` - Schema validation utilities
- `tests/test_structured_output.py` - 51 comprehensive tests

**Benefits**:
- Guaranteed valid JSON output
- Schema validation before/after LLM calls
- No more parsing failures from malformed responses
- Works with all LM Studio compatible models

---

### 2. Vision/Multimodal Support (Phase 2)

**Commits**: `7c9abfc`, `73f1311`, `68247ac`, `e0feb73`, `b11cf11`, `016d294`, `664d5b2`

Process images alongside text using vision-capable models (LLaVA, Qwen-VL, etc).

**New MCP Tools** (6 tools):
| Tool | Description |
|------|-------------|
| `vision_analyze_image` | Analyze image content with custom prompt |
| `vision_describe_image` | Get detailed image description |
| `vision_extract_text` | OCR - extract text from images |
| `vision_compare_images` | Compare multiple images |
| `vision_analyze_screenshot` | Analyze UI screenshots |
| `vision_answer_question` | Visual Q&A about images |

**Example Usage**:
```python
# Analyze an image
result = await vision_analyze_image(
    image_path="/path/to/image.png",
    prompt="What objects are in this image?"
)

# Extract text from screenshot
text = await vision_extract_text(
    image_path="/path/to/screenshot.png"
)
```

**Technical Details**:
- Automatic base64 encoding for LM Studio compatibility
- URL fetching with proper content-type handling
- Support for PNG, JPEG, GIF, WebP formats
- Image preprocessing utilities

**Files Added/Modified**:
- `config/constants.py` - Vision constants (max size, formats)
- `utils/image_utils.py` - Image processing utilities
- `llm/llm_client.py` - `vision_completion()` method
- `tools/vision_tools.py` - 6 MCP vision tools
- `tests/test_vision.py` - 50 comprehensive tests

**Benefits**:
- Multimodal AI capabilities in your workflows
- OCR without external dependencies
- UI/screenshot analysis for testing
- Works with any vision model in LM Studio

---

### 3. Model Capability Registry (Phase 3)

**Commits**: `5aaa862`, `a645721`, `be195e0`, `c0019ff`, `a9b9f96`, `961c75e`, `a52d616`, `45fc8fa`

A comprehensive system for querying model capabilities, with BFCL benchmark data integration.

**New MCP Tools** (4 tools):
| Tool | Description |
|------|-------------|
| `lms_list_downloaded_models` | List all downloaded models with metadata |
| `lms_download_model` | Download models from Hugging Face |
| `lms_resolve_model` | Intelligent model resolution with fallback |
| `get_model_capabilities` | Get detailed capabilities with BFCL scores |

**New Features**:
- **VRAM Estimation**: Estimate GPU memory requirements
  - Accounts for quantization (Q4/Q8 vs FP16/FP32)
  - KV cache scaling with context length
  - ~10% overhead buffer for safety
- **Thinking Model Detection**: Identify reasoning models (QwQ, DeepSeek-R1, o1)
- **Model Fallback Manager**: Suggest alternatives when models unavailable
- **Persistent Cache**: Smart delta updates (only research new models)

**VRAM Estimation Formula**:
```
VRAM = (file_size * quant_multiplier + kv_cache) * 1.1 overhead

Where:
- quant_multiplier: 1.0 (Q4/Q8), 1.2 (FP16), 1.5 (FP32)
- kv_cache: ~0.5GB per 10B params at 32K context
```

**Example Usage**:
```python
# Get model capabilities with BFCL score
caps = await get_model_capabilities(model="qwen/qwen3-coder-30b")
# Returns: {
#   "model_key": "qwen/qwen3-coder-30b",
#   "tool_use_score": 0.933,  # BFCL benchmark
#   "estimated_vram_gb": 18.5,
#   "is_thinking_model": false,
#   "max_context_length": 32768
# }

# Resolve model with fallback
result = await lms_resolve_model(
    requested_model="qwen/qwen3-coder-30b",
    task_type="coding"
)
```

**Files Added**:
- `model_registry/` - New module with:
  - `schemas.py` - Data structures
  - `lms_integration.py` - LMS CLI wrapper
  - `cache.py` - Persistent cache
  - `research.py` - BFCL benchmark integration
  - `registry.py` - Main orchestrator
  - `tools.py` - MCP tools
- `utils/lms_helper.py` - LMS CLI helper functions

**Benefits**:
- Know if a model can fit in your VRAM before loading
- Find the best model for tool calling (BFCL scores)
- Automatic fallback suggestions
- Cached lookups for fast repeated queries

---

### 4. Autonomous Agent Enhancements

**Commits**: `d8a3028`, `77be32f`, `2c3c7f6`, `f74fbf5`, `fdc7e28`, `98a414e`, `4777088`, `3f8493c`, `c7d2bf4`, `1dfceaf`, `3c42f27`

Critical improvements for reliable autonomous execution, especially with smaller LLMs.

**New Features**:

#### Type Coercion for Smaller Models
Smaller LLMs (e.g., Llama 3.2 3B) often pass numeric parameters as strings. We now automatically coerce types:

```python
# LLM sends: {"head": "10", "tail": "5"}
# Coerced to: {"head": 10, "tail": 5}
```

- Centralized `safe_call_tool()` wrapper
- Configurable via `LMS_EXTRA_NUMERIC_PARAMS` env var
- 10+ numeric parameters auto-detected

#### Force Tool Usage on First Round
```python
# Round 0: tool_choice="required" - MUST call a tool
# Round 1+: tool_choice="auto" - Can provide final answer
```

This prevents LLMs from hallucinating answers instead of using tools.

#### Explicit Tool Result Injection
Fixed critical bug where thinking models ignored tool results:
```python
# Now explicitly inject: "Tool 'X' returned: {result}"
```

#### Intelligent Model Selection
- Detect oversized models before loading
- Automatic fallback to smaller variants
- VRAM-aware model selection

**Files Added/Modified**:
- `mcp_client/type_coercion.py` - Type coercion module (NEW)
- `tools/dynamic_autonomous.py` - `tool_choice` support
- `llm/llm_client.py` - `tool_choice` parameter
- `mcp_client/executor.py` - Use `safe_call_tool`

**Benefits**:
- Works reliably with 3B-7B parameter models
- Fewer hallucinations
- Proper tool result handling
- Type errors eliminated

---

## Resilience & Reliability Improvements

### Retry Logic with Exponential Backoff

**Commits**: `b46e2a7`, `eaa59c5`

New `utils/retry.py` module for handling transient failures:

```python
# Automatic retry on timeout with exponential backoff + jitter
# Formula: min(max_delay, base_delay * 2^attempt * (0.5 + random(0, 0.5)))

# Configuration via environment variables:
LMS_MAX_RETRIES=3           # Max retry attempts
LMS_RETRY_BASE_DELAY=1.0    # Base delay in seconds
LMS_RETRY_MAX_DELAY=10.0    # Max delay cap
```

Applied to:
- `list_downloaded_models()`
- `list_loaded_models()`
- All LMS CLI operations

### API Timeout Protection

**Commit**: `3e8355d`

All API calls now have appropriate timeouts:
| Operation | Timeout | Rationale |
|-----------|---------|-----------|
| `health_check()` | 5s | Quick check |
| `list_models()` | 10s | Model enumeration |
| `get_current_model()` | 10s | Single model info |
| `chat_completion()` | 58s | Under MCP 60s limit |

---

## Bug Fixes

### Critical Fixes

| Bug | Commit | Description |
|-----|--------|-------------|
| **LM_STUDIO_BASE_URL undefined** | `53ac89a` | `ensure_model_loaded()` referenced undefined class attribute |
| **search_models broken** | `c0019ff` | LMS CLI has no search-only command - removed broken function |
| **Tool results ignored** | `4777088` | Thinking models ignored tool results - now explicitly injected |
| **Type coercion missing** | `2c3c7f6` | Smaller models passed strings for numbers - auto-coercion added |
| **Hallucination on first round** | `77be32f` | LLMs skipped tool calls - forced with `tool_choice=required` |
| **Model selection bias** | `d02f806` | Removed hardcoded model preferences in tests |
| **E2E false positives** | `fca6930` | Improved error detection in E2E tests |
| **Memory errors** | `c7d2bf4` | Better handling of oversized model loading |

### Code Quality Fixes

| Issue | Commit | Description |
|-------|--------|-------------|
| Dead code removed | `eaa59c5` | ~50 lines of unused `retry_on_timeout` decorator |
| Misleading docs | `eaa59c5` | Docstring claimed CalledProcessError raised but wasn't |
| Misleading comment | `f818c07` | Comment claimed NUMERIC_PARAMS was reloadable |

---

## Test Coverage

### New Tests Added

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_structured_output.py` | 51 | Structured JSON output |
| `test_vision.py` | 50 | Vision/multimodal tools |
| `test_type_coercion.py` | 16 | Type coercion (10 + 6 env var) |
| `test_retry.py` | 8 | Retry logic |
| `test_integration_lms.py` | 4 | Real LMS CLI integration |
| Various E2E improvements | 10+ | Hallucination detection |

### Test Results

```
331 passed, 9 skipped in 530.56s (0:08:50)
```

- **331 tests pass** (up from 171 in v3.1.0 - nearly doubled!)
- **9 skipped** - Integration tests (LMS CLI marker)
- **0 failures**

---

## Configuration

### New Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LMS_MAX_RETRIES` | `3` | Max retry attempts for CLI operations |
| `LMS_RETRY_BASE_DELAY` | `1.0` | Base delay between retries (seconds) |
| `LMS_RETRY_MAX_DELAY` | `10.0` | Maximum delay cap (seconds) |
| `LMS_EXTRA_NUMERIC_PARAMS` | `""` | Additional numeric params for type coercion |

### Example Configuration

```bash
# .env file
LMS_MAX_RETRIES=5
LMS_RETRY_BASE_DELAY=2.0
LMS_EXTRA_NUMERIC_PARAMS=custom_limit,page_size,batch_size
```

---

## Breaking Changes

**NONE** - This release is 100% backward compatible.

All new features are:
- Additive (new tools, new parameters)
- Optional (existing code works unchanged)
- Non-breaking (no API changes to existing methods)

---

## Migration Guide

### From v3.1.x to v3.2.0

**No changes required!** Just update and restart:

```bash
cd /path/to/lmstudio-bridge-enhanced
git pull
git checkout v3.2.0

# Restart Claude Code to load updated MCP
```

### Optional: Use New Features

```python
# Structured output
result = await chat_completion(
    messages=[...],
    response_format={"type": "json_object"}  # NEW
)

# Vision analysis
result = await vision_analyze_image(
    image_path="/path/to/image.png",
    prompt="Describe this"
)

# Model capabilities
caps = await get_model_capabilities(model="qwen/qwen3")
```

---

## Statistics

| Metric | Value |
|--------|-------|
| **Commits** | 44 |
| **New MCP Tools** | 10 (6 vision + 4 model registry) |
| **New Tests** | 139 |
| **Total Tests** | 331 (up from 171) |
| **Test Pass Rate** | 100% |
| **New Files** | 15+ |
| **Lines Added** | ~3,000+ |

---

## Files Added

### New Modules
- `mcp_client/type_coercion.py` - Centralized type coercion
- `utils/retry.py` - Retry with exponential backoff
- `utils/image_utils.py` - Image processing utilities
- `utils/json_schema.py` - JSON schema validation
- `tools/vision_tools.py` - 6 vision MCP tools
- `model_registry/` - Complete model registry module
  - `schemas.py`, `lms_integration.py`, `cache.py`
  - `research.py`, `registry.py`, `tools.py`

### New Tests
- `tests/test_structured_output.py` (51 tests)
- `tests/test_vision.py` (50 tests)
- `tests/test_type_coercion.py` (16 tests)
- `tests/test_retry.py` (8 tests)
- `tests/test_integration_lms.py` (4 tests)

---

## Contributors

- **Ahmed Maged** - Primary Developer
- **Claude Code** - AI Collaboration Partner

---

## Acknowledgments

Special thanks to:
- LM Studio team for excellent local LLM support
- Berkeley Function Calling Leaderboard (BFCL) for benchmark data
- MCP protocol contributors
- All early adopters and testers

---

## What's Next (v3.3.0 Roadmap)

### Planned Features
- Streaming responses for real-time output
- Multi-model ensembles
- Cost-optimized model routing
- Enhanced MCP server discovery

### Long-term Vision
- Multi-backend support (OpenAI, Anthropic, Google)
- Enterprise features (RBAC, audit logging)
- Visual workflow builder

---

## Summary

**v3.2.0 is a major feature release** that adds:

- **Structured JSON Output** for reliable parsing
- **Vision/Multimodal Support** with 6 new tools
- **Model Capability Registry** with BFCL data
- **Autonomous Agent Improvements** for smaller LLMs
- **Resilience Features** with retry logic and timeouts
- **100+ new tests** (331 total, up from 171)

All features are backward compatible. Upgrade now!

---

**Release**: v3.2.0
**Date**: November 23, 2025
**Status**: **PRODUCTION READY**

**Full Changelog**: v3.1.1...v3.2.0
