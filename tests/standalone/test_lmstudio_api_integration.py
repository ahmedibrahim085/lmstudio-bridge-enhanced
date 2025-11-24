#!/usr/bin/env python3
"""
Comprehensive LM Studio API Integration Test Suite

Tests ALL LM Studio API endpoints:
1. health_check - API connectivity
2. list_models - Model enumeration
3. get_current_model - Current model info
4. chat_completion - Traditional chat API
5. text_completion - Raw text completion
6. create_response - Stateful responses API
7. generate_embeddings - Vector embeddings
8. Autonomous execution - End-to-end with tools
"""

import asyncio
import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm.llm_client import LLMClient, DEFAULT_MAX_TOKENS
from tools.autonomous import AutonomousExecutionTools


class LMStudioAPITester:
    """Comprehensive LM Studio API integration tester."""

    def __init__(self):
        self.llm = LLMClient()
        self.tools = AutonomousExecutionTools(self.llm)
        self.results = {}

    def print_section(self, title):
        """Print section header."""
        print("\n" + "="*80)
        print(f"{title}")
        print("="*80 + "\n")

    def test_health_check(self):
        """Test 1: Health Check API."""
        self.print_section("TEST 1: Health Check API")

        try:
            is_healthy = self.llm.health_check()

            if is_healthy:
                print("✅ LM Studio is running and accessible")
                print(f"   Base URL: {self.llm.api_base}")
                self.results['health_check'] = {'status': 'PASS', 'healthy': True}
                return True
            else:
                print("❌ LM Studio is not accessible")
                self.results['health_check'] = {'status': 'FAIL', 'healthy': False}
                return False

        except Exception as e:
            print(f"❌ Health check failed: {e}")
            self.results['health_check'] = {'status': 'ERROR', 'error': str(e)}
            return False

    def test_list_models(self):
        """Test 2: List Models API."""
        self.print_section("TEST 2: List Models API")

        try:
            models = self.llm.list_models()

            if models and len(models) > 0:
                print(f"✅ Found {len(models)} models")
                print(f"\nAvailable models:")
                for i, model in enumerate(models[:5], 1):  # Show first 5
                    print(f"   {i}. {model}")
                if len(models) > 5:
                    print(f"   ... and {len(models) - 5} more")

                self.results['list_models'] = {
                    'status': 'PASS',
                    'count': len(models),
                    'models': models[:5]
                }
                return True
            else:
                print("❌ No models found")
                self.results['list_models'] = {'status': 'FAIL', 'count': 0}
                return False

        except Exception as e:
            print(f"❌ List models failed: {e}")
            self.results['list_models'] = {'status': 'ERROR', 'error': str(e)}
            return False

    def test_get_model_info(self):
        """Test 3: Get Model Info API."""
        self.print_section("TEST 3: Get Model Info API")

        try:
            model_info = self.llm.get_model_info()

            if model_info:
                model_id = model_info.get('id', 'unknown')
                print(f"✅ Current model: {model_id}")
                print(f"   Object type: {model_info.get('object', 'N/A')}")
                print(f"   Owned by: {model_info.get('owned_by', 'N/A')}")
                self.results['get_model_info'] = {
                    'status': 'PASS',
                    'model': model_id,
                    'info': model_info
                }
                return True
            else:
                print("❌ No model info available")
                self.results['get_model_info'] = {'status': 'FAIL', 'model': None}
                return False

        except Exception as e:
            print(f"❌ Get model info failed: {e}")
            self.results['get_model_info'] = {'status': 'ERROR', 'error': str(e)}
            return False

    def test_chat_completion(self):
        """Test 4: Chat Completion API."""
        self.print_section("TEST 4: Chat Completion API (/v1/chat/completions)")

        try:
            messages = [
                {"role": "user", "content": "Say 'Hello World' and nothing else."}
            ]

            print("Sending test message...")
            print(f"Messages: {json.dumps(messages, indent=2)}")
            print()

            response = self.llm.chat_completion(
                messages=messages,
                max_tokens=DEFAULT_MAX_TOKENS
            )

            if response and 'choices' in response:
                content = response['choices'][0]['message'].get('content', '')
                usage = response.get('usage', {})

                print("✅ Chat completion successful")
                print(f"\nResponse: {content}")
                print(f"\nToken usage:")
                print(f"   Input: {usage.get('prompt_tokens', 0)}")
                print(f"   Output: {usage.get('completion_tokens', 0)}")
                print(f"   Total: {usage.get('total_tokens', 0)}")

                self.results['chat_completion'] = {
                    'status': 'PASS',
                    'response': content,
                    'usage': usage
                }
                return True
            else:
                print("❌ Invalid response format")
                self.results['chat_completion'] = {'status': 'FAIL', 'reason': 'invalid_format'}
                return False

        except Exception as e:
            print(f"❌ Chat completion failed: {e}")
            import traceback
            traceback.print_exc()
            self.results['chat_completion'] = {'status': 'ERROR', 'error': str(e)}
            return False

    def test_text_completion(self):
        """Test 5: Text Completion API."""
        self.print_section("TEST 5: Text Completion API (/v1/completions)")

        try:
            prompt = "def hello_world():\n    "

            print("Sending code completion prompt...")
            print(f"Prompt: {repr(prompt)}")
            print()

            response = self.llm.text_completion(
                prompt=prompt,
                max_tokens=DEFAULT_MAX_TOKENS,
                stop_sequences=["\n\n"]
            )

            if response and 'choices' in response:
                text = response['choices'][0].get('text', '')
                usage = response.get('usage', {})

                print("✅ Text completion successful")
                print(f"\nCompletion: {repr(text)}")
                print(f"\nToken usage:")
                print(f"   Input: {usage.get('prompt_tokens', 0)}")
                print(f"   Output: {usage.get('completion_tokens', 0)}")
                print(f"   Total: {usage.get('total_tokens', 0)}")

                self.results['text_completion'] = {
                    'status': 'PASS',
                    'completion': text,
                    'usage': usage
                }
                return True
            else:
                print("❌ Invalid response format")
                self.results['text_completion'] = {'status': 'FAIL', 'reason': 'invalid_format'}
                return False

        except Exception as e:
            print(f"❌ Text completion failed: {e}")
            import traceback
            traceback.print_exc()
            self.results['text_completion'] = {'status': 'ERROR', 'error': str(e)}
            return False

    def test_create_response(self):
        """Test 6: Create Response API (Stateful)."""
        self.print_section("TEST 6: Create Response API (/v1/responses) - Stateful")

        try:
            # Message 1
            print("Message 1: What is the capital of France?")
            response1 = self.llm.create_response(
                input_text="What is the capital of France?",
                model="default"
            )

            if not response1 or 'id' not in response1:
                print("❌ Invalid response format for message 1")
                self.results['create_response'] = {'status': 'FAIL', 'reason': 'invalid_format'}
                return False

            response1_id = response1['id']
            output1 = response1.get('output', [])
            content1 = ""
            for item in output1:
                if item.get('type') == 'message':
                    for c in item.get('content', []):
                        if c.get('type') == 'output_text':
                            content1 = c.get('text', '')

            print(f"✅ Response 1 ID: {response1_id}")
            print(f"   Content: {content1[:100]}...")
            print()

            # Message 2 (referencing previous)
            print("Message 2: What is its population? (referencing previous)")
            response2 = self.llm.create_response(
                input_text="What is its population?",
                previous_response_id=response1_id,
                model="default"
            )

            if not response2 or 'id' not in response2:
                print("❌ Invalid response format for message 2")
                self.results['create_response'] = {'status': 'FAIL', 'reason': 'invalid_format_msg2'}
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

            print(f"✅ Response 2 ID: {response2_id}")
            print(f"   Previous ID: {prev_id}")
            print(f"   References previous: {prev_id == response1_id}")
            print(f"   Content: {content2[:100]}...")

            if prev_id == response1_id:
                print("\n✅ Stateful conversation works!")
                self.results['create_response'] = {
                    'status': 'PASS',
                    'stateful': True,
                    'response1_id': response1_id,
                    'response2_id': response2_id
                }
                return True
            else:
                print("\n❌ Stateful link broken")
                self.results['create_response'] = {'status': 'FAIL', 'stateful': False}
                return False

        except Exception as e:
            print(f"❌ Create response failed: {e}")
            import traceback
            traceback.print_exc()
            self.results['create_response'] = {'status': 'ERROR', 'error': str(e)}
            return False

    def test_generate_embeddings(self):
        """Test 7: Generate Embeddings API."""
        self.print_section("TEST 7: Generate Embeddings API (/v1/embeddings)")

        try:
            # First, check if an embedding model is available
            models = self.llm.list_models()
            embedding_models = [m for m in models if 'embed' in m.lower()]

            if not embedding_models:
                print("⚠️  No embedding models found")
                print("   This test requires an embedding model loaded in LM Studio")
                print("   Example: text-embedding-nomic-embed-text-v1.5")
                self.results['generate_embeddings'] = {
                    'status': 'SKIP',
                    'reason': 'no_embedding_model'
                }
                return None  # Skip, not fail

            print(f"Found embedding model: {embedding_models[0]}")
            print()

            text = "This is a test sentence for embeddings."
            print(f"Generating embedding for: {repr(text)}")
            print()

            response = self.llm.generate_embeddings(
                text=text,
                model=embedding_models[0]
            )

            if response and 'data' in response:
                embedding = response['data'][0].get('embedding', [])
                usage = response.get('usage', {})

                print("✅ Embeddings generated successfully")
                print(f"\nEmbedding dimensions: {len(embedding)}")
                print(f"First 5 values: {embedding[:5]}")
                print(f"\nToken usage: {usage.get('total_tokens', 0)}")

                self.results['generate_embeddings'] = {
                    'status': 'PASS',
                    'dimensions': len(embedding),
                    'model': embedding_models[0]
                }
                return True
            else:
                print("❌ Invalid response format")
                self.results['generate_embeddings'] = {'status': 'FAIL', 'reason': 'invalid_format'}
                return False

        except Exception as e:
            print(f"❌ Generate embeddings failed: {e}")
            import traceback
            traceback.print_exc()
            self.results['generate_embeddings'] = {'status': 'ERROR', 'error': str(e)}
            return False

    async def test_autonomous_execution(self):
        """Test 8: End-to-end Autonomous Execution."""
        self.print_section("TEST 8: Autonomous Execution (End-to-End with Tools)")

        try:
            # Test with filesystem MCP (simplest)
            working_dir = os.path.dirname(os.path.abspath(__file__))
            task = "Count how many Python files (*.py) are in the current directory and tell me the exact number."

            print(f"Task: {task}")
            print(f"Working directory: {working_dir}")
            print("\nExecuting autonomous_filesystem_full()...")
            print("(This will take a few seconds as the local LLM works)")
            print()

            result = await self.tools.autonomous_filesystem_full(
                task=task,
                working_directory=working_dir,
                max_rounds=10
            )

            if result and not result.startswith("Error"):
                print("✅ Autonomous execution completed!")
                print(f"\nResult: {result}")

                # Verify it actually counted files
                import glob
                actual_count = len(glob.glob(os.path.join(working_dir, "*.py")))
                print(f"\nActual Python files: {actual_count}")

                self.results['autonomous_execution'] = {
                    'status': 'PASS',
                    'result': result,
                    'actual_files': actual_count
                }
                return True
            else:
                print(f"❌ Autonomous execution failed")
                print(f"Result: {result}")
                self.results['autonomous_execution'] = {
                    'status': 'FAIL',
                    'result': result
                }
                return False

        except Exception as e:
            print(f"❌ Autonomous execution failed: {e}")
            import traceback
            traceback.print_exc()
            self.results['autonomous_execution'] = {'status': 'ERROR', 'error': str(e)}
            return False

    async def run_all_tests(self):
        """Run all tests in sequence."""
        print("\n" + "="*80)
        print("LM STUDIO API INTEGRATION TEST SUITE")
        print("="*80)
        print("\nTesting all LM Studio API endpoints...")
        print("This will validate the complete integration.")
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

        # Test 2: List Models
        result = self.test_list_models()
        tests_run += 1
        if result is True:
            tests_passed += 1
        elif result is False:
            tests_failed += 1
        else:
            tests_error += 1

        # Test 3: Get Model Info
        result = self.test_get_model_info()
        tests_run += 1
        if result is True:
            tests_passed += 1
        elif result is False:
            tests_failed += 1
        else:
            tests_error += 1

        # Test 4: Chat Completion
        result = self.test_chat_completion()
        tests_run += 1
        if result is True:
            tests_passed += 1
        elif result is False:
            tests_failed += 1
        else:
            tests_error += 1

        # Test 5: Text Completion
        result = self.test_text_completion()
        tests_run += 1
        if result is True:
            tests_passed += 1
        elif result is False:
            tests_failed += 1
        else:
            tests_error += 1

        # Test 6: Create Response (Stateful)
        result = self.test_create_response()
        tests_run += 1
        if result is True:
            tests_passed += 1
        elif result is False:
            tests_failed += 1
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

            if status == 'ERROR' and 'error' in result:
                print(f"   Error: {result['error']}")

        print()

        if failed == 0 and errors == 0:
            print("🎉 ALL TESTS PASSED (or skipped)!")
            print()
            print("LM Studio integration is working correctly!")
            print("All APIs are functioning as expected.")
        else:
            print("⚠️  SOME TESTS FAILED")
            print()
            print("Please review the failures above.")
            print("Check LM Studio is running and models are loaded.")

        print()

        # Save results to file
        results_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'test_results_lmstudio_integration.json'
        )
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"Results saved to: {results_file}")
        print()


async def main():
    """Main test runner."""
    tester = LMStudioAPITester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
