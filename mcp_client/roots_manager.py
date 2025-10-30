#!/usr/bin/env python3
"""
Roots Protocol Manager for dynamic directory updates.

Implements the MCP Roots Protocol allowing runtime directory updates
without reconnecting to the filesystem MCP server.
"""

from typing import List, Optional, Dict, Any, Callable
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class RootsManager:
    """Manages roots for MCP client, implementing the Roots Protocol.

    The Roots Protocol allows clients to dynamically update which directories
    an MCP server can access at runtime via roots/list requests and
    roots/list_changed notifications.
    """

    def __init__(self, initial_roots: Optional[List[str]] = None):
        """Initialize roots manager.

        Args:
            initial_roots: Initial list of directory paths
        """
        self._roots: List[Dict[str, str]] = []
        self._listeners: List[Callable] = []

        if initial_roots:
            self.set_roots(initial_roots)

    def set_roots(self, directory_paths: List[str]) -> None:
        """Set the current roots to a new list of directories.

        Args:
            directory_paths: List of absolute directory paths

        Raises:
            ValueError: If any path is invalid
        """
        new_roots = []

        for path_str in directory_paths:
            # Convert to absolute path
            path = Path(path_str).expanduser().resolve()

            if not path.exists():
                raise ValueError(f"Root directory does not exist: {path}")

            if not path.is_dir():
                raise ValueError(f"Root path is not a directory: {path}")

            # Create root object in MCP format
            root = {
                "uri": f"file://{path}",
                "name": path.name or str(path)
            }
            new_roots.append(root)

        # Update roots
        old_roots = self._roots
        self._roots = new_roots

        # Notify listeners if roots changed
        if old_roots != new_roots:
            logger.info(f"Roots updated: {len(new_roots)} directories")
            self._notify_listeners()

    def add_root(self, directory_path: str) -> None:
        """Add a new root directory to the existing list.

        Args:
            directory_path: Absolute directory path to add
        """
        path = Path(directory_path).expanduser().resolve()

        if not path.exists():
            raise ValueError(f"Root directory does not exist: {path}")

        if not path.is_dir():
            raise ValueError(f"Root path is not a directory: {path}")

        # Check if already exists
        uri = f"file://{path}"
        if any(root["uri"] == uri for root in self._roots):
            logger.debug(f"Root already exists: {path}")
            return

        # Add new root
        root = {
            "uri": uri,
            "name": path.name or str(path)
        }
        self._roots.append(root)

        logger.info(f"Added root: {path}")
        self._notify_listeners()

    def remove_root(self, directory_path: str) -> None:
        """Remove a root directory from the list.

        Args:
            directory_path: Directory path to remove
        """
        path = Path(directory_path).expanduser().resolve()
        uri = f"file://{path}"

        # Filter out the root
        original_count = len(self._roots)
        self._roots = [root for root in self._roots if root["uri"] != uri]

        if len(self._roots) < original_count:
            logger.info(f"Removed root: {path}")
            self._notify_listeners()
        else:
            logger.debug(f"Root not found: {path}")

    def get_roots(self) -> List[Dict[str, str]]:
        """Get current roots in MCP format.

        Returns:
            List of root objects with 'uri' and 'name' fields
        """
        return self._roots.copy()

    def get_roots_list_response(self) -> Dict[str, Any]:
        """Get roots/list response in MCP protocol format.

        Returns:
            Response dictionary for roots/list request
        """
        return {
            "roots": self._roots
        }

    def register_listener(self, callback: Callable) -> None:
        """Register a callback to be notified when roots change.

        The callback will be called with no arguments whenever roots are updated.

        Args:
            callback: Function to call when roots change
        """
        if callback not in self._listeners:
            self._listeners.append(callback)

    def unregister_listener(self, callback: Callable) -> None:
        """Unregister a roots change listener.

        Args:
            callback: Function to unregister
        """
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self) -> None:
        """Notify all registered listeners that roots have changed."""
        for callback in self._listeners:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in roots change listener: {e}")

    def clear_roots(self) -> None:
        """Remove all roots."""
        if self._roots:
            self._roots = []
            logger.info("All roots cleared")
            self._notify_listeners()

    def has_roots(self) -> bool:
        """Check if any roots are configured.

        Returns:
            True if at least one root is configured
        """
        return len(self._roots) > 0

    def get_directory_paths(self) -> List[str]:
        """Get list of directory paths (without file:// prefix).

        Returns:
            List of absolute directory paths
        """
        paths = []
        for root in self._roots:
            uri = root["uri"]
            if uri.startswith("file://"):
                path = uri[7:]  # Remove "file://" prefix
                paths.append(path)
        return paths


__all__ = ["RootsManager"]
