#!/usr/bin/env python3
"""Tests for hardcoded value extraction to config/constants.py.

Verifies that magic numbers previously scattered across production code
are now defined as named constants and imported where used.
"""
import pytest


# ---------------------------------------------------------------------------
# New constants exist with expected values
# ---------------------------------------------------------------------------

class TestNewConstantsExist:
    """New constants must be defined in config/constants.py."""

    def test_llm_pool_connections(self):
        from config.constants import LLM_POOL_CONNECTIONS
        assert LLM_POOL_CONNECTIONS == 10

    def test_llm_pool_maxsize(self):
        from config.constants import LLM_POOL_MAXSIZE
        assert LLM_POOL_MAXSIZE == 20

    def test_image_pool_connections(self):
        from config.constants import IMAGE_POOL_CONNECTIONS
        assert IMAGE_POOL_CONNECTIONS == 5

    def test_image_pool_maxsize(self):
        from config.constants import IMAGE_POOL_MAXSIZE
        assert IMAGE_POOL_MAXSIZE == 10

    def test_http_retry_total(self):
        from config.constants import HTTP_RETRY_TOTAL
        assert HTTP_RETRY_TOTAL == 3

    def test_http_retry_backoff_factor(self):
        from config.constants import HTTP_RETRY_BACKOFF_FACTOR
        assert HTTP_RETRY_BACKOFF_FACTOR == 0.3

    def test_image_download_timeout(self):
        from config.constants import IMAGE_DOWNLOAD_TIMEOUT
        assert IMAGE_DOWNLOAD_TIMEOUT == 30

    def test_lms_cli_check_timeout(self):
        from config.constants import LMS_CLI_CHECK_TIMEOUT
        assert LMS_CLI_CHECK_TIMEOUT == 5

    def test_lms_cli_load_timeout(self):
        from config.constants import LMS_CLI_LOAD_TIMEOUT
        assert LMS_CLI_LOAD_TIMEOUT == 60

    def test_lms_cli_unload_timeout(self):
        from config.constants import LMS_CLI_UNLOAD_TIMEOUT
        assert LMS_CLI_UNLOAD_TIMEOUT == 30

    def test_lms_cli_default_timeout(self):
        from config.constants import LMS_CLI_DEFAULT_TIMEOUT
        assert LMS_CLI_DEFAULT_TIMEOUT == 30

    def test_lms_cli_ps_timeout(self):
        from config.constants import LMS_CLI_PS_TIMEOUT
        assert LMS_CLI_PS_TIMEOUT == 10


# ---------------------------------------------------------------------------
# Production code uses constants instead of hardcoded values
# ---------------------------------------------------------------------------

class TestConstantsUsedInCode:
    """Verify production modules import and use the extracted constants."""

    def test_model_validator_uses_model_list_timeout(self):
        """model_validator.py must use MODEL_LIST_TIMEOUT, not hardcoded 10.0."""
        import inspect
        from llm.model_validator import ModelValidator
        source = inspect.getsource(ModelValidator._fetch_models)
        assert "MODEL_LIST_TIMEOUT" in source
        assert "timeout=10.0" not in source

    def test_model_validator_uses_retry_constants(self):
        """model_validator.py must use DEFAULT_MAX_RETRIES and DEFAULT_RETRY_BASE_DELAY."""
        import inspect
        from llm.model_validator import ModelValidator
        source = inspect.getsource(ModelValidator._fetch_models)
        # The decorator is applied to the method - check module source
        import llm.model_validator as mod
        mod_source = inspect.getsource(mod)
        assert "DEFAULT_MAX_RETRIES" in mod_source
        assert "DEFAULT_RETRY_BASE_DELAY" in mod_source

    def test_image_utils_uses_pool_constants(self):
        """image_utils.py must use IMAGE_POOL_* and HTTP_RETRY_* constants."""
        import inspect
        import utils.image_utils as mod
        source = inspect.getsource(mod)
        assert "IMAGE_POOL_CONNECTIONS" in source
        assert "IMAGE_POOL_MAXSIZE" in source
        assert "HTTP_RETRY_TOTAL" in source
        assert "HTTP_RETRY_BACKOFF_FACTOR" in source

    def test_image_utils_uses_download_timeout(self):
        """image_utils.py must use IMAGE_DOWNLOAD_TIMEOUT, not hardcoded 30."""
        import inspect
        import utils.image_utils as mod
        source = inspect.getsource(mod._process_url)
        assert "IMAGE_DOWNLOAD_TIMEOUT" in source
        assert "timeout=30" not in source

    def test_llm_client_uses_pool_constants(self):
        """llm_client.py must use LLM_POOL_* and HTTP_RETRY_* constants."""
        import inspect
        import llm.llm_client as mod
        source = inspect.getsource(mod)
        assert "LLM_POOL_CONNECTIONS" in source
        assert "LLM_POOL_MAXSIZE" in source
        assert "HTTP_RETRY_TOTAL" in source
        assert "HTTP_RETRY_BACKOFF_FACTOR" in source

    def test_lms_helper_uses_cli_timeouts(self):
        """lms_helper.py must use LMS_CLI_* timeout constants."""
        import inspect
        import utils.lms_helper as mod
        source = inspect.getsource(mod)
        assert "LMS_CLI_CHECK_TIMEOUT" in source
        assert "LMS_CLI_LOAD_TIMEOUT" in source
        assert "LMS_CLI_UNLOAD_TIMEOUT" in source
        assert "LMS_CLI_PS_TIMEOUT" in source
