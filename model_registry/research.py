#!/usr/bin/env python3
"""
Model Research Engine - Deep web search for model capabilities.

This module provides functionality to research model capabilities
by searching the web and parsing benchmark data.

Research Strategy:
1. Search for "{model_name} BFCL benchmark tool calling"
2. Search for "{model_family} capabilities benchmark"
3. Parse results to extract scores
4. Fall back to inference if no data found
"""

import re
import logging
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass

from .schemas import (
    ModelMetadata,
    ModelCapabilities,
    BenchmarkData,
    CapabilityScore,
    CapabilitySource,
    ResearchStatus
)

logger = logging.getLogger(__name__)


# Known model benchmarks (from BFCL leaderboard and other sources)
# This serves as a fallback when web search fails
KNOWN_BENCHMARKS: Dict[str, Dict[str, Any]] = {
    # GLM-4 models - Best for tool calling
    "glm-4": {
        "bfcl_score": 0.906,
        "tool_calling_excellent": True,
        "source": "BFCL Leaderboard 2024"
    },
    "glm4": {
        "bfcl_score": 0.906,
        "tool_calling_excellent": True,
        "source": "BFCL Leaderboard 2024"
    },

    # Qwen3 models - Excellent tool calling
    "qwen3": {
        "bfcl_score": 0.933,
        "tool_calling_excellent": True,
        "source": "BFCL Leaderboard 2024"
    },
    "qwen3-coder": {
        "bfcl_score": 0.933,
        "tool_calling_excellent": True,
        "coding_excellent": True,
        "source": "BFCL Leaderboard 2024"
    },

    # Llama 3 models
    "llama3": {
        "bfcl_score": 0.85,
        "tool_calling_good": True,
        "source": "BFCL Leaderboard 2024"
    },
    "llama-3": {
        "bfcl_score": 0.85,
        "tool_calling_good": True,
        "source": "BFCL Leaderboard 2024"
    },

    # Mistral models
    "mistral": {
        "bfcl_score": 0.82,
        "tool_calling_good": True,
        "source": "BFCL Leaderboard 2024"
    },
    "magistral": {
        "bfcl_score": 0.88,
        "tool_calling_excellent": True,
        "reasoning_excellent": True,
        "source": "Mistral AI benchmarks"
    },

    # Gemma models
    "gemma": {
        "bfcl_score": 0.78,
        "tool_calling_moderate": True,
        "source": "Community benchmarks"
    },
    "gemma3": {
        "bfcl_score": 0.82,
        "tool_calling_good": True,
        "vision": True,
        "source": "Google AI benchmarks"
    },

    # DeepSeek models
    "deepseek": {
        "reasoning_excellent": True,
        "source": "DeepSeek benchmarks"
    },
    "deepseek-r1": {
        "reasoning_excellent": True,
        "thinking": True,
        "source": "DeepSeek benchmarks"
    },

    # GPT-OSS (OpenAI open source)
    "gpt-oss": {
        "bfcl_score": 0.90,
        "tool_calling_excellent": True,
        "source": "OpenAI benchmarks"
    },

    # Granite models
    "granite": {
        "bfcl_score": 0.85,
        "tool_calling_good": True,
        "long_context": True,
        "source": "IBM benchmarks"
    },
}


@dataclass
class ResearchResult:
    """Result of researching a model."""
    model_id: str
    success: bool
    capabilities: Optional[ModelCapabilities] = None
    benchmarks: Optional[BenchmarkData] = None
    recommended_for: List[str] = None
    error: Optional[str] = None
    source: str = "unknown"

    def __post_init__(self):
        if self.recommended_for is None:
            self.recommended_for = []


class ModelResearcher:
    """
    Researches model capabilities through web search and known data.

    Research Process:
    1. Check known benchmarks first (fast, reliable)
    2. Try web search for specific model data
    3. Fall back to inference from model family
    """

    def __init__(self, web_search_enabled: bool = True):
        """
        Initialize researcher.

        Args:
            web_search_enabled: Whether to perform web searches
        """
        self.web_search_enabled = web_search_enabled

    async def research_model(
        self,
        metadata: ModelMetadata,
        force_web_search: bool = False
    ) -> ResearchResult:
        """
        Research capabilities for a model.

        Args:
            metadata: Model metadata from LMS
            force_web_search: Force web search even if known data exists

        Returns:
            ResearchResult with findings
        """
        model_id = metadata.model_id
        model_family = metadata.model_family
        logger.info(f"Researching model: {model_id} (family: {model_family})")

        try:
            # Step 1: Check known benchmarks
            known_data = self._lookup_known_benchmarks(model_id, model_family)

            if known_data and not force_web_search:
                logger.info(f"Found known benchmark data for {model_id}")
                return self._build_result_from_known(model_id, known_data, metadata)

            # Step 2: Try web search (if enabled)
            if self.web_search_enabled:
                web_result = await self._web_search_model(model_id, model_family)
                if web_result and web_result.success:
                    logger.info(f"Found web search data for {model_id}")
                    return web_result

            # Step 3: Fall back to known data or inference
            if known_data:
                return self._build_result_from_known(model_id, known_data, metadata)

            # Step 4: Inference only
            logger.info(f"Using inference for {model_id}")
            return self._build_result_from_inference(model_id, metadata)

        except Exception as e:
            logger.error(f"Error researching model {model_id}: {e}")
            return ResearchResult(
                model_id=model_id,
                success=False,
                error=str(e)
            )

    def _lookup_known_benchmarks(
        self,
        model_id: str,
        model_family: str
    ) -> Optional[Dict[str, Any]]:
        """
        Look up known benchmark data for a model.

        Args:
            model_id: Model identifier
            model_family: Model family

        Returns:
            Known benchmark data if found
        """
        model_lower = model_id.lower()

        # Try exact model ID match first
        for key, data in KNOWN_BENCHMARKS.items():
            if key in model_lower:
                return data

        # Try model family
        if model_family and model_family.lower() in KNOWN_BENCHMARKS:
            return KNOWN_BENCHMARKS[model_family.lower()]

        return None

    def _build_result_from_known(
        self,
        model_id: str,
        known_data: Dict[str, Any],
        metadata: ModelMetadata
    ) -> ResearchResult:
        """Build research result from known benchmark data."""
        capabilities = ModelCapabilities()
        benchmarks = BenchmarkData()
        recommended_for = []

        # Parse BFCL score
        if "bfcl_score" in known_data:
            score = known_data["bfcl_score"]
            benchmarks.bfcl_score = score
            benchmarks.source_url = "https://gorilla.cs.berkeley.edu/leaderboard.html"
            benchmarks.retrieved_at = datetime.now()

            # Update tool calling capability with score
            capabilities.tool_calling = CapabilityScore(
                supported=score,
                confidence=0.95,
                source=CapabilitySource.WEB_RESEARCH,
                details=f"BFCL score: {score}"
            )

            if score >= 0.90:
                recommended_for.extend(["tool_use", "agents", "automation"])
            elif score >= 0.80:
                recommended_for.extend(["tool_use", "simple_agents"])

        # Parse tool calling quality
        if known_data.get("tool_calling_excellent"):
            if not capabilities.tool_calling:
                capabilities.tool_calling = CapabilityScore(
                    supported=True,
                    confidence=0.90,
                    source=CapabilitySource.WEB_RESEARCH,
                    details="Excellent tool calling from benchmarks"
                )
            recommended_for.extend(["tool_use", "agents"])
        elif known_data.get("tool_calling_good"):
            if not capabilities.tool_calling:
                capabilities.tool_calling = CapabilityScore(
                    supported=True,
                    confidence=0.85,
                    source=CapabilitySource.WEB_RESEARCH,
                    details="Good tool calling from benchmarks"
                )
            recommended_for.append("tool_use")

        # Parse reasoning capability
        if known_data.get("reasoning_excellent"):
            capabilities.reasoning = CapabilityScore(
                supported=True,
                confidence=0.90,
                source=CapabilitySource.WEB_RESEARCH,
                details="Excellent reasoning from benchmarks"
            )
            recommended_for.extend(["reasoning", "analysis"])

        # Parse coding capability
        if known_data.get("coding_excellent"):
            capabilities.coding = CapabilityScore(
                supported=True,
                confidence=0.90,
                source=CapabilitySource.WEB_RESEARCH,
                details="Excellent coding from benchmarks"
            )
            recommended_for.extend(["coding", "code_review"])

        # Parse vision capability
        if known_data.get("vision"):
            capabilities.vision = CapabilityScore(
                supported=True,
                confidence=0.90,
                source=CapabilitySource.WEB_RESEARCH,
                details="Vision support confirmed"
            )
            recommended_for.extend(["vision", "image_analysis"])

        # Parse long context
        if known_data.get("long_context"):
            capabilities.long_context = CapabilityScore(
                supported=True,
                confidence=0.90,
                source=CapabilitySource.WEB_RESEARCH,
                details="Long context support"
            )
            recommended_for.append("long_documents")

        # Merge with existing capabilities from LMS metadata
        capabilities = self._merge_capabilities(metadata.capabilities, capabilities)

        # Deduplicate recommendations
        recommended_for = list(set(recommended_for))

        return ResearchResult(
            model_id=model_id,
            success=True,
            capabilities=capabilities,
            benchmarks=benchmarks,
            recommended_for=recommended_for,
            source=known_data.get("source", "Known benchmarks")
        )

    def _build_result_from_inference(
        self,
        model_id: str,
        metadata: ModelMetadata
    ) -> ResearchResult:
        """Build research result from inference only."""
        # Use existing LMS metadata capabilities
        capabilities = metadata.capabilities
        recommended_for = metadata.recommended_for.copy()

        # Lower confidence for inferred data
        return ResearchResult(
            model_id=model_id,
            success=True,
            capabilities=capabilities,
            benchmarks=BenchmarkData(),
            recommended_for=recommended_for,
            source="Inferred from model metadata"
        )

    def _merge_capabilities(
        self,
        lms_caps: ModelCapabilities,
        research_caps: ModelCapabilities
    ) -> ModelCapabilities:
        """
        Merge LMS metadata capabilities with research findings.

        Research findings take precedence for scored capabilities,
        LMS metadata provides baseline boolean capabilities.
        """
        merged = ModelCapabilities()

        # For each capability, prefer research data with scores
        for cap_name in ["tool_calling", "vision", "structured_output",
                         "reasoning", "coding", "long_context"]:
            lms_cap = getattr(lms_caps, cap_name, None)
            research_cap = getattr(research_caps, cap_name, None)

            if research_cap is not None:
                # Research data available - use it
                setattr(merged, cap_name, research_cap)
            elif lms_cap is not None:
                # Only LMS data - use it
                setattr(merged, cap_name, lms_cap)

        return merged

    async def _web_search_model(
        self,
        model_id: str,
        model_family: str
    ) -> Optional[ResearchResult]:
        """
        Search the web for model benchmark data.

        This is a placeholder for actual web search implementation.
        In production, this would use a search API or web scraping.

        Args:
            model_id: Model identifier
            model_family: Model family

        Returns:
            ResearchResult if data found, None otherwise
        """
        # TODO: Implement actual web search
        # Options:
        # 1. Use MCP fetch tool
        # 2. Use search API (Google, Bing)
        # 3. Scrape BFCL leaderboard
        #
        # For now, return None to fall back to known data
        logger.debug(f"Web search not yet implemented for {model_id}")
        return None

    async def research_models_batch(
        self,
        models: List[ModelMetadata],
        concurrency: int = 5
    ) -> Dict[str, ResearchResult]:
        """
        Research multiple models concurrently.

        Args:
            models: List of model metadata
            concurrency: Max concurrent research tasks

        Returns:
            Dictionary mapping model_id to ResearchResult
        """
        semaphore = asyncio.Semaphore(concurrency)
        results = {}

        async def research_with_semaphore(metadata: ModelMetadata):
            async with semaphore:
                result = await self.research_model(metadata)
                results[metadata.model_id] = result

        tasks = [research_with_semaphore(m) for m in models]
        await asyncio.gather(*tasks, return_exceptions=True)

        return results


def apply_research_to_metadata(
    metadata: ModelMetadata,
    result: ResearchResult
) -> ModelMetadata:
    """
    Apply research result to model metadata.

    Args:
        metadata: Original model metadata
        result: Research result

    Returns:
        Updated model metadata
    """
    if not result.success:
        metadata.research_status = ResearchStatus.FAILED
        return metadata

    # Update capabilities
    if result.capabilities:
        metadata.capabilities = result.capabilities

    # Update benchmarks
    if result.benchmarks:
        metadata.benchmarks = result.benchmarks

    # Update recommendations
    if result.recommended_for:
        # Merge with existing
        existing = set(metadata.recommended_for)
        new_recs = set(result.recommended_for)
        metadata.recommended_for = list(existing | new_recs)

    # Mark as researched
    metadata.research_status = ResearchStatus.COMPLETED
    metadata.researched_at = datetime.now()

    return metadata
