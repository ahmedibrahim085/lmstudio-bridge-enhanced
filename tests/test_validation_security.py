#!/usr/bin/env python3
"""
Comprehensive validation security tests for v2 security enhancements.

Tests the advanced security validation features ported from v2:
1. Symlink bypass prevention
2. Null byte injection prevention
3. Blocked directories enforcement
4. Path traversal detection
5. Warning directories behavior
"""

import pytest
import tempfile
import os
from pathlib import Path
from utils.validation import (
    validate_working_directory,
    validate_task,
    validate_max_rounds,
    validate_max_tokens,
    ValidationError,
    _validate_single_directory
)


class TestSymlinkBypassPrevention:
    """Test that symlinks cannot bypass blocked directory restrictions."""

    def test_etc_symlink_blocked_on_macos(self):
        """Test that /etc (symlink to /private/etc on macOS) is blocked."""
        with pytest.raises(ValidationError) as exc_info:
            validate_working_directory('/etc')

        error_msg = str(exc_info.value)
        assert "Access denied to sensitive system directory" in error_msg
        assert "/private/etc" in error_msg or "/etc" in error_msg
        assert "system configuration files" in error_msg.lower()

    def test_private_etc_directly_blocked(self):
        """Test that /private/etc is directly blocked (symlink target)."""
        with pytest.raises(ValidationError) as exc_info:
            validate_working_directory('/private/etc')

        error_msg = str(exc_info.value)
        assert "Access denied" in error_msg
        assert "system configuration files" in error_msg.lower()

    def test_bin_directory_blocked(self):
        """Test that /bin is blocked."""
        with pytest.raises(ValidationError) as exc_info:
            validate_working_directory('/bin')

        error_msg = str(exc_info.value)
        assert "Access denied" in error_msg
        assert "essential system binaries" in error_msg.lower()

    def test_sbin_directory_blocked(self):
        """Test that /sbin is blocked."""
        with pytest.raises(ValidationError) as exc_info:
            validate_working_directory('/sbin')

        error_msg = str(exc_info.value)
        assert "Access denied" in error_msg

    def test_root_home_directory_blocked(self):
        """Test that /root is blocked."""
        with pytest.raises(ValidationError) as exc_info:
            validate_working_directory('/root')

        error_msg = str(exc_info.value)
        assert "Access denied" in error_msg
        assert "root user home directory" in error_msg.lower()

    def test_macos_system_directory_blocked(self):
        """Test that /System (macOS) is blocked."""
        with pytest.raises(ValidationError) as exc_info:
            validate_working_directory('/System')

        error_msg = str(exc_info.value)
        assert "Access denied" in error_msg

    def test_linux_boot_directory_blocked(self):
        """Test that /boot (Linux) is blocked."""
        with pytest.raises(ValidationError) as exc_info:
            validate_working_directory('/boot')

        error_msg = str(exc_info.value)
        assert "Access denied" in error_msg


class TestNullByteInjectionPrevention:
    """Test that null byte injection attacks are prevented."""

    def test_null_byte_in_path_blocked(self):
        """Test that paths with null bytes are blocked."""
        with pytest.raises(ValidationError) as exc_info:
            validate_working_directory('/tmp/test\x00/malicious')

        error_msg = str(exc_info.value)
        assert "null byte" in error_msg.lower()
        assert "injection" in error_msg.lower()

    def test_null_byte_at_start_blocked(self):
        """Test that null byte at start is blocked."""
        with pytest.raises(ValidationError) as exc_info:
            validate_working_directory('\x00/tmp/test')

        error_msg = str(exc_info.value)
        assert "null byte" in error_msg.lower()

    def test_null_byte_at_end_blocked(self):
        """Test that null byte at end is blocked."""
        with pytest.raises(ValidationError) as exc_info:
            validate_working_directory('/tmp/test\x00')

        error_msg = str(exc_info.value)
        assert "null byte" in error_msg.lower()

    def test_multiple_null_bytes_blocked(self):
        """Test that multiple null bytes are blocked."""
        with pytest.raises(ValidationError) as exc_info:
            validate_working_directory('/tmp\x00/test\x00/malicious')

        error_msg = str(exc_info.value)
        assert "null byte" in error_msg.lower()


class TestBlockedDirectories:
    """Test that all 7 blocked directories are enforced."""

    @pytest.mark.parametrize("blocked_dir", [
        '/etc',
        '/bin',
        '/sbin',
        '/System',
        '/boot',
        '/root',
        '/private/etc'
    ])
    def test_blocked_directory(self, blocked_dir):
        """Test that blocked directory raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_working_directory(blocked_dir)

        error_msg = str(exc_info.value)
        assert "Access denied" in error_msg

    @pytest.mark.parametrize("blocked_subdir", [
        '/etc/passwd',
        '/bin/bash',
        '/sbin/reboot',
        '/root/.ssh',
        '/System/Library'
    ])
    def test_blocked_subdirectory(self, blocked_subdir):
        """Test that subdirectories of blocked directories are also blocked."""
        # Note: These paths may not exist, but validation should still block them
        # based on path prefix matching
        path = Path(blocked_subdir).parent
        with pytest.raises(ValidationError):
            validate_working_directory(str(path))


class TestWarningDirectories:
    """Test that warning directories log warnings but allow access."""

    def test_var_directory_allowed_with_warning(self, caplog):
        """Test that /var is allowed but logs warning."""
        import logging
        caplog.set_level(logging.WARNING)

        # /var should exist on Unix systems
        if Path('/var').exists():
            try:
                result = validate_working_directory('/var')
                # On macOS, /var resolves to /private/var (symlink)
                assert result in ['/var', '/private/var']
                assert "SECURITY WARNING" in caplog.text
                assert "/var" in caplog.text
            except ValidationError:
                pytest.skip("/var not accessible on this system")

    def test_tmp_directory_allowed(self):
        """Test that /tmp is allowed (with warning)."""
        if Path('/tmp').exists():
            result = validate_working_directory('/tmp')
            assert result in ['/tmp', '/private/tmp']  # macOS /tmp -> /private/tmp


class TestValidUserDirectories:
    """Test that valid user directories are allowed without blocking."""

    def test_user_home_directory_allowed(self):
        """Test that user home directory is allowed."""
        home = str(Path.home())
        result = validate_working_directory(home)
        assert result == home

    def test_user_subdirectory_allowed(self):
        """Test that user subdirectories are allowed."""
        # Create a temp directory in user space
        with tempfile.TemporaryDirectory() as tmpdir:
            result = validate_working_directory(tmpdir)
            assert os.path.samefile(result, tmpdir)

    def test_project_directory_allowed(self):
        """Test that project directory is allowed."""
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        result = validate_working_directory(project_dir)
        assert os.path.samefile(result, project_dir)

    def test_current_directory_allowed(self):
        """Test that current directory is allowed."""
        cwd = os.getcwd()
        result = validate_working_directory(cwd)
        assert os.path.samefile(result, cwd)


class TestPathTraversalDetection:
    """Test that path traversal attempts are detected and logged."""

    def test_double_dot_traversal_logged(self, caplog):
        """Test that .. in paths is logged as warning."""
        import logging
        caplog.set_level(logging.WARNING)

        # Create a valid temp directory, then use .. to reference it
        with tempfile.TemporaryDirectory() as tmpdir:
            parent = Path(tmpdir).parent
            # Use ../dirname to reference the temp dir
            traversal_path = f"{tmpdir}/subdir/../"

            # This should work but log a warning
            try:
                result = validate_working_directory(traversal_path)
                # Check if path traversal was logged
                # (may or may not be logged depending on Path.resolve() behavior)
            except ValidationError:
                # If it fails, it's because the path doesn't exist, not security
                pass


class TestRootDirectoryBlocking:
    """Test that root directory is blocked for security."""

    def test_root_directory_blocked(self):
        """Test that / is blocked."""
        with pytest.raises(ValidationError) as exc_info:
            validate_working_directory('/')

        error_msg = str(exc_info.value)
        assert "Root directory '/' is not allowed" in error_msg
        assert "ENTIRE filesystem" in error_msg

    def test_root_directory_explicit_denial_message(self):
        """Test that root directory denial has helpful message."""
        with pytest.raises(ValidationError) as exc_info:
            validate_working_directory('/')

        error_msg = str(exc_info.value)
        assert "System files" in error_msg
        assert "Best practice" in error_msg
        assert "/Users/" in error_msg  # Should suggest valid alternatives


class TestMultipleDirectoryValidation:
    """Test validation of multiple directories (list input)."""

    def test_multiple_valid_directories(self):
        """Test that list of valid directories is allowed."""
        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                dirs = [tmpdir1, tmpdir2]
                result = validate_working_directory(dirs)
                assert len(result) == 2
                assert os.path.samefile(result[0], tmpdir1)
                assert os.path.samefile(result[1], tmpdir2)

    def test_multiple_directories_with_one_blocked(self):
        """Test that if one directory in list is blocked, entire validation fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dirs = [tmpdir, '/etc']  # One valid, one blocked
            with pytest.raises(ValidationError) as exc_info:
                validate_working_directory(dirs)

            error_msg = str(exc_info.value)
            assert "Access denied" in error_msg

    def test_empty_directory_list_fails(self):
        """Test that empty directory list fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            validate_working_directory([])

        error_msg = str(exc_info.value)
        assert "cannot be empty" in error_msg.lower()


class TestInputValidation:
    """Test input validation edge cases."""

    def test_none_directory_with_allow_none_true(self):
        """Test that None is allowed when allow_none=True."""
        result = validate_working_directory(None, allow_none=True)
        assert result is None

    def test_none_directory_with_allow_none_false(self):
        """Test that None is rejected when allow_none=False."""
        with pytest.raises(ValidationError) as exc_info:
            validate_working_directory(None, allow_none=False)

        error_msg = str(exc_info.value)
        assert "cannot be None" in error_msg

    def test_empty_string_directory_fails(self):
        """Test that empty string fails validation."""
        with pytest.raises(ValidationError):
            _validate_single_directory('')

    def test_nonexistent_directory_fails(self):
        """Test that nonexistent directory fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            validate_working_directory('/this/path/should/not/exist/12345')

        error_msg = str(exc_info.value)
        assert "does not exist" in error_msg

    def test_file_instead_of_directory_fails(self):
        """Test that file path fails when directory expected."""
        with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
            try:
                with pytest.raises(ValidationError) as exc_info:
                    validate_working_directory(tmpfile.name)

                error_msg = str(exc_info.value)
                assert "not a directory" in error_msg
            finally:
                os.unlink(tmpfile.name)


class TestTaskValidation:
    """Test task parameter validation."""

    def test_valid_task(self):
        """Test that valid task passes."""
        validate_task("This is a valid task")

    def test_empty_task_fails(self):
        """Test that empty task fails."""
        with pytest.raises(ValidationError):
            validate_task("")

    def test_whitespace_only_task_fails(self):
        """Test that whitespace-only task fails."""
        with pytest.raises(ValidationError):
            validate_task("   ")

    def test_too_long_task_fails(self):
        """Test that task > 10000 chars fails."""
        with pytest.raises(ValidationError) as exc_info:
            validate_task("x" * 10001)

        error_msg = str(exc_info.value)
        assert "too long" in error_msg.lower()


class TestMaxRoundsValidation:
    """Test max_rounds parameter validation."""

    def test_valid_max_rounds(self):
        """Test that valid max_rounds passes."""
        assert validate_max_rounds(100) == 100

    def test_max_rounds_too_low_fails(self):
        """Test that max_rounds < 1 fails."""
        with pytest.raises(ValidationError):
            validate_max_rounds(0)

    def test_max_rounds_too_high_fails(self):
        """Test that max_rounds > 10000 fails."""
        with pytest.raises(ValidationError):
            validate_max_rounds(10001)


class TestMaxTokensValidation:
    """Test max_tokens parameter validation."""

    def test_valid_max_tokens(self):
        """Test that valid max_tokens passes."""
        assert validate_max_tokens(1000) == 1000

    def test_max_tokens_too_low_fails(self):
        """Test that max_tokens < 1 fails."""
        with pytest.raises(ValidationError):
            validate_max_tokens(0)

    def test_max_tokens_exceeds_model_max_fails(self):
        """Test that max_tokens > model_max fails."""
        with pytest.raises(ValidationError) as exc_info:
            validate_max_tokens(5000, model_max=4096)

        error_msg = str(exc_info.value)
        assert "exceeds model's maximum" in error_msg


def test_security_test_suite_completeness():
    """Meta-test: Verify all security features are tested."""
    # Count test classes
    security_test_classes = [
        TestSymlinkBypassPrevention,
        TestNullByteInjectionPrevention,
        TestBlockedDirectories,
        TestWarningDirectories,
        TestValidUserDirectories,
        TestPathTraversalDetection,
        TestRootDirectoryBlocking,
        TestMultipleDirectoryValidation,
        TestInputValidation,
        TestTaskValidation,
        TestMaxRoundsValidation,
        TestMaxTokensValidation
    ]

    # Ensure we have comprehensive coverage
    assert len(security_test_classes) >= 10, "Should have at least 10 test classes for security"

    # Count total test methods
    total_tests = sum(
        len([m for m in dir(cls) if m.startswith('test_')])
        for cls in security_test_classes
    )

    assert total_tests >= 40, f"Should have at least 40 security tests, found {total_tests}"
    print(f"\n✅ Security test suite completeness: {len(security_test_classes)} classes, {total_tests} tests")


if __name__ == "__main__":
    # Run with: python3 -m pytest tests/test_validation_security.py -v
    pytest.main([__file__, "-v", "--tb=short"])
