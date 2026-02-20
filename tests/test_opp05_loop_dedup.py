"""OPP-05: Verify autonomous loop deduplication."""
import ast
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestPreloadValidateHelper:
    """Tests for _preload_and_validate_model helper extraction."""

    def test_method_exists(self):
        """_preload_and_validate_model must exist on DynamicAutonomousAgent."""
        from tools.dynamic_autonomous import DynamicAutonomousAgent
        assert hasattr(DynamicAutonomousAgent, "_preload_and_validate_model")

    def test_method_is_async(self):
        """_preload_and_validate_model must be a coroutine function."""
        import inspect
        from tools.dynamic_autonomous import DynamicAutonomousAgent
        assert inspect.iscoroutinefunction(DynamicAutonomousAgent._preload_and_validate_model)


class TestDispatcherClasses:
    """Tests for tool dispatcher abstraction."""

    def test_single_dispatcher_exists(self):
        """_SingleSessionDispatcher must be importable."""
        from tools.dynamic_autonomous import _SingleSessionDispatcher
        assert _SingleSessionDispatcher is not None

    def test_multi_dispatcher_exists(self):
        """_MultiSessionDispatcher must be importable."""
        from tools.dynamic_autonomous import _MultiSessionDispatcher
        assert _MultiSessionDispatcher is not None

    def test_single_dispatcher_has_dispatch(self):
        """_SingleSessionDispatcher must have a dispatch method."""
        from tools.dynamic_autonomous import _SingleSessionDispatcher
        assert hasattr(_SingleSessionDispatcher, "dispatch")

    def test_multi_dispatcher_has_dispatch(self):
        """_MultiSessionDispatcher must have a dispatch method."""
        from tools.dynamic_autonomous import _MultiSessionDispatcher
        assert hasattr(_MultiSessionDispatcher, "dispatch")


class TestLoopUnification:
    """Tests that the old multi-MCP loop is gone and unified loop accepts dispatcher."""

    def test_no_autonomous_loop_multi_mcp(self):
        """_autonomous_loop_multi_mcp must be removed (unified into _autonomous_loop)."""
        source_path = os.path.join(os.path.dirname(__file__), "..", "tools", "dynamic_autonomous.py")
        with open(source_path) as f:
            tree = ast.parse(f.read())
        methods = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(node.name)
        assert "_autonomous_loop_multi_mcp" not in methods, \
            "_autonomous_loop_multi_mcp should be removed after unification"

    def test_autonomous_loop_accepts_dispatcher(self):
        """_autonomous_loop's first parameter (after self) should be 'dispatcher'."""
        source_path = os.path.join(os.path.dirname(__file__), "..", "tools", "dynamic_autonomous.py")
        with open(source_path) as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "_autonomous_loop":
                # args.args[0] is self, args.args[1] should be dispatcher
                param_names = [arg.arg for arg in node.args.args]
                assert "dispatcher" in param_names, \
                    f"_autonomous_loop params should include 'dispatcher', got: {param_names}"
                return
        assert False, "_autonomous_loop not found"


class TestPublicAPIUnchanged:
    """Verify public methods still exist and are async."""

    def test_autonomous_with_mcp_exists(self):
        import inspect
        from tools.dynamic_autonomous import DynamicAutonomousAgent
        assert inspect.iscoroutinefunction(DynamicAutonomousAgent.autonomous_with_mcp)

    def test_autonomous_with_multiple_mcps_exists(self):
        import inspect
        from tools.dynamic_autonomous import DynamicAutonomousAgent
        assert inspect.iscoroutinefunction(DynamicAutonomousAgent.autonomous_with_multiple_mcps)

    def test_autonomous_discover_and_execute_exists(self):
        import inspect
        from tools.dynamic_autonomous import DynamicAutonomousAgent
        assert inspect.iscoroutinefunction(DynamicAutonomousAgent.autonomous_discover_and_execute)
