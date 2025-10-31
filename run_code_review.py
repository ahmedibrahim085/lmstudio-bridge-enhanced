#!/usr/bin/env python3
"""
Run code review with local LLM.

This script reviews code files using the local LM Studio LLM
and documents the results.
"""

import sys
sys.path.insert(0, '.')

from llm.llm_client import LLMClient


def review_file(file_path: str, llm: LLMClient):
    """Review a single file with the LLM."""

    # Read the file
    with open(file_path, 'r') as f:
        code = f.read()

    # Create review prompt
    messages = [
        {
            "role": "system",
            "content": "You are a senior Python code reviewer with expertise in best practices, security, and performance. Provide specific, actionable feedback."
        },
        {
            "role": "user",
            "content": f"""Review this Python code for issues and improvements:

```python
{code}
```

Focus on:
1. Logic errors
2. Edge cases not handled
3. Security vulnerabilities
4. Performance issues
5. Code quality and best practices

Provide a rating from 1-10 and list any issues found."""
        }
    ]

    # Call LLM with correct API (synchronous, no await)
    response = llm.chat_completion(
        messages=messages,
        max_tokens=2048,
        temperature=0.3
    )

    return response['choices'][0]['message']['content']


def main():
    """Main code review function."""
    # Initialize LLMClient with specific model
    from config.constants import DEFAULT_REVIEW_MODEL
    llm = LLMClient(model=DEFAULT_REVIEW_MODEL)

    print("="*60)
    print("CODE REVIEW: llm/model_validator.py")
    print("="*60)
    print()

    try:
        review = review_file(
            'llm/model_validator.py',
            llm
        )

        print(review)
        print()
        print("="*60)
        print("CODE REVIEW COMPLETE")
        print("="*60)

    except Exception as e:
        print(f"ERROR: Code review failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
