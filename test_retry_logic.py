#!/usr/bin/env python3
"""
Test script to verify retry logic with exponential backoff.

This test verifies that the @retry_with_backoff decorator properly handles
errors by mocking the underlying HTTP requests and ensuring retry behavior.
"""

import sys
import os
from unittest.mock import Mock, patch, call
import requests

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm.llm_client import LLMClient
from llm.exceptions import LLMResponseError, LLMTimeoutError


class RetryLogicTester:
    """Test retry logic implementation."""

    def __init__(self):
        self.llm = LLMClient()

    def print_section(self, title):
        """Print section header."""
        print("\n" + "="*80)
        print(f"{title}")
        print("="*80 + "\n")

    def test_retry_on_llm_response_error(self):
        """Test 1: Verify retry logic activates on LLMResponseError."""
        self.print_section("TEST 1: Retry on LLMResponseError")

        # Create mock responses for HTTP 500 error
        def create_error_response():
            mock_error = Mock()
            mock_error.status_code = 500
            mock_error.text = "Internal Server Error"
            mock_error.response = mock_error  # HTTPError needs .response attribute
            # Make raise_for_status() raise an HTTPError
            mock_error.raise_for_status = Mock(
                side_effect=requests.exceptions.HTTPError("500 Server Error", response=mock_error)
            )
            return mock_error

        # Create mock success response
        mock_success_response = Mock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = {
            "id": "resp_test_123",
            "object": "response",
            "status": "completed",
            "choices": [{"message": {"role": "assistant", "content": "Success"}}]
        }
        mock_success_response.raise_for_status = Mock()  # No error

        print("Simulating: 2 HTTP 500 errors, then success")
        print("Expected: 3 total attempts (1 initial + 2 retries)")
        print()

        with patch('requests.post') as mock_post:
            # First two calls: HTTP 500 errors
            # Third call: Success
            mock_post.side_effect = [
                create_error_response(),
                create_error_response(),
                mock_success_response
            ]

            try:
                result = self.llm.create_response(
                    input_text="Test message"
                )

                # Verify we made 3 attempts
                assert mock_post.call_count == 3, f"Expected 3 attempts, got {mock_post.call_count}"

                if result and result.get('id') == 'resp_test_123':
                    print("✅ TEST PASSED")
                    print(f"   Made {mock_post.call_count} attempts (as expected)")
                    print("   Retry logic successfully handled HTTP 500 errors")
                    print(f"   Result: {result}")
                    return True
                else:
                    print("❌ TEST FAILED")
                    print("   Unexpected result format")
                    return False

            except Exception as e:
                print("❌ TEST FAILED")
                print(f"   Error: {e}")
                print(f"   Attempts made: {mock_post.call_count}")
                return False

    def test_retry_on_all_llm_response_errors(self):
        """Test 2: Verify retry happens on ALL LLMResponseError (including HTTP 400)."""
        self.print_section("TEST 2: Retry on ALL LLMResponseError (HTTP 400/500/etc)")

        # Create mock response that simulates HTTP 400 error
        def create_400_error():
            mock_error = Mock()
            mock_error.status_code = 400
            mock_error.text = "Bad Request"
            mock_error.response = mock_error
            mock_error.raise_for_status = Mock(
                side_effect=requests.exceptions.HTTPError("400 Client Error", response=mock_error)
            )
            return mock_error

        # Create success response
        mock_success_response = Mock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = {
            "id": "resp_test_400_recovery",
            "object": "response",
            "status": "completed",
            "choices": [{"message": {"role": "assistant", "content": "Success"}}]
        }
        mock_success_response.raise_for_status = Mock()

        print("Simulating: 1 HTTP 400 error, then success")
        print("Expected: 2 attempts (decorator retries on ALL LLMResponseError)")
        print()
        print("Note: Current implementation retries ALL HTTP errors converted to LLMResponseError,")
        print("      including HTTP 400. This may not be ideal but is the current behavior.")
        print()

        with patch('requests.post') as mock_post:
            mock_post.side_effect = [
                create_400_error(),
                mock_success_response
            ]

            try:
                result = self.llm.create_response(
                    input_text="Test message"
                )

                # Verify we made 2 attempts (retried once)
                if mock_post.call_count == 2:
                    print("✅ TEST PASSED")
                    print(f"   Made {mock_post.call_count} attempts (as expected)")
                    print("   Decorator retries on ALL LLMResponseError exceptions")
                    print(f"   Result: {result}")
                    return True
                else:
                    print("❌ TEST FAILED")
                    print(f"   Made {mock_post.call_count} attempts (expected 2)")
                    return False

            except (LLMResponseError, requests.exceptions.HTTPError) as e:
                print("❌ TEST FAILED")
                print(f"   Should have succeeded after retry, but raised: {e}")
                print(f"   Attempts made: {mock_post.call_count}")
                return False
            except Exception as e:
                print("❌ TEST FAILED")
                print(f"   Unexpected error type: {type(e).__name__}")
                print(f"   Error: {e}")
                return False

    def test_max_retries_exhausted(self):
        """Test 3: Verify behavior when all retries exhausted."""
        self.print_section("TEST 3: Max Retries Exhausted")

        # Create mock response that always returns HTTP 500
        def create_persistent_error():
            mock_error = Mock()
            mock_error.status_code = 500
            mock_error.text = "Internal Server Error"
            mock_error.response = mock_error
            mock_error.raise_for_status = Mock(
                side_effect=requests.exceptions.HTTPError("500 Server Error", response=mock_error)
            )
            return mock_error

        print("Simulating: Persistent HTTP 500 errors (all attempts fail)")
        print("Expected: 3 total attempts, then raise LLMResponseError")
        print()

        with patch('requests.post') as mock_post:
            # Always return error for every attempt
            mock_post.side_effect = [create_persistent_error() for _ in range(5)]  # More than enough

            try:
                result = self.llm.create_response(
                    input_text="Test message"
                )

                print("❌ TEST FAILED")
                print("   Should have raised LLMResponseError after max retries")
                print(f"   Instead got result: {result}")
                return False

            except LLMResponseError as e:
                if mock_post.call_count == 3:
                    print("✅ TEST PASSED")
                    print(f"   Made {mock_post.call_count} attempts (1 initial + 2 retries)")
                    print("   Correctly raised LLMResponseError after exhausting retries")
                    return True
                else:
                    print("❌ TEST FAILED")
                    print(f"   Made {mock_post.call_count} attempts (expected 3)")
                    return False
            except Exception as e:
                print("❌ TEST FAILED")
                print(f"   Unexpected error type: {type(e).__name__}")
                print(f"   Error: {e}")
                print(f"   Attempts made: {mock_post.call_count}")
                return False

    def test_chat_completion_retry(self):
        """Test 4: Verify retry logic works for chat_completion() too."""
        self.print_section("TEST 4: Chat Completion Retry")

        # Create mock error response
        def create_error_response():
            mock_error = Mock()
            mock_error.status_code = 500
            mock_error.text = "Internal Server Error"
            mock_error.response = mock_error
            mock_error.raise_for_status = Mock(
                side_effect=requests.exceptions.HTTPError("500 Server Error", response=mock_error)
            )
            return mock_error

        # Create mock success response
        mock_success_response = Mock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = {
            "choices": [{
                "message": {"role": "assistant", "content": "Hello!"}
            }]
        }
        mock_success_response.raise_for_status = Mock()  # No error

        print("Simulating: 1 HTTP 500 error, then success")
        print("Expected: 2 attempts (1 initial + 1 retry)")
        print()

        with patch('requests.post') as mock_post:
            # First call: HTTP 500, second call: success
            mock_post.side_effect = [
                create_error_response(),
                mock_success_response
            ]

            try:
                result = self.llm.chat_completion(
                    messages=[{"role": "user", "content": "Hi"}]
                )

                # Verify we made 2 attempts
                assert mock_post.call_count == 2, f"Expected 2 attempts, got {mock_post.call_count}"

                if result and result.get('choices'):
                    print("✅ TEST PASSED")
                    print(f"   Made {mock_post.call_count} attempts (as expected)")
                    print("   chat_completion() retry logic working correctly")
                    print(f"   Response: {result['choices'][0]['message']['content']}")
                    return True
                else:
                    print("❌ TEST FAILED")
                    print("   Unexpected result format")
                    return False

            except Exception as e:
                print("❌ TEST FAILED")
                print(f"   Error: {e}")
                print(f"   Attempts made: {mock_post.call_count}")
                return False

    def run_all_tests(self):
        """Run all retry logic tests."""
        self.print_section("RETRY LOGIC TEST SUITE")

        print("Testing @retry_with_backoff decorator implementation")
        print("Decorator is applied at method level with:")
        print("  - max_retries: 3 total attempts (1 initial + 2 retries)")
        print("  - base_delay: 1.0 seconds")
        print("  - Retries on: LLMResponseError, LLMTimeoutError")
        print()

        tests_run = 0
        tests_passed = 0

        # Test 1: Retry on LLMResponseError
        result = self.test_retry_on_llm_response_error()
        tests_run += 1
        if result:
            tests_passed += 1

        # Test 2: Retry on ALL LLMResponseError (including HTTP 400)
        result = self.test_retry_on_all_llm_response_errors()
        tests_run += 1
        if result:
            tests_passed += 1

        # Test 3: Max retries exhausted
        result = self.test_max_retries_exhausted()
        tests_run += 1
        if result:
            tests_passed += 1

        # Test 4: Chat completion retry
        result = self.test_chat_completion_retry()
        tests_run += 1
        if result:
            tests_passed += 1

        # Final summary
        self.print_final_summary(tests_run, tests_passed)

        # Return non-zero exit code if any tests failed
        if tests_passed < tests_run:
            sys.exit(1)

    def print_final_summary(self, total, passed):
        """Print test summary."""
        self.print_section("TEST SUMMARY")

        print(f"Tests run: {total}")
        print(f"Tests passed: {passed}")
        print(f"Tests failed: {total - passed}")
        print()

        if passed == total:
            print("✅ ALL TESTS PASSED")
            print()
            print("Retry logic implementation verified:")
            print("  ✅ Retries on HTTP 500 errors (LLMResponseError)")
            print("  ✅ Retries on ALL LLMResponseError (including HTTP 400)")
            print("  ✅ Exhausts retries correctly (3 attempts)")
            print("  ✅ Works for both create_response() and chat_completion()")
            print()
            print("Retry configuration (set at decorator level):")
            print("  - max_retries: 3 total attempts")
            print("  - base_delay: 1.0 seconds")
            print("  - Backoff multiplier: 2.0 (exponential)")
            print("  - Retry sequence: 1s → 2s → fail")
            print("  - Exceptions: LLMResponseError, LLMTimeoutError")
        else:
            print("❌ SOME TESTS FAILED")
            print("   Review the failures above")


def main():
    """Main test runner."""
    tester = RetryLogicTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
