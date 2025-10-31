#!/usr/bin/env python3
"""
Get LLM Reviews for Phase 2 Implementation

Uses LLMClient directly to get reviews from 3 local LLMs:
1. Magistral - General architecture review
2. Qwen3-Coder-30B - Code quality review
3. Qwen3-Thinking - Deep analysis review
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from llm.llm_client import LLMClient


# Read the review request document
REVIEW_REQUEST_PATH = Path(__file__).parent / "PHASE2_REVIEW_REQUEST.md"
with open(REVIEW_REQUEST_PATH) as f:
    review_context = f.read()


REVIEW_PROMPT_TEMPLATE = """You are reviewing the Phase 2 Multi-Model Support implementation for lmstudio-bridge-enhanced MCP server.

{role_specific_instructions}

## Implementation Overview

{review_context}

## Your Task

Please provide a comprehensive code review covering:

1. **Rating**: 1-10 for overall quality
2. **Critical Issues**: Anything that blocks production (show line numbers if possible)
3. **Major Issues**: Important but not blocking
4. **Minor Issues**: Nice-to-haves
5. **Strengths**: What's done well
6. **Recommendations**: Specific improvements

Focus on:
- Code correctness
- Error handling robustness
- Async/await safety
- Production readiness
- Maintainability

Be honest and thorough. This is for improving the implementation.
"""


MAGISTRAL_INSTRUCTIONS = """
**Your Role**: General Architecture Reviewer (Magistral)

Focus on:
- Overall architecture assessment
- Design patterns and anti-patterns
- Security concerns
- API design quality
- Integration points
- Backward compatibility
"""


QWEN_CODER_INSTRUCTIONS = """
**Your Role**: Code Quality Reviewer (Qwen3-Coder-30B)

Focus on:
- Code style and Python best practices
- Type hints usage and correctness
- Error handling patterns
- Performance considerations
- Code duplication and DRY principle
- Documentation quality
"""


QWEN_THINKING_INSTRUCTIONS = """
**Your Role**: Deep Analysis Reviewer (Qwen3-Thinking)

Focus on:
- Edge cases not covered in tests
- Potential race conditions or async issues
- Integration points that could fail
- Long-term maintenance concerns
- Subtle bugs or logic errors
- Memory leaks or resource handling
"""


async def get_review(model: str, role_instructions: str, reviewer_name: str) -> str:
    """Get review from a specific model."""
    print(f"\n{'='*80}")
    print(f"Getting review from {reviewer_name} ({model})...")
    print(f"{'='*80}\n")

    try:
        client = LLMClient(model=model)

        prompt = REVIEW_PROMPT_TEMPLATE.format(
            role_specific_instructions=role_instructions,
            review_context=review_context
        )

        response = client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,  # Long review expected
            temperature=0.7
        )

        review = response['choices'][0]['message']['content']

        print(f"✅ Got review from {reviewer_name} ({len(review)} characters)\n")

        return review

    except Exception as e:
        print(f"❌ Failed to get review from {reviewer_name}: {e}\n")
        import traceback
        traceback.print_exc()
        return f"ERROR: Failed to get review from {reviewer_name}: {e}"


async def main():
    """Get all 3 reviews."""
    print("="*80)
    print("PHASE 2 LLM CODE REVIEWS")
    print("="*80)
    print("\nRequesting reviews from 3 local LLMs...")
    print("This may take several minutes...\n")

    reviews = {}

    from config.constants import REVIEW_MODELS

    # 1. Magistral - General Review
    reviews["magistral"] = await get_review(
        model=REVIEW_MODELS[0],  # magistral-small-2509
        role_instructions=MAGISTRAL_INSTRUCTIONS,
        reviewer_name="Magistral"
    )

    # 2. Qwen3-Coder-30B - Code Quality
    reviews["qwen_coder"] = await get_review(
        model=REVIEW_MODELS[1],  # qwen3-coder-30b
        role_instructions=QWEN_CODER_INSTRUCTIONS,
        reviewer_name="Qwen3-Coder-30B"
    )

    # 3. Qwen3-Thinking - Deep Analysis
    reviews["qwen_thinking"] = await get_review(
        model=REVIEW_MODELS[2],  # qwen3-4b-thinking-2507
        role_instructions=QWEN_THINKING_INSTRUCTIONS,
        reviewer_name="Qwen3-Thinking"
    )

    # Save all reviews to markdown file
    output_path = Path(__file__).parent / "PHASE2_LLM_REVIEWS.md"

    with open(output_path, "w") as f:
        f.write("# Phase 2 Multi-Model Support - LLM Code Reviews\n\n")
        f.write("**Date**: October 30, 2025\n")
        f.write("**Reviewers**: Magistral, Qwen3-Coder-30B, Qwen3-Thinking\n")
        f.write("**Status**: Complete\n\n")
        f.write("---\n\n")

        # Magistral Review
        f.write("## Review 1: Magistral (General Architecture)\n\n")
        f.write("**Model**: mistralai/magistral-small-2509\n")
        f.write("**Focus**: Architecture, Design Patterns, Security\n\n")
        f.write(reviews["magistral"])
        f.write("\n\n---\n\n")

        # Qwen3-Coder Review
        f.write("## Review 2: Qwen3-Coder-30B (Code Quality)\n\n")
        f.write("**Model**: qwen/qwen3-coder-30b\n")
        f.write("**Focus**: Code Style, Best Practices, Performance\n\n")
        f.write(reviews["qwen_coder"])
        f.write("\n\n---\n\n")

        # Qwen3-Thinking Review
        f.write("## Review 3: Qwen3-Thinking (Deep Analysis)\n\n")
        f.write("**Model**: qwen/qwen3-4b-thinking-2507\n")
        f.write("**Focus**: Edge Cases, Race Conditions, Long-term Maintenance\n\n")
        f.write(reviews["qwen_thinking"])
        f.write("\n\n---\n\n")

        f.write("## Summary\n\n")
        f.write("All 3 LLM reviews completed. See individual sections above for detailed feedback.\n")

    print("\n" + "="*80)
    print("REVIEWS COMPLETE")
    print("="*80)
    print(f"\nAll reviews saved to: {output_path}\n")
    print("Summary:")
    print(f"  ✅ Magistral: {len(reviews['magistral'])} chars")
    print(f"  ✅ Qwen3-Coder-30B: {len(reviews['qwen_coder'])} chars")
    print(f"  ✅ Qwen3-Thinking: {len(reviews['qwen_thinking'])} chars")
    print()


if __name__ == "__main__":
    asyncio.run(main())
