"""MCP tools for agent slot management (OPP-31 Phase 5).

Exposes agent slot lifecycle + role management as MCP tools.
All methods return JSON strings for MCP protocol compliance.
Errors are returned as structured JSON, never raised as exceptions.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from config.roles import RoleRegistry, RoleTemplate
from config.slot_manager import AgentSlotManager

logger = logging.getLogger(__name__)


class ProfileTools:
    """Agent slot + role management tools for MCP.

    All methods return JSON strings. Errors are caught and returned
    as ``{"error": "..."}`` rather than raised.

    Args:
        slot_manager: AgentSlotManager for slot lifecycle.
        role_registry: RoleRegistry for role lookup and creation.
    """

    def __init__(
        self,
        slot_manager: AgentSlotManager,
        role_registry: RoleRegistry,
    ) -> None:
        self._manager = slot_manager
        self._registry = role_registry

    def create_agent(
        self,
        name: str,
        role: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Create a named agent slot with a role and optional model.

        Returns JSON with slot details, or ``{"error": "..."}`` on failure.
        """
        overrides: Dict[str, Any] = {}
        if temperature is not None:
            overrides["temperature"] = temperature
        if max_tokens is not None:
            overrides["max_tokens"] = max_tokens

        try:
            config = self._manager.create_slot(
                name=name,
                role=role,
                model_id=model,
                overrides=overrides or None,
            )
            return json.dumps({
                "name": name,
                "role": config.role_name,
                "model_id": config.model_id,
                "family": config.family,
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
                "task_type": config.task_type,
            })
        except (ValueError, KeyError) as exc:
            return json.dumps({"error": str(exc)})

    def list_agents(self) -> str:
        """List all active agent slots. Returns JSON."""
        slots = self._manager.list_slots()
        return json.dumps({"agents": slots})

    def remove_agent(self, name: str) -> str:
        """Remove an agent slot. Returns JSON confirmation or error."""
        try:
            self._manager.remove_slot(name)
            return json.dumps({"removed": name})
        except KeyError as exc:
            return json.dumps({"error": str(exc)})

    def list_roles(self) -> str:
        """List all available role templates. Returns JSON."""
        role_names = self._registry.list()
        roles: List[Dict[str, Any]] = []
        for rname in role_names:
            role = self._registry.get(rname)
            roles.append({
                "name": role.name,
                "description": role.description,
                "temperature": role.temperature,
                "max_tokens": role.max_tokens,
            })
        return json.dumps({"roles": roles})

    def create_role(
        self,
        name: str,
        description: str,
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        preferred_capabilities: Optional[List[str]] = None,
    ) -> str:
        """Create a new role template at runtime. Returns JSON."""
        caps = tuple(preferred_capabilities) if preferred_capabilities else ()
        role = RoleTemplate(
            name=name,
            description=description,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            preferred_capabilities=caps,
        )
        try:
            self._registry.add(role)
            return json.dumps({"name": name, "created": True})
        except ValueError as exc:
            return json.dumps({"error": str(exc)})


def register_profile_tools(mcp, slot_manager: AgentSlotManager, role_registry: RoleRegistry) -> None:
    """Register agent profile tools with FastMCP server.

    Args:
        mcp: FastMCP server instance.
        slot_manager: AgentSlotManager for slot lifecycle.
        role_registry: RoleRegistry for role lookup.
    """
    tools = ProfileTools(slot_manager=slot_manager, role_registry=role_registry)

    @mcp.tool()
    async def create_agent(
        name: str,
        role: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Create a named agent slot with a role and optional model assignment.

        If model is not specified, auto-resolves the best available model
        for the role's preferred capabilities.

        Examples:
            create_agent("my-coder", "coder")
            create_agent("my-coder", "coder", model="qwen2.5-coder-7b")
        """
        return tools.create_agent(
            name=name, role=role, model=model,
            temperature=temperature, max_tokens=max_tokens,
        )

    @mcp.tool()
    async def list_agents() -> str:
        """List all active agent slots with their models and configs."""
        return tools.list_agents()

    @mcp.tool()
    async def remove_agent(name: str) -> str:
        """Remove an agent slot. Does not unload the model from LM Studio."""
        return tools.remove_agent(name=name)

    @mcp.tool()
    async def list_roles() -> str:
        """List all available role templates (built-in + custom)."""
        return tools.list_roles()

    @mcp.tool()
    async def create_role(
        name: str,
        description: str,
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        preferred_capabilities: Optional[List[str]] = None,
    ) -> str:
        """Create a new role template at runtime."""
        return tools.create_role(
            name=name, description=description,
            system_prompt=system_prompt, temperature=temperature,
            max_tokens=max_tokens, preferred_capabilities=preferred_capabilities,
        )


__all__ = [
    "ProfileTools",
    "register_profile_tools",
]
