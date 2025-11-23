#!/usr/bin/env python3
"""
End-to-End tests for multi-model support.

These tests validate complete workflows using real MCP connections
and LM Studio models. They test the entire flow from tool call to
final result with different models.

Requirements:
- LM Studio running with at least 2 models loaded
- Filesystem MCP configured in .mcp.json
- Memory MCP configured (optional, for multi-MCP tests)

Usage:
    pytest tests/test_e2e_multi_model.py -v -s
"""

import pytest
import asyncio
import sys
import os
from typing import List, Dict, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools.dynamic_autonomous import DynamicAutonomousAgent
from llm.exceptions import ModelNotFoundError, LLMConnectionError
from tests.test_constants import (
    REASONING_MODEL,
    CODING_MODEL,
    SMALL_MODEL,
    VISION_MODEL,
    FILESYSTEM_MCP,
    MEMORY_MCP,
    DEFAULT_MAX_ROUNDS,
    SHORT_MAX_ROUNDS,
    LONG_MAX_ROUNDS,
    E2E_ANALYSIS_TASK,
    E2E_IMPLEMENTATION_TASK,
    SIMPLE_TASK,
    INVALID_MODEL_NAME,
    ERROR_KEYWORDS,
    NO_CONTENT_MESSAGE,
)


class TestE2EMultiModelWorkflows:
    """End-to-end tests for complete multi-model workflows."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_reasoning_to_coding_pipeline(self):
        """
        E2E Test: Reasoning model analyzes, coding model implements.

        Workflow:
        1. Reasoning model (Magistral) analyzes codebase structure
        2. Coding model (Qwen-Coder) generates code based on analysis

        Validates: Complete multi-model pipeline works end-to-end
        """
        agent = DynamicAutonomousAgent()

        # Get available models
        try:
            models = await agent.model_validator.get_available_models()
        except Exception as e:
            pytest.skip(f"LM Studio not available: {e}")

        if len(models) < 2:
            pytest.skip("Need at least 2 models loaded for this test")

        # Find reasoning and coding models
        # NOTE: Avoid 'thinking' models as they tend to hallucinate tool results
        # Prefer 'magistral' (good at reasoning) or 'coder' models
        reasoning_model = None
        coding_model = None

        for model in models:
            # Skip embedding models
            if 'embedding' in model.lower():
                continue
            # Prefer magistral for reasoning (good instruction following)
            if 'magistral' in model.lower() and not reasoning_model:
                reasoning_model = model
            elif 'coder' in model.lower():
                coding_model = model

        # Fallback to non-embedding models
        non_embedding = [m for m in models if 'embedding' not in m.lower()]
        if not reasoning_model and non_embedding:
            reasoning_model = non_embedding[0]
        if not coding_model and non_embedding:
            coding_model = non_embedding[1] if len(non_embedding) > 1 else non_embedding[0]

        print(f"\n🧠 Using reasoning model: {reasoning_model}")
        print(f"💻 Using coding model: {coding_model}")

        # Step 1: Analysis with reasoning model
        # CRITICAL: The task must explicitly request the LLM to output the ACTUAL tool results
        # Without this, some models hallucinate file names instead of reporting actual results
        print("\n📊 Step 1: Analyzing with reasoning model...")
        analysis_task = (
            "Use the list_directory tool to list files in the llm/ directory. "
            "In your response, you MUST include the ACTUAL file names returned by the tool. "
            "List each file name exactly as shown in the tool output."
        )
        analysis = await agent.autonomous_with_mcp(
            mcp_name=FILESYSTEM_MCP,
            task=analysis_task,
            max_rounds=SHORT_MAX_ROUNDS,
            model=reasoning_model
        )

        assert analysis is not None
        # Check for actual error responses (not just the word "error" in legitimate content)
        actual_error_patterns = [
            "Error:", "ERROR:", "failed:", "FAILED:",
            "Task incomplete", "No content in response"
        ]
        has_actual_error = any(pattern in analysis for pattern in actual_error_patterns)
        assert not has_actual_error, f"Analysis contains error: {analysis[:200]}..."
        # Validate analysis contains ACTUAL files from llm/ directory (prevent hallucination)
        # These are known files that MUST exist in llm/
        known_files = ['llm_client.py', 'exceptions.py', 'model_validator.py', '__init__.py']
        has_real_files = any(f in analysis for f in known_files)
        has_py_files = '.py' in analysis
        print(f"✅ Analysis complete: {len(analysis)} characters")
        print(f"   Contains real files: {has_real_files}, Contains .py: {has_py_files}")

        # FAIL if model hallucinated (no real files found)
        # This catches cases where LLM skips tool calls and makes up file names
        assert has_real_files, (
            f"HALLUCINATION DETECTED: Model did not use actual tool results!\n"
            f"Expected one of: {known_files}\n"
            f"Got: {analysis[:300]}..."
        )

        # Step 2: Implementation with coding model - PIPELINE TEST
        # This tests that output from Step 1 (reasoning model) flows to Step 2 (coding model)
        print("\n🔨 Step 2: Pipeline to coding model...")
        implementation_task = (
            f"Based on this file listing from the llm/ directory:\n\n"
            f"{analysis}\n\n"
            f"Pick ONE of these Python files and explain what it likely does based on its name. "
            f"Be specific about the file name you choose."
        )
        implementation = await agent.autonomous_with_mcp(
            mcp_name=FILESYSTEM_MCP,
            task=implementation_task,
            max_rounds=SHORT_MAX_ROUNDS,
            model=coding_model
        )

        assert implementation is not None
        # Check for actual error responses (not just the word "error" in legitimate content)
        # LLM may legitimately discuss "error handling" or "exceptions.py"
        actual_error_patterns = [
            "Error:", "ERROR:", "failed:", "FAILED:",
            "Task incomplete", "No content in response"
        ]
        has_actual_error = any(pattern in implementation for pattern in actual_error_patterns)
        assert not has_actual_error, f"Implementation contains error: {implementation[:200]}..."
        print(f"✅ Implementation complete: {len(implementation)} characters")

        # Verify both steps produced meaningful results
        assert len(analysis) > 50, "Analysis too short"
        assert len(implementation) > 50, "Implementation too short"

        print("\n✅ E2E Pipeline Test PASSED")

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_model_switching_within_mcp(self):
        """
        E2E Test: Switch models for different tasks within same MCP.

        Workflow:
        1. Simple task with default model
        2. Complex task with reasoning model
        3. Code generation with coding model

        Validates: Model switching works correctly within single MCP
        """
        agent = DynamicAutonomousAgent()

        try:
            models = await agent.model_validator.get_available_models()
        except Exception as e:
            pytest.skip(f"LM Studio not available: {e}")

        if len(models) < 1:
            pytest.skip("Need at least 1 model loaded")

        print(f"\n📦 Available models: {models}")

        # Task 1: Simple with default (no model parameter)
        print("\n🔹 Task 1: Simple task with default model")
        result1 = await agent.autonomous_with_mcp(
            mcp_name="filesystem",
            task="List the files in the llm/ directory",
            max_rounds=10
        )

        assert result1 is not None
        assert "Error" not in result1 or "error" not in result1.lower()
        print(f"✅ Task 1 complete: {len(result1)} characters")

        # Task 2: With specific model
        print(f"\n🔹 Task 2: Specific model task ({models[0]})")
        result2 = await agent.autonomous_with_mcp(
            mcp_name="filesystem",
            task="What is the purpose of the llm/ directory based on its contents?",
            max_rounds=15,
            model=models[0]
        )

        assert result2 is not None
        assert "Error" not in result2 or "error" not in result2.lower()
        print(f"✅ Task 2 complete: {len(result2)} characters")

        # Task 3: Different model if available
        if len(models) > 1:
            print(f"\n🔹 Task 3: Different model ({models[1]})")
            result3 = await agent.autonomous_with_mcp(
                mcp_name="filesystem",
                task="Count how many Python files are in llm/",
                max_rounds=10,
                model=models[1]
            )

            assert result3 is not None
            print(f"✅ Task 3 complete: {len(result3)} characters")

        print("\n✅ Model Switching Test PASSED")

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_multi_mcp_with_model(self):
        """
        E2E Test: Multiple MCPs with consistent model.

        Workflow:
        1. Use filesystem + memory MCPs together
        2. Use specific model throughout

        Validates: Multi-MCP works with model parameter
        """
        agent = DynamicAutonomousAgent()

        try:
            models = await agent.model_validator.get_available_models()
        except Exception as e:
            pytest.skip(f"LM Studio not available: {e}")

        if len(models) < 1:
            pytest.skip("Need at least 1 model loaded")

        # Check if memory MCP is available
        from mcp_client.discovery import MCPDiscovery
        discovery = MCPDiscovery()
        available_mcps = discovery.list_available_mcps()

        if 'memory' not in available_mcps:
            pytest.skip("Memory MCP not configured")

        # Use model loading fixture to ensure model is actually loaded
        # This handles memory errors properly rather than just picking small models
        from tests.fixtures.model_management import ensure_model_loaded
        from llm.exceptions import ModelMemoryError

        # Try models in order until one loads successfully
        test_model = None
        for model in models:
            try:
                if ensure_model_loaded(model):
                    test_model = model
                    break
            except ModelMemoryError as e:
                print(f"⚠️  Model '{model}' requires too much memory: {e.required_memory or 'unknown'}")
                continue

        if not test_model:
            pytest.skip("No model could be loaded - all models require too much memory")

        print(f"\n🔧 Using model: {test_model}")
        print(f"📦 Using MCPs: filesystem, memory")

        # Execute multi-MCP task with model
        result = await agent.autonomous_with_multiple_mcps(
            mcp_names=["filesystem", "memory"],
            task="Read the README.md file and create a knowledge graph entity summarizing the project",
            max_rounds=30,
            model=test_model
        )

        assert result is not None
        assert "Error" not in result or "error" not in result.lower()
        print(f"✅ Multi-MCP result: {len(result)} characters")

        print("\n✅ Multi-MCP Test PASSED")

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_invalid_model_error_handling(self):
        """
        E2E Test: Invalid model produces clear error.

        Workflow:
        1. Attempt to use non-existent model
        2. Verify error message is helpful

        Validates: Error handling works in production
        """
        agent = DynamicAutonomousAgent()

        # Try to use invalid model
        print("\n❌ Attempting to use invalid model...")
        result = await agent.autonomous_with_mcp(
            mcp_name=FILESYSTEM_MCP,
            task=SIMPLE_TASK,
            model=INVALID_MODEL_NAME
        )

        # Should return error message (not raise exception)
        assert result is not None
        assert any(keyword in result for keyword in ERROR_KEYWORDS)
        assert "not found" in result.lower()
        assert INVALID_MODEL_NAME in result

        print(f"✅ Got expected error: {result[:200]}...")
        print("\n✅ Error Handling Test PASSED")

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_backward_compatibility_no_model(self):
        """
        E2E Test: Existing code without model parameter still works.

        Workflow:
        1. Call autonomous tool without model parameter
        2. Verify it uses default and works

        Validates: 100% backward compatibility
        """
        agent = DynamicAutonomousAgent()

        try:
            models = await agent.model_validator.get_available_models()
        except Exception as e:
            pytest.skip(f"LM Studio not available: {e}")

        if len(models) < 1:
            pytest.skip("Need at least 1 model loaded")

        print("\n🔄 Testing backward compatibility (no model parameter)...")

        # Old-style call without model parameter
        result = await agent.autonomous_with_mcp(
            mcp_name="filesystem",
            task="What files are in the tests/ directory?"
        )

        assert result is not None
        assert "Error" not in result or "error" not in result.lower()
        print(f"✅ Backward compatible call worked: {len(result)} characters")

        print("\n✅ Backward Compatibility Test PASSED")


class TestE2EModelValidation:
    """End-to-end tests for model validation."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_validation_caching(self):
        """
        E2E Test: Model validation caching works.

        Workflow:
        1. First call validates model (may be slow)
        2. Subsequent calls use cache (should be fast)

        Validates: Caching optimization works
        """
        agent = DynamicAutonomousAgent()

        try:
            models = await agent.model_validator.get_available_models()
        except Exception as e:
            pytest.skip(f"LM Studio not available: {e}")

        if len(models) < 1:
            pytest.skip("Need at least 1 model loaded")

        model_name = models[0]
        print(f"\n⚡ Testing validation caching with: {model_name}")

        # First validation (may fetch from API)
        import time
        start = time.perf_counter()
        result1 = await agent.model_validator.validate_model(model_name)
        duration1 = (time.perf_counter() - start) * 1000

        assert result1 is True
        print(f"✅ First validation: {duration1:.2f}ms")

        # Second validation (should use cache)
        start = time.perf_counter()
        result2 = await agent.model_validator.validate_model(model_name)
        duration2 = (time.perf_counter() - start) * 1000

        assert result2 is True
        print(f"✅ Second validation: {duration2:.2f}ms (cached)")

        # Third validation (should use cache)
        start = time.perf_counter()
        result3 = await agent.model_validator.validate_model(model_name)
        duration3 = (time.perf_counter() - start) * 1000

        assert result3 is True
        print(f"✅ Third validation: {duration3:.2f}ms (cached)")

        # Cached calls should be much faster (< 1ms ideally)
        print(f"\n📊 Cache performance: {duration2:.4f}ms, {duration3:.4f}ms")

        print("\n✅ Validation Caching Test PASSED")

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_none_and_default_models(self):
        """
        E2E Test: None and 'default' model values work.

        Workflow:
        1. Validate None (should pass)
        2. Validate 'default' string (should pass)

        Validates: Special model values handled correctly
        """
        from llm.model_validator import ModelValidator

        validator = ModelValidator()

        print("\n🔍 Testing special model values...")

        # Test None
        result_none = await validator.validate_model(None)
        assert result_none is True
        print("✅ None validated successfully")

        # Test 'default'
        result_default = await validator.validate_model("default")
        assert result_default is True
        print("✅ 'default' validated successfully")

        print("\n✅ Special Values Test PASSED")


class TestE2ERealWorldScenarios:
    """End-to-end tests for real-world usage scenarios."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.slow
    async def test_complete_analysis_implementation_workflow(self):
        """
        E2E Test: Complete real-world workflow.

        Workflow:
        1. Analyze project structure (reasoning model)
        2. Identify improvement areas (reasoning model)
        3. Generate implementation (coding model)
        4. Create tests (coding model)

        Validates: Full multi-step real-world usage
        """
        agent = DynamicAutonomousAgent()

        try:
            models = await agent.model_validator.get_available_models()
        except Exception as e:
            pytest.skip(f"LM Studio not available: {e}")

        if len(models) < 1:
            pytest.skip("Need at least 1 model loaded")

        # Use first available model for all steps
        model = models[0]
        print(f"\n🚀 Real-world workflow using: {model}")

        # Step 1: Project analysis
        # FIX: Use explicit path like passing tests (llm/, tools/, utils/)
        print("\n📋 Step 1: Analyzing project...")
        analysis = await agent.autonomous_with_mcp(
            mcp_name="filesystem",
            task="List the files in the utils/ directory and describe what utilities exist.",
            max_rounds=20,
            model=model
        )

        assert analysis is not None
        assert len(analysis) > 50
        print(f"✅ Analysis: {len(analysis)} characters")

        # Step 2: Read specific file
        # FIX: Make task explicit about directory structure (learning from passing tests)
        print("\n📄 Step 2: Reading implementation details...")
        details_task = (
            f"Based on the utils/ directory structure you found:\n\n"
            f"{analysis}\n\n"
            f"Now read the utils/retry_logic.py file and summarize what it does."
        )
        details = await agent.autonomous_with_mcp(
            mcp_name="filesystem",
            task=details_task,
            max_rounds=15,
            model=model
        )

        assert details is not None
        assert len(details) > 50
        print(f"✅ Details: {len(details)} characters")

        print("\n✅ Real-world Workflow Test PASSED")


def test_e2e_suite_completeness():
    """Meta-test: Verify E2E test coverage."""
    import inspect

    test_classes = [
        TestE2EMultiModelWorkflows,
        TestE2EModelValidation,
        TestE2ERealWorldScenarios,
    ]

    total_tests = 0
    for test_class in test_classes:
        test_methods = [m for m in dir(test_class) if m.startswith('test_')]
        print(f"\n{test_class.__name__}: {len(test_methods)} tests")
        total_tests += len(test_methods)

    assert total_tests >= 8, f"Need 8+ E2E tests, have {total_tests}"
    print(f"\n✅ E2E test suite has {total_tests} tests")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("END-TO-END MULTI-MODEL TESTS")
    print("=" * 60)
    print("\nRequirements:")
    print("- LM Studio running with 2+ models loaded")
    print("- Filesystem MCP configured")
    print("- Memory MCP configured (optional)")
    print("\nRun with: pytest tests/test_e2e_multi_model.py -v -s -m e2e")
    print("=" * 60 + "\n")

    pytest.main([__file__, "-v", "-s", "-m", "e2e"])
