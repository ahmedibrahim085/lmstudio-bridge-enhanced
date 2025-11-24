#!/usr/bin/env python3
"""
Phase 2.2 Manual Verification Test

Since the tool functions are defined inside register_dynamic_autonomous_tools(),
this test manually verifies the changes by reading and parsing the file.
"""

from pathlib import Path
import re


def test_phase_2_2_manual():
    """Manual verification of Phase 2.2 changes."""

    print("=" * 80)
    print("PHASE 2.2 MANUAL VERIFICATION TEST")
    print("=" * 80)
    print()

    file_path = Path(__file__).parent / "tools" / "dynamic_autonomous_register.py"
    with open(file_path, 'r') as f:
        content = f.read()

    total_tests = 0
    passed_tests = 0
    failed_tests = []

    # Expected tool functions
    tool_functions = [
        "autonomous_with_mcp",
        "autonomous_with_multiple_mcps",
        "autonomous_discover_and_execute"
    ]

    print("TEST SUITE 1: Function Signatures")
    print("-" * 80)

    for func_name in tool_functions:
        # Find function definition
        pattern = rf"async def {func_name}\((.*?)\) -> str:"
        match = re.search(pattern, content, re.DOTALL)

        if match:
            signature = match.group(1)

            # Check for model parameter
            has_model = re.search(r'model:\s*Annotated\[Optional\[str\]', signature)

            # Check for default None
            has_default_none = re.search(r'model:.*?=\s*None', signature, re.DOTALL)

            total_tests += 1
            if has_model and has_default_none:
                print(f"✅ {func_name}: has model: Optional[str] = None")
                passed_tests += 1
            else:
                print(f"❌ {func_name}: missing proper model parameter")
                failed_tests.append(f"{func_name} signature")
        else:
            print(f"❌ {func_name}: function not found")
            total_tests += 1
            failed_tests.append(f"{func_name} not found")

    print()

    # Test Suite 2: Docstring Args
    print("TEST SUITE 2: Docstring Args Section")
    print("-" * 80)

    for func_name in tool_functions:
        # Find docstring Args section for this function
        func_pattern = rf'async def {func_name}\(.*?\).*?""".*?Args:(.*?)(?:Returns:|Raises:)'
        match = re.search(func_pattern, content, re.DOTALL)

        if match:
            args_section = match.group(1)

            # Check for model parameter documented
            has_model_doc = 'model:' in args_section or 'model :' in args_section

            total_tests += 1
            if has_model_doc:
                print(f"✅ {func_name}: Args documents model parameter")
                passed_tests += 1
            else:
                print(f"❌ {func_name}: Args missing model parameter")
                failed_tests.append(f"{func_name} Args")
        else:
            print(f"❌ {func_name}: Args section not found")
            total_tests += 1
            failed_tests.append(f"{func_name} Args not found")

    print()

    # Test Suite 3: Docstring Raises Section
    print("TEST SUITE 3: Docstring Raises Section")
    print("-" * 80)

    for func_name in tool_functions:
        # Find docstring Raises section
        func_pattern = rf'async def {func_name}\(.*?\).*?""".*?Raises:(.*?)(?:Examples:|$)'
        match = re.search(func_pattern, content, re.DOTALL)

        if match:
            raises_section = match.group(1)

            # Check for ModelNotFoundError
            has_error_doc = 'ModelNotFoundError' in raises_section

            total_tests += 1
            if has_error_doc:
                print(f"✅ {func_name}: Raises documents ModelNotFoundError")
                passed_tests += 1
            else:
                print(f"❌ {func_name}: Raises missing ModelNotFoundError")
                failed_tests.append(f"{func_name} Raises")
        else:
            print(f"❌ {func_name}: Raises section not found")
            total_tests += 1
            failed_tests.append(f"{func_name} Raises not found")

    print()

    # Test Suite 4: Docstring Examples
    print("TEST SUITE 4: Docstring Examples Section")
    print("-" * 80)

    for func_name in tool_functions:
        # Find docstring Examples section
        func_pattern = rf'async def {func_name}\(.*?\).*?""".*?Examples:(.*?)"""'
        match = re.search(func_pattern, content, re.DOTALL)

        if match:
            examples_section = match.group(1)

            # Check for model parameter in examples
            has_model_example = 'model=' in examples_section or 'model =' in examples_section

            total_tests += 1
            if has_model_example:
                print(f"✅ {func_name}: Examples show model parameter usage")
                passed_tests += 1
            else:
                print(f"❌ {func_name}: Examples missing model parameter")
                failed_tests.append(f"{func_name} Examples")
        else:
            print(f"❌ {func_name}: Examples section not found")
            total_tests += 1
            failed_tests.append(f"{func_name} Examples not found")

    print()

    # Test Suite 5: Function Calls Pass model
    print("TEST SUITE 5: Function Calls Pass model Parameter")
    print("-" * 80)

    for func_name in tool_functions:
        # Find the return statement
        func_pattern = rf'async def {func_name}\(.*?\).*?return await agent\.{func_name}\((.*?)\)'
        match = re.search(func_pattern, content, re.DOTALL)

        if match:
            call_args = match.group(1)

            # Check for model=model in call
            passes_model = 'model=model' in call_args

            total_tests += 1
            if passes_model:
                print(f"✅ {func_name}: passes model=model to agent method")
                passed_tests += 1
            else:
                print(f"❌ {func_name}: does NOT pass model to agent method")
                failed_tests.append(f"{func_name} passes model")
        else:
            print(f"❌ {func_name}: return statement not found")
            total_tests += 1
            failed_tests.append(f"{func_name} return not found")

    print()

    # Summary
    print("=" * 80)
    print("PHASE 2.2 TEST SUMMARY")
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

    # Test counts by suite
    print("Test Counts by Suite:")
    print(f"  1. Function Signatures: 3 tests")
    print(f"  2. Docstring Args: 3 tests")
    print(f"  3. Docstring Raises: 3 tests")
    print(f"  4. Docstring Examples: 3 tests")
    print(f"  5. Function Calls: 3 tests")
    print(f"  TOTAL: {total_tests} tests")
    print()

    if passed_tests == total_tests:
        print("✅ ALL TESTS PASSED - Phase 2.2 is COMPLETE!")
        print()
        print("Phase 2.2 Achievements:")
        print("  ✅ All 3 tool functions support optional model parameter")
        print("  ✅ Complete documentation with Args, Raises, Examples")
        print("  ✅ Model parameter properly passed to agent methods")
        print("  ✅ Proper type hints (Optional[str])")
        print("  ✅ 100% backward compatible (model=None default)")
        print()
        print("✨ Claude Code can now specify models when calling:")
        print("  - mcp__lmstudio-bridge-enhanced_v2__autonomous_with_mcp")
        print("  - mcp__lmstudio-bridge-enhanced_v2__autonomous_with_multiple_mcps")
        print("  - mcp__lmstudio-bridge-enhanced_v2__autonomous_discover_and_execute")
        print()
        print("📋 Next Steps:")
        print("  1. Commit Phase 2.2 changes")
        print("  2. Phase 2.3: Update LLMClient error handling")
        print("  3. Phase 2.4: Integration tests")
        return True
    else:
        print("❌ SOME TESTS FAILED - Phase 2.2 needs fixes")
        return False


if __name__ == "__main__":
    success = test_phase_2_2_manual()
    exit(0 if success else 1)
