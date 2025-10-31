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
            # Mock MCP discovery
            with patch('tools.dynamic_autonomous.MCPDiscovery') as mock_discovery:
                mock_disc_instance = MagicMock()
                mock_disc_instance.get_connection_params.return_value = {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem"],
                    "env": None
                }
                mock_discovery.return_value = mock_disc_instance

                # Mock stdio_client context manager
                with patch('tools.dynamic_autonomous.stdio_client') as mock_stdio:
                    # Mock ClientSession
                    with patch('tools.dynamic_autonomous.ClientSession') as mock_session_class:
                        # Create mock session instance
                        mock_session = AsyncMock()

                        # Mock session methods
                        mock_init_result = MagicMock()
                        mock_init_result.serverInfo.name = "test-server"
                        mock_session.initialize.return_value = mock_init_result

                        # Mock tools
                        mock_tool = MagicMock()
                        mock_tool.name = "test_tool"
                        mock_tool.description = "Test tool description"
                        mock_tool.inputSchema = {"type": "object", "properties": {}}
                        mock_tools_result = MagicMock()
                        mock_tools_result.tools = [mock_tool]
                        mock_session.list_tools.return_value = mock_tools_result

                        # Mock tool call
                        mock_session.call_tool.return_value = MagicMock(
                            content=[MagicMock(type="text", text="Tool result")]
                        )

                        # Setup session context manager
                        mock_session.__aenter__.return_value = mock_session
                        mock_session.__aexit__.return_value = None
                        mock_session_class.return_value = mock_session

                        # Setup stdio_client context manager
                        mock_read = MagicMock()
                        mock_write = MagicMock()
                        mock_stdio.return_value.__aenter__.return_value = (mock_read, mock_write)
                        mock_stdio.return_value.__aexit__.return_value = None

                        # Mock the agent's LLM client directly - Use create_response API (stateful /v1/responses)
                        agent.llm = MagicMock()

                        # Mock create_response to return stateful API format
                        agent.llm.create_response.return_value = {
                            "id": "resp_test_123",
                            "output": [
                                {
                                    "type": "message",
                                    "content": [
                                        {"type": "output_text", "text": "Task complete"}
                                    ]
                                }
                            ]
                        }
                        agent.llm.get_default_max_tokens.return_value = 8192

                        # Execute with specific model
                        result = await agent.autonomous_with_mcp(
                            mcp_name="filesystem",
                            task="Test task",
                            max_rounds=2,
                            model="qwen/qwen3-coder-30b"
                        )

                        # Verify model was validated
                        agent.model_validator.validate_model.assert_called_once_with("qwen/qwen3-coder-30b")

                        # Verify result
                        assert result is not None
                        assert "Task complete" in result

    @pytest.mark.asyncio
    async def test_autonomous_without_model_uses_default(self):
        """Test that omitting model parameter uses default LLM client."""
        agent = DynamicAutonomousAgent()

        # Mock MCP discovery
        with patch('tools.dynamic_autonomous.MCPDiscovery') as mock_discovery:
            mock_disc_instance = MagicMock()
            mock_disc_instance.get_connection_params.return_value = {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem"],
                "env": None
            }
            mock_discovery.return_value = mock_disc_instance

            # Mock stdio_client and ClientSession
            with patch('tools.dynamic_autonomous.stdio_client') as mock_stdio:
                with patch('tools.dynamic_autonomous.ClientSession') as mock_session_class:
                    # Setup mock session
                    mock_session = AsyncMock()
                    mock_init_result = MagicMock()
                    mock_init_result.serverInfo.name = "test-server"
                    mock_session.initialize.return_value = mock_init_result

                    mock_tool = MagicMock()
                    mock_tool.name = "test_tool"
                    mock_tool.description = "Test tool"
                    mock_tool.inputSchema = {"type": "object", "properties": {}}
                    mock_tools_result = MagicMock()
                    mock_tools_result.tools = [mock_tool]
                    mock_session.list_tools.return_value = mock_tools_result

                    mock_session.__aenter__.return_value = mock_session
                    mock_session.__aexit__.return_value = None
                    mock_session_class.return_value = mock_session

                    mock_stdio.return_value.__aenter__.return_value = (MagicMock(), MagicMock())
                    mock_stdio.return_value.__aexit__.return_value = None

                    # Mock the default LLM client - Use create_response API
                    agent.llm = MagicMock()
                    agent.llm.create_response.return_value = {
                        "id": "resp_test_456",
                        "output": [
                            {
                                "type": "message",
                                "content": [
                                    {"type": "output_text", "text": "Done"}
                                ]
                            }
                        ]
                    }
                    agent.llm.get_default_max_tokens.return_value = 8192

                    # Verify validator not called when no model specified
                    with patch.object(agent.model_validator, 'validate_model') as mock_validate:
                        result = await agent.autonomous_with_mcp(
                            mcp_name="filesystem",
                            task="Test",
                            max_rounds=1
                            # No model parameter - should use default
                        )

                        # Validator should NOT be called when model is None
                        mock_validate.assert_not_called()
                        assert result is not None
                        assert "Done" in result

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
                mock_disc_instance = MagicMock()
                mock_disc_instance.get_connection_params.return_value = {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem"],
                    "env": None
                }
                mock_disc_instance.validate_mcp_names.return_value = ["filesystem", "memory"]
                mock_discovery.return_value = mock_disc_instance

                # Mock stdio_client and ClientSession
                with patch('tools.dynamic_autonomous.stdio_client') as mock_stdio:
                    with patch('tools.dynamic_autonomous.ClientSession') as mock_session_class:
                        # Create mock session
                        mock_session = AsyncMock()
                        mock_init_result = MagicMock()
                        mock_init_result.serverInfo.name = "test-server"
                        mock_session.initialize.return_value = mock_init_result

                        mock_tool = MagicMock()
                        mock_tool.name = "test_tool"
                        mock_tool.description = "Test tool"
                        mock_tool.inputSchema = {"type": "object", "properties": {}}
                        mock_tools_result = MagicMock()
                        mock_tools_result.tools = [mock_tool]
                        mock_session.list_tools.return_value = mock_tools_result

                        mock_session.__aenter__.return_value = mock_session
                        mock_session.__aexit__.return_value = None
                        mock_session_class.return_value = mock_session

                        mock_stdio.return_value.__aenter__.return_value = (MagicMock(), MagicMock())
                        mock_stdio.return_value.__aexit__.return_value = None

                        # Mock the agent's LLM client directly - Use create_response API
                        agent.llm = MagicMock()
                        agent.llm.create_response.return_value = {
                            "id": "resp_test_789",
                            "output": [
                                {
                                    "type": "message",
                                    "content": [
                                        {"type": "output_text", "text": "Complete"}
                                    ]
                                }
                            ]
                        }
                        agent.llm.get_default_max_tokens.return_value = 8192

                        result = await agent.autonomous_with_multiple_mcps(
                            mcp_names=["filesystem", "memory"],
                            task="Test task",
                            max_rounds=1,
                            model="qwen/qwen3-coder-30b"
                        )

                        # Verify model was validated
                        agent.model_validator.validate_model.assert_called_with("qwen/qwen3-coder-30b")
                        assert result is not None
                        assert "Complete" in result

    @pytest.mark.asyncio
    async def test_discover_and_execute_with_model(self):
        """Test autonomous_discover_and_execute with specific model."""
        agent = DynamicAutonomousAgent()

        with patch.object(agent.model_validator, 'validate_model', return_value=True):
            # Mock LMSHelper to skip preloading
            with patch('tools.dynamic_autonomous.LMSHelper') as mock_lms:
                mock_lms.is_installed.return_value = False

                with patch('tools.dynamic_autonomous.MCPDiscovery') as mock_discovery:
                    mock_disc_instance = MagicMock()
                    mock_disc_instance.list_available_mcps.return_value = ["filesystem"]
                    mock_disc_instance.validate_mcp_names.return_value = ["filesystem"]  # Add this!
                    mock_disc_instance.get_connection_params.return_value = {
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-filesystem"],
                        "env": None
                    }
                    mock_discovery.return_value = mock_disc_instance

                    # Mock stdio_client and ClientSession
                    with patch('tools.dynamic_autonomous.stdio_client') as mock_stdio:
                        with patch('tools.dynamic_autonomous.ClientSession') as mock_session_class:
                            mock_session = AsyncMock()
                            mock_init_result = MagicMock()
                            mock_init_result.serverInfo.name = "test-server"
                            mock_session.initialize.return_value = mock_init_result

                            mock_tool = MagicMock()
                            mock_tool.name = "test_tool"
                            mock_tool.description = "Test tool"
                            mock_tool.inputSchema = {"type": "object", "properties": {}}
                            mock_tools_result = MagicMock()
                            mock_tools_result.tools = [mock_tool]
                            mock_session.list_tools.return_value = mock_tools_result

                            mock_session.__aenter__.return_value = mock_session
                            mock_session.__aexit__.return_value = None
                            mock_session_class.return_value = mock_session

                            mock_stdio.return_value.__aenter__.return_value = (MagicMock(), MagicMock())
                            mock_stdio.return_value.__aexit__.return_value = None

                            # Mock the agent's LLM client directly - Use create_response API
                            agent.llm = MagicMock()
                            agent.llm.create_response.return_value = {
                                "id": "resp_test_101112",
                                "output": [
                                    {
                                        "type": "message",
                                        "content": [
                                            {"type": "output_text", "text": "Done"}
                                        ]
                                    }
                                ]
                            }
                            agent.llm.get_default_max_tokens.return_value = 8192

                            result = await agent.autonomous_discover_and_execute(
                                task="Test",
                                max_rounds=1,
                                model="mistralai/magistral-small-2509"
                            )

                            agent.model_validator.validate_model.assert_called_with("mistralai/magistral-small-2509")
                            assert result is not None
                            assert "Done" in result

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
            mock_disc_instance = MagicMock()
            mock_disc_instance.get_connection_params.return_value = {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem"],
                "env": None
            }
            mock_discovery.return_value = mock_disc_instance

            # Mock stdio_client and ClientSession
            with patch('tools.dynamic_autonomous.stdio_client') as mock_stdio:
                with patch('tools.dynamic_autonomous.ClientSession') as mock_session_class:
                    mock_session = AsyncMock()
                    mock_init_result = MagicMock()
                    mock_init_result.serverInfo.name = "test-server"
                    mock_session.initialize.return_value = mock_init_result

                    mock_tool = MagicMock()
                    mock_tool.name = "test_tool"
                    mock_tool.description = "Test tool"
                    mock_tool.inputSchema = {"type": "object", "properties": {}}
                    mock_tools_result = MagicMock()
                    mock_tools_result.tools = [mock_tool]
                    mock_session.list_tools.return_value = mock_tools_result

                    mock_session.__aenter__.return_value = mock_session
                    mock_session.__aexit__.return_value = None
                    mock_session_class.return_value = mock_session

                    mock_stdio.return_value.__aenter__.return_value = (MagicMock(), MagicMock())
                    mock_stdio.return_value.__aexit__.return_value = None

                    # Mock the default LLM client - Use create_response API
                    agent.llm = MagicMock()
                    agent.llm.create_response.return_value = {
                        "id": "resp_test_131415",
                        "output": [
                            {
                                "type": "message",
                                "content": [
                                    {"type": "output_text", "text": "Success"}
                                ]
                            }
                        ]
                    }
                    agent.llm.get_default_max_tokens.return_value = 8192

                    # Should work without model parameter
                    result = await agent.autonomous_with_mcp(
                        mcp_name="filesystem",
                        task="Test task",
                        max_rounds=1
                    )

                    assert result is not None
                    assert "Success" in result


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
