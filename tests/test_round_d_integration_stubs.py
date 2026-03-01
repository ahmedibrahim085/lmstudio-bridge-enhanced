#!/usr/bin/env python3
"""Integration test stubs for Round D API surface changes.

These tests require a running LM Studio instance and are skipped by default.
Run with: pytest -m integration --run-integration

Each stub documents the manual verification needed for new Round D methods.
"""
import pytest

SKIP_REASON = "requires running LM Studio instance"


@pytest.mark.integration
class TestOPP22Integration:
    """Integration stubs for OPP-22: Single-Model Lookup."""

    @pytest.mark.skip(reason=SKIP_REASON)
    def test_get_model_returns_real_model(self):
        """LMSRestClient.get_model() returns a real model dict from LM Studio."""

    @pytest.mark.skip(reason=SKIP_REASON)
    def test_get_model_not_found_returns_none(self):
        """LMSRestClient.get_model('nonexistent') returns None against live API."""

    @pytest.mark.skip(reason=SKIP_REASON)
    def test_is_model_loaded_reflects_actual_state(self):
        """is_model_loaded() matches LM Studio's actual loaded model state."""


@pytest.mark.integration
class TestOPP23Integration:
    """Integration stubs for OPP-23: Streaming Usage Tracking."""

    @pytest.mark.skip(reason=SKIP_REASON)
    def test_stream_usage_from_live_stream(self):
        """parse_sse_stream_with_usage() captures real usage from LM Studio stream."""

    @pytest.mark.skip(reason=SKIP_REASON)
    def test_stream_usage_token_counts_nonzero(self):
        """StreamUsage from live stream has nonzero prompt and completion tokens."""


@pytest.mark.integration
class TestOPP26Integration:
    """Integration stubs for OPP-26: Advanced Sampling Parameters."""

    @pytest.mark.skip(reason=SKIP_REASON)
    def test_min_p_affects_generation(self):
        """chat_completion with min_p=0.01 vs min_p=0.99 produces different outputs."""

    @pytest.mark.skip(reason=SKIP_REASON)
    def test_top_k_affects_generation(self):
        """chat_completion with top_k=1 vs top_k=100 produces different outputs."""

    @pytest.mark.skip(reason=SKIP_REASON)
    def test_sampling_params_accepted_by_server(self):
        """LM Studio accepts min_p and top_k without HTTP 400 errors."""


@pytest.mark.integration
class TestOPP30Integration:
    """Integration stubs for OPP-30: Echo Load Config."""

    @pytest.mark.skip(reason=SKIP_REASON)
    def test_load_model_returns_config(self):
        """load_model() returns config dict with gpu_offload and context_length."""

    @pytest.mark.skip(reason=SKIP_REASON)
    def test_config_matches_lm_studio_settings(self):
        """Echoed config matches what LM Studio UI shows for loaded model."""
