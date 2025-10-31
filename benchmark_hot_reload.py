#!/usr/bin/env python3
"""
Benchmark the performance cost of hot reload (reading .mcp.json on every call).

This measures:
1. File read time
2. JSON parse time
3. Total reload time
4. Impact on tool call latency
"""

import time
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_client.discovery import MCPDiscovery
from config.constants import (
    DEFAULT_LMSTUDIO_HOST,
    DEFAULT_LMSTUDIO_PORT,
    MODELS_ENDPOINT,
)

print("="*80)
print("HOT RELOAD PERFORMANCE BENCHMARK")
print("="*80)
print()

# Test 1: Measure file read + JSON parse (single call)
print("TEST 1: Single .mcp.json reload")
print("-"*80)

mcp_json_path = os.path.expanduser("~/.lmstudio/mcp.json")
print(f"File: {mcp_json_path}")
print(f"File size: {os.path.getsize(mcp_json_path)} bytes")
print()

start = time.perf_counter()
with open(mcp_json_path) as f:
    config = json.load(f)
end = time.perf_counter()

read_time = (end - start) * 1000  # Convert to milliseconds
print(f"Read + Parse time: {read_time:.4f} ms")
print(f"MCPs found: {len(config.get('mcpServers', {}))}")
print()

# Test 2: Measure MCPDiscovery instantiation (includes all operations)
print("TEST 2: MCPDiscovery instantiation (full reload)")
print("-"*80)

start = time.perf_counter()
discovery = MCPDiscovery(mcp_json_path)
end = time.perf_counter()

instantiation_time = (end - start) * 1000
print(f"Instantiation time: {instantiation_time:.4f} ms")
print()

# Test 3: Repeated calls (simulate tool calls)
print("TEST 3: Repeated reloads (100 calls)")
print("-"*80)

iterations = 100
start = time.perf_counter()
for i in range(iterations):
    discovery = MCPDiscovery(mcp_json_path)
    _ = discovery.list_available_mcps()
end = time.perf_counter()

total_time = (end - start) * 1000
avg_time = total_time / iterations
print(f"Total time: {total_time:.2f} ms")
print(f"Average per call: {avg_time:.4f} ms")
print(f"Calls per second: {1000/avg_time:.0f}")
print()

# Test 4: Repeated calls (1000 calls for better accuracy)
print("TEST 4: Heavy load (1000 calls)")
print("-"*80)

iterations = 1000
start = time.perf_counter()
for i in range(iterations):
    discovery = MCPDiscovery(mcp_json_path)
    _ = discovery.list_available_mcps()
end = time.perf_counter()

total_time = (end - start) * 1000
avg_time = total_time / iterations
print(f"Total time: {total_time:.2f} ms")
print(f"Average per call: {avg_time:.4f} ms")
print(f"Calls per second: {1000/avg_time:.0f}")
print()

# Test 5: Compare with cached (no reload)
print("TEST 5: Cached vs Hot Reload comparison")
print("-"*80)

# Cached (current behavior)
discovery_cached = MCPDiscovery(mcp_json_path)
iterations = 1000

start = time.perf_counter()
for i in range(iterations):
    _ = discovery_cached.list_available_mcps()
end = time.perf_counter()
cached_avg = ((end - start) * 1000) / iterations

# Hot reload
start = time.perf_counter()
for i in range(iterations):
    discovery = MCPDiscovery(mcp_json_path)
    _ = discovery.list_available_mcps()
end = time.perf_counter()
reload_avg = ((end - start) * 1000) / iterations

overhead = reload_avg - cached_avg
overhead_percent = (overhead / cached_avg) * 100 if cached_avg > 0 else 0

print(f"Cached (current):     {cached_avg:.4f} ms per call")
print(f"Hot reload:           {reload_avg:.4f} ms per call")
print(f"Overhead:             {overhead:.4f} ms per call")
print(f"Overhead percentage:  {overhead_percent:.1f}%")
print()

# Test 6: Context - Compare with actual LLM call
print("TEST 6: Context - LLM API call time for comparison")
print("-"*80)

import requests

try:
    # Use constants instead of hardcoded values
    lm_studio_url = f"http://{os.getenv('LMSTUDIO_HOST', DEFAULT_LMSTUDIO_HOST)}:{os.getenv('LMSTUDIO_PORT', str(DEFAULT_LMSTUDIO_PORT))}{MODELS_ENDPOINT}"

    start = time.perf_counter()
    response = requests.get(lm_studio_url, timeout=5)
    end = time.perf_counter()

    llm_api_time = (end - start) * 1000
    print(f"LM Studio API call (GET /models): {llm_api_time:.2f} ms")
    print()
    print(f"Hot reload overhead: {reload_avg:.4f} ms")
    print(f"LLM API call time:   {llm_api_time:.2f} ms")
    print(f"Hot reload is {llm_api_time/reload_avg:.1f}x faster than LLM API call")
    print()
except Exception as e:
    print(f"Could not measure LLM API time: {e}")
    print()

# Summary
print("="*80)
print("SUMMARY")
print("="*80)
print()

print("Performance Impact of Hot Reload:")
print(f"  • Per tool call: ~{reload_avg:.4f} ms")
print(f"  • Overhead vs cached: ~{overhead:.4f} ms ({overhead_percent:.1f}%)")
print()

if reload_avg < 1.0:
    print("✅ NEGLIGIBLE: Hot reload takes < 1 millisecond")
    print("   This is MUCH faster than:")
    print("   - Network requests (10-100ms)")
    print("   - LLM inference (100-5000ms)")
    print("   - Disk I/O for actual MCP operations (1-10ms)")
    print()
    print("   RECOMMENDATION: Hot reload is essentially FREE")
elif reload_avg < 10.0:
    print("✅ MINIMAL: Hot reload takes < 10 milliseconds")
    print("   This is MUCH faster than:")
    print("   - LLM inference (100-5000ms)")
    print("   - Most MCP operations (10-100ms)")
    print()
    print("   RECOMMENDATION: Hot reload overhead is acceptable")
elif reload_avg < 100.0:
    print("⚠️ NOTICEABLE: Hot reload takes < 100 milliseconds")
    print("   This adds visible latency to tool calls")
    print()
    print("   RECOMMENDATION: Consider TTL cache (reload every 60s)")
else:
    print("❌ SIGNIFICANT: Hot reload takes > 100 milliseconds")
    print("   This is a bottleneck")
    print()
    print("   RECOMMENDATION: Use TTL cache or file watcher")

print()
print("="*80)
