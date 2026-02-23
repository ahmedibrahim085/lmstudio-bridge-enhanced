#!/usr/bin/env python3
"""
OPP-15: Conversation Branching — Fork/Merge Tree Navigation.

Provides ConversationNode and ConversationTree for managing conversation
histories as trees. Users can fork from any point, explore branches, and
merge results.

Usage
-----
    from llm.conversation_branch import ConversationTree

    tree = ConversationTree()
    root_id = tree.add_message({"role": "user", "content": "Hello"})
    reply_id = tree.add_message({"role": "assistant", "content": "Hi!"})

    # Fork back to root and explore an alternative path
    tree.fork(root_id, branch_name="alt")
    alt_id = tree.add_message({"role": "assistant", "content": "Hey there!"})

    # Merge the alternative back onto the main branch
    new_tip = tree.merge_branches(source_tip_id=alt_id, target_tip_id=reply_id)
"""

import time
import uuid
from dataclasses import dataclass
from typing import Any, Optional

from config.constants import (
    MAX_BRANCH_DEPTH,
    MAX_BRANCHES_PER_TREE,
)


def _new_id() -> str:
    """Generate a short unique node ID (12 hex chars)."""
    return uuid.uuid4().hex[:12]


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class ConversationNode:
    """A single node in a conversation tree.

    Attributes:
        node_id:     Unique identifier for this node.
        parent_id:   ID of the parent node, or None for the root.
        message:     The conversation message dict (role + content).
        children:    List of child node IDs.
        branch_name: Optional human-readable label for this branch tip.
        created_at:  Monotonic timestamp of creation.
        metadata:    Arbitrary caller-supplied metadata.
    """

    node_id: str
    parent_id: Optional[str]
    message: dict[str, Any]
    children: list[str]
    branch_name: Optional[str]
    created_at: float
    metadata: dict[str, Any]


# ---------------------------------------------------------------------------
# Tree
# ---------------------------------------------------------------------------


class ConversationTree:
    """Manage a conversation as a tree that supports forking and merging.

    The tree maintains:
    - A dict of all nodes keyed by node_id.
    - A root_id pointing to the root node.
    - An active_tip (the current branch tip) that new messages append to by
      default.

    Limits (from config/constants.py):
    - MAX_BRANCH_DEPTH: maximum depth of any branch (prevents runaway chains).
    - MAX_BRANCHES_PER_TREE: maximum total nodes (prevents memory exhaustion).
    """

    def __init__(self) -> None:
        self._nodes: dict[str, ConversationNode] = {}
        self._root_id: Optional[str] = None
        self._active_branch: Optional[str] = None  # current tip node ID

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def root_id(self) -> Optional[str]:
        """The root node ID, or None if the tree is empty."""
        return self._root_id

    @property
    def active_tip(self) -> Optional[str]:
        """The active branch tip node ID."""
        return self._active_branch

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _depth_of(self, node_id: str) -> int:
        """Return the depth of *node_id* (root = 1)."""
        depth = 0
        current: Optional[str] = node_id
        while current is not None:
            depth += 1
            current = self._nodes[current].parent_id
        return depth

    def _ancestors(self, node_id: str) -> list[str]:
        """Return list of ancestor IDs from *node_id* up to (but excluding) root.

        The list is ordered from *node_id* up: [node_id, parent, grandparent, ...].
        """
        path: list[str] = []
        current: Optional[str] = node_id
        while current is not None:
            path.append(current)
            current = self._nodes[current].parent_id
        return path

    def _leaf_nodes(self) -> list[str]:
        """Return IDs of all leaf nodes (nodes with no children)."""
        return [nid for nid, n in self._nodes.items() if not n.children]

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def add_message(
        self,
        message: dict[str, Any],
        parent_id: Optional[str] = None,
        branch_name: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """Add a message to the tree and return its node_id.

        If *parent_id* is None, the new node is appended after the current
        active_tip.  If the tree is empty, the new node becomes the root.

        Args:
            message:     The conversation message dict.
            parent_id:   Explicit parent node ID, or None to use active tip.
            branch_name: Optional human-readable label for this node.
            metadata:    Optional metadata dict.

        Returns:
            The new node's ID string.

        Raises:
            KeyError:    If *parent_id* is provided but not found in the tree.
            ValueError:  If MAX_BRANCH_DEPTH or MAX_BRANCHES_PER_TREE would be
                         exceeded.
        """
        # --- Validate total-node limit ----------------------------------
        if len(self._nodes) >= MAX_BRANCHES_PER_TREE:
            raise ValueError(
                f"Cannot add node: tree already has {len(self._nodes)} nodes, "
                f"which equals MAX_BRANCHES_PER_TREE ({MAX_BRANCHES_PER_TREE}). "
                "Delete a branch before adding more."
            )

        # --- Resolve effective parent -----------------------------------
        if self._root_id is None:
            # Empty tree — this message becomes the root
            effective_parent: Optional[str] = None
        elif parent_id is not None:
            if parent_id not in self._nodes:
                raise KeyError(f"Parent node '{parent_id}' not found in tree.")
            effective_parent = parent_id
        else:
            # Default: append to current active tip
            effective_parent = self._active_branch

        # --- Validate depth limit ---------------------------------------
        if effective_parent is not None:
            new_depth = self._depth_of(effective_parent) + 1
            if new_depth > MAX_BRANCH_DEPTH:
                raise ValueError(
                    f"Cannot add node: depth {new_depth} would exceed "
                    f"MAX_BRANCH_DEPTH ({MAX_BRANCH_DEPTH})."
                )

        # --- Create node ------------------------------------------------
        node_id = _new_id()
        node = ConversationNode(
            node_id=node_id,
            parent_id=effective_parent,
            message=message,
            children=[],
            branch_name=branch_name,
            created_at=time.monotonic(),
            metadata=metadata or {},
        )
        self._nodes[node_id] = node

        # Register as child of parent
        if effective_parent is not None:
            self._nodes[effective_parent].children.append(node_id)

        # First node → root
        if self._root_id is None:
            self._root_id = node_id

        # Advance active tip
        self._active_branch = node_id
        return node_id

    def fork(self, from_node_id: str, branch_name: Optional[str] = None) -> str:
        """Set the active branch to *from_node_id* (creating a fork point).

        Subsequent add_message calls (without an explicit parent_id) will
        branch off from this node.

        Args:
            from_node_id: The node ID to fork from.
            branch_name:  Optional label to assign to the fork node.

        Returns:
            *from_node_id* (the fork point node ID).

        Raises:
            KeyError:   If *from_node_id* is not in the tree.
            ValueError: If MAX_BRANCHES_PER_TREE would be exceeded (defensive
                        check — the fork itself doesn't add nodes, but we
                        validate to keep callers honest about tree capacity).
        """
        if from_node_id not in self._nodes:
            raise KeyError(f"Node '{from_node_id}' not found in tree.")

        # Defensive: check that the tree hasn't already hit the limit.
        # A fork switches the active tip but doesn't add a node, so we check
        # whether the *next* add would overflow — but that's up to add_message.
        # The spec says fork should raise ValueError when limit would be exceeded.
        # We treat this as: if we're already AT the limit (no room for further
        # adds) we raise here too, matching the intent.
        if len(self._nodes) >= MAX_BRANCHES_PER_TREE:
            raise ValueError(
                f"Cannot create branch: tree already has {len(self._nodes)} nodes "
                f"(MAX_BRANCHES_PER_TREE={MAX_BRANCHES_PER_TREE})."
            )

        if branch_name is not None:
            self._nodes[from_node_id].branch_name = branch_name

        self._active_branch = from_node_id
        return from_node_id

    def get_branch_messages(
        self, tip_node_id: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """Return messages along the branch ending at *tip_node_id*.

        Walks from the tip up to the root, then reverses to give chronological
        (root-first) order.

        Args:
            tip_node_id: Tip of the branch, or None to use active_tip.

        Returns:
            List of message dicts in chronological order.  Empty list for an
            empty tree or if no active branch is set.
        """
        if not self._nodes:
            return []

        tip = tip_node_id if tip_node_id is not None else self._active_branch
        if tip is None:
            return []

        # Walk up from tip to root
        path: list[dict[str, Any]] = []
        current: Optional[str] = tip
        while current is not None:
            path.append(self._nodes[current].message)
            current = self._nodes[current].parent_id

        path.reverse()
        return path

    def switch_branch(self, node_id: str) -> None:
        """Switch the active branch tip to *node_id*.

        Args:
            node_id: The node to make the new active tip.

        Raises:
            ValueError: If *node_id* is not found in the tree.
        """
        if node_id not in self._nodes:
            raise ValueError(f"Node '{node_id}' not found in tree.")
        self._active_branch = node_id

    def merge_branches(
        self,
        source_tip_id: str,
        target_tip_id: str,
        strategy: str = "append",
    ) -> str:
        """Merge the source branch into the target branch.

        Args:
            source_tip_id: Tip of the branch to merge FROM.
            target_tip_id: Tip of the branch to merge INTO.
            strategy:      Merge strategy: "append" or "summary".
                           - "append":  Each message on the source branch (that
                             is not already on the target branch path) is added
                             as new nodes after the target tip.
                           - "summary": A single new node is created whose
                             content is the concatenation of all source messages.

        Returns:
            The node_id of the new tip after the merge.

        Raises:
            KeyError: If either *source_tip_id* or *target_tip_id* not found.
        """
        if source_tip_id not in self._nodes:
            raise KeyError(f"Source node '{source_tip_id}' not found in tree.")
        if target_tip_id not in self._nodes:
            raise KeyError(f"Target node '{target_tip_id}' not found in tree.")

        # Collect source branch path (root-first)
        source_path = self._path_to_root(source_tip_id)  # root-first
        target_ancestors = set(self._path_to_root(target_tip_id))

        # Messages unique to the source branch (not shared with target)
        source_only: list[ConversationNode] = [
            self._nodes[nid] for nid in source_path if nid not in target_ancestors
        ]

        if strategy == "summary":
            combined_content = " | ".join(
                str(n.message.get("content", "")) for n in source_only
            )
            merged_msg: dict[str, Any] = {
                "role": "assistant",
                "content": f"[merged] {combined_content}",
            }
            new_tip = self.add_message(
                merged_msg,
                parent_id=target_tip_id,
                branch_name="merged",
                metadata={"merge_strategy": "summary"},
            )
        else:
            # "append" strategy: graft each source-only node after target tip
            current_parent = target_tip_id
            for node in source_only:
                new_tip = self.add_message(
                    node.message,
                    parent_id=current_parent,
                    branch_name=node.branch_name,
                    metadata={**node.metadata, "merge_strategy": "append"},
                )
                current_parent = new_tip

            if not source_only:
                # Nothing to merge — return target tip unchanged
                new_tip = target_tip_id

        return new_tip

    def _path_to_root(self, node_id: str) -> list[str]:
        """Return the list of node IDs from root down to *node_id* (root-first)."""
        path: list[str] = []
        current: Optional[str] = node_id
        while current is not None:
            path.append(current)
            current = self._nodes[current].parent_id
        path.reverse()
        return path

    def list_branches(self) -> list[dict[str, Any]]:
        """Return info about all branch tips (leaf nodes).

        Returns:
            List of dicts, each with keys:
            - branch_name:  The branch name label (may be None).
            - tip_node_id:  Node ID of the branch tip (leaf).
            - depth:        Depth of the tip node (root = 1).
            - message_count: Number of messages on the path from root to tip.
        """
        if not self._nodes:
            return []

        result: list[dict[str, Any]] = []
        for leaf_id in self._leaf_nodes():
            depth = self._depth_of(leaf_id)
            result.append(
                {
                    "branch_name": self._nodes[leaf_id].branch_name,
                    "tip_node_id": leaf_id,
                    "depth": depth,
                    "message_count": depth,
                }
            )
        return result

    def get_node(self, node_id: str) -> ConversationNode:
        """Return the node with *node_id*.

        Raises:
            KeyError: If *node_id* is not found.
        """
        if node_id not in self._nodes:
            raise KeyError(f"Node '{node_id}' not found in tree.")
        return self._nodes[node_id]

    def get_tree_stats(self) -> dict[str, Any]:
        """Return summary statistics for the tree.

        Returns:
            Dict with keys: total_nodes, total_branches, max_depth,
            active_branch (current active tip node ID or None).
        """
        if not self._nodes:
            return {
                "total_nodes": 0,
                "total_branches": 0,
                "max_depth": 0,
                "active_branch": None,
            }

        leaves = self._leaf_nodes()
        max_depth = max(self._depth_of(lid) for lid in leaves) if leaves else 0

        return {
            "total_nodes": len(self._nodes),
            "total_branches": len(leaves),
            "max_depth": max_depth,
            "active_branch": self._active_branch,
        }

    def delete_branch(self, tip_node_id: str) -> int:
        """Delete the branch from *tip_node_id* back to the nearest fork point.

        A "fork point" is a node that has more than one child — deleting stops
        just before removing the shared ancestor.  If the tip is a direct child
        of root with no siblings, the entire branch (except root) is removed.

        Args:
            tip_node_id: The leaf/tip of the branch to delete.

        Returns:
            The number of nodes deleted.

        Raises:
            ValueError: If *tip_node_id* is the root node.
            ValueError: If deleting would leave the tree with no branches
                        (i.e. this is the only remaining branch).
            KeyError:   If *tip_node_id* is not in the tree (implicit via
                        get_node).
        """
        if tip_node_id not in self._nodes:
            raise KeyError(f"Node '{tip_node_id}' not found in tree.")

        if tip_node_id == self._root_id:
            raise ValueError("Cannot delete the root node.")

        # Safety: ensure at least one other leaf will remain after deletion
        leaves = self._leaf_nodes()
        if len(leaves) <= 1:
            raise ValueError(
                "Cannot delete: this is the only branch in the tree."
            )

        # Walk from tip toward root, collecting nodes to delete.
        # Stop when we hit a node that has more than one child (fork point)
        # or when we hit the root.
        to_delete: list[str] = []
        current: Optional[str] = tip_node_id

        while current is not None and current != self._root_id:
            node = self._nodes[current]
            # If the node has multiple children it's a fork point — stop here
            # (don't delete the fork point itself, only the branch below it)
            if len(node.children) > 1:
                break
            to_delete.append(current)
            current = node.parent_id

        # Remove children references from the parent of the topmost deleted node
        if to_delete:
            topmost = to_delete[-1]
            parent_id = self._nodes[topmost].parent_id
            if parent_id and parent_id in self._nodes:
                self._nodes[parent_id].children = [
                    c for c in self._nodes[parent_id].children if c != topmost
                ]

        # Delete the nodes
        for nid in to_delete:
            del self._nodes[nid]

        # If active tip was deleted, reset to root
        if self._active_branch in set(to_delete):
            self._active_branch = self._root_id

        return len(to_delete)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize the entire tree to a plain Python dict.

        Returns:
            A dict suitable for JSON serialization or persistence.
        """
        return {
            "root_id": self._root_id,
            "active_branch": self._active_branch,
            "nodes": {
                nid: {
                    "node_id": n.node_id,
                    "parent_id": n.parent_id,
                    "message": n.message,
                    "children": list(n.children),
                    "branch_name": n.branch_name,
                    "created_at": n.created_at,
                    "metadata": n.metadata,
                }
                for nid, n in self._nodes.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConversationTree":
        """Deserialize a tree from a dict produced by :meth:`to_dict`.

        Args:
            data: The serialized tree dict.

        Returns:
            A new :class:`ConversationTree` instance.
        """
        tree = cls()
        tree._root_id = data.get("root_id")
        tree._active_branch = data.get("active_branch")

        for nid, nd in data.get("nodes", {}).items():
            tree._nodes[nid] = ConversationNode(
                node_id=nd["node_id"],
                parent_id=nd.get("parent_id"),
                message=nd["message"],
                children=list(nd.get("children", [])),
                branch_name=nd.get("branch_name"),
                created_at=nd.get("created_at", 0.0),
                metadata=nd.get("metadata", {}),
            )

        return tree


__all__ = [
    "ConversationNode",
    "ConversationTree",
]
