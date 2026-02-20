"""AST-based code quality guards to prevent regressions."""

import ast
import os


class TestNoBareExcepts:
    """Verify no bare except: clauses exist in production code."""

    def _get_python_files(self):
        """Get all .py files in production code (exclude tests/)."""
        py_files = []
        for root, dirs, files in os.walk("."):
            # Skip test directories, hidden dirs, __pycache__
            dirs[:] = [d for d in dirs if d not in ("tests", "__pycache__", ".git", "venv", ".venv", "docs")]
            for f in files:
                if f.endswith(".py"):
                    py_files.append(os.path.join(root, f))
        return py_files

    def test_no_bare_except_in_production_code(self):
        """No bare 'except:' clauses should exist in production code."""
        violations = []

        for filepath in self._get_python_files():
            with open(filepath, "r") as f:
                try:
                    tree = ast.parse(f.read(), filename=filepath)
                except SyntaxError:
                    continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler) and node.type is None:
                    violations.append(f"{filepath}:{node.lineno}")

        assert not violations, (
            f"Found {len(violations)} bare except: clause(s) — "
            f"use 'except Exception:' instead:\n" +
            "\n".join(f"  - {v}" for v in violations)
        )


class TestNoSysPathInsert:
    """Verify no sys.path.insert hacks in tools/ directory."""

    def test_no_sys_path_insert_in_tools(self):
        """No sys.path.insert() calls should exist in tools/ directory."""
        violations = []

        for root, _, files in os.walk("tools"):
            for f in files:
                if not f.endswith(".py"):
                    continue
                filepath = os.path.join(root, f)
                with open(filepath, "r") as fh:
                    for i, line in enumerate(fh, 1):
                        if "sys.path.insert" in line or "sys.path.append" in line:
                            violations.append(f"{filepath}:{i}: {line.strip()}")

        assert not violations, (
            f"Found sys.path manipulation in tools/:\n" +
            "\n".join(f"  - {v}" for v in violations)
        )
