"""Resolved configuration output from DynamicResolver (OPP-31 Phase 3).

A ResolvedConfig is the fully-resolved, immutable result of combining:
  role template + family overlay + user overrides + critical constraints.
It is ready to be passed directly to the LM Studio API.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ResolvedConfig:
    """Fully resolved, immutable configuration — ready for LM Studio API.

    Attributes:
        role_name: Which role template was used.
        model_id: Which model was assigned (explicit or auto-resolved).
        family: Detected model family (e.g. 'qwen', 'deepseek-r1', 'unknown').
        task_type: Knowledge base task type used for overlay lookup.
        system_prompt: Behavioral instructions for the LLM.
        temperature: Sampling temperature (after layering + constraints).
        max_tokens: Maximum output tokens.
        top_p: Nucleus sampling threshold (None = use model default).
        top_k: Top-k sampling limit (None = use model default).
        context_length: Working memory context window.
        context_overflow_policy: How to handle context overflow.
    """

    role_name: str
    model_id: str
    family: str
    task_type: str
    system_prompt: str
    temperature: float
    max_tokens: int
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    context_length: int = 16384
    context_overflow_policy: str = "truncateMiddle"


__all__ = [
    "ResolvedConfig",
]
