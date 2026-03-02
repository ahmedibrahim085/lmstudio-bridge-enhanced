"""Tests for version consistency across project files."""

import re


class TestVersionConsistency:
    """Verify version strings are in sync across the project."""

    def test_constants_version_matches_setup_version(self):
        """VERSION in config/constants/version.py must match version in setup.py."""
        # Read config/constants/version.py
        with open("config/constants/version.py", "r") as f:
            constants_content = f.read()

        # Read setup.py
        with open("setup.py", "r") as f:
            setup_content = f.read()

        # Extract VERSION from version.py (must be at start of line)
        const_match = re.search(r'^VERSION\s*=\s*["\']([^"\']+)["\']', constants_content, re.MULTILINE)
        assert const_match, "Could not find VERSION in config/constants/version.py"
        const_version = const_match.group(1)

        # Extract version from setup.py
        setup_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', setup_content)
        assert setup_match, "Could not find version in setup.py"
        setup_version = setup_match.group(1)

        assert const_version == setup_version, (
            f"Version mismatch: config/constants/version.py has '{const_version}' "
            f"but setup.py has '{setup_version}'"
        )

    def test_python_requires_matches_constants(self):
        """python_requires in setup.py must match MIN_PYTHON_VERSION in constants/version.py."""
        with open("config/constants/version.py", "r") as f:
            constants_content = f.read()

        with open("setup.py", "r") as f:
            setup_content = f.read()

        const_match = re.search(r'^MIN_PYTHON_VERSION\s*=\s*["\']([^"\']+)["\']', constants_content, re.MULTILINE)
        assert const_match, "Could not find MIN_PYTHON_VERSION in config/constants/version.py"

        setup_match = re.search(r'python_requires\s*=\s*["\']>=([^"\']+)["\']', setup_content)
        assert setup_match, "Could not find python_requires in setup.py"

        assert const_match.group(1) == setup_match.group(1), (
            f"Python version mismatch: constants has '{const_match.group(1)}' "
            f"but setup.py requires '>={setup_match.group(1)}'"
        )
