#!/usr/bin/env python3
"""
Deep Investigation: HTTP 500 Error with /v1/responses + Tools

This script systematically tests different scenarios to understand
why /v1/responses returns HTTP 500 when called with tools.

Test Strategy:
1. Baseline: /v1/responses without tools (should work)
2. Minimal: /v1/responses with 1 simple tool
3. Small: /v1/responses with 3 tools
4. Medium: /v1/responses with 7 tools
5. Full: /v1/responses with 14 tools (original failing case)
6. Compare payloads with /v1/chat/completions (which works)
"""

import asyncio
import sys
import os
import json
import requests

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm.llm_client import LLMClient
from mcp_client.connection import MCPConnection
from mcp_client.tool_discovery import ToolDiscovery, SchemaConverter


class HTTP500Investigator:
    """Investigate HTTP 500 error with /v1/responses + tools."""

    def __init__(self):
        self.llm = LLMClient()
        self.results = {}

    def print_section(self, title):
        """Print section header."""
        print("\n" + "="*80)
        print(f"{title}")
        print("="*80 + "\n")

    def test_baseline_no_tools(self):
        """Test 1: Baseline - /v1/responses without tools."""
        self.print_section("TEST 1: Baseline - /v1/responses WITHOUT tools")

        try:
            response = self.llm.create_response(
                input_text="Say hello",
                model="default"
            )

            if response and 'id' in response:
                print("✅ Baseline works (no tools)")
                print(f"   Response ID: {response['id']}")
                self.results['baseline_no_tools'] = {'status': 'PASS'}
                return True
            else:
                print("❌ Baseline failed")
                self.results['baseline_no_tools'] = {'status': 'FAIL'}
                return False

        except Exception as e:
            print(f"❌ Error: {e}")
            self.results['baseline_no_tools'] = {'status': 'ERROR', 'error': str(e)}
            return False

    def test_minimal_one_tool(self):
        """Test 2: Minimal - /v1/responses with 1 simple tool."""
        self.print_section("TEST 2: Minimal - /v1/responses with 1 SIMPLE tool")

        try:
            # One very simple tool
            tools = [{
                "type": "function",
                "name": "get_time",
                "description": "Get current time",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }]

            print(f"Tool count: {len(tools)}")
            print(f"Tool payload size: {len(json.dumps(tools))} bytes")
            print()

            response = self.llm.create_response(
                input_text="What time is it?",
                tools=tools,
                model="default"
            )

            if response and 'id' in response:
                print("✅ SUCCESS with 1 simple tool!")
                print(f"   Response ID: {response['id']}")
                print(f"   Output: {json.dumps(response.get('output', []), indent=2)[:200]}")
                self.results['minimal_one_tool'] = {'status': 'PASS', 'tool_count': 1}
                return True
            else:
                print("❌ Failed with 1 tool")
                self.results['minimal_one_tool'] = {'status': 'FAIL'}
                return False

        except requests.exceptions.HTTPError as e:
            print(f"❌ HTTP Error: {e}")
            print(f"   Status: {e.response.status_code}")
            print(f"   Response: {e.response.text[:500]}")
            self.results['minimal_one_tool'] = {
                'status': 'ERROR',
                'error': str(e),
                'status_code': e.response.status_code
            }
            return False
        except Exception as e:
            print(f"❌ Error: {e}")
            self.results['minimal_one_tool'] = {'status': 'ERROR', 'error': str(e)}
            return False

    def test_small_three_tools(self):
        """Test 3: Small - /v1/responses with 3 tools."""
        self.print_section("TEST 3: Small - /v1/responses with 3 tools")

        try:
            # Three simple tools
            tools = [
                {
                    "type": "function",
                    "name": "get_time",
                    "description": "Get current time",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                },
                {
                    "type": "function",
                    "name": "add",
                    "description": "Add two numbers",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "a": {"type": "number"},
                            "b": {"type": "number"}
                        },
                        "required": ["a", "b"]
                    }
                },
                {
                    "type": "function",
                    "name": "greet",
                    "description": "Greet someone",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"}
                        },
                        "required": ["name"]
                    }
                }
            ]

            print(f"Tool count: {len(tools)}")
            print(f"Tool payload size: {len(json.dumps(tools))} bytes")
            print()

            response = self.llm.create_response(
                input_text="Use the tools",
                tools=tools,
                model="default"
            )

            if response and 'id' in response:
                print("✅ SUCCESS with 3 tools!")
                print(f"   Response ID: {response['id']}")
                self.results['small_three_tools'] = {'status': 'PASS', 'tool_count': 3}
                return True
            else:
                print("❌ Failed with 3 tools")
                self.results['small_three_tools'] = {'status': 'FAIL'}
                return False

        except requests.exceptions.HTTPError as e:
            print(f"❌ HTTP Error: {e}")
            print(f"   Status: {e.response.status_code}")
            print(f"   Response: {e.response.text[:500]}")
            self.results['small_three_tools'] = {
                'status': 'ERROR',
                'error': str(e),
                'status_code': e.response.status_code
            }
            return False
        except Exception as e:
            print(f"❌ Error: {e}")
            self.results['small_three_tools'] = {'status': 'ERROR', 'error': str(e)}
            return False

    async def test_filesystem_full_payload(self):
        """Test 4: Full - /v1/responses with 14 filesystem tools (original)."""
        self.print_section("TEST 4: Full - /v1/responses with 14 FILESYSTEM tools")

        try:
            # Connect to filesystem MCP and get all tools
            working_dir = os.path.dirname(os.path.abspath(__file__))
            connection = MCPConnection(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-filesystem", working_dir]
            )

            async with connection.connect() as session:
                # Discover all filesystem tools
                discovery = ToolDiscovery(session)
                all_tools = await discovery.discover_tools()
                openai_tools = SchemaConverter.mcp_tools_to_openai(all_tools)

                print(f"Tool count: {len(openai_tools)}")
                print(f"Tool payload size: {len(json.dumps(openai_tools))} bytes")
                print(f"\nTool names: {[t['function']['name'] for t in openai_tools[:5]]}...")
                print()

                # Convert to flattened format
                flattened_tools = LLMClient.convert_tools_to_responses_format(openai_tools)

                print("Attempting /v1/responses with full filesystem tools...")
                response = self.llm.create_response(
                    input_text="List files",
                    tools=flattened_tools,
                    model="default"
                )

                if response and 'id' in response:
                    print("✅ SUCCESS with 14 filesystem tools!")
                    print(f"   Response ID: {response['id']}")
                    self.results['filesystem_full'] = {'status': 'PASS', 'tool_count': len(openai_tools)}
                    return True
                else:
                    print("❌ Failed with 14 tools")
                    self.results['filesystem_full'] = {'status': 'FAIL'}
                    return False

        except requests.exceptions.HTTPError as e:
            print(f"❌ HTTP Error: {e}")
            print(f"   Status: {e.response.status_code}")
            print(f"   Response body: {e.response.text[:1000]}")

            # Try to parse error details
            try:
                error_json = e.response.json()
                print(f"\n   Error details:")
                print(f"   {json.dumps(error_json, indent=2)}")
            except:
                pass

            self.results['filesystem_full'] = {
                'status': 'ERROR',
                'error': str(e),
                'status_code': e.response.status_code,
                'response_body': e.response.text[:500]
            }
            return False
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            self.results['filesystem_full'] = {'status': 'ERROR', 'error': str(e)}
            return False

    def test_chat_completions_comparison(self):
        """Test 5: Compare - /v1/chat/completions with same tools."""
        self.print_section("TEST 5: Comparison - /v1/chat/completions with tools")

        try:
            # Same 3 tools as Test 3
            tools = [
                {
                    "type": "function",
                    "function": {  # Note: nested format for chat/completions
                        "name": "get_time",
                        "description": "Get current time",
                        "parameters": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "add",
                        "description": "Add two numbers",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "a": {"type": "number"},
                                "b": {"type": "number"}
                            },
                            "required": ["a", "b"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "greet",
                        "description": "Greet someone",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"}
                            },
                            "required": ["name"]
                        }
                    }
                }
            ]

            print(f"Tool count: {len(tools)}")
            print(f"Tool payload size: {len(json.dumps(tools))} bytes")
            print("Using /v1/chat/completions (for comparison)")
            print()

            response = self.llm.chat_completion(
                messages=[{"role": "user", "content": "Use the tools"}],
                tools=tools,
                max_tokens=100
            )

            if response and 'choices' in response:
                print("✅ /v1/chat/completions works with 3 tools")
                message = response['choices'][0]['message']
                if message.get('tool_calls'):
                    print(f"   Tool calls detected: {len(message['tool_calls'])}")
                self.results['chat_completions_comparison'] = {'status': 'PASS'}
                return True
            else:
                print("❌ /v1/chat/completions failed")
                self.results['chat_completions_comparison'] = {'status': 'FAIL'}
                return False

        except Exception as e:
            print(f"❌ Error: {e}")
            self.results['chat_completions_comparison'] = {'status': 'ERROR', 'error': str(e)}
            return False

    async def run_investigation(self):
        """Run all investigation tests."""
        print("\n" + "="*80)
        print("HTTP 500 ERROR INVESTIGATION - /v1/responses + Tools")
        print("="*80)
        print("\nSystematically testing different tool scenarios...")
        print("Goal: Understand why /v1/responses returns HTTP 500 with tools")
        print()

        tests_run = 0
        tests_passed = 0

        # Test 1: Baseline (no tools)
        result = self.test_baseline_no_tools()
        tests_run += 1
        if result: tests_passed += 1

        # Test 2: 1 simple tool
        result = self.test_minimal_one_tool()
        tests_run += 1
        if result: tests_passed += 1

        # Test 3: 3 tools
        result = self.test_small_three_tools()
        tests_run += 1
        if result: tests_passed += 1

        # Test 4: 14 filesystem tools (original failing case)
        result = await self.test_filesystem_full_payload()
        tests_run += 1
        if result: tests_passed += 1

        # Test 5: chat/completions comparison
        result = self.test_chat_completions_comparison()
        tests_run += 1
        if result: tests_passed += 1

        # Final summary
        self.print_final_summary(tests_run, tests_passed)

    def print_final_summary(self, total, passed):
        """Print investigation summary."""
        self.print_section("INVESTIGATION SUMMARY")

        print(f"Tests run: {total}")
        print(f"Tests passed: {passed}")
        print(f"Tests failed: {total - passed}")
        print()

        # Analyze results
        print("Result Analysis:")
        print("-" * 80)

        for test_name, result in self.results.items():
            status = result.get('status')
            icon = '✅' if status == 'PASS' else '❌'
            print(f"{icon} {test_name}: {status}")

            if status == 'ERROR':
                if 'status_code' in result:
                    print(f"   HTTP Status: {result['status_code']}")
                if 'tool_count' in result:
                    print(f"   Tool count: {result['tool_count']}")

        print()

        # Determine root cause
        self.print_section("ROOT CAUSE ANALYSIS")

        baseline = self.results.get('baseline_no_tools', {}).get('status')
        minimal = self.results.get('minimal_one_tool', {}).get('status')
        small = self.results.get('small_three_tools', {}).get('status')
        full = self.results.get('filesystem_full', {}).get('status')

        print("Analysis:")
        print()

        if baseline == 'PASS':
            print("✅ /v1/responses works WITHOUT tools")
        else:
            print("❌ /v1/responses broken even without tools (baseline issue)")
            return

        if minimal == 'PASS':
            print("✅ /v1/responses works with 1 simple tool")
        else:
            print("❌ /v1/responses fails even with 1 simple tool")
            print("   → Issue: Basic tool support is broken")
            return

        if small == 'PASS':
            print("✅ /v1/responses works with 3 tools")
        else:
            print("❌ /v1/responses fails with 3 tools")
            print("   → Issue: Multiple tools cause failure")
            return

        if full == 'PASS':
            print("✅ /v1/responses works with 14 filesystem tools!")
            print("   → Previous failure was likely transient or environment-specific")
        else:
            print("❌ /v1/responses fails with 14 filesystem tools")
            print()
            print("Conclusion:")
            print("  → Tool complexity or payload size causes HTTP 500")
            print("  → Filesystem tools have more complex schemas than simple tools")
            print("  → Possible issues:")
            print("     1. Payload size limit exceeded")
            print("     2. Complex nested schemas not handled properly")
            print("     3. LM Studio bug with certain tool patterns")

        print()

        # Save results
        results_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'investigation_http_500_results.json'
        )
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"Results saved to: {results_file}")
        print()


async def main():
    """Main investigation runner."""
    investigator = HTTP500Investigator()
    await investigator.run_investigation()


if __name__ == "__main__":
    asyncio.run(main())
