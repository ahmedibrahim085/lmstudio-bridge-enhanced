#!/usr/bin/env python3
"""
Base class for standalone test runners.

Provides common functionality for test orchestration:
- Test result tracking
- Section headers for organized output
- Summary printing with pass/fail statistics
- Support for both sync and async tests
"""

from typing import List, Tuple, Callable, Any
import sys
import traceback


class TestRunner:
    """Base class for standalone test runners."""

    def __init__(self, test_name: str):
        """Initialize test runner.

        Args:
            test_name: Name of the test suite (e.g., "RETRY LOGIC TEST SUITE")
        """
        self.test_name = test_name
        self.results: List[Tuple[str, bool, str]] = []  # (test_name, passed, error_msg)
        self.total_tests = 0
        self.passed_tests = 0

    def print_section(self, title: str) -> None:
        """Print a section header.

        Args:
            title: Section title to display
        """
        print(f"\n{'='*80}")
        print(f"  {title}")
        print(f"{'='*80}\n")

    def run_test(self, test_name: str, test_func: Callable[[], Any]) -> bool:
        """Run a single synchronous test and track results.

        Args:
            test_name: Name of the test for display
            test_func: Test function to execute (no parameters)

        Returns:
            True if test passed, False otherwise
        """
        self.total_tests += 1
        try:
            test_func()
            self.passed_tests += 1
            self.results.append((test_name, True, ""))
            print(f"✓ {test_name}")
            return True
        except AssertionError as e:
            error_msg = str(e) or "Assertion failed"
            self.results.append((test_name, False, error_msg))
            print(f"✗ {test_name}: {error_msg}")
            return False
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            self.results.append((test_name, False, error_msg))
            print(f"✗ {test_name}: {error_msg}")
            if "--verbose" in sys.argv or "-v" in sys.argv:
                traceback.print_exc()
            return False

    async def run_test_async(self, test_name: str, test_func: Callable[[], Any]) -> bool:
        """Run a single asynchronous test and track results.

        Args:
            test_name: Name of the test for display
            test_func: Async test function to execute (no parameters)

        Returns:
            True if test passed, False otherwise
        """
        self.total_tests += 1
        try:
            await test_func()
            self.passed_tests += 1
            self.results.append((test_name, True, ""))
            print(f"✓ {test_name}")
            return True
        except AssertionError as e:
            error_msg = str(e) or "Assertion failed"
            self.results.append((test_name, False, error_msg))
            print(f"✗ {test_name}: {error_msg}")
            return False
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            self.results.append((test_name, False, error_msg))
            print(f"✗ {test_name}: {error_msg}")
            if "--verbose" in sys.argv or "-v" in sys.argv:
                traceback.print_exc()
            return False

    def print_summary(self) -> None:
        """Print test summary with statistics and failed tests."""
        self.print_section(f"{self.test_name} - Summary")

        # Print statistics
        print(f"Total Tests: {self.total_tests}")
        print(f"Passed: {self.passed_tests}")
        print(f"Failed: {self.total_tests - self.passed_tests}")

        if self.total_tests > 0:
            success_rate = (self.passed_tests / self.total_tests) * 100
            print(f"Success Rate: {success_rate:.1f}%")
        else:
            print("Success Rate: N/A (no tests run)")

        # Print failed tests if any
        failed_tests = [(name, error) for name, passed, error in self.results if not passed]
        if failed_tests:
            print(f"\n{'-'*80}")
            print("Failed Tests:")
            print(f"{'-'*80}")
            for test_name, error in failed_tests:
                print(f"  ✗ {test_name}")
                if error:
                    # Indent error message
                    for line in error.split('\n'):
                        print(f"    {line}")
            print(f"{'-'*80}\n")
        else:
            print(f"\n{'='*80}")
            print("🎉 All tests passed!")
            print(f"{'='*80}\n")

    def get_exit_code(self) -> int:
        """Get appropriate exit code based on test results.

        Returns:
            0 if all tests passed, 1 if any failed
        """
        return 0 if self.passed_tests == self.total_tests else 1

    def run_all(self, tests: List[Tuple[str, Callable[[], Any]]]) -> int:
        """Run a list of synchronous tests and print summary.

        Args:
            tests: List of (test_name, test_func) tuples

        Returns:
            Exit code (0 if all passed, 1 if any failed)
        """
        self.print_section(self.test_name)

        for test_name, test_func in tests:
            self.run_test(test_name, test_func)

        self.print_summary()
        return self.get_exit_code()

    async def run_all_async(self, tests: List[Tuple[str, Callable[[], Any]]]) -> int:
        """Run a list of asynchronous tests and print summary.

        Args:
            tests: List of (test_name, async_test_func) tuples

        Returns:
            Exit code (0 if all passed, 1 if any failed)
        """
        self.print_section(self.test_name)

        for test_name, test_func in tests:
            await self.run_test_async(test_name, test_func)

        self.print_summary()
        return self.get_exit_code()
