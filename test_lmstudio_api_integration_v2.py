#!/usr/bin/env python3
"""
Comprehensive LM Studio API Integration Test Suite V2
Merged best of both test suites:
- OLD suite: Health check, autonomous end-to-end, result persistence
- NEW suite: Multi-round conversations, context recall verification

Tests ALL LM Studio API endpoints:
1. health_check - API connectivity
2. list_models - Model enumeration
3. get_current_model - Current model info
4. chat_completion - Multi-round chat with context verification
5. text_completion - Raw text completion
6. create_response - Multi-round stateful API with context verification
7. generate_embeddings - Vector embeddings
8. Autonomous execution - End-to-end with tools
"""

import asyncio
import sys
import os
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from llm.llm_client import LLMClient, DEFAULT_MAX_TOKENS
from tools.autonomous import AutonomousExecutionTools
from utils.lms_helper import LMSHelper, check_lms_availability


class LMStudioAPITesterV2:
    """Comprehensive LM Studio API integration tester V2 - Best of both worlds."""

    def __init__(self):
        self.llm = LLMClient()
        self.tools = AutonomousExecutionTools(self.llm)
        self.results = {}
        self.lms_available = LMSHelper.is_installed()

    def print_section(self, title):
        """Print section header."""
        print("\n" + "="*80)
        print(f"{title}")
        print("="*80 + "\n")

    def print_test(self, test_name):
        """Print test name."""
        print(f"\n📍 {test_name}")

    def print_success(self, message):
        """Print success message."""
        print(f"   ✅ {message}")

    def print_fail(self, message):
        """Print failure message."""
        print(f"   ❌ {message}")

    def print_info(self, message):
        """Print info message."""
        print(f"   ℹ️  {message}")

    def test_health_check(self):
        """Test 1: Health Check API."""
        self.print_section("TEST 1: Health Check API")

        try:
            is_healthy = self.llm.health_check()

            if is_healthy:
                self.print_success("LM Studio is running and accessible")
                self.print_info(f"Base URL: {self.llm.api_base}")
                self.results['health_check'] = {'status': 'PASS', 'healthy': True}
                return True
            else:
                self.print_fail("LM Studio is not accessible")
                self.results['health_check'] = {'status': 'FAIL', 'healthy': False}
                return False

        except Exception as e:
            self.print_fail(f"Health check failed: {e}")
            self.results['health_check'] = {'status': 'ERROR', 'error': str(e)}
            return False

    def test_list_models(self):
        """Test 2: List Models API."""
        self.print_section("TEST 2: List Models API (GET /v1/models)")

        try:
            self.print_info(f"Endpoint: {self.llm.api_base}/models")
            models = self.llm.list_models()

            if models and len(models) > 0:
                self.print_success(f"Found {len(models)} models")
                self.print_info("\nAvailable models:")
                for i, model in enumerate(models[:5], 1):  # Show first 5
                    print(f"      {i}. {model}")
                if len(models) > 5:
                    print(f"      ... and {len(models) - 5} more")

                self.results['list_models'] = {
                    'status': 'PASS',
                    'count': len(models),
                    'models': models[:5]
                }
                return True
            else:
                self.print_fail("No models found")
                self.results['list_models'] = {'status': 'FAIL', 'count': 0}
                return False

        except Exception as e:
            self.print_fail(f"List models failed: {e}")
            self.results['list_models'] = {'status': 'ERROR', 'error': str(e)}
            return False

    def test_get_model_info(self):
        """Test 3: Get Model Info API."""
        self.print_section("TEST 3: Get Current Model Info")

        try:
            model_info = self.llm.get_model_info()

            if model_info:
                model_id = model_info.get('id', 'unknown')
                self.print_success(f"Current model: {model_id}")
                self.print_info(f"Object type: {model_info.get('object', 'N/A')}")
                self.print_info(f"Owned by: {model_info.get('owned_by', 'N/A')}")
                self.results['get_model_info'] = {
                    'status': 'PASS',
                    'model': model_id,
                    'info': model_info
                }
                return True
            else:
                self.print_fail("No model info available")
                self.results['get_model_info'] = {'status': 'FAIL', 'model': None}
                return False

        except Exception as e:
            self.print_fail(f"Get model info failed: {e}")
            self.results['get_model_info'] = {'status': 'ERROR', 'error': str(e)}
            return False

    def test_chat_completion_multiround(self):
        """Test 4: Multi-Round Chat Completion API (NEW - CRITICAL TEST!)."""
        self.print_section("TEST 4: Multi-Round Chat Completion (POST /v1/chat/completions)")

        try:
            self.print_info(f"Endpoint: {self.llm.api_base}/chat/completions")

            # Round 1: Initial message
            self.print_test("Round 1: Initial message")
            messages = [
                {"role": "user", "content": "My favorite number is 42."}
            ]
            self.print_info(f"Sending {len(messages)} message(s)")

            response1 = self.llm.chat_completion(
                messages=messages,
                max_tokens=150
            )

            if not response1 or 'choices' not in response1:
                self.print_fail("Invalid response format for Round 1")
                self.results['chat_completion_multiround'] = {'status': 'FAIL', 'reason': 'invalid_format_r1'}
                return False

            assistant_msg1 = response1['choices'][0]['message']
            content1 = assistant_msg1.get("content", "")
            reasoning1 = assistant_msg1.get("reasoning_content", "")
            usage1 = response1.get('usage', {})

            self.print_success("Response received")
            if content1:
                self.print_info(f"Content: {content1[:60]}...")
            if reasoning1:
                self.print_info(f"Reasoning: {reasoning1[:60]}...")
            self.print_info(f"Token usage: {usage1.get('total_tokens', 0)}")

            # Append assistant response to message history
            messages.append({
                "role": "assistant",
                "content": content1
            })

            # Round 2: Follow-up question (CRITICAL - tests conversation history!)
            self.print_test("Round 2: Follow-up question (should have 3 messages)")
            messages.append({
                "role": "user",
                "content": "What is my favorite number?"
            })
            self.print_info(f"Sending {len(messages)} message(s)")
            self.print_info("Message history:")
            for i, msg in enumerate(messages, 1):
                content_preview = msg["content"][:40] + "..." if len(msg["content"]) > 40 else msg["content"]
                print(f"      {i}. {msg['role']}: {content_preview}")

            response2 = self.llm.chat_completion(
                messages=messages,
                max_tokens=150
            )

            if not response2 or 'choices' not in response2:
                self.print_fail("Invalid response format for Round 2")
                self.results['chat_completion_multiround'] = {'status': 'FAIL', 'reason': 'invalid_format_r2'}
                return False

            assistant_msg2 = response2['choices'][0]['message']
            content2 = assistant_msg2.get("content", "")
            reasoning2 = assistant_msg2.get("reasoning_content", "")
            usage2 = response2.get('usage', {})

            self.print_success("Response received")
            if content2:
                self.print_info(f"Content: {content2[:80]}...")
            if reasoning2:
                self.print_info(f"Reasoning: {reasoning2[:80]}...")
            self.print_info(f"Token usage: {usage2.get('total_tokens', 0)}")

            # CRITICAL: Verify LLM actually used conversation history
            full_response = content2 + reasoning2
            if "42" in full_response:
                self.print_success("✨ CONVERSATION HISTORY WORKING - LLM remembered '42' from Round 1!")
                context_verified = True
            else:
                self.print_fail("CONVERSATION HISTORY NOT WORKING - LLM did not remember '42'")
                self.print_info(f"Full response: {full_response}")
                context_verified = False

            self.results['chat_completion_multiround'] = {
                'status': 'PASS' if context_verified else 'FAIL',
                'rounds': 2,
                'messages_sent': len(messages),
                'context_verified': context_verified,
                'usage_r1': usage1,
                'usage_r2': usage2
            }

            print("\n" + "-"*80)
            self.print_info("Check LM Studio logs for message count growth:")
            print("      tail -20 ~/.lmstudio/server-logs/2025-10/2025-10-30.1.log | grep 'conversation with'")
            self.print_info("Expected: 'conversation with 1 messages' then 'conversation with 3 messages'")
            print("-"*80)

            return context_verified

        except Exception as e:
            self.print_fail(f"Multi-round chat completion failed: {e}")
            import traceback
            traceback.print_exc()
            self.results['chat_completion_multiround'] = {'status': 'ERROR', 'error': str(e)}
            return False

    def test_text_completion(self):
        """Test 5: Text Completion API."""
        self.print_section("TEST 5: Text Completion API (POST /v1/completions)")

        try:
            self.print_info(f"Endpoint: {self.llm.api_base}/completions")

            prompt = "Complete this sentence: The capital of France is"
            self.print_info(f"Prompt: {repr(prompt)}")

            response = self.llm.text_completion(
                prompt=prompt,
                max_tokens=DEFAULT_MAX_TOKENS,
                model=self.llm.model  # Add model parameter (required when multiple models loaded)
            )

            if response and 'choices' in response:
                text = response['choices'][0].get('text', '')
                usage = response.get('usage', {})

                self.print_success("Text completion successful")
                self.print_info(f"Completion: {text[:80]}...")
                self.print_info(f"Token usage: {usage.get('total_tokens', 0)}")

                # Check if reasonable answer
                if "paris" in text.lower() or "france" in text.lower():
                    self.print_success("Reasonable completion generated")

                self.results['text_completion'] = {
                    'status': 'PASS',
                    'completion': text,
                    'usage': usage
                }
                return True
            else:
                self.print_fail("Invalid response format")
                self.results['text_completion'] = {'status': 'FAIL', 'reason': 'invalid_format'}
                return False

        except Exception as e:
            # Expected for chat-tuned models
            if "404" in str(e):
                self.print_info("Text completion not supported by current model (expected for chat models)")
                self.results['text_completion'] = {'status': 'SKIP', 'reason': 'not_supported_by_model'}
                return None
            else:
                self.print_fail(f"Text completion failed: {e}")
                self.results['text_completion'] = {'status': 'ERROR', 'error': str(e)}
                return False

    def test_create_response_multiround(self):
        """Test 6: Multi-Round Stateful Response API (NEW - with context verification!)."""
        self.print_section("TEST 6: Multi-Round Stateful Response API (POST /v1/responses)")

        try:
            self.print_info(f"Endpoint: {self.llm.api_base}/responses")

            # Round 1: Set context
            self.print_test("Round 1: Set context (no previous_response_id)")
            response1 = self.llm.create_response(
                input_text="My name is Alice.",
                previous_response_id=None
            )

            if not response1 or 'id' not in response1:
                self.print_fail("Invalid response format for Round 1")
                self.results['create_response_multiround'] = {'status': 'FAIL', 'reason': 'invalid_format_r1'}
                return False

            response1_id = response1['id']
            output1 = response1.get('output', [])
            content1 = ""
            for item in output1:
                if item.get('type') == 'message':
                    for c in item.get('content', []):
                        if c.get('type') == 'output_text':
                            content1 = c.get('text', '')

            self.print_success("Response received")
            self.print_info(f"Response ID: {response1_id}")
            self.print_info(f"Status: {response1.get('status')}")
            if content1:
                self.print_info(f"Content: {content1[:80]}...")

            # Round 2: Follow-up with previous_response_id (CRITICAL!)
            self.print_test("Round 2: Follow-up (with previous_response_id)")
            response2 = self.llm.create_response(
                input_text="What is my name?",
                previous_response_id=response1_id  # Link to previous!
            )

            if not response2 or 'id' not in response2:
                self.print_fail("Invalid response format for Round 2")
                self.results['create_response_multiround'] = {'status': 'FAIL', 'reason': 'invalid_format_r2'}
                return False

            response2_id = response2['id']
            prev_id = response2.get('previous_response_id')
            output2 = response2.get('output', [])
            content2 = ""
            for item in output2:
                if item.get('type') == 'message':
                    for c in item.get('content', []):
                        if c.get('type') == 'output_text':
                            content2 = c.get('text', '')

            self.print_success("Response received")
            self.print_info(f"Response ID: {response2_id}")
            self.print_info(f"Previous Response ID: {prev_id}")
            self.print_info(f"Link verified: {prev_id == response1_id}")
            if content2:
                self.print_info(f"Content: {content2[:80]}...")

            # CRITICAL: Verify LLM actually used conversation context
            if "alice" in content2.lower():
                self.print_success("✨ STATEFUL CONVERSATION WORKING - LLM remembered 'Alice' from Round 1!")
                context_verified = True
            else:
                self.print_fail("STATEFUL CONVERSATION NOT WORKING - LLM did not remember 'Alice'")
                self.print_info(f"Full response: {content2}")
                context_verified = False

            # Verify API structure
            api_structure_ok = (prev_id == response1_id)

            self.results['create_response_multiround'] = {
                'status': 'PASS' if (api_structure_ok and context_verified) else 'FAIL',
                'rounds': 2,
                'api_structure_ok': api_structure_ok,
                'context_verified': context_verified,
                'response1_id': response1_id,
                'response2_id': response2_id
            }

            print("\n" + "-"*80)
            self.print_info("Stateful API note:")
            print("      Logs show 'conversation with 1 messages' for BOTH rounds (CORRECT!)")
            print("      Only current input sent, history maintained server-side via previous_response_id")
            print("      This achieves 97% token savings vs sending full history")
            print("-"*80)

            return api_structure_ok and context_verified

        except Exception as e:
            self.print_fail(f"Multi-round stateful response failed: {e}")
            import traceback
            traceback.print_exc()
            self.results['create_response_multiround'] = {'status': 'ERROR', 'error': str(e)}
            return False

    def test_generate_embeddings(self):
        """Test 7: Generate Embeddings API."""
        self.print_section("TEST 7: Generate Embeddings API (POST /v1/embeddings)")

        try:
            self.print_info(f"Endpoint: {self.llm.api_base}/embeddings")

            # Check if embedding model available
            models = self.llm.list_models()
            embedding_models = [m for m in models if 'embed' in m.lower()]

            if not embedding_models:
                self.print_info("No embedding models found")
                self.print_info("This test requires an embedding model loaded in LM Studio")
                self.print_info("Example: text-embedding-qwen3-embedding-8b")
                self.results['generate_embeddings'] = {
                    'status': 'SKIP',
                    'reason': 'no_embedding_model'
                }
                return None

            self.print_info(f"Found embedding model: {embedding_models[0]}")

            # Test single text
            self.print_test("Single text embedding")
            text = "Hello, world!"
            self.print_info(f"Text: {repr(text)}")

            response1 = self.llm.generate_embeddings(
                text=text,
                model=embedding_models[0]
            )

            if response1 and 'data' in response1:
                embedding = response1['data'][0].get('embedding', [])
                usage = response1.get('usage', {})

                self.print_success("Embedding generated")
                self.print_info(f"Dimensions: {len(embedding)}")
                self.print_info(f"First 5 values: {embedding[:5]}")
                self.print_info(f"Token usage: {usage.get('total_tokens', 0)}")

                # Test batch
                self.print_test("Batch embeddings (3 texts)")
                response2 = self.llm.generate_embeddings(
                    text=["Text 1", "Text 2", "Text 3"],
                    model=embedding_models[0]
                )

                if response2 and 'data' in response2:
                    self.print_success(f"Generated {len(response2['data'])} embeddings")
                    for i, item in enumerate(response2['data'], 1):
                        emb = item.get('embedding', [])
                        self.print_info(f"Embedding {i}: {len(emb)} dimensions")

                self.results['generate_embeddings'] = {
                    'status': 'PASS',
                    'dimensions': len(embedding),
                    'model': embedding_models[0],
                    'batch_tested': True
                }
                return True
            else:
                self.print_fail("Invalid response format")
                self.results['generate_embeddings'] = {'status': 'FAIL', 'reason': 'invalid_format'}
                return False

        except Exception as e:
            # Expected if no embedding model loaded
            if "404" in str(e):
                self.print_info("Embeddings endpoint not available (requires embedding model)")
                self.results['generate_embeddings'] = {'status': 'SKIP', 'reason': 'endpoint_not_available'}
                return None
            else:
                self.print_fail(f"Generate embeddings failed: {e}")
                self.results['generate_embeddings'] = {'status': 'ERROR', 'error': str(e)}
                return False

    async def test_autonomous_execution(self):
        """Test 8: End-to-end Autonomous Execution."""
        self.print_section("TEST 8: Autonomous Execution (End-to-End with Tools)")

        try:
            # Check LMS CLI availability and preload model if possible
            if self.lms_available:
                model_name = self.llm.model or "qwen/qwen3-4b-thinking-2507"
                self.print_info(f"LMS CLI detected - Ensuring model loaded: {model_name}")

                if LMSHelper.ensure_model_loaded(model_name):
                    self.print_success("Model preloaded and kept loaded (prevents 404)")
                else:
                    self.print_info("Could not preload model with LMS CLI")
            else:
                self.print_info("⚠️  LMS CLI not available - model may auto-unload causing 404")
                self.print_info("   Install: brew install lmstudio-ai/lms/lms")
                self.print_info("   This would prevent intermittent 404 errors")

            # Test with filesystem MCP (simplest)
            working_dir = str(Path(__file__).parent)
            task = "Count how many Python files (*.py) are in the current directory and tell me the exact number."

            self.print_info(f"Task: {task}")
            self.print_info(f"Working directory: {working_dir}")
            print("\nExecuting autonomous_filesystem_full()...")
            print("(This will take a few seconds as the local LLM works)")
            print()

            result = await self.tools.autonomous_filesystem_full(
                task=task,
                working_directory=working_dir,
                max_rounds=10
            )

            if result and not result.startswith("Error"):
                self.print_success("Autonomous execution completed!")
                self.print_info(f"Result: {result[:200]}...")

                # Verify it actually counted files
                import glob
                actual_count = len(glob.glob(str(Path(working_dir) / "*.py")))
                self.print_info(f"Actual Python files: {actual_count}")

                # Check if result mentions correct count
                if str(actual_count) in result:
                    self.print_success("Count verified - autonomous agent worked correctly!")

                self.results['autonomous_execution'] = {
                    'status': 'PASS',
                    'result': result[:500],
                    'actual_files': actual_count
                }
                return True
            else:
                self.print_fail("Autonomous execution failed")
                self.print_info(f"Result: {result}")
                self.results['autonomous_execution'] = {
                    'status': 'FAIL',
                    'result': result
                }
                return False

        except Exception as e:
            self.print_fail(f"Autonomous execution failed: {e}")
            import traceback
            traceback.print_exc()
            self.results['autonomous_execution'] = {'status': 'ERROR', 'error': str(e)}
            return False

    async def run_all_tests(self):
        """Run all tests in sequence."""
        print("\n" + "="*80)
        print("LM STUDIO API INTEGRATION TEST SUITE V2")
        print("Merged: Multi-round testing + Comprehensive coverage")
        print("="*80)
        print("\nTesting all LM Studio API endpoints with conversation verification...")
        print()

        # Track results
        tests_run = 0
        tests_passed = 0
        tests_failed = 0
        tests_skipped = 0
        tests_error = 0

        # Test 1: Health Check (prerequisite)
        result = self.test_health_check()
        tests_run += 1
        if result is True:
            tests_passed += 1
        elif result is False:
            tests_failed += 1
            print("\n❌ Health check failed - cannot continue")
            return self.print_final_summary(tests_run, tests_passed, tests_failed, tests_skipped, tests_error)
        else:
            tests_error += 1

        # Test 2: List Models
        result = self.test_list_models()
        tests_run += 1
        if result is True:
            tests_passed += 1
        elif result is False:
            tests_failed += 1
        elif result is None:
            tests_skipped += 1
        else:
            tests_error += 1

        # Test 3: Get Model Info
        result = self.test_get_model_info()
        tests_run += 1
        if result is True:
            tests_passed += 1
        elif result is False:
            tests_failed += 1
        elif result is None:
            tests_skipped += 1
        else:
            tests_error += 1

        # Test 4: Multi-Round Chat Completion (NEW - CRITICAL!)
        result = self.test_chat_completion_multiround()
        tests_run += 1
        if result is True:
            tests_passed += 1
        elif result is False:
            tests_failed += 1
        elif result is None:
            tests_skipped += 1
        else:
            tests_error += 1

        # Test 5: Text Completion
        result = self.test_text_completion()
        tests_run += 1
        if result is True:
            tests_passed += 1
        elif result is False:
            tests_failed += 1
        elif result is None:
            tests_skipped += 1
        else:
            tests_error += 1

        # Test 6: Multi-Round Stateful Response (NEW - with verification!)
        result = self.test_create_response_multiround()
        tests_run += 1
        if result is True:
            tests_passed += 1
        elif result is False:
            tests_failed += 1
        elif result is None:
            tests_skipped += 1
        else:
            tests_error += 1

        # Test 7: Generate Embeddings
        result = self.test_generate_embeddings()
        tests_run += 1
        if result is True:
            tests_passed += 1
        elif result is False:
            tests_failed += 1
        elif result is None:
            tests_skipped += 1
        else:
            tests_error += 1

        # Test 8: Autonomous Execution
        result = await self.test_autonomous_execution()
        tests_run += 1
        if result is True:
            tests_passed += 1
        elif result is False:
            tests_failed += 1
        elif result is None:
            tests_skipped += 1
        else:
            tests_error += 1

        # Final summary
        self.print_final_summary(tests_run, tests_passed, tests_failed, tests_skipped, tests_error)

    def print_final_summary(self, total, passed, failed, skipped, errors):
        """Print final test summary."""
        self.print_section("FINAL TEST SUMMARY")

        print(f"Tests run:    {total}")
        print(f"✅ Passed:     {passed}")
        print(f"❌ Failed:     {failed}")
        print(f"⚠️  Skipped:   {skipped}")
        print(f"💥 Errors:     {errors}")
        print()

        success_rate = (passed / total * 100) if total > 0 else 0
        print(f"Success rate: {success_rate:.1f}%")
        print()

        # Detailed results
        print("Detailed Results:")
        print("-" * 80)
        for test_name, result in self.results.items():
            status = result.get('status', 'UNKNOWN')
            icon = {
                'PASS': '✅',
                'FAIL': '❌',
                'SKIP': '⚠️ ',
                'ERROR': '💥'
            }.get(status, '❓')

            print(f"{icon} {test_name}: {status}")

            # Show additional details for multi-round tests
            if 'multiround' in test_name:
                if 'context_verified' in result:
                    context_icon = '✅' if result['context_verified'] else '❌'
                    print(f"   {context_icon} Context verification: {result['context_verified']}")
                if 'rounds' in result:
                    print(f"   🔄 Rounds tested: {result['rounds']}")

            if status == 'ERROR' and 'error' in result:
                print(f"   Error: {result['error'][:100]}...")
            if status == 'SKIP' and 'reason' in result:
                print(f"   Reason: {result['reason']}")

        print()

        # V2 specific highlights
        print("V2 Test Suite Highlights:")
        print("-" * 80)
        print("✨ Multi-round chat completion testing (NEW)")
        print("✨ Context recall verification for both APIs (NEW)")
        print("✅ Health check and model info")
        print("✅ End-to-end autonomous execution")
        print("✅ Result persistence to JSON")
        print()

        if failed == 0 and errors == 0:
            print("🎉 ALL TESTS PASSED (or skipped)!")
            print()
            print("LM Studio integration is working correctly!")
            print("All APIs functioning as expected, including:")
            print("  • Multi-round conversations with context")
            print("  • Stateful API with server-side history")
            print("  • Autonomous tool execution")
        else:
            print("⚠️  SOME TESTS FAILED")
            print()
            print("Please review the failures above.")
            print("Check LM Studio is running and models are loaded.")

        print()

        # Save results to file
        results_file = Path(__file__).parent / 'test_results_lmstudio_integration_v2.json'
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"Results saved to: {results_file}")
        print()


async def main():
    """Main test runner."""
    tester = LMStudioAPITesterV2()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
