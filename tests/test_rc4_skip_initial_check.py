"""
RC-4 Skip Initial Check -- Test Suite

Tests that _ensure_model_loaded() in LLMClient passes skip_initial_check=True
to ensure_model_loaded_with_verification(), eliminating the redundant GET #2.

Call chain (before fix):
    _ensure_model_loaded()
      -> LMSHelper.is_model_loaded()                        # GET #1
      -> returns False
      -> LMSHelper.ensure_model_loaded_with_verification()
           -> LMSHelper.is_model_loaded()                   # GET #2 (REDUNDANT)
           -> LMSHelper.load_model()                        # POST (necessary)
           -> LMSHelper.verify_model_loaded()               # GET #3 (necessary)

Fix: pass skip_initial_check=True from _ensure_model_loaded() so GET #2 is skipped.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add project root so all imports resolve
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestEnsureModelLoadedSkipsRedundantCheck(unittest.TestCase):
    """Verify _ensure_model_loaded passes skip_initial_check=True."""

    def _make_client(self, model: str = "test-model") -> object:
        """Create an LLMClient instance without triggering real HTTP."""
        from llm.llm_client import LLMClient
        client = LLMClient.__new__(LLMClient)
        client.model = model
        client.api_base = "http://localhost:1234/v1"
        client.session = MagicMock()
        return client

    def test_skip_initial_check_passed_when_model_not_loaded(self):
        """
        When is_model_loaded() returns False, _ensure_model_loaded() MUST call
        ensure_model_loaded_with_verification(..., skip_initial_check=True).

        RED: fails because skip_initial_check parameter does not exist yet.
        """
        client = self._make_client()

        with (
            patch("utils.lms_helper.LMSHelper.is_installed", return_value=True),
            patch("utils.lms_helper.LMSHelper.is_model_loaded", return_value=False) as mock_is_loaded,
            patch(
                "utils.lms_helper.LMSHelper.ensure_model_loaded_with_verification",
                return_value=True,
            ) as mock_ensure,
        ):
            client._ensure_model_loaded("test-model", ttl=600)

        # is_model_loaded should have been called once (the guard in _ensure_model_loaded)
        mock_is_loaded.assert_called_once_with("test-model")

        # ensure_model_loaded_with_verification must be called with skip_initial_check=True
        mock_ensure.assert_called_once()
        call_kwargs = mock_ensure.call_args
        self.assertIn(
            "skip_initial_check",
            call_kwargs.kwargs,
            "ensure_model_loaded_with_verification() was NOT called with skip_initial_check kwarg",
        )
        self.assertTrue(
            call_kwargs.kwargs["skip_initial_check"],
            "skip_initial_check must be True to suppress the redundant GET",
        )

    def test_ttl_forwarded_alongside_skip_initial_check(self):
        """
        The ttl argument must still be forwarded correctly when skip_initial_check=True.
        """
        client = self._make_client()

        with (
            patch("utils.lms_helper.LMSHelper.is_installed", return_value=True),
            patch("utils.lms_helper.LMSHelper.is_model_loaded", return_value=False),
            patch(
                "utils.lms_helper.LMSHelper.ensure_model_loaded_with_verification",
                return_value=True,
            ) as mock_ensure,
        ):
            client._ensure_model_loaded("test-model", ttl=600)

        call_kwargs = mock_ensure.call_args
        self.assertEqual(
            call_kwargs.kwargs.get("ttl"),
            600,
            "ttl must still be forwarded when skip_initial_check=True",
        )

    def test_no_call_to_ensure_when_model_already_loaded(self):
        """
        When is_model_loaded() returns True, ensure_model_loaded_with_verification
        must NOT be called at all.
        """
        client = self._make_client()

        with (
            patch("utils.lms_helper.LMSHelper.is_installed", return_value=True),
            patch("utils.lms_helper.LMSHelper.is_model_loaded", return_value=True),
            patch(
                "utils.lms_helper.LMSHelper.ensure_model_loaded_with_verification",
            ) as mock_ensure,
        ):
            client._ensure_model_loaded("test-model", ttl=600)

        mock_ensure.assert_not_called()


class TestEnsureModelLoadedWithVerificationSignature(unittest.TestCase):
    """Verify ensure_model_loaded_with_verification accepts skip_initial_check."""

    def test_signature_has_skip_initial_check(self):
        """
        ensure_model_loaded_with_verification() must have a skip_initial_check parameter
        with a default of False.

        RED: fails because the parameter doesn't exist yet.
        """
        import inspect
        from utils.lms_helper import LMSHelper

        sig = inspect.signature(LMSHelper.ensure_model_loaded_with_verification)
        params = sig.parameters

        self.assertIn(
            "skip_initial_check",
            params,
            "ensure_model_loaded_with_verification() is missing 'skip_initial_check' parameter",
        )
        self.assertIs(
            params["skip_initial_check"].default,
            False,
            "skip_initial_check default must be False (backward-compatible)",
        )

    def test_skip_initial_check_suppresses_redundant_get(self):
        """
        When skip_initial_check=True, the is_model_loaded() call inside
        ensure_model_loaded_with_verification() must be bypassed.

        RED: fails because the guard doesn't exist yet.
        """
        from utils.lms_helper import LMSHelper

        with (
            patch.object(LMSHelper, "is_model_loaded", return_value=False) as mock_loaded,
            patch.object(LMSHelper, "load_model", return_value=True),
            patch.object(LMSHelper, "verify_model_loaded", return_value=True),
            patch("utils.lms_helper.time.sleep"),
        ):
            result = LMSHelper.ensure_model_loaded_with_verification(
                "test-model", ttl=600, skip_initial_check=True
            )

        self.assertTrue(result)
        # is_model_loaded must NOT have been called (it was skipped)
        mock_loaded.assert_not_called()

    def test_skip_false_still_calls_is_model_loaded(self):
        """
        When skip_initial_check=False (default), is_model_loaded() IS called as before.
        This is the backward-compatibility check.
        """
        from utils.lms_helper import LMSHelper

        with (
            patch.object(LMSHelper, "is_model_loaded", return_value=True) as mock_loaded,
        ):
            result = LMSHelper.ensure_model_loaded_with_verification(
                "test-model", skip_initial_check=False
            )

        self.assertTrue(result)
        mock_loaded.assert_called_once_with("test-model")


if __name__ == "__main__":
    unittest.main()
