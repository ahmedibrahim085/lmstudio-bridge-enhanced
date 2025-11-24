#!/usr/bin/env bash

# Comprehensive Standalone Test Runner
# Date: November 2, 2025
# Purpose: Run ALL standalone test scripts and capture results

RESULTS_FILE="/tmp/standalone_tests_results.txt"
SUMMARY_FILE="/tmp/standalone_tests_summary.txt"

# Get the script directory (project root)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TESTS_DIR="${SCRIPT_DIR}/tests/standalone"

echo "=== STANDALONE TEST SCRIPTS EXECUTION ===" | tee "$RESULTS_FILE"
echo "Started at: $(date)" | tee -a "$RESULTS_FILE"
echo "Tests directory: ${TESTS_DIR}" | tee -a "$RESULTS_FILE"
echo "" | tee -a "$RESULTS_FILE"

cd "$SCRIPT_DIR"

# Get all test scripts from tests/standalone/
TEST_SCRIPTS=$(ls -1 "${TESTS_DIR}"/test*.py 2>/dev/null)
TOTAL_SCRIPTS=$(echo "$TEST_SCRIPTS" | wc -l | tr -d ' ')
PASSED=0
FAILED=0
SKIPPED=0

echo "Found $TOTAL_SCRIPTS standalone test scripts" | tee -a "$RESULTS_FILE"
echo "" | tee -a "$RESULTS_FILE"

# Run each script
SCRIPT_NUM=1
for script in $TEST_SCRIPTS; do
    echo "[$SCRIPT_NUM/$TOTAL_SCRIPTS] Running: $script" | tee -a "$RESULTS_FILE"
    echo "----------------------------------------" | tee -a "$RESULTS_FILE"

    # Run script (no timeout on macOS)
    python3 "$script" >> "$RESULTS_FILE" 2>&1
    EXIT_CODE=$?

    if [ $EXIT_CODE -eq 0 ]; then
        echo "✅ PASSED: $script" | tee -a "$RESULTS_FILE"
        PASSED=$((PASSED + 1))
    else
        echo "❌ FAILED: $script (exit code: $EXIT_CODE)" | tee -a "$RESULTS_FILE"
        FAILED=$((FAILED + 1))
    fi

    echo "" | tee -a "$RESULTS_FILE"
    SCRIPT_NUM=$((SCRIPT_NUM + 1))
done

# Generate summary
echo "=== SUMMARY ===" | tee "$SUMMARY_FILE" | tee -a "$RESULTS_FILE"
echo "Total Scripts: $TOTAL_SCRIPTS" | tee -a "$SUMMARY_FILE" | tee -a "$RESULTS_FILE"
echo "Passed: $PASSED" | tee -a "$SUMMARY_FILE" | tee -a "$RESULTS_FILE"
echo "Failed: $FAILED" | tee -a "$SUMMARY_FILE" | tee -a "$RESULTS_FILE"
echo "Skipped: $SKIPPED" | tee -a "$SUMMARY_FILE" | tee -a "$RESULTS_FILE"
echo "Completed at: $(date)" | tee -a "$SUMMARY_FILE" | tee -a "$RESULTS_FILE"

echo ""
echo "Results saved to: $RESULTS_FILE"
echo "Summary saved to: $SUMMARY_FILE"
