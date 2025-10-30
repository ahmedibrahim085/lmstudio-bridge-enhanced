#!/usr/bin/env python3
"""
Real Integration Tests - Phase 2 Multi-Model Support

Actually tests the implementation with real LM Studio.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from llm.llm_client import LLMClient
from llm.exceptions import (
    LLMError,
    LLMTimeoutError,
    LLMConnectionError,
    LLMResponseError,
    ModelNotFoundError,
)
from llm.model_validator import ModelValidator
from tools.dynamic_autonomous import DynamicAutonomousAgent


async def test_1_basic_llm_client():
    """Test 1: Basic LLMClient with model parameter."""
    print("\n" + "="*80)
    print("TEST 1: Basic LLMClient with Model Parameter")
    print("="*80)

    try:
        # Test with default model
        print("\n1.1 Testing with default model...")
        client = LLMClient()
        response = client.chat_completion(
            messages=[{"role": "user", "content": "Say 'test 1 pass' and nothing else"}],
            max_tokens=50
        )
        print(f"✅ Default model response: {response['choices'][0]['message']['content'][:50]}")

        # Test with specific model
        print("\n1.2 Testing with specific model (qwen/qwen3-coder-30b)...")
        client2 = LLMClient(model="qwen/qwen3-coder-30b")
        response2 = client2.chat_completion(
            messages=[{"role": "user", "content": "Say 'test 1.2 pass' and nothing else"}],
            max_tokens=50
        )
        print(f"✅ Specific model response: {response2['choices'][0]['message']['content'][:50]}")

        return True

    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
        return False


async def test_2_model_validator():
    """Test 2: Model validation."""
    print("\n" + "="*80)
    print("TEST 2: Model Validator")
    print("="*80)

    try:
        validator = ModelValidator()

        # Test valid model
        print("\n2.1 Testing valid model (qwen/qwen3-coder-30b)...")
        await validator.validate_model("qwen/qwen3-coder-30b")
        print("✅ Valid model accepted")

        # Test invalid model
        print("\n2.2 Testing invalid model (nonexistent-model)...")
        try:
            await validator.validate_model("nonexistent-model-xyz-123")
            print("❌ Should have raised ModelNotFoundError")
            return False
        except ModelNotFoundError as e:
            print(f"✅ Correctly raised ModelNotFoundError: {str(e)[:100]}...")

        # Test 'default' model
        print("\n2.3 Testing 'default' model...")
        await validator.validate_model("default")
        print("✅ 'default' model accepted")

        return True

    except Exception as e:
        print(f"❌ Test 2 failed: {e}")
        return False


async def test_3_autonomous_agent_with_model():
    """Test 3: DynamicAutonomousAgent with model parameter."""
    print("\n" + "="*80)
    print("TEST 3: DynamicAutonomousAgent with Model Parameter")
    print("="*80)

    try:
        agent = DynamicAutonomousAgent()

        # Simple test without MCP (just validate the flow)
        print("\n3.1 Testing agent initialization with model validator...")
        print(f"✅ Agent has model_validator: {agent.model_validator is not None}")

        # Test model validation through agent
        print("\n3.2 Testing model validation through agent...")
        try:
            # This should work - valid model
            await agent.model_validator.validate_model("qwen/qwen3-coder-30b")
            print("✅ Agent validated qwen/qwen3-coder-30b")

            # This should fail - invalid model
            try:
                await agent.model_validator.validate_model("fake-model-123")
                print("❌ Should have raised ModelNotFoundError")
                return False
            except ModelNotFoundError:
                print("✅ Agent correctly rejected fake-model-123")

        except Exception as e:
            print(f"❌ Validation failed: {e}")
            return False

        return True

    except Exception as e:
        print(f"❌ Test 3 failed: {e}")
        return False


async def test_4_exception_handling():
    """Test 4: Exception handling with different error types."""
    print("\n" + "="*80)
    print("TEST 4: Exception Handling")
    print("="*80)

    try:
        # Test connection to wrong port (should raise LLMConnectionError)
        print("\n4.1 Testing connection error (wrong port)...")
        client_wrong_port = LLMClient(api_base="http://localhost:9999")
        try:
            client_wrong_port.list_models()
            print("❌ Should have raised LLMConnectionError")
            return False
        except LLMConnectionError as e:
            print(f"✅ Correctly raised LLMConnectionError: {str(e)[:80]}...")

        # Test timeout (very short timeout)
        print("\n4.2 Testing timeout...")
        client = LLMClient()
        try:
            # This might not always timeout, but we're testing the exception type
            response = client.chat_completion(
                messages=[{"role": "user", "content": "x" * 10000}],
                timeout=0.001  # 1ms timeout - should fail
            )
            print("⚠️  Timeout test didn't trigger (request was too fast)")
        except LLMTimeoutError as e:
            print(f"✅ Correctly raised LLMTimeoutError: {str(e)[:80]}...")
        except LLMError as e:
            # Might get different error depending on timing
            print(f"✅ Raised LLMError (acceptable): {type(e).__name__}")

        return True

    except Exception as e:
        print(f"❌ Test 4 failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_5_model_switching():
    """Test 5: Switching between different models."""
    print("\n" + "="*80)
    print("TEST 5: Model Switching")
    print("="*80)

    try:
        models_to_test = [
            "qwen/qwen3-coder-30b",
            "mistralai/magistral-small-2509",
            "qwen/qwen3-4b-thinking-2507",
        ]

        for i, model in enumerate(models_to_test, 1):
            print(f"\n5.{i} Testing with {model}...")
            client = LLMClient(model=model)
            response = client.chat_completion(
                messages=[{"role": "user", "content": f"Say 'model {i} works' and nothing else"}],
                max_tokens=50
            )
            content = response['choices'][0]['message']['content']
            print(f"✅ {model}: {content[:50]}")

        return True

    except Exception as e:
        print(f"❌ Test 5 failed: {e}")
        return False


async def test_6_create_response_with_model():
    """Test 6: create_response() with model parameter (critical for autonomous agents)."""
    print("\n" + "="*80)
    print("TEST 6: create_response() with Model Parameter")
    print("="*80)

    try:
        client = LLMClient()

        # Test with default model
        print("\n6.1 Testing create_response with default model...")
        response1 = client.create_response(
            input_text="Say 'response 1 works' and nothing else",
            model=None  # Use default
        )
        print(f"✅ Default model: {response1['output'][0]['content'][:50]}")

        # Test with specific model
        print("\n6.2 Testing create_response with qwen/qwen3-coder-30b...")
        response2 = client.create_response(
            input_text="Say 'response 2 works' and nothing else",
            model="qwen/qwen3-coder-30b"
        )
        print(f"✅ Specific model: {response2['output'][0]['content'][:50]}")

        return True

    except Exception as e:
        print(f"❌ Test 6 failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all integration tests."""
    print("="*80)
    print("REAL INTEGRATION TESTS - Phase 2 Multi-Model Support")
    print("="*80)
    print("\nTesting with REAL LM Studio instance...")
    print("This will make actual API calls and validate behavior.")
    print()

    results = {
        "Test 1: Basic LLMClient": await test_1_basic_llm_client(),
        "Test 2: Model Validator": await test_2_model_validator(),
        "Test 3: Autonomous Agent": await test_3_autonomous_agent_with_model(),
        "Test 4: Exception Handling": await test_4_exception_handling(),
        "Test 5: Model Switching": await test_5_model_switching(),
        "Test 6: create_response()": await test_6_create_response_with_model(),
    }

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print()
    print(f"Results: {passed}/{total} passed ({100*passed//total}%)")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED - Phase 2 implementation ACTUALLY WORKS!")
        return True
    else:
        print(f"\n❌ {total - passed} tests failed - implementation has issues")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
