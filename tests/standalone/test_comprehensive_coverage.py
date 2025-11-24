#!/usr/bin/env python3
"""
Comprehensive test suite agreed upon after deep discussion with local LLM.

This implements the 3 HIGH-PRIORITY tests identified through collaborative analysis:
1. autonomous_persistent_session - Session persistence across tasks
2. autonomous_filesystem_full - Multi-tool filesystem operations
3. autonomous_memory_full - Knowledge graph building

These tests cover the critical integration points identified as gaps in current coverage.
"""

import asyncio
import logging
import sys
import os
import tempfile
import uuid

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


async def test_persistent_session():
    """
    Test 1: autonomous_persistent_session - HIGHEST PRIORITY (NOT TESTED AT ALL)

    Validates:
    - Running multiple tasks in ONE session
    - Directory switching between tasks
    - Session state persistence
    - Tool results correct across all tasks
    """
    from tools.autonomous import AutonomousExecutionTools

    logger.info("="*80)
    logger.info("TEST 1: autonomous_persistent_session (CRITICAL - NOT TESTED BEFORE)")
    logger.info("="*80)

    # Create unique test directories
    dir1 = "/private/tmp/test_session_dir1"
    dir2 = "/private/tmp/test_session_dir2"
    os.makedirs(dir1, exist_ok=True)
    os.makedirs(dir2, exist_ok=True)

    # Unique identifiers to prevent hallucination
    unique_id_1 = f"UNIQUE_PERSISTENT_SESSION_TEST_{uuid.uuid4().hex[:8]}"
    unique_id_2 = f"UNIQUE_SESSION_DIR2_TEST_{uuid.uuid4().hex[:8]}"

    agent = AutonomousExecutionTools()

    tasks = [
        {
            "task": f"Create a file at {dir1}/session_test.txt with content: {unique_id_1}",
            "working_directory": dir1
        },
        {
            "task": f"Read the file {dir1}/session_test.txt and tell me the unique string it contains",
            "working_directory": dir1
        },
        {
            "task": f"Create a file at {dir2}/session_test2.txt with content: {unique_id_2}",
            "working_directory": dir2  # DIRECTORY SWITCH!
        },
        {
            "task": f"Read the file {dir2}/session_test2.txt and tell me the unique string it contains",
            "working_directory": dir2
        }
    ]

    logger.info(f"Running 4 tasks in ONE persistent session")
    logger.info(f"Unique ID 1: {unique_id_1}")
    logger.info(f"Unique ID 2: {unique_id_2}")

    results = await agent.autonomous_persistent_session(
        tasks=tasks,
        initial_directory=dir1,
        max_rounds=10
    )

    logger.info("-"*80)
    for i, result in enumerate(results, 1):
        logger.info(f"Task {i} Result: {result[:100]}...")

    # Cleanup first (before assertions)
    try:
        os.remove(f"{dir1}/session_test.txt")
        os.remove(f"{dir2}/session_test2.txt")
    except:
        pass

    # Validate all tasks completed
    assert len(results) == 4, (
        f"Expected 4 task results, got {len(results)}. "
        f"Session may have timed out or LLM failed to respond. "
        f"Results: {results}"
    )

    # Check task 2 got unique_id_1
    assert unique_id_1 in results[1], (
        f"Task 2 failed: Expected {unique_id_1} in result, got: {results[1][:200]}"
    )
    logger.info(f"✅ Task 2 passed: Found {unique_id_1}")

    # Check task 4 got unique_id_2 (after directory switch!)
    assert unique_id_2 in results[3], (
        f"Task 4 failed: Expected {unique_id_2} in result, got: {results[3][:200]}"
    )
    logger.info(f"✅ Task 4 passed: Found {unique_id_2} after directory switch")

    logger.info("✅ TEST 1 PASSED: Persistent session works across tasks and directories!")


async def test_filesystem_multi_tool():
    """
    Test 2: autonomous_filesystem_full - Multi-tool chain

    Tests the full filesystem lifecycle:
    1. write_file - Create file with unique content
    2. read_text_file - Verify write worked
    3. list_directory - Verify file appears in listing
    4. search_files - Find file by pattern
    5. edit_file - Modify the file
    6. read_text_file - Verify edit worked
    """
    from tools.autonomous import AutonomousExecutionTools

    logger.info("\n" + "="*80)
    logger.info("TEST 2: autonomous_filesystem_full - Multi-tool chain")
    logger.info("="*80)

    test_dir = "/private/tmp/test_filesystem_multi"
    os.makedirs(test_dir, exist_ok=True)

    # Unique content
    unique_original = f"ORIGINAL_CONTENT_{uuid.uuid4().hex[:8]}"
    unique_edited = f"EDITED_CONTENT_{uuid.uuid4().hex[:8]}"
    test_filename = f"multitest_{uuid.uuid4().hex[:6]}.txt"

    agent = AutonomousExecutionTools()

    task = f"""
    Perform these filesystem operations in sequence:

    1. Create a file at {test_dir}/{test_filename} with content: {unique_original}
    2. Read the file back and verify it contains: {unique_original}
    3. List the directory {test_dir} and verify {test_filename} appears
    4. Search for files matching pattern "*{test_filename[:10]}*" in {test_dir}
    5. Add a new line to the file with content: {unique_edited}
    6. Read the file again and verify it now contains BOTH: {unique_original} and {unique_edited}

    Report on each step and confirm both unique strings are in the final file content.
    Use write_file, read_text_file, list_directory, search_files, and edit_file tools.
    """

    logger.info(f"Test file: {test_filename}")
    logger.info(f"Original content: {unique_original}")
    logger.info(f"Edited content: {unique_edited}")

    result = await agent.autonomous_filesystem_full(
        task=task,
        working_directory=test_dir,
        max_rounds=15
    )

    logger.info("-"*80)
    logger.info(f"Result: {result}")

    # Verify both unique strings are in result
    success = True
    if unique_original not in result:
        logger.error(f"❌ Failed: Original content {unique_original} not found")
        success = False
    else:
        logger.info(f"✅ Original content verified: {unique_original}")

    if unique_edited not in result:
        logger.error(f"❌ Failed: Edited content {unique_edited} not found")
        success = False
    else:
        logger.info(f"✅ Edited content verified: {unique_edited}")

    # Cleanup
    try:
        os.remove(f"{test_dir}/{test_filename}")
    except:
        pass

    if success:
        logger.info("✅ TEST 2 PASSED: Multi-tool filesystem operations work!")
        return True
    else:
        logger.error("❌ TEST 2 FAILED: Some filesystem operations failed")
        return False


async def test_memory_knowledge_graph():
    """
    Test 3: autonomous_memory_full - Knowledge graph building

    Tests building a complete knowledge graph:
    1. Create entity "Person"
    2. Create entity "Project"
    3. Create relation between them
    4. Add observations to Person
    5. Search to verify structure
    6. Read graph to verify everything exists
    """
    from tools.autonomous import AutonomousExecutionTools

    logger.info("\n" + "="*80)
    logger.info("TEST 3: autonomous_memory_full - Knowledge graph")
    logger.info("="*80)

    # Unique entity names
    person_name = f"Person_Test_{uuid.uuid4().hex[:8]}"
    project_name = f"Project_Test_{uuid.uuid4().hex[:8]}"
    observation_text = f"UNIQUE_OBSERVATION_{uuid.uuid4().hex[:8]}"
    relation_type = "works_on"

    agent = AutonomousExecutionTools()

    task = f"""
    Build a knowledge graph with these exact steps:

    1. Create an entity named '{person_name}' of type 'Person' with observation 'Software engineer'
    2. Create an entity named '{project_name}' of type 'Project' with observation 'AI project'
    3. Create a relation: '{person_name}' '{relation_type}' '{project_name}'
    4. Add an observation to '{person_name}': '{observation_text}'
    5. Search for entities containing 'Test_' to verify both entities exist
    6. Read the entire knowledge graph and verify:
       - Entity {person_name} exists
       - Entity {project_name} exists
       - Relation '{relation_type}' exists between them
       - Observation '{observation_text}' is attached to {person_name}

    Use create_entities, create_relations, add_observations, search_nodes, and read_graph tools.
    Report all the unique names to prove you actually used the tools.
    """

    logger.info(f"Person entity: {person_name}")
    logger.info(f"Project entity: {project_name}")
    logger.info(f"Observation: {observation_text}")

    result = await agent.autonomous_memory_full(
        task=task,
        max_rounds=15
    )

    logger.info("-"*80)
    logger.info(f"Result: {result}")

    # Verify all unique identifiers are in result
    success = True

    if person_name not in result:
        logger.error(f"❌ Failed: Person entity {person_name} not found")
        success = False
    else:
        logger.info(f"✅ Person entity verified: {person_name}")

    if project_name not in result:
        logger.error(f"❌ Failed: Project entity {project_name} not found")
        success = False
    else:
        logger.info(f"✅ Project entity verified: {project_name}")

    if observation_text not in result:
        logger.error(f"❌ Failed: Observation {observation_text} not found")
        success = False
    else:
        logger.info(f"✅ Observation verified: {observation_text}")

    if relation_type not in result:
        logger.error(f"❌ Failed: Relation type {relation_type} not found")
        success = False
    else:
        logger.info(f"✅ Relation verified: {relation_type}")

    if success:
        logger.info("✅ TEST 3 PASSED: Knowledge graph building works!")
        return True
    else:
        logger.error("❌ TEST 3 FAILED: Knowledge graph has issues")
        return False


async def main():
    """Run all comprehensive tests agreed upon with local LLM."""
    logger.info("\n" + "🎯"*40)
    logger.info("COMPREHENSIVE TEST COVERAGE SUITE")
    logger.info("Tests agreed upon after deep discussion with local LLM")
    logger.info("🎯"*40 + "\n")

    results = {}

    # Test 1: Persistent session (HIGHEST PRIORITY)
    try:
        results['persistent_session'] = await test_persistent_session()
    except Exception as e:
        logger.error(f"❌ TEST 1 EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        results['persistent_session'] = False

    # Test 2: Filesystem multi-tool
    try:
        results['filesystem_multi'] = await test_filesystem_multi_tool()
    except Exception as e:
        logger.error(f"❌ TEST 2 EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        results['filesystem_multi'] = False

    # Test 3: Memory knowledge graph
    try:
        results['memory_graph'] = await test_memory_knowledge_graph()
    except Exception as e:
        logger.error(f"❌ TEST 3 EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        results['memory_graph'] = False

    # Final summary
    logger.info("\n" + "="*80)
    logger.info("COMPREHENSIVE TEST RESULTS")
    logger.info("="*80)

    for test_name, result in results.items():
        if result is True:
            logger.info(f"✅ {test_name.upper()}: PASSED")
        else:
            logger.error(f"❌ {test_name.upper()}: FAILED")

    passed = sum(1 for r in results.values() if r is True)
    total = len(results)

    logger.info("-"*80)
    logger.info(f"TOTAL: {passed}/{total} tests passed")

    if passed == total:
        logger.info("\n🎉 ALL COMPREHENSIVE TESTS PASSED!")
        logger.info("✅ Complete test coverage achieved for all critical integration points")
    else:
        logger.error(f"\n❌ {total - passed} test(s) failed")
        logger.error("More work needed to achieve full coverage")

    logger.info("="*80)


if __name__ == "__main__":
    asyncio.run(main())
