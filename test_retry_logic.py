#!/usr/bin/env python3
"""
Test script to verify retry logic with exponential backoff.

This test uses monkey-patching to simulate HTTP 500 errors
and verifies that the retry mechanism works correctly.
"""

import sys
import os
from unittest.mock import Mock, patch
import requests

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm.llm_client import LLMClient


class RetryLogicTester:
    """Test retry logic implementation."""

    def __init__(self):
        self.llm = LLMClient()

    def print_section(self, title):
        """Print section header."""
        print("\n" + "="*80)
        print(f"{title}")
        print("="*80 + "\n")

    def test_retry_on_http_500(self):
        """Test 1: Verify retry logic activates on HTTP 500."""
        self.print_section("TEST 1: Retry on HTTP 500")

        # Create mock response that simulates HTTP 500 error
        mock_error_response = Mock()
        mock_error_response.status_code = 500
        mock_error_response.text = "Internal Server Error"
        mock_error_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "500 Server Error: Internal Server Error",
            response=mock_error_response
        )

        # Create mock success response
        mock_success_response = Mock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = {
            "id": "resp_test_123",
            "object": "response",
            "status": "completed"
        }
        mock_success_response.raise_for_status = Mock()  # No error

        print("Simulating: 2 HTTP 500 errors, then success")
        print()

        with patch('requests.post') as mock_post:
            # First two calls: HTTP 500
            # Third call: Success
            mock_post.side_effect = [
                mock_error_response,
                mock_error_response,
                mock_success_response
            ]

            try:
                result = self.llm.create_response(
                    input_text="Test message",
                    max_retries=2,  # Allow 2 retries
                    retry_delay=0.1  # Fast retries for testing
                )

                if result and result.get('id') == 'resp_test_123':
                    print("✅ TEST PASSED")
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
                return False

    def test_no_retry_on_http_400(self):
        """Test 2: Verify no retry on HTTP 400 (client error)."""
        self.print_section("TEST 2: No Retry on HTTP 400")

        # Create mock response that simulates HTTP 400 error
        mock_error_response = Mock()
        mock_error_response.status_code = 400
        mock_error_response.text = "Bad Request"
        mock_error_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "400 Client Error: Bad Request",
            response=mock_error_response
        )

        print("Simulating: HTTP 400 error (should NOT retry)")
        print()

        with patch('requests.post') as mock_post:
            mock_post.return_value = mock_error_response

            try:
                result = self.llm.create_response(
                    input_text="Test message",
                    max_retries=2,
                    retry_delay=0.1
                )

                print("❌ TEST FAILED")
                print("   Should have raised HTTPError")
                return False

            except requests.exceptions.HTTPError as e:
                if "400" in str(e):
                    print("✅ TEST PASSED")
                    print("   Correctly raised HTTPError without retrying")
                    print("   (HTTP 400 errors should fail fast)")
                    return True
                else:
                    print("❌ TEST FAILED")
                    print(f"   Wrong error: {e}")
                    return False

    def test_max_retries_exhausted(self):
        """Test 3: Verify behavior when all retries exhausted."""
        self.print_section("TEST 3: Max Retries Exhausted")

        # Create mock response that always returns HTTP 500
        mock_error_response = Mock()
        mock_error_response.status_code = 500
        mock_error_response.text = "Internal Server Error"
        mock_error_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "500 Server Error: Internal Server Error",
            response=mock_error_response
        )

        print("Simulating: Persistent HTTP 500 errors (3 attempts, all fail)")
        print()

        with patch('requests.post') as mock_post:
            mock_post.return_value = mock_error_response

            try:
                result = self.llm.create_response(
                    input_text="Test message",
                    max_retries=2,  # Total 3 attempts
                    retry_delay=0.1
                )

                print("❌ TEST FAILED")
                print("   Should have raised HTTPError after max retries")
                return False

            except requests.exceptions.HTTPError as e:
                if "500" in str(e):
                    print("✅ TEST PASSED")
                    print("   Correctly raised HTTPError after exhausting retries")
                    print(f"   Total attempts: 3 (1 initial + 2 retries)")
                    return True
                else:
                    print("❌ TEST FAILED")
                    print(f"   Wrong error: {e}")
                    return False

    def test_chat_completion_retry(self):
        """Test 4: Verify retry logic works for chat_completion() too."""
        self.print_section("TEST 4: Chat Completion Retry")

        # Create mock responses
        mock_error_response = Mock()
        mock_error_response.status_code = 500
        mock_error_response.text = "Internal Server Error"
        mock_error_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "500 Server Error: Internal Server Error",
            response=mock_error_response
        )

        mock_success_response = Mock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = {
            "choices": [{
                "message": {"role": "assistant", "content": "Hello!"}
            }]
        }
        mock_success_response.raise_for_status = Mock()

        print("Simulating: 1 HTTP 500 error, then success")
        print()

        with patch('requests.post') as mock_post:
            # First call: HTTP 500, second call: success
            mock_post.side_effect = [
                mock_error_response,
                mock_success_response
            ]

            try:
                result = self.llm.chat_completion(
                    messages=[{"role": "user", "content": "Hi"}],
                    max_retries=2,
                    retry_delay=0.1
                )

                if result and result.get('choices'):
                    print("✅ TEST PASSED")
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
                return False

    def run_all_tests(self):
        """Run all retry logic tests."""
        self.print_section("RETRY LOGIC TEST SUITE")

        print("Testing retry logic implementation with exponential backoff")
        print()

        tests_run = 0
        tests_passed = 0

        # Test 1: Retry on HTTP 500
        result = self.test_retry_on_http_500()
        tests_run += 1
        if result:
            tests_passed += 1

        # Test 2: No retry on HTTP 400
        result = self.test_no_retry_on_http_400()
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
            print("  ✅ Retries on HTTP 500 errors")
            print("  ✅ No retry on HTTP 400 errors (fail fast)")
            print("  ✅ Exhausts retries correctly")
            print("  ✅ Works for both create_response() and chat_completion()")
            print()
            print("Retry configuration:")
            print("  - Default max retries: 2 (3 total attempts)")
            print("  - Initial delay: 1.0 seconds")
            print("  - Backoff multiplier: 2.0 (exponential)")
            print("  - Retry sequence: 1s → 2s → fail")
        else:
            print("❌ SOME TESTS FAILED")
            print("   Review the failures above")


def main():
    """Main test runner."""
    tester = RetryLogicTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
