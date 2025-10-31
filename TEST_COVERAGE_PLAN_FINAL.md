# Final Test Coverage Plan - Integration APIs

**Created**: 2025-10-31
**Based On**: Actual code analysis from TEST_PLAN_CONTEXT.md
**Goal**: Achieve comprehensive test coverage for all 5 LLM API integrations

---

## Executive Summary

**Modules to Test**: 4 (completions, embeddings, health, autonomous)
**Total Tests Needed**: 41-50 tests
**APIs Covered**: All 5 (chat_completion, text_completion, create_response, generate_embeddings, list_models + health_check)
**Estimated Effort**: 20-25 hours
**Priority**: High - These are production-critical modules with zero test coverage

---

## Test File 1: tests/test_completions.py

**Module**: tools/completions.py
**Class**: CompletionTools
**APIs Used**: chat_completion, text_completion, create_response (3 APIs)
**Priority**: Medium (multiple APIs, moderate complexity)
**Estimated Tests**: 11-14
**Estimated Effort**: 6-8 hours

### Tests for `chat_completion()` method:

#### test_chat_completion_success
- Mock: `tools.llm.chat_completion`
- Return: `{"choices": [{"message": {"content": "Response text"}}]}`
- Call: `chat_completion(prompt="Hello", system_prompt="Be helpful")`
- Assert: Returns "Response text"

#### test_chat_completion_no_system_prompt
- Mock: `tools.llm.chat_completion`
- Return: Valid response
- Call: `chat_completion(prompt="Hello", system_prompt="")`
- Assert: Only user message in messages array

#### test_chat_completion_empty_choices
- Mock: `tools.llm.chat_completion`
- Return: `{"choices": []}`
- Call: `chat_completion(prompt="Hello")`
- Assert: Returns "Error: No response generated"

#### test_chat_completion_empty_content
- Mock: `tools.llm.chat_completion`
- Return: `{"choices": [{"message": {"content": ""}}]}`
- Call: `chat_completion(prompt="Hello")`
- Assert: Returns "Error: Empty response from model"

#### test_chat_completion_exception
- Mock: `tools.llm.chat_completion`
- Raise: Exception("API Error")
- Call: `chat_completion(prompt="Hello")`
- Assert: Returns "Error generating completion: API Error"

### Tests for `text_completion()` method:

#### test_text_completion_success
- Mock: `tools.llm.text_completion`
- Return: `{"choices": [{"text": "Completed text"}]}`
- Call: `text_completion(prompt="Once upon a time")`
- Assert: Returns "Completed text"

#### test_text_completion_with_stop_sequences
- Mock: `tools.llm.text_completion`
- Return: Valid response
- Call: `text_completion(prompt="Hello", stop_sequences=["\n", "."])`
- Assert: stop_sequences passed to API

#### test_text_completion_empty_choices
- Mock: `tools.llm.text_completion`
- Return: `{"choices": []}`
- Call: `text_completion(prompt="Hello")`
- Assert: Returns "Error: No completion generated"

#### test_text_completion_empty_text
- Mock: `tools.llm.text_completion`
- Return: `{"choices": [{"text": ""}]}`
- Call: `text_completion(prompt="Hello")`
- Assert: Returns "Error: Empty completion from model"

#### test_text_completion_exception
- Mock: `tools.llm.text_completion`
- Raise: Exception("Timeout")
- Call: `text_completion(prompt="Hello")`
- Assert: Returns "Error generating text completion: Timeout"

### Tests for `create_response()` method:

#### test_create_response_success
- Mock: `tools.llm.create_response`
- Return: `{"id": "resp_123", "output": [...]}`
- Call: `create_response(input_text="Hello")`
- Assert: Returns valid JSON string with response

#### test_create_response_with_previous_id
- Mock: `tools.llm.create_response`
- Return: Valid response
- Call: `create_response(input_text="Continue", previous_response_id="resp_123")`
- Assert: previous_response_id passed to API

#### test_create_response_with_model
- Mock: `tools.llm.create_response`
- Return: Valid response
- Call: `create_response(input_text="Hello", model="custom-model")`
- Assert: model parameter passed to API

#### test_create_response_exception
- Mock: `tools.llm.create_response`
- Raise: Exception("Connection failed")
- Call: `create_response(input_text="Hello")`
- Assert: Returns JSON with error message

---

## Test File 2: tests/test_embeddings.py

**Module**: tools/embeddings.py
**Class**: EmbeddingsTools
**APIs Used**: generate_embeddings (1 API)
**Priority**: High (simple, quick win)
**Estimated Tests**: 5-6
**Estimated Effort**: 3-4 hours

### Tests for `generate_embeddings()` method:

#### test_generate_embeddings_single_string
- Mock: `tools.llm.generate_embeddings`
- Return: `{"data": [{"embedding": [0.1, 0.2, 0.3]}]}`
- Call: `generate_embeddings(text="Hello world")`
- Assert: Returns valid JSON with embeddings

#### test_generate_embeddings_list_of_strings
- Mock: `tools.llm.generate_embeddings`
- Return: `{"data": [{"embedding": [...]}, {"embedding": [...]}]}`
- Call: `generate_embeddings(text=["Hello", "World"])`
- Assert: Returns JSON with multiple embeddings

#### test_generate_embeddings_default_model
- Mock: `tools.llm.generate_embeddings`
- Return: Valid response
- Call: `generate_embeddings(text="Hello", model="default")`
- Assert: model=None passed to API (line 42 logic)

#### test_generate_embeddings_custom_model
- Mock: `tools.llm.generate_embeddings`
- Return: Valid response
- Call: `generate_embeddings(text="Hello", model="custom-embeddings")`
- Assert: model="custom-embeddings" passed to API

#### test_generate_embeddings_exception
- Mock: `tools.llm.generate_embeddings`
- Raise: Exception("Model not found")
- Call: `generate_embeddings(text="Hello")`
- Assert: Returns JSON with error message

#### test_generate_embeddings_empty_text
- Mock: No mock needed
- Call: `generate_embeddings(text="")`
- Assert: Handles empty input gracefully

---

## Test File 3: tests/test_health.py

**Module**: tools/health.py
**Class**: HealthTools
**APIs Used**: health_check, list_models, chat_completion (3 methods, 3 APIs)
**Priority**: High (simple, quick win)
**Estimated Tests**: 10
**Estimated Effort**: 4-5 hours

### Tests for `health_check()` method:

#### test_health_check_api_running
- Mock: `tools.llm.health_check`
- Return: True
- Call: `health_check()`
- Assert: Returns "LM Studio API is running and accessible."

#### test_health_check_api_not_responding
- Mock: `tools.llm.health_check`
- Return: False
- Call: `health_check()`
- Assert: Returns "LM Studio API is not responding."

#### test_health_check_exception
- Mock: `tools.llm.health_check`
- Raise: Exception("Connection refused")
- Call: `health_check()`
- Assert: Returns "Error connecting to LM Studio API: Connection refused"

### Tests for `list_models()` method:

#### test_list_models_success
- Mock: `tools.llm.list_models`
- Return: ["model1", "model2", "model3"]
- Call: `list_models()`
- Assert: Returns formatted string with all models

#### test_list_models_empty
- Mock: `tools.llm.list_models`
- Return: []
- Call: `list_models()`
- Assert: Returns "No models found in LM Studio."

#### test_list_models_formatting
- Mock: `tools.llm.list_models`
- Return: ["qwen/qwen3-coder-30b"]
- Call: `list_models()`
- Assert: Contains "Available models" header and "- qwen/qwen3-coder-30b"

#### test_list_models_exception
- Mock: `tools.llm.list_models`
- Raise: Exception("API timeout")
- Call: `list_models()`
- Assert: Returns "Error listing models: API timeout"

### Tests for `get_current_model()` method:

#### test_get_current_model_success
- Mock: `tools.llm.chat_completion`
- Return: `{"model": "qwen/qwen3-coder-30b", "choices": [...]}`
- Call: `get_current_model()`
- Assert: Returns "Currently loaded model: qwen/qwen3-coder-30b"

#### test_get_current_model_unknown
- Mock: `tools.llm.chat_completion`
- Return: `{"choices": [...]}`  # No "model" key
- Call: `get_current_model()`
- Assert: Returns "Currently loaded model: Unknown"

#### test_get_current_model_exception
- Mock: `tools.llm.chat_completion`
- Raise: Exception("Not connected")
- Call: `get_current_model()`
- Assert: Returns "Error identifying current model: Not connected"

---

## Test File 4: tests/test_autonomous_simple.py

**Module**: tools/autonomous.py
**Class**: AutonomousExecutionTools
**APIs Used**: create_response, chat_completion (2 APIs)
**Priority**: Complex (requires careful design)
**Estimated Tests**: 15-20
**Estimated Effort**: 8-10 hours

**Note**: This module is COMPLEX. Recommend starting with simpler tests first.

### Phase 1: Basic Method Tests (5-8 tests)

#### test_init_with_default_client
- Mock: None
- Call: `AutonomousExecutionTools()`
- Assert: Creates default LLMClient

#### test_init_with_custom_client
- Mock: None
- Setup: Create mock LLMClient
- Call: `AutonomousExecutionTools(llm_client=mock_client)`
- Assert: Uses provided client

#### test_execute_autonomous_stateful_success
- Mock: `tools.llm.create_response`
- Return: Final answer response
- Call: Internal method (if exposed for testing)
- Assert: Returns final answer

### Phase 2: Autonomous Function Tests (10-12 tests)

Focus on testing the MCP tool functions:
- `autonomous_filesystem_full`
- `autonomous_persistent_session`
- Other registered MCP tools

**Strategy**: Mock MCP connections, focus on API call patterns

#### test_autonomous_filesystem_full_basic
- Mock: MCP connection, create_response
- Call: `autonomous_filesystem_full(task="List files")`
- Assert: Completes without error

**Additional tests needed for**:
- Error handling at each stage
- Max rounds reached
- MCP connection failures
- Directory validation
- Model preloading logic

**Recommendation**: Create this test file LAST after learning patterns from simpler modules.

---

## Implementation Strategy

### Phase 1: Quick Wins (Week 1)
**Goal**: Get 26-30 tests passing
1. `tests/test_health.py` (10 tests, 4-5 hours)
   - Simple methods, straightforward mocking
   - Builds confidence
2. `tests/test_embeddings.py` (5-6 tests, 3-4 hours)
   - Single method, clear API usage
   - Good learning opportunity

### Phase 2: Multiple APIs (Week 2)
**Goal**: Add 11-14 tests
3. `tests/test_completions.py` (11-14 tests, 6-8 hours)
   - 3 methods, 3 different APIs
   - Moderate complexity
   - Reuse patterns from Phase 1

### Phase 3: Complex Module (Week 3)
**Goal**: Add 15-20 tests
4. `tests/test_autonomous_simple.py` (15-20 tests, 8-10 hours)
   - Start with basic tests
   - Add complexity gradually
   - May need multiple iterations

---

## Mock Patterns to Reuse

### From test_multi_model_integration.py:

```python
# Pattern 1: Mock LLM client method
agent.llm = MagicMock()
agent.llm.create_response.return_value = {
    "id": "resp_test_123",
    "output": [
        {
            "type": "message",
            "content": [
                {"type": "output_text", "text": "Task complete"}
            ]
        }
    ]
}

# Pattern 2: Mock chat_completion
agent.llm.chat_completion.return_value = {
    "choices": [
        {
            "message": {
                "content": "Response text"
            }
        }
    ]
}

# Pattern 3: Mock MCP connection
with patch('tools.module.stdio_client') as mock_stdio:
    with patch('tools.module.ClientSession') as mock_session_class:
        mock_session = AsyncMock()
        # Setup session mocks...
```

### Standard Test Class Structure:

```python
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from tools.completions import CompletionTools

class TestCompletionTools:
    @pytest.fixture
    def tools(self):
        """Create CompletionTools instance with mocked LLM client."""
        mock_client = MagicMock()
        return CompletionTools(llm_client=mock_client)

    @pytest.mark.asyncio
    async def test_method_name(self, tools):
        """Test description."""
        # Setup
        tools.llm.api_method.return_value = {...}

        # Execute
        result = await tools.method(...)

        # Assert
        assert result == expected
        tools.llm.api_method.assert_called_once_with(...)
```

---

## Success Criteria

### Minimum Viable Coverage:
- ✅ All public methods have happy path tests
- ✅ All error handling paths tested
- ✅ All 5 APIs have test coverage
- ✅ Edge cases covered (empty inputs, None values)

### Target Coverage:
- 🎯 80%+ code coverage across all 4 modules
- 🎯 All API mocking patterns documented
- 🎯 Integration with existing test suite
- 🎯 CI/CD pipeline integration

### Stretch Goals:
- 🚀 90%+ code coverage
- 🚀 Performance benchmarks for autonomous functions
- 🚀 E2E tests with real LM Studio instance

---

## Risk Mitigation

### Risk 1: Complex MCP Mocking
**Mitigation**: Start with simpler modules, learn patterns, apply to complex modules

### Risk 2: Autonomous Module Complexity
**Mitigation**: Phase 3 approach, start with basic tests, add complexity gradually

### Risk 3: API Response Format Changes
**Mitigation**: Use fixtures for common responses, easy to update in one place

### Risk 4: Time Estimation
**Mitigation**: 20-25 hours is conservative, may take 25-30 hours with debugging

---

## Next Actions

1. ✅ Review this plan with user
2. ⏳ Create test file structure
3. ⏳ Implement Phase 1 (health + embeddings)
4. ⏳ Review and iterate based on learnings
5. ⏳ Implement Phase 2 (completions)
6. ⏳ Implement Phase 3 (autonomous)
7. ⏳ Achieve 80%+ coverage goal

---

🎯 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
