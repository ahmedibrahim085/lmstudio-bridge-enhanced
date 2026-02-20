"""Architecture guard tests to prevent regressions."""

import os


class TestNoDeadPackages:
    """Verify deleted packages stay deleted."""

    def test_adapters_directory_does_not_exist(self):
        """adapters/ was removed in B1 — must not be recreated."""
        assert not os.path.isdir("adapters"), "adapters/ directory should not exist (removed in B1)"

    def test_app_directory_does_not_exist(self):
        """app/ was removed in B1 — must not be recreated."""
        assert not os.path.isdir("app"), "app/ directory should not exist (removed in B1)"

    def test_domain_directory_does_not_exist(self):
        """domain/ was removed in B1 — must not be recreated."""
        assert not os.path.isdir("domain"), "domain/ directory should not exist (removed in B1)"


class TestNoDeprecatedAutonomous:
    """Verify deprecated autonomous.py stays removed."""

    def test_autonomous_py_does_not_exist(self):
        """tools/autonomous.py was removed in C1 — must not be recreated."""
        assert not os.path.exists("tools/autonomous.py"), (
            "tools/autonomous.py should not exist (deprecated, removed in C1)"
        )

    def test_no_autonomous_imports_in_main(self):
        """main.py must not import from tools.autonomous (removed in C1)."""
        with open("main.py", "r") as f:
            content = f.read()

        assert "from tools.autonomous" not in content, (
            "main.py still imports from tools.autonomous (should use dynamic_autonomous)"
        )

    def test_no_autonomous_in_tools_init(self):
        """tools/__init__.py must not reference autonomous module (removed in C1)."""
        with open("tools/__init__.py", "r") as f:
            content = f.read()

        assert "autonomous" not in content.lower() or "dynamic_autonomous" in content.lower(), (
            "tools/__init__.py still references deprecated autonomous module"
        )
