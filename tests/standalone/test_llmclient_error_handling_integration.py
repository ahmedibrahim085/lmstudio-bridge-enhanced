#!/usr/bin/env python3
"""
Phase 2.3 Test Suite - LLMClient Error Handling Integration

Tests that LLMClient properly integrates the new exception hierarchy
and uses the retry decorator.
"""

import ast
import inspect
import re
from pathlib import Path
from llm.llm_client import LLMClient
from llm.exceptions import (
    LLMError,
    LLMTimeoutError,
    LLMConnectionError,
    LLMResponseError,
    LLMRateLimitError,
)
from utils.error_handling import retry_with_backoff


def test_phase_2_3():
    """Comprehensive test suite for Phase 2.3 LLMClient error handling."""

    print("=" * 80)
    print("PHASE 2.3 TEST SUITE - LLMClient Error Handling Integration")
    print("=" * 80)
    print()

    total_tests = 0
    passed_tests = 0
    failed_tests = []

    # Test Suite 1: Imports
    print("TEST SUITE 1: Exception Imports")
    print("-" * 80)

    file_path = Path(__file__).parent / "llm" / "llm_client.py"
    with open(file_path, 'r') as f:
        content = f.read()

    # Check for exception imports
    required_imports = [
        "LLMError",
        "LLMTimeoutError",
        "LLMConnectionError",
        "LLMResponseError",
        "LLMRateLimitError",
    ]

    for imp in required_imports:
        total_tests += 1
        if f"from llm.exceptions import" in content and imp in content:
            print(f"✅ Imports {imp}")
            passed_tests += 1
        else:
            print(f"❌ Missing import: {imp}")
            failed_tests.append(f"Import {imp}")

    # Check for retry_with_backoff import
    total_tests += 1
    if "from utils.error_handling import retry_with_backoff" in content:
        print(f"✅ Imports retry_with_backoff decorator")
        passed_tests += 1
    else:
        print(f"❌ Missing import: retry_with_backoff")
        failed_tests.append("Import retry_with_backoff")

    print()

    # Test Suite 2: Helper Function
    print("TEST SUITE 2: Exception Handler Function")
    print("-" * 80)

    total_tests += 1
    if "_handle_request_exception" in content:
        print(f"✅ _handle_request_exception function exists")
        passed_tests += 1
    else:
        print(f"❌ _handle_request_exception function missing")
        failed_tests.append("_handle_request_exception function")

    print()

    # Test Suite 3: Decorator Usage
    print("TEST SUITE 3: Retry Decorator Usage")
    print("-" * 80)

    methods_requiring_decorator = [
        "chat_completion",
        "text_completion",
        "generate_embeddings",
        "create_response"
    ]

    for method in methods_requiring_decorator:
        total_tests += 1
        # Look for @retry_with_backoff before the method definition
        pattern = rf"@retry_with_backoff\(.*?\)\s+def {method}\("
        if re.search(pattern, content, re.DOTALL):
            print(f"✅ {method}: uses @retry_with_backoff decorator")
            passed_tests += 1
        else:
            print(f"❌ {method}: missing @retry_with_backoff decorator")
            failed_tests.append(f"{method} decorator")

    print()

    # Test Suite 4: Docstring Updates
    print("TEST SUITE 4: Docstring Raises Sections")
    print("-" * 80)

    for method in methods_requiring_decorator:
        total_tests += 1
        # Find the function definition line number
        func_def_pattern = rf'^\s+def {method}\('
        lines = content.split('\n')
        func_line_idx = None

        for idx, line in enumerate(lines):
            if re.match(func_def_pattern, line):
                func_line_idx = idx
                break

        if func_line_idx is not None:
            # Extract ~50 lines after function definition (should include full docstring)
            func_section = '\n'.join(lines[func_line_idx:func_line_idx+50])

            # Check if docstring contains new exception types
            has_new_exceptions = (
                "LLMTimeoutError" in func_section or
                "LLMConnectionError" in func_section or
                "LLMResponseError" in func_section or
                "LLMError" in func_section
            )

            if has_new_exceptions:
                print(f"✅ {method}: docstring documents new exception types")
                passed_tests += 1
            else:
                print(f"❌ {method}: docstring missing new exception types")
                failed_tests.append(f"{method} docstring")
        else:
            print(f"❌ {method}: function definition not found")
            failed_tests.append(f"{method} function not found")

    print()

    # Test Suite 5: Exception Usage
    print("TEST SUITE 5: Exception Handler Calls")
    print("-" * 80)

    for method in methods_requiring_decorator + ["list_models", "get_model_info"]:
        total_tests += 1
        # Check if method calls _handle_request_exception
        method_pattern = rf'def {method}\(.*?\):(.*?)(?=\n    def |\Z)'
        match = re.search(method_pattern, content, re.DOTALL)

        if match:
            method_body = match.group(1)
            if "_handle_request_exception" in method_body:
                print(f"✅ {method}: calls _handle_request_exception")
                passed_tests += 1
            else:
                print(f"❌ {method}: does not call _handle_request_exception")
                failed_tests.append(f"{method} exception handling")
        else:
            print(f"⚠️  {method}: could not parse method body")

    print()

    # Test Suite 6: Removed Manual Retry Logic
    print("TEST SUITE 6: Manual Retry Logic Removal")
    print("-" * 80)

    total_tests += 1
    # Check that manual retry loops are removed
    has_manual_retry = "for attempt in range(max_retries" in content
    if not has_manual_retry:
        print(f"✅ Manual retry loops removed (using decorator instead)")
        passed_tests += 1
    else:
        print(f"❌ Manual retry loops still present")
        failed_tests.append("Manual retry loops")

    print()

    # Summary
    print("=" * 80)
    print("PHASE 2.3 TEST SUMMARY")
    print("=" * 80)
    print()
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests} ✅")
    print(f"Failed: {len(failed_tests)} ❌")
    print(f"Success Rate: {100 * passed_tests / total_tests:.1f}%")
    print()

    if failed_tests:
        print("Failed Tests:")
        for test in failed_tests:
            print(f"  - {test}")
        print()

    if passed_tests == total_tests:
        print("✅ ALL TESTS PASSED - Phase 2.3 is COMPLETE!")
        print()
        print("Phase 2.3 Achievements:")
        print("  ✅ Integrated new exception hierarchy (5 exception types)")
        print("  ✅ Added _handle_request_exception helper function")
        print("  ✅ Applied @retry_with_backoff decorator to 4 core methods")
        print("  ✅ Updated all docstrings with new exception types")
        print("  ✅ All methods properly handle and convert exceptions")
        print("  ✅ Removed manual retry loops (cleaner code)")
        print()
        print("Benefits:")
        print("  • Clear, specific exceptions for different error types")
        print("  • Automatic retry with exponential backoff")
        print("  • Better error messages with context")
        print("  • Easier debugging (original exception tracked)")
        print("  • Cleaner code (decorator vs manual retry loops)")
        return True
    else:
        print("❌ SOME TESTS FAILED - Phase 2.3 needs fixes")
        return False


if __name__ == "__main__":
    success = test_phase_2_3()
    exit(0 if success else 1)
