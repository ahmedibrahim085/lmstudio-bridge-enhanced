#!/usr/bin/env python3
"""
Integration tests for multi-model support.

Tests the complete flow of model parameter through the system:
- Tool registration with model parameter
- Agent validation of model
- LLM client creation with specific model
- Error handling for invalid models
"""

import pytest
import asyncio
from unittest import mock
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools.dynamic_autonomous import DynamicAutonomousAgent
from llm.exceptions import ModelNotFoundError
from llm.model_validator import ModelValidator


class TestMultiModelIntegration:
    """Integration tests for multi-model support across all autonomous functions."""

    @pytest.mark.asyncio
    async def test_autonomous_with_mcp_specific_model(self):
        """Test autonomous_with_mcp with specific model parameter."""
        agent = DynamicAutonomousAgent()

        # Mock model validator to return valid
        with patch.object(agent.model_validator, 'validate_model', return_value=True):
            # Mock MCP operations
            with patch('tools.dynamic_autonomous.MCPDiscovery') as mock_discovery:
                with patch('tools.dynamic_autonomous.connect_to_mcp_server') as mock_connect:
                    # Mock successful MCP connection
                    mock_conn = AsyncMock()
                    mock_conn.__aenter__.return_value = mock_conn
                    mock_conn.__aexit__.return_value = None
                    mock_conn.call_tool = AsyncMock(return_value={"content": [{"type": "text", "text": "Tool result"}]})
                    mock_connect.return_value = mock_conn

                    # Mock discovery
                    mock_disc_instance = MagicMock()
                    mock_disc_instance.get_connection_params.return_value = {
                        "command": "test",
                        "args": []
                    }
                    mock_discovery.return_value = mock_disc_instance

                    # Mock LLM client
                    with patch('tools.dynamic_autonomous.LLMClient') as mock_llm_class:
                        mock_llm = AsyncMock()
                        mock_llm.chat_completion.return_value = {
                            "choices": [{
                                "message": {
                                    "content": "Task complete"
                                }
                            }]
                        }
                        mock_llm_class.return_value = mock_llm

                        # Execute with specific model
                        result = await agent.autonomous_with_mcp(
                            mcp_name="filesystem",
                            task="Test task",
                            max_rounds=2,
                            model="qwen/qwen3-coder-30b"
                        )

                        # Verify model was validated
                        agent.model_validator.validate_model.assert_called_once_with("qwen/qwen3-coder-30b")

                        # Verify LLM client was created with model
                        assert mock_llm_class.called
                        assert result is not None

    @pytest.mark.asyncio
    async def test_autonomous_without_model_uses_default(self):
        """Test that omitting model parameter uses default LLM client."""
        agent = DynamicAutonomousAgent()

        with patch('tools.dynamic_autonomous.MCPDiscovery') as mock_discovery:
            with patch('tools.dynamic_autonomous.connect_to_mcp_server') as mock_connect:
                mock_conn = AsyncMock()
                mock_conn.__aenter__.return_value = mock_conn
                mock_conn.__aexit__.return_value = None
                mock_conn.call_tool = AsyncMock(return_value={"content": [{"type": "text", "text": "Result"}]})
                mock_connect.return_value = mock_conn

                mock_disc_instance = MagicMock()
                mock_disc_instance.get_connection_params.return_value = {"command": "test", "args": []}
                mock_discovery.return_value = mock_disc_instance

                # Mock the default LLM client
                agent.llm = AsyncMock()
                agent.llm.chat_completion.return_value = {
                    "choices": [{"message": {"content": "Done"}}]
                }

                result = await agent.autonomous_with_mcp(
                    mcp_name="filesystem",
                    task="Test",
                    max_rounds=1
                    # No model parameter - should use default
                )

                # Verify validator was not called (no model to validate)
                with patch.object(agent.model_validator, 'validate_model') as mock_validate:
                    # Re-run to verify
                    await agent.autonomous_with_mcp(
                        mcp_name="filesystem",
                        task="Test",
                        max_rounds=1
                    )
                    mock_validate.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_model_returns_error(self):
        """Test that invalid model name returns clear error message."""
        agent = DynamicAutonomousAgent()

        # Mock validator to raise ModelNotFoundError
        with patch.object(agent.model_validator, 'validate_model') as mock_validate:
            mock_validate.side_effect = ModelNotFoundError(
                "nonexistent-model",
                ["model1", "model2", "model3"]
            )

            result = await agent.autonomous_with_mcp(
                mcp_name="filesystem",
                task="Test task",
                model="nonexistent-model"
            )

            # Verify error message is clear
            assert "Error" in result
            assert "not found" in result.lower()
            assert "nonexistent-model" in result

    @pytest.mark.asyncio
    async def test_multiple_mcps_with_model(self):
        """Test autonomous_with_multiple_mcps with specific model."""
        agent = DynamicAutonomousAgent()

        with patch.object(agent.model_validator, 'validate_model', return_value=True):
            with patch('tools.dynamic_autonomous.MCPDiscovery') as mock_discovery:
                with patch('tools.dynamic_autonomous.connect_to_mcp_server') as mock_connect:
                    mock_conn = AsyncMock()
                    mock_conn.__aenter__.return_value = mock_conn
                    mock_conn.__aexit__.return_value = None
                    mock_conn.call_tool = AsyncMock(return_value={"content": [{"type": "text", "text": "Result"}]})
                    mock_conn.list_tools.return_value = []
                    mock_connect.return_value = mock_conn

                    mock_disc_instance = MagicMock()
                    mock_disc_instance.get_connection_params.return_value = {"command": "test", "args": []}
                    mock_discovery.return_value = mock_disc_instance

                    with patch('tools.dynamic_autonomous.LLMClient') as mock_llm_class:
                        mock_llm = AsyncMock()
                        mock_llm.chat_completion.return_value = {
                            "choices": [{"message": {"content": "Complete"}}]
                        }
                        mock_llm_class.return_value = mock_llm

                        result = await agent.autonomous_with_multiple_mcps(
                            mcp_names=["filesystem", "memory"],
                            task="Test task",
                            max_rounds=1,
                            model="qwen/qwen3-coder-30b"
                        )

                        # Verify model was validated
                        agent.model_validator.validate_model.assert_called_with("qwen/qwen3-coder-30b")
                        assert result is not None

    @pytest.mark.asyncio
    async def test_discover_and_execute_with_model(self):
        """Test autonomous_discover_and_execute with specific model."""
        agent = DynamicAutonomousAgent()

        with patch.object(agent.model_validator, 'validate_model', return_value=True):
            with patch('tools.dynamic_autonomous.MCPDiscovery') as mock_discovery:
                with patch('tools.dynamic_autonomous.connect_to_mcp_server') as mock_connect:
                    mock_conn = AsyncMock()
                    mock_conn.__aenter__.return_value = mock_conn
                    mock_conn.__aexit__.return_value = None
                    mock_conn.call_tool = AsyncMock(return_value={"content": [{"type": "text", "text": "Result"}]})
                    mock_conn.list_tools.return_value = []
                    mock_connect.return_value = mock_conn

                    mock_disc_instance = MagicMock()
                    mock_disc_instance.get_all_enabled_mcps.return_value = ["filesystem"]
                    mock_disc_instance.get_connection_params.return_value = {"command": "test", "args": []}
                    mock_discovery.return_value = mock_disc_instance

                    with patch('tools.dynamic_autonomous.LLMClient') as mock_llm_class:
                        mock_llm = AsyncMock()
                        mock_llm.chat_completion.return_value = {
                            "choices": [{"message": {"content": "Done"}}]
                        }
                        mock_llm_class.return_value = mock_llm

                        result = await agent.autonomous_discover_and_execute(
                            task="Test",
                            max_rounds=1,
                            model="mistralai/magistral-small-2509"
                        )

                        agent.model_validator.validate_model.assert_called_with("mistralai/magistral-small-2509")
                        assert result is not None

    @pytest.mark.asyncio
    async def test_model_validation_error_handling(self):
        """Test proper error handling when model validation fails."""
        agent = DynamicAutonomousAgent()

        # Test with connection error
        with patch.object(agent.model_validator, 'validate_model') as mock_validate:
            from llm.exceptions import LLMConnectionError
            mock_validate.side_effect = LLMConnectionError("Cannot connect to LM Studio")

            result = await agent.autonomous_with_mcp(
                mcp_name="filesystem",
                task="Test",
                model="test-model"
            )

            assert "Error" in result
            assert "connect" in result.lower()

    @pytest.mark.asyncio
    async def test_backward_compatibility_no_model_param(self):
        """Test backward compatibility - works without model parameter."""
        agent = DynamicAutonomousAgent()

        with patch('tools.dynamic_autonomous.MCPDiscovery') as mock_discovery:
            with patch('tools.dynamic_autonomous.connect_to_mcp_server') as mock_connect:
                mock_conn = AsyncMock()
                mock_conn.__aenter__.return_value = mock_conn
                mock_conn.__aexit__.return_value = None
                mock_conn.call_tool = AsyncMock(return_value={"content": [{"type": "text", "text": "OK"}]})
                mock_connect.return_value = mock_conn

                mock_disc_instance = MagicMock()
                mock_disc_instance.get_connection_params.return_value = {"command": "test", "args": []}
                mock_discovery.return_value = mock_disc_instance

                agent.llm = AsyncMock()
                agent.llm.chat_completion.return_value = {
                    "choices": [{"message": {"content": "Success"}}]
                }

                # Should work without model parameter
                result = await agent.autonomous_with_mcp(
                    mcp_name="filesystem",
                    task="Test task",
                    max_rounds=1
                )

                assert result is not None


class TestModelValidatorIntegration:
    """Integration tests for ModelValidator with actual model checking."""

    @pytest.mark.asyncio
    async def test_validator_initialization(self):
        """Test ModelValidator can be initialized."""
        validator = ModelValidator()
        assert validator is not None
        assert hasattr(validator, 'validate_model')

    @pytest.mark.asyncio
    async def test_validator_with_none_model(self):
        """Test validator accepts None (uses default)."""
        validator = ModelValidator()
        result = await validator.validate_model(None)
        assert result is True  # None should always be valid (uses default)

    @pytest.mark.asyncio
    async def test_validator_with_default_string(self):
        """Test validator accepts 'default' string."""
        validator = ModelValidator()
        result = await validator.validate_model("default")
        assert result is True


def test_integration_suite_completeness():
    """Meta-test: Verify integration test coverage."""
    import inspect

    test_classes = [
        TestMultiModelIntegration,
        TestModelValidatorIntegration,
    ]

    total_tests = 0
    for test_class in test_classes:
        test_methods = [m for m in dir(test_class) if m.startswith('test_')]
        total_tests += len(test_methods)

    assert total_tests >= 10, f"Need 10+ integration tests, have {total_tests}"
    print(f"✅ Integration test suite has {total_tests} tests")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
