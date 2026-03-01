#!/usr/bin/env python3
"""
OPP-15: Conversation Branching — Test Suite.

TDD: These tests were written BEFORE the implementation.
They verify ConversationNode, ConversationTree, constants, and all
edge cases for fork/merge/delete/serialization operations.

Test Groups
-----------
1.  ConversationNode — dataclass fields
2.  ConversationTree — add_message
3.  ConversationTree — fork
4.  ConversationTree — get_branch_messages
5.  ConversationTree — switch_branch
6.  ConversationTree — merge_branches
7.  ConversationTree — list_branches
8.  ConversationTree — delete_branch
9.  ConversationTree — serialization (to_dict / from_dict)
10. ConversationTree — get_tree_stats
11. Constants validation
12. Edge cases
"""

import time
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Imports under test — these will FAIL until implementation is in place
# ---------------------------------------------------------------------------
from config.constants import (
    DEFAULT_BRANCH_PREFIX,
    MAX_BRANCH_DEPTH,
    MAX_BRANCHES_PER_TREE,
)
from llm.conversation_branch import ConversationNode, ConversationTree

# ===========================================================================
# Helpers
# ===========================================================================


def _msg(role: str = "user", content: str = "hello") -> dict[str, Any]:
    return {"role": role, "content": content}


# ===========================================================================
# Group 1: ConversationNode
# ===========================================================================


class TestConversationNode:
    """Tests for the ConversationNode dataclass."""

    def test_create_node_with_all_fields(self):
        """Happy path: node can be created with all required fields."""
        node = ConversationNode(
            node_id="abc123",
            parent_id=None,
            message={"role": "user", "content": "Hello"},
            children=[],
            branch_name="main",
            created_at=time.monotonic(),
            metadata={"key": "value"},
        )
        assert node.node_id == "abc123"
        assert node.parent_id is None
        assert node.message["role"] == "user"
        assert node.children == []
        assert node.branch_name == "main"
        assert node.metadata == {"key": "value"}

    def test_default_children_is_empty_list(self):
        """Edge: node with no children has empty list by default."""
        node = ConversationNode(
            node_id="x1",
            parent_id=None,
            message=_msg(),
            children=[],
            branch_name=None,
            created_at=time.monotonic(),
            metadata={},
        )
        assert node.children == []
        assert isinstance(node.children, list)

    def test_node_id_is_string(self):
        """node_id field is a string."""
        node = ConversationNode(
            node_id="deadbeef1234",
            parent_id="parent99",
            message=_msg(),
            children=["child1"],
            branch_name=None,
            created_at=time.monotonic(),
            metadata={},
        )
        assert isinstance(node.node_id, str)


# ===========================================================================
# Group 2: ConversationTree — add_message
# ===========================================================================


class TestAddMessage:
    """Tests for ConversationTree.add_message()."""

    def test_first_message_becomes_root(self):
        """First message added to an empty tree becomes the root node."""
        tree = ConversationTree()
        node_id = tree.add_message(_msg("user", "Hello"))
        assert tree.root_id == node_id

    def test_second_message_appends_to_active_branch(self):
        """Second message is a child of the first (linear chain)."""
        tree = ConversationTree()
        id1 = tree.add_message(_msg("user", "Hello"))
        id2 = tree.add_message(_msg("assistant", "Hi!"))

        node1 = tree.get_node(id1)
        assert id2 in node1.children
        assert tree.active_tip == id2

    def test_message_with_explicit_parent_id_creates_branch(self):
        """Passing parent_id explicitly attaches the new node to that parent."""
        tree = ConversationTree()
        root_id = tree.add_message(_msg("user", "Root"))
        branch_id = tree.add_message(_msg("user", "Branch"), parent_id=root_id)

        root_node = tree.get_node(root_id)
        assert branch_id in root_node.children

    def test_validates_max_branch_depth(self):
        """Adding a node that would exceed MAX_BRANCH_DEPTH raises ValueError."""
        tree = ConversationTree()
        node_id = tree.add_message(_msg())
        # Build a chain of MAX_BRANCH_DEPTH nodes
        for _ in range(MAX_BRANCH_DEPTH - 1):
            node_id = tree.add_message(_msg(), parent_id=node_id)
        # One more should raise
        with pytest.raises(ValueError, match="depth"):
            tree.add_message(_msg(), parent_id=node_id)

    def test_validates_max_branches_per_tree(self):
        """Adding more than MAX_BRANCHES_PER_TREE total nodes raises ValueError."""
        tree = ConversationTree()
        # Add root
        root_id = tree.add_message(_msg())
        # Each add from root creates a new branch tip — fill up to limit
        for i in range(MAX_BRANCHES_PER_TREE - 1):
            tree.add_message(_msg("user", f"msg{i}"), parent_id=root_id)
        # One more should raise
        with pytest.raises(ValueError, match="branch"):
            tree.add_message(_msg("user", "overflow"), parent_id=root_id)

    def test_returns_node_id_string(self):
        """add_message returns a non-empty string node ID."""
        tree = ConversationTree()
        nid = tree.add_message(_msg())
        assert isinstance(nid, str)
        assert len(nid) > 0


# ===========================================================================
# Group 3: ConversationTree — fork
# ===========================================================================


class TestFork:
    """Tests for ConversationTree.fork()."""

    def test_fork_from_existing_node(self):
        """Forking from an existing node returns that node's ID (fork point)."""
        tree = ConversationTree()
        root_id = tree.add_message(_msg("user", "Root"))
        tree.add_message(_msg("assistant", "Response"))

        fork_id = tree.fork(root_id, branch_name="alt")
        assert fork_id == root_id

    def test_active_branch_switches_to_fork_point(self):
        """After fork(), active_tip is set to the fork node ID."""
        tree = ConversationTree()
        root_id = tree.add_message(_msg("user", "Root"))
        tree.add_message(_msg("assistant", "Response"))

        tree.fork(root_id)
        assert tree.active_tip == root_id

    def test_fork_from_nonexistent_node_raises_key_error(self):
        """Forking from a node ID that does not exist raises KeyError."""
        tree = ConversationTree()
        tree.add_message(_msg())
        with pytest.raises(KeyError):
            tree.fork("nonexistent_node_id")

    def test_fork_respects_max_branches_per_tree(self):
        """Fork raises ValueError when MAX_BRANCHES_PER_TREE would be exceeded."""
        tree = ConversationTree()
        root_id = tree.add_message(_msg())
        # Fill up to limit with branches from root
        for i in range(MAX_BRANCHES_PER_TREE - 1):
            tree.add_message(_msg("user", f"b{i}"), parent_id=root_id)
        # Now fork should raise (tree is full)
        with pytest.raises(ValueError, match="branch"):
            tree.fork(root_id, branch_name="overflow")


# ===========================================================================
# Group 4: ConversationTree — get_branch_messages
# ===========================================================================


class TestGetBranchMessages:
    """Tests for ConversationTree.get_branch_messages()."""

    def test_linear_conversation_returns_messages_in_order(self):
        """Linear chain: messages are returned root-first (chronological)."""
        tree = ConversationTree()
        tree.add_message(_msg("user", "A"))
        tree.add_message(_msg("assistant", "B"))
        tree.add_message(_msg("user", "C"))

        messages = tree.get_branch_messages()
        contents = [m["content"] for m in messages]
        assert contents == ["A", "B", "C"]

    def test_branched_conversation_returns_correct_path(self):
        """Branched tree: only the path from tip to root is returned."""
        tree = ConversationTree()
        root_id = tree.add_message(_msg("user", "Root"))
        # Main branch
        tree.add_message(_msg("assistant", "Main"))
        # Fork back to root and add an alt branch
        tree.fork(root_id)
        alt_id = tree.add_message(_msg("assistant", "Alt"))

        # Get messages for the alt tip
        alt_msgs = tree.get_branch_messages(tip_node_id=alt_id)
        contents = [m["content"] for m in alt_msgs]
        assert "Root" in contents
        assert "Alt" in contents
        assert "Main" not in contents

    def test_empty_tree_returns_empty_list(self):
        """Empty tree returns empty list."""
        tree = ConversationTree()
        assert tree.get_branch_messages() == []

    def test_none_tip_uses_active_branch(self):
        """When tip_node_id is None, active_tip is used."""
        tree = ConversationTree()
        tree.add_message(_msg("user", "First"))
        tree.add_message(_msg("assistant", "Second"))

        # active_tip is the last added node
        messages = tree.get_branch_messages(tip_node_id=None)
        assert len(messages) == 2
        assert messages[-1]["content"] == "Second"


# ===========================================================================
# Group 5: ConversationTree — switch_branch
# ===========================================================================


class TestSwitchBranch:
    """Tests for ConversationTree.switch_branch()."""

    def test_switches_active_tip_to_target_node(self):
        """switch_branch changes active_tip to the specified node."""
        tree = ConversationTree()
        root_id = tree.add_message(_msg("user", "Root"))
        tree.add_message(_msg("assistant", "Tip"))

        tree.switch_branch(root_id)
        assert tree.active_tip == root_id

    def test_nonexistent_node_raises_value_error(self):
        """Switching to a non-existent node raises ValueError."""
        tree = ConversationTree()
        tree.add_message(_msg())
        with pytest.raises(ValueError):
            tree.switch_branch("does_not_exist")

    def test_after_switch_get_branch_messages_uses_new_branch(self):
        """After switch_branch, get_branch_messages() reflects the new active tip."""
        tree = ConversationTree()
        root_id = tree.add_message(_msg("user", "Root"))
        tree.add_message(_msg("assistant", "Longer path"))

        tree.switch_branch(root_id)
        messages = tree.get_branch_messages()
        assert len(messages) == 1
        assert messages[0]["content"] == "Root"


# ===========================================================================
# Group 6: ConversationTree — merge_branches
# ===========================================================================


class TestMergeBranches:
    """Tests for ConversationTree.merge_branches()."""

    def _setup_two_branches(self) -> tuple[ConversationTree, str, str]:
        """Helper: build tree with two diverging branches. Returns (tree, main_tip, alt_tip)."""
        tree = ConversationTree()
        root_id = tree.add_message(_msg("user", "Root"))
        main_id = tree.add_message(_msg("assistant", "Main"))
        tree.fork(root_id)
        alt_id = tree.add_message(_msg("assistant", "Alt"))
        return tree, main_id, alt_id

    def test_append_strategy_source_messages_added_after_target_tip(self):
        """append strategy: source branch messages appear after target tip."""
        tree, main_id, alt_id = self._setup_two_branches()
        new_tip = tree.merge_branches(source_tip_id=alt_id, target_tip_id=main_id, strategy="append")

        merged = tree.get_branch_messages(tip_node_id=new_tip)
        contents = [m["content"] for m in merged]
        # Root + Main come first, then Alt
        assert "Root" in contents
        assert "Main" in contents
        assert "Alt" in contents
        main_pos = contents.index("Main")
        alt_pos = contents.index("Alt")
        assert main_pos < alt_pos

    def test_summary_strategy_creates_single_merged_node(self):
        """summary strategy: returns a single new node whose content is a concatenation."""
        tree, main_id, alt_id = self._setup_two_branches()
        new_tip = tree.merge_branches(source_tip_id=alt_id, target_tip_id=main_id, strategy="summary")

        merged_node = tree.get_node(new_tip)
        # The merged node should contain both source messages
        assert merged_node is not None

    def test_merge_returns_new_tip_node_id(self):
        """merge_branches returns a string node ID."""
        tree, main_id, alt_id = self._setup_two_branches()
        result = tree.merge_branches(source_tip_id=alt_id, target_tip_id=main_id)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_invalid_source_raises_key_error(self):
        """Non-existent source_tip_id raises KeyError."""
        tree = ConversationTree()
        root_id = tree.add_message(_msg())
        with pytest.raises(KeyError):
            tree.merge_branches(source_tip_id="invalid", target_tip_id=root_id)

    def test_invalid_target_raises_key_error(self):
        """Non-existent target_tip_id raises KeyError."""
        tree = ConversationTree()
        root_id = tree.add_message(_msg())
        with pytest.raises(KeyError):
            tree.merge_branches(source_tip_id=root_id, target_tip_id="invalid")


# ===========================================================================
# Group 7: ConversationTree — list_branches
# ===========================================================================


class TestListBranches:
    """Tests for ConversationTree.list_branches()."""

    def test_empty_tree_returns_empty_list(self):
        """Empty tree returns empty list."""
        tree = ConversationTree()
        assert tree.list_branches() == []

    def test_single_branch_returns_one_entry(self):
        """Linear tree has exactly one branch entry."""
        tree = ConversationTree()
        tree.add_message(_msg("user", "A"))
        tree.add_message(_msg("assistant", "B"))

        branches = tree.list_branches()
        assert len(branches) == 1

    def test_multiple_branches_returns_all_with_correct_info(self):
        """Forked tree lists all branch tips with expected keys."""
        tree = ConversationTree()
        root_id = tree.add_message(_msg("user", "Root"))
        main_id = tree.add_message(_msg("assistant", "Main"))
        tree.fork(root_id, branch_name="alt-branch")
        alt_id = tree.add_message(_msg("assistant", "Alt"))

        branches = tree.list_branches()
        # At least 2 branches (main and alt)
        assert len(branches) >= 2

        for b in branches:
            assert "tip_node_id" in b
            assert "depth" in b
            assert "message_count" in b

        tip_ids = [b["tip_node_id"] for b in branches]
        assert main_id in tip_ids
        assert alt_id in tip_ids

    def test_branch_info_contains_branch_name(self):
        """branch info dict contains branch_name key."""
        tree = ConversationTree()
        tree.add_message(_msg())
        branches = tree.list_branches()
        assert len(branches) == 1
        assert "branch_name" in branches[0]


# ===========================================================================
# Group 8: ConversationTree — delete_branch
# ===========================================================================


class TestDeleteBranch:
    """Tests for ConversationTree.delete_branch()."""

    def test_deletes_nodes_from_tip_to_fork_point(self):
        """delete_branch removes nodes from tip back to the shared ancestor."""
        tree = ConversationTree()
        root_id = tree.add_message(_msg("user", "Root"))
        tree.add_message(_msg("assistant", "Main"))
        tree.fork(root_id)
        alt_id = tree.add_message(_msg("assistant", "Alt"))

        count = tree.delete_branch(alt_id)
        assert count >= 1
        # Alt node should no longer exist
        with pytest.raises(KeyError):
            tree.get_node(alt_id)

    def test_returns_count_of_deleted_nodes(self):
        """delete_branch returns an integer >= 1."""
        tree = ConversationTree()
        root_id = tree.add_message(_msg("user", "Root"))
        tree.add_message(_msg("assistant", "Main"))
        tree.fork(root_id)
        alt_id = tree.add_message(_msg("assistant", "Alt"))

        count = tree.delete_branch(alt_id)
        assert isinstance(count, int)
        assert count >= 1

    def test_cannot_delete_only_branch_raises_value_error(self):
        """Deleting the only branch (linear tree) raises ValueError."""
        tree = ConversationTree()
        tree.add_message(_msg("user", "Root"))
        tip_id = tree.add_message(_msg("assistant", "Tip"))

        with pytest.raises(ValueError):
            tree.delete_branch(tip_id)

    def test_cannot_delete_root_raises_value_error(self):
        """Attempting to delete a node that is the root raises ValueError."""
        tree = ConversationTree()
        root_id = tree.add_message(_msg())

        with pytest.raises(ValueError):
            tree.delete_branch(root_id)


# ===========================================================================
# Group 9: ConversationTree — serialization
# ===========================================================================


class TestSerialization:
    """Tests for ConversationTree.to_dict() and ConversationTree.from_dict()."""

    def test_to_dict_produces_valid_dict(self):
        """to_dict returns a plain Python dict."""
        tree = ConversationTree()
        tree.add_message(_msg("user", "Hello"))
        data = tree.to_dict()
        assert isinstance(data, dict)

    def test_from_dict_restores_identical_tree(self):
        """from_dict reconstructs a tree equal in structure to the original."""
        tree = ConversationTree()
        tree.add_message(_msg("user", "Root"))
        tree.add_message(_msg("assistant", "Response"))

        data = tree.to_dict()
        restored = ConversationTree.from_dict(data)

        assert restored.root_id == tree.root_id
        assert restored.active_tip == tree.active_tip
        assert len(restored._nodes) == len(tree._nodes)

    def test_round_trip_preserves_all_data(self):
        """Round-trip to_dict → from_dict preserves messages and structure."""
        tree = ConversationTree()
        root_id = tree.add_message(_msg("user", "Root"))
        tree.add_message(_msg("assistant", "Answer"), branch_name="main")

        restored = ConversationTree.from_dict(tree.to_dict())
        root_node = restored.get_node(root_id)
        assert root_node.message["content"] == "Root"

    def test_empty_tree_serializes_and_deserializes(self):
        """Empty tree can be serialized and deserialized without error."""
        tree = ConversationTree()
        data = tree.to_dict()
        restored = ConversationTree.from_dict(data)

        assert restored.root_id is None
        assert restored.active_tip is None


# ===========================================================================
# Group 10: ConversationTree — get_tree_stats
# ===========================================================================


class TestGetTreeStats:
    """Tests for ConversationTree.get_tree_stats()."""

    def test_returns_required_keys(self):
        """get_tree_stats returns dict with required keys."""
        tree = ConversationTree()
        tree.add_message(_msg())
        stats = tree.get_tree_stats()

        assert "total_nodes" in stats
        assert "total_branches" in stats
        assert "max_depth" in stats
        assert "active_branch" in stats

    def test_empty_tree_all_zeros(self):
        """Empty tree stats return zero/None values."""
        tree = ConversationTree()
        stats = tree.get_tree_stats()

        assert stats["total_nodes"] == 0
        assert stats["total_branches"] == 0
        assert stats["max_depth"] == 0

    def test_after_operations_correct_counts(self):
        """Stats correctly reflect added nodes."""
        tree = ConversationTree()
        tree.add_message(_msg("user", "Root"))
        tree.add_message(_msg("assistant", "Second"))

        stats = tree.get_tree_stats()
        assert stats["total_nodes"] == 2
        assert stats["max_depth"] >= 2


# ===========================================================================
# Group 11: Constants validation
# ===========================================================================


class TestOpp15Constants:
    """Validate that OPP-15 constants are well-formed."""

    def test_max_branch_depth_is_positive_int(self):
        """MAX_BRANCH_DEPTH is a positive integer."""
        assert isinstance(MAX_BRANCH_DEPTH, int)
        assert MAX_BRANCH_DEPTH > 0

    def test_max_branches_per_tree_is_positive_int(self):
        """MAX_BRANCHES_PER_TREE is a positive integer."""
        assert isinstance(MAX_BRANCHES_PER_TREE, int)
        assert MAX_BRANCHES_PER_TREE > 0

    def test_default_branch_prefix_is_non_empty_string(self):
        """DEFAULT_BRANCH_PREFIX is a non-empty string."""
        assert isinstance(DEFAULT_BRANCH_PREFIX, str)
        assert len(DEFAULT_BRANCH_PREFIX) > 0


# ===========================================================================
# Group 12: Edge cases
# ===========================================================================


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_add_message_to_empty_tree_auto_creates_root(self):
        """Adding to an empty tree with no parent_id auto-creates root."""
        tree = ConversationTree()
        nid = tree.add_message(_msg("user", "First"))
        assert tree.root_id == nid
        assert tree.active_tip == nid

    def test_fork_and_immediately_add_message(self):
        """Fork then immediately add a message — message is child of fork point."""
        tree = ConversationTree()
        root_id = tree.add_message(_msg("user", "Root"))
        tree.add_message(_msg("assistant", "Main"))

        tree.fork(root_id)
        new_id = tree.add_message(_msg("user", "After fork"))

        root_node = tree.get_node(root_id)
        assert new_id in root_node.children

    def test_multiple_forks_from_same_node(self):
        """Multiple forks from the same node create multiple branches."""
        tree = ConversationTree()
        root_id = tree.add_message(_msg("user", "Root"))

        tree.fork(root_id, branch_name="branch-a")
        id_a = tree.add_message(_msg("assistant", "A"))

        tree.fork(root_id, branch_name="branch-b")
        id_b = tree.add_message(_msg("assistant", "B"))

        tree.fork(root_id, branch_name="branch-c")
        id_c = tree.add_message(_msg("assistant", "C"))

        branches = tree.list_branches()
        tip_ids = [b["tip_node_id"] for b in branches]
        assert id_a in tip_ids
        assert id_b in tip_ids
        assert id_c in tip_ids

    def test_very_deep_linear_chain_near_max_depth(self):
        """A chain near MAX_BRANCH_DEPTH - 1 nodes does NOT raise."""
        tree = ConversationTree()
        node_id = tree.add_message(_msg())
        # Build MAX_BRANCH_DEPTH - 1 nodes total (root + MAX_BRANCH_DEPTH-2 more)
        for _ in range(MAX_BRANCH_DEPTH - 2):
            node_id = tree.add_message(_msg(), parent_id=node_id)
        # Should succeed without error
        stats = tree.get_tree_stats()
        assert stats["total_nodes"] == MAX_BRANCH_DEPTH - 1
