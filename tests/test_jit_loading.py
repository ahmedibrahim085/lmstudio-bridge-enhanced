"""
OPP-03 JIT (Just-In-Time) Model Loading -- Test Suite

Tests for:
- JIT TTL constants in config/constants.py
- temperature + ttl parameters in create_response()
- JIT guard (is_model_loaded + ensure_model_loaded_with_verification) in create_response()
- ttl parameter + JIT guard in generate_embeddings()
- Proactive preload in autonomous_with_mcp() and autonomous_with_multiple_mcps()
- temperature forwarding in _autonomous_loop and _autonomous_loop_multi_mcp

All tests are self-contained -- no LM Studio or MCP instance required.
unittest.mock is used for all external calls.
"""

import asyncio
import inspect
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root so all imports resolve
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Helpers: canonical response builders (mirrors test_opp02 pattern)
# ---------------------------------------------------------------------------

def _make_function_call_response(
    tool_name: str = "read_file",
    arguments: dict | None = None,
    response_id: str = "resp_1",
) -> dict:
    return {
        "id": response_id,
        "status": "completed",
        "output": [
            {
                "type": "function_call",
                "name": tool_name,
                "arguments": arguments or {"path": "/tmp/test.txt"},
            }
        ],
    }


def _make_message_response(
    text: str = "Task complete.",
    response_id: str = "resp_final",
) -> dict:
    return {
        "id": response_id,
        "status": "completed",
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": text}],
            }
        ],
    }


# ===========================================================================
# 1. CONSTANTS TESTS
# ===========================================================================

class TestJITTTLConstants(unittest.TestCase):
    """Verify JIT TTL constants are present and sane."""

    def test_jit_ttl_default_is_reasonable(self):
        """JIT_TTL_DEFAULT must be between 5 minutes (300s) and 1 hour (3600s)."""
        from config.constants import JIT_TTL_DEFAULT
        self.assertGreaterEqual(
            JIT_TTL_DEFAULT, 300,
            "JIT_TTL_DEFAULT should be at least 5 minutes"
        )
        self.assertLessEqual(
            JIT_TTL_DEFAULT, 3600,
            "JIT_TTL_DEFAULT should be at most 1 hour"
        )

    def test_jit_ttl_autonomous_is_longest(self):
        """JIT_TTL_AUTONOMOUS must be >= JIT_TTL_DEFAULT (long-running tasks need more time)."""
        from config.constants import JIT_TTL_AUTONOMOUS, JIT_TTL_DEFAULT
        self.assertGreaterEqual(
            JIT_TTL_AUTONOMOUS, JIT_TTL_DEFAULT,
            "JIT_TTL_AUTONOMOUS should be at least as long as JIT_TTL_DEFAULT"
        )


# ===========================================================================
# 2. create_response() TESTS
# ===========================================================================

class TestCreateResponseSignature(unittest.TestCase):
    """Verify create_response() signature has the new parameters."""

    def setUp(self):
        from llm.llm_client import LLMClient
        self.sig = inspect.signature(LLMClient.create_response)
        self.params = self.sig.parameters

    def test_create_response_accepts_temperature(self):
        """create_response() must accept a temperature parameter."""
        self.assertIn(
            "temperature", self.params,
            "create_response() is missing 'temperature' parameter"
        )

    def test_create_response_temperature_default_is_none(self):
        """temperature parameter default must be None (optional, not auto-added)."""
        param = self.params.get("temperature")
        self.assertIsNotNone(param)
        self.assertIsNone(
            param.default,
            "temperature default should be None so it's only added when explicitly set"
        )

    def test_create_response_accepts_ttl(self):
        """create_response() must accept a ttl parameter."""
        self.assertIn(
            "ttl", self.params,
            "create_response() is missing 'ttl' parameter"
        )


class TestCreateResponsePayload(unittest.TestCase):
    """Verify create_response() includes correct fields in HTTP payload."""

    def _make_client(self):
        """Create LLMClient with mocked session."""
        from llm.llm_client import LLMClient
        client = LLMClient.__new__(LLMClient)
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "resp_test",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "done"}],
                }
            ],
        }
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_response
        client.session = mock_session
        client.model = "test-model"
        client.api_base = "http://localhost:1234/v1"
        return client, mock_session

    def test_create_response_includes_temperature_in_payload(self):
        """When temperature=0.5 is passed, it must appear in the POST body."""
        client, mock_session = self._make_client()

        with patch("utils.lms_helper.LMSHelper.is_installed", return_value=False):
            client.create_response(
                input_text="hello",
                model="test-model",
                temperature=0.5
            )

        call_kwargs = mock_session.post.call_args
        payload = call_kwargs[1]["json"]  # keyword arg "json"
        self.assertIn("temperature", payload)
        self.assertAlmostEqual(payload["temperature"], 0.5)

    def test_create_response_default_temperature_when_none(self):
        """When temperature=None (default), temperature must NOT appear in payload."""
        client, mock_session = self._make_client()

        with patch("utils.lms_helper.LMSHelper.is_installed", return_value=False):
            client.create_response(
                input_text="hello",
                model="test-model"
                # temperature not passed → defaults to None
            )

        call_kwargs = mock_session.post.call_args
        payload = call_kwargs[1]["json"]
        self.assertNotIn(
            "temperature", payload,
            "temperature should NOT be in payload when not explicitly set"
        )

    def test_create_response_includes_ttl_in_payload(self):
        """ttl must always appear in the POST body."""
        client, mock_session = self._make_client()

        with patch("utils.lms_helper.LMSHelper.is_installed", return_value=False):
            client.create_response(
                input_text="hello",
                model="test-model",
                ttl=999
            )

        call_kwargs = mock_session.post.call_args
        payload = call_kwargs[1]["json"]
        self.assertIn("ttl", payload)
        self.assertEqual(payload["ttl"], 999)

    def test_create_response_default_ttl_when_none(self):
        """When ttl is not specified, JIT_TTL_DEFAULT must be used in payload."""
        from config.constants import JIT_TTL_DEFAULT
        client, mock_session = self._make_client()

        with patch("utils.lms_helper.LMSHelper.is_installed", return_value=False):
            client.create_response(
                input_text="hello",
                model="test-model"
            )

        call_kwargs = mock_session.post.call_args
        payload = call_kwargs[1]["json"]
        self.assertIn("ttl", payload)
        self.assertEqual(
            payload["ttl"], JIT_TTL_DEFAULT,
            f"Expected JIT_TTL_DEFAULT={JIT_TTL_DEFAULT} but got {payload.get('ttl')}"
        )


class TestCreateResponseJITGuard(unittest.TestCase):
    """Verify the JIT guard in create_response() calls LMSHelper correctly."""

    def _make_client(self):
        from llm.llm_client import LLMClient
        client = LLMClient.__new__(LLMClient)
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "resp_test",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "done"}],
                }
            ],
        }
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_response
        client.session = mock_session
        client.model = "test-model"
        client.api_base = "http://localhost:1234/v1"
        return client

    def test_create_response_triggers_load_when_not_loaded(self):
        """When is_model_loaded returns False, ensure_model_loaded_with_verification must be called."""
        client = self._make_client()

        with patch("utils.lms_helper.LMSHelper.is_installed", return_value=True), \
             patch("utils.lms_helper.LMSHelper.is_model_loaded", return_value=False) as mock_check, \
             patch("utils.lms_helper.LMSHelper.ensure_model_loaded_with_verification", return_value=True) as mock_load:

            client.create_response(input_text="hello", model="test-model")

            mock_check.assert_called_once_with("test-model")
            mock_load.assert_called_once()

    def test_create_response_skips_load_when_loaded(self):
        """When is_model_loaded returns True, ensure_model_loaded_with_verification must NOT be called."""
        client = self._make_client()

        with patch("utils.lms_helper.LMSHelper.is_installed", return_value=True), \
             patch("utils.lms_helper.LMSHelper.is_model_loaded", return_value=True), \
             patch("utils.lms_helper.LMSHelper.ensure_model_loaded_with_verification") as mock_load:

            client.create_response(input_text="hello", model="test-model")

            mock_load.assert_not_called()


# ===========================================================================
# 3. generate_embeddings() TESTS
# ===========================================================================

class TestGenerateEmbeddingsJIT(unittest.TestCase):
    """Verify generate_embeddings() has ttl parameter and JIT guard."""

    def _make_client(self):
        from llm.llm_client import LLMClient
        client = LLMClient.__new__(LLMClient)
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"embedding": [0.1, 0.2]}]}
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_response
        client.session = mock_session
        client.model = "embed-model"
        client.api_base = "http://localhost:1234/v1"
        return client, mock_session

    def test_generate_embeddings_includes_ttl(self):
        """ttl must appear in the embeddings POST body."""
        from config.constants import JIT_TTL_EMBEDDING
        client, mock_session = self._make_client()

        with patch("utils.lms_helper.LMSHelper.is_installed", return_value=False):
            client.generate_embeddings(text="test text", model="embed-model")

        call_kwargs = mock_session.post.call_args
        payload = call_kwargs[1]["json"]
        self.assertIn("ttl", payload)
        # When not specified, should use JIT_TTL_EMBEDDING
        self.assertEqual(
            payload["ttl"], JIT_TTL_EMBEDDING,
            f"Expected JIT_TTL_EMBEDDING={JIT_TTL_EMBEDDING} but got {payload.get('ttl')}"
        )

    def test_generate_embeddings_triggers_load(self):
        """JIT guard: when model not loaded, ensure_model_loaded_with_verification is called."""
        client, mock_session = self._make_client()

        with patch("utils.lms_helper.LMSHelper.is_installed", return_value=True), \
             patch("utils.lms_helper.LMSHelper.is_model_loaded", return_value=False) as mock_check, \
             patch("utils.lms_helper.LMSHelper.ensure_model_loaded_with_verification", return_value=True) as mock_load:

            client.generate_embeddings(text="hello", model="embed-model")

            mock_check.assert_called_once_with("embed-model")
            mock_load.assert_called_once()


# ===========================================================================
# 4. AUTONOMOUS ENTRY METHOD TESTS
# ===========================================================================

class TestAutonomousPreload(unittest.TestCase):
    """Verify proactive preload in autonomous_with_mcp and autonomous_with_multiple_mcps."""

    def _make_agent(self):
        """Create DynamicAutonomousAgent with mocked LLM and loop."""
        from llm.llm_client import LLMClient
        from llm.model_validator import ModelValidator
        from tools.dynamic_autonomous import DynamicAutonomousAgent

        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.model = "test-model"
        mock_llm.get_default_max_tokens.return_value = 8192

        mock_validator = MagicMock(spec=ModelValidator)
        mock_validator.validate_model = AsyncMock()

        agent = DynamicAutonomousAgent.__new__(DynamicAutonomousAgent)
        agent.llm = mock_llm
        agent.model_validator = mock_validator
        agent.mcp_json_path = None
        return agent

    def test_autonomous_with_mcp_triggers_preload(self):
        """autonomous_with_mcp must call LMSHelper.ensure_model_loaded before executing."""
        agent = self._make_agent()

        # Mock the entire execution so we never need a real MCP
        with patch("utils.lms_helper.LMSHelper.is_installed", return_value=True), \
             patch("utils.lms_helper.LMSHelper.ensure_model_loaded", return_value=True) as mock_preload, \
             patch.object(agent, "_autonomous_loop", new_callable=AsyncMock,
                          return_value="done"), \
             patch("tools.dynamic_autonomous.MCPDiscovery") as mock_discovery_cls, \
             patch("tools.dynamic_autonomous.stdio_client"), \
             patch("tools.dynamic_autonomous.ClientSession"):

            # Configure mock discovery to raise so we don't need a real MCP
            mock_discovery = MagicMock()
            mock_discovery.get_connection_params.side_effect = ValueError("No MCP config needed for test")
            mock_discovery_cls.return_value = mock_discovery

            asyncio.get_event_loop().run_until_complete(
                agent.autonomous_with_mcp(
                    mcp_name="filesystem",
                    task="Test preload"
                )
            )

        mock_preload.assert_called_once()

    def test_autonomous_with_multiple_mcps_triggers_preload(self):
        """autonomous_with_multiple_mcps must call LMSHelper.ensure_model_loaded before executing."""
        agent = self._make_agent()

        with patch("utils.lms_helper.LMSHelper.is_installed", return_value=True), \
             patch("utils.lms_helper.LMSHelper.ensure_model_loaded", return_value=True) as mock_preload, \
             patch.object(agent, "_autonomous_loop_multi_mcp", new_callable=AsyncMock,
                          return_value="done"), \
             patch("tools.dynamic_autonomous.MCPDiscovery") as mock_discovery_cls:

            mock_discovery = MagicMock()
            mock_discovery.validate_mcp_names.side_effect = ValueError("No MCP config needed for test")
            mock_discovery_cls.return_value = mock_discovery

            asyncio.get_event_loop().run_until_complete(
                agent.autonomous_with_multiple_mcps(
                    mcp_names=["filesystem", "memory"],
                    task="Test preload multi"
                )
            )

        mock_preload.assert_called_once()


# ===========================================================================
# 5. AUTONOMOUS LOOP TEMPERATURE FORWARDING TEST
# ===========================================================================

class TestAutonomousLoopTemperature(unittest.TestCase):
    """Verify _autonomous_loop passes temperature to create_response."""

    def _make_agent_with_response(self, responses):
        """Create agent whose llm.create_response returns responses in order."""
        from llm.llm_client import LLMClient
        from llm.model_validator import ModelValidator
        from tools.dynamic_autonomous import DynamicAutonomousAgent

        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.model = "test-model"
        mock_llm.create_response = MagicMock(side_effect=responses)

        mock_validator = MagicMock(spec=ModelValidator)
        mock_validator.validate_model = AsyncMock()

        agent = DynamicAutonomousAgent.__new__(DynamicAutonomousAgent)
        agent.llm = mock_llm
        agent.model_validator = mock_validator
        agent.mcp_json_path = None
        return agent, mock_llm

    def test_autonomous_loop_passes_temperature(self):
        """_autonomous_loop must forward temperature to create_response call."""
        from config.constants import DEFAULT_TEMPERATURE

        agent, mock_llm = self._make_agent_with_response(
            [_make_message_response("Task complete.")]
        )

        # Mock session
        mock_session = AsyncMock()

        asyncio.get_event_loop().run_until_complete(
            agent._autonomous_loop(
                session=mock_session,
                openai_tools=[],
                task="test task",
                max_rounds=5,
                max_tokens=8192,
                model="test-model"
            )
        )

        # Verify create_response was called with temperature
        self.assertTrue(mock_llm.create_response.called)
        call_kwargs = mock_llm.create_response.call_args
        # Check keyword args
        kwargs = call_kwargs[1] if call_kwargs[1] else {}
        self.assertIn(
            "temperature", kwargs,
            "create_response must be called with temperature= keyword argument"
        )
        self.assertAlmostEqual(
            kwargs["temperature"], DEFAULT_TEMPERATURE,
            msg=f"temperature should be DEFAULT_TEMPERATURE={DEFAULT_TEMPERATURE}"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
