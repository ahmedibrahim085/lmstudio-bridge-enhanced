#!/usr/bin/env python3
"""
Tests for configuration validation using Pydantic.

This test suite validates:
- LMStudioConfig validation (host, port)
- MCPConfig validation (working directory)
- Config.from_env() error handling
- Pydantic validation behavior
"""

import pytest
import os
from pydantic import ValidationError

# Import from config package to avoid circular import issues
from config import LMStudioConfig, MCPConfig, Config


class TestLMStudioConfigValidation:
    """Test LMStudioConfig validation."""

    def test_valid_config(self):
        """Test creating config with valid values."""
        config = LMStudioConfig(
            host="localhost",
            port=8080,
            api_base="http://localhost:8080/v1",
            default_model="test-model"
        )
        assert config.host == "localhost"
        assert config.port == 8080
        assert config.api_base == "http://localhost:8080/v1"
        assert config.default_model == "test-model"

    def test_valid_config_with_default_port(self):
        """Test config with standard LM Studio port."""
        config = LMStudioConfig(
            host="127.0.0.1",
            port=1234,
            api_base="http://127.0.0.1:1234/v1",
            default_model="test-model"
        )
        assert config.host == "127.0.0.1"
        assert config.port == 1234

    def test_host_validation_strips_whitespace(self):
        """Test that host validation strips whitespace."""
        config = LMStudioConfig(
            host="  localhost  ",
            port=1234,
            api_base="http://localhost:1234/v1",
            default_model="test-model"
        )
        assert config.host == "localhost"  # Should be stripped

    def test_invalid_port_zero(self):
        """Test that port 0 is invalid."""
        with pytest.raises(ValidationError) as exc_info:
            LMStudioConfig(
                host="localhost",
                port=0,
                api_base="http://localhost:0/v1",
                default_model="test-model"
            )
        assert "Port must be between 1-65535" in str(exc_info.value) or "greater than or equal to 1" in str(exc_info.value)

    def test_invalid_port_negative(self):
        """Test that negative port is invalid."""
        with pytest.raises(ValidationError) as exc_info:
            LMStudioConfig(
                host="localhost",
                port=-1,
                api_base="http://localhost:-1/v1",
                default_model="test-model"
            )
        assert "greater than or equal to 1" in str(exc_info.value) or "Port must be between 1-65535" in str(exc_info.value)

    def test_invalid_port_too_large(self):
        """Test that port > 65535 is invalid."""
        with pytest.raises(ValidationError) as exc_info:
            LMStudioConfig(
                host="localhost",
                port=99999,
                api_base="http://localhost:99999/v1",
                default_model="test-model"
            )
        assert "Port must be between 1-65535" in str(exc_info.value) or "less than or equal to 65535" in str(exc_info.value)

    def test_invalid_host_empty(self):
        """Test that empty host is invalid."""
        with pytest.raises(ValidationError) as exc_info:
            LMStudioConfig(
                host="",
                port=1234,
                api_base="http://localhost:1234/v1",
                default_model="test-model"
            )
        assert "Host must be a non-empty string" in str(exc_info.value) or "at least 1 character" in str(exc_info.value)

    def test_invalid_host_whitespace_only(self):
        """Test that whitespace-only host is invalid."""
        with pytest.raises(ValidationError) as exc_info:
            LMStudioConfig(
                host="   ",
                port=1234,
                api_base="http://localhost:1234/v1",
                default_model="test-model"
            )
        assert "Host must be a non-empty string" in str(exc_info.value)

    def test_invalid_empty_api_base(self):
        """Test that empty api_base is invalid."""
        with pytest.raises(ValidationError) as exc_info:
            LMStudioConfig(
                host="localhost",
                port=1234,
                api_base="",
                default_model="test-model"
            )
        assert "at least 1 character" in str(exc_info.value)

    def test_invalid_empty_model(self):
        """Test that empty default_model is invalid."""
        with pytest.raises(ValidationError) as exc_info:
            LMStudioConfig(
                host="localhost",
                port=1234,
                api_base="http://localhost:1234/v1",
                default_model=""
            )
        assert "at least 1 character" in str(exc_info.value)

    def test_port_edge_case_1(self):
        """Test port=1 (minimum valid port)."""
        config = LMStudioConfig(
            host="localhost",
            port=1,
            api_base="http://localhost:1/v1",
            default_model="test-model"
        )
        assert config.port == 1

    def test_port_edge_case_65535(self):
        """Test port=65535 (maximum valid port)."""
        config = LMStudioConfig(
            host="localhost",
            port=65535,
            api_base="http://localhost:65535/v1",
            default_model="test-model"
        )
        assert config.port == 65535


class TestMCPConfigValidation:
    """Test MCPConfig validation."""

    def test_valid_config(self):
        """Test creating config with valid working directory."""
        config = MCPConfig(default_working_directory="/home/user/project")
        assert config.default_working_directory == "/home/user/project"

    def test_working_directory_strips_whitespace(self):
        """Test that working directory strips whitespace."""
        config = MCPConfig(default_working_directory="  /home/user/project  ")
        assert config.default_working_directory == "/home/user/project"

    def test_invalid_empty_working_directory(self):
        """Test that empty working directory is invalid."""
        with pytest.raises(ValidationError) as exc_info:
            MCPConfig(default_working_directory="")
        assert "Working directory must be a non-empty string" in str(exc_info.value) or "at least 1 character" in str(exc_info.value)

    def test_invalid_whitespace_only_working_directory(self):
        """Test that whitespace-only working directory is invalid."""
        with pytest.raises(ValidationError) as exc_info:
            MCPConfig(default_working_directory="   ")
        assert "Working directory must be a non-empty string" in str(exc_info.value)


class TestConfigFromEnv:
    """Test Config.from_env() error handling."""

    def test_from_env_with_invalid_port(self, monkeypatch):
        """Test from_env() raises error for invalid port."""
        monkeypatch.setenv("LMSTUDIO_PORT", "not_a_number")

        with pytest.raises(ValueError) as exc_info:
            LMStudioConfig.from_env()

        assert "Invalid LMSTUDIO_PORT" in str(exc_info.value)

    def test_from_env_with_port_out_of_range(self, monkeypatch):
        """Test from_env() raises error for port out of range."""
        monkeypatch.setenv("LMSTUDIO_PORT", "99999")

        with pytest.raises(ValueError) as exc_info:
            LMStudioConfig.from_env()

        assert "Configuration validation error" in str(exc_info.value) or "Port must be between 1-65535" in str(exc_info.value)

    def test_from_env_with_valid_port(self, monkeypatch):
        """Test from_env() succeeds with valid environment variables."""
        monkeypatch.setenv("LMSTUDIO_HOST", "127.0.0.1")
        monkeypatch.setenv("LMSTUDIO_PORT", "8080")
        monkeypatch.setenv("DEFAULT_MODEL", "test-model")

        config = LMStudioConfig.from_env()

        assert config.host == "127.0.0.1"
        assert config.port == 8080
        assert config.default_model == "test-model"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
