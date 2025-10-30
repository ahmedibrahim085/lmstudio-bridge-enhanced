#!/usr/bin/env python3
"""
Phase 2.2 Test Suite - Tool Registration Multi-Model Support

Tests that all MCP tool functions in dynamic_autonomous_register.py
properly support the optional model parameter.
"""

import ast
import inspect
from typing import get_type_hints, get_origin, get_args
from pathlib import Path


def test_phase_2_2():
    """Comprehensive test suite for Phase 2.2 tool registration updates."""

    print("=" * 80)
    print("PHASE 2.2 TEST SUITE - Tool Registration Multi-Model Support")
    print("=" * 80)
    print()

    # Read the file
    file_path = Path(__file__).parent / "tools" / "dynamic_autonomous_register.py"
    with open(file_path, 'r') as f:
        content = f.read()

    # Parse AST
    tree = ast.parse(content)

    # Find all function definitions decorated with @mcp.tool()
    tool_functions = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Check if decorated with @mcp.tool()
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call):
                    if hasattr(decorator.func, 'attr') and decorator.func.attr == 'tool':
                        tool_functions.append(node)
                        break

    print(f"Found {len(tool_functions)} functions decorated with @mcp.tool()")
    print()

    # Expected tool functions that should have model parameter
    expected_tool_functions_with_model = [
        "autonomous_with_mcp",
        "autonomous_with_multiple_mcps",
        "autonomous_discover_and_execute"
    ]

    # Function that should NOT have model parameter
    expected_tool_functions_without_model = [
        "list_available_mcps"
    ]

    total_tests = 0
    passed_tests = 0
    failed_tests = []

    # Test Suite 1: Function Signatures
    print("TEST SUITE 1: Function Signatures")
    print("-" * 80)

    for func_node in tool_functions:
        func_name = func_node.name

        if func_name in expected_tool_functions_with_model:
            # Check for model parameter
            has_model = False
            model_default = None

            for arg in func_node.args.args:
                if arg.arg == 'model':
                    has_model = True
                    # Find default value
                    arg_index = func_node.args.args.index(arg)
                    defaults_offset = len(func_node.args.args) - len(func_node.args.defaults)
                    if arg_index >= defaults_offset:
                        default_index = arg_index - defaults_offset
                        default_node = func_node.args.defaults[default_index]
                        if isinstance(default_node, ast.Constant):
                            model_default = default_node.value
                    break

            total_tests += 1
            if has_model and model_default is None:
                print(f"✅ {func_name}: has model parameter with default=None")
                passed_tests += 1
            else:
                print(f"❌ {func_name}: missing model parameter or wrong default")
                failed_tests.append(f"{func_name} signature")

        elif func_name in expected_tool_functions_without_model:
            # Should NOT have model parameter
            has_model = any(arg.arg == 'model' for arg in func_node.args.args)

            total_tests += 1
            if not has_model:
                print(f"✅ {func_name}: correctly does NOT have model parameter")
                passed_tests += 1
            else:
                print(f"❌ {func_name}: should NOT have model parameter")
                failed_tests.append(f"{func_name} should not have model")

    print()

    # Test Suite 2: Docstring Documentation
    print("TEST SUITE 2: Docstring Documentation")
    print("-" * 80)

    for func_node in tool_functions:
        func_name = func_node.name

        if func_name in expected_tool_functions_with_model:
            docstring = ast.get_docstring(func_node)

            if docstring:
                # Check for model in Args section
                has_model_arg = "model:" in docstring.lower() or "model :" in docstring.lower()

                # Check for ModelNotFoundError in Raises section
                has_raises = "ModelNotFoundError" in docstring

                # Check for model examples
                has_model_example = 'model=' in docstring or 'model =' in docstring

                # Args test
                total_tests += 1
                if has_model_arg:
                    print(f"✅ {func_name}: docstring Args documents model parameter")
                    passed_tests += 1
                else:
                    print(f"❌ {func_name}: docstring Args missing model parameter")
                    failed_tests.append(f"{func_name} docstring Args")

                # Raises test
                total_tests += 1
                if has_raises:
                    print(f"✅ {func_name}: docstring Raises documents ModelNotFoundError")
                    passed_tests += 1
                else:
                    print(f"❌ {func_name}: docstring Raises missing ModelNotFoundError")
                    failed_tests.append(f"{func_name} docstring Raises")

                # Examples test
                total_tests += 1
                if has_model_example:
                    print(f"✅ {func_name}: docstring Examples show model parameter usage")
                    passed_tests += 1
                else:
                    print(f"❌ {func_name}: docstring Examples missing model parameter")
                    failed_tests.append(f"{func_name} docstring Examples")
            else:
                print(f"⚠️  {func_name}: no docstring found")
                total_tests += 3
                failed_tests.extend([
                    f"{func_name} docstring Args",
                    f"{func_name} docstring Raises",
                    f"{func_name} docstring Examples"
                ])

    print()

    # Test Suite 3: Function Calls Pass model Parameter
    print("TEST SUITE 3: Function Calls Pass model Parameter")
    print("-" * 80)

    for func_node in tool_functions:
        func_name = func_node.name

        if func_name in expected_tool_functions_with_model:
            # Find the return statement that calls agent method
            passes_model = False

            for node in ast.walk(func_node):
                if isinstance(node, ast.Return) and node.value:
                    if isinstance(node.value, ast.Await):
                        call_node = node.value.value
                        if isinstance(call_node, ast.Call):
                            # Check if model is passed as keyword argument
                            for keyword in call_node.keywords:
                                if keyword.arg == 'model':
                                    passes_model = True
                                    break

            total_tests += 1
            if passes_model:
                print(f"✅ {func_name}: passes model parameter to agent method")
                passed_tests += 1
            else:
                print(f"❌ {func_name}: does NOT pass model parameter to agent method")
                failed_tests.append(f"{func_name} passes model")

    print()

    # Test Suite 4: Type Annotations
    print("TEST SUITE 4: Type Annotations")
    print("-" * 80)

    for func_node in tool_functions:
        func_name = func_node.name

        if func_name in expected_tool_functions_with_model:
            # Check model parameter annotation
            model_annotation = None

            for arg in func_node.args.args:
                if arg.arg == 'model':
                    if arg.annotation:
                        # Get annotation as string
                        model_annotation = ast.unparse(arg.annotation)
                    break

            total_tests += 1
            # Should be Annotated[Optional[str], Field(...)]
            if model_annotation and 'Optional[str]' in model_annotation:
                print(f"✅ {func_name}: model parameter has Optional[str] type hint")
                passed_tests += 1
            else:
                print(f"❌ {func_name}: model parameter missing or wrong type hint")
                failed_tests.append(f"{func_name} type hint")

    print()

    # Test Suite 5: Backward Compatibility
    print("TEST SUITE 5: Backward Compatibility")
    print("-" * 80)

    for func_node in tool_functions:
        func_name = func_node.name

        if func_name in expected_tool_functions_with_model:
            # Count required vs optional parameters
            num_args = len(func_node.args.args)
            num_defaults = len(func_node.args.defaults)
            num_required = num_args - num_defaults

            # model should be optional (has default)
            model_is_optional = False
            for i, arg in enumerate(func_node.args.args):
                if arg.arg == 'model':
                    defaults_start = num_args - num_defaults
                    if i >= defaults_start:
                        model_is_optional = True
                    break

            total_tests += 1
            if model_is_optional:
                print(f"✅ {func_name}: model parameter is optional (has default)")
                passed_tests += 1
            else:
                print(f"❌ {func_name}: model parameter is required (breaks backward compat)")
                failed_tests.append(f"{func_name} backward compat")

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
    print(f"  1. Function Signatures: 4 tests")
    print(f"  2. Docstring Documentation: 9 tests (3 per function)")
    print(f"  3. Function Calls: 3 tests")
    print(f"  4. Type Annotations: 3 tests")
    print(f"  5. Backward Compatibility: 3 tests")
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
        print("Claude Code can now specify models when calling:")
        print("  - mcp__lmstudio-bridge-enhanced_v2__autonomous_with_mcp")
        print("  - mcp__lmstudio-bridge-enhanced_v2__autonomous_with_multiple_mcps")
        print("  - mcp__lmstudio-bridge-enhanced_v2__autonomous_discover_and_execute")
        return True
    else:
        print("❌ SOME TESTS FAILED - Phase 2.2 needs fixes")
        return False


if __name__ == "__main__":
    success = test_phase_2_2()
    exit(0 if success else 1)
