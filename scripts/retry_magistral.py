#!/usr/bin/env python3
"""Retry getting Magistral review with longer timeout."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from llm.llm_client import LLMClient

# Shorter, more focused prompt for Magistral
MAGISTRAL_PROMPT = """You are reviewing Phase 2 Multi-Model Support for lmstudio-bridge-enhanced MCP server.

**Changes Made**:
- Added model parameter to 3 agent methods (autonomous_with_mcp, autonomous_with_multiple_mcps, autonomous_discover_and_execute)
- Exposed model parameter through MCP tool interface (3 tools callable by Claude Code)
- Integrated custom exception hierarchy (5 types: LLMTimeoutError, LLMConnectionError, LLMRateLimitError, LLMResponseError, LLMError)
- Applied @retry_with_backoff decorator to 4 core methods
- Fixed ModelValidator URL bug (/v1/v1/models → /v1/models)
- All 6 integration tests passed with real LM Studio

**Your Role**: General Architecture Review

Please provide:
1. **Rating**: 1-10
2. **Critical Issues**: Production blockers
3. **Major Issues**: Important but not blocking
4. **Minor Issues**: Nice-to-haves
5. **Strengths**: What's done well
6. **Recommendations**: Specific improvements

Keep it concise and focused on architecture, design patterns, and security."""

def main():
    print("Retrying Magistral review with longer timeout and simpler prompt...")

    try:
        from config.constants import DEFAULT_REVIEW_MODEL
        client = LLMClient(model=DEFAULT_REVIEW_MODEL)

        # Much longer timeout for Magistral (120s instead of 55s)
        response = client.chat_completion(
            messages=[{"role": "user", "content": MAGISTRAL_PROMPT}],
            max_tokens=2000,  # Shorter than before
            temperature=0.7,
            timeout=120  # 2 minutes
        )

        review = response['choices'][0]['message']['content']

        print(f"\n✅ Got Magistral review ({len(review)} characters)\n")

        # Append to existing review file
        review_file = Path(__file__).parent / "PHASE2_LLM_REVIEWS.md"
        content = review_file.read_text()

        # Replace the ERROR line with actual review
        updated_content = content.replace(
            "ERROR: Failed to get review from Magistral: Chat completion timed out. LM Studio may be overloaded or unresponsive.",
            review
        )

        review_file.write_text(updated_content)

        print("✅ Updated PHASE2_LLM_REVIEWS.md with Magistral review")

    except Exception as e:
        print(f"❌ Failed again: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
