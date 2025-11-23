#!/usr/bin/env python3
"""
Model Registry Schemas - Data structures for model capability tracking.

This module defines the core data structures used to represent model
metadata, capabilities, and benchmark information.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class ModelType(str, Enum):
    """Type of model."""
    LLM = "llm"
    EMBEDDING = "embedding"


class CapabilitySource(str, Enum):
    """Source of capability information."""
    LMS_METADATA = "lms_metadata"      # From LM Studio CLI metadata
    WEB_RESEARCH = "web_research"       # From web search/BFCL lookup
    INFERRED = "inferred"               # Inferred from model name/family
    USER_PROVIDED = "user_provided"     # User-specified override


class ResearchStatus(str, Enum):
    """Research status for a model."""
    NOT_RESEARCHED = "not_researched"
    RESEARCHING = "researching"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class CapabilityScore:
    """
    Represents a capability with its score/status and confidence.

    Attributes:
        supported: Whether the capability is supported (bool) or a score (float 0-1)
        confidence: Confidence level of this assessment (0.0-1.0)
        source: Where this information came from
        details: Additional details (e.g., benchmark name, version)
    """
    supported: bool | float
    confidence: float
    source: CapabilitySource
    details: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "supported": self.supported,
            "confidence": self.confidence,
            "source": self.source.value,
        }
        if self.details:
            result["details"] = self.details
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CapabilityScore":
        """Create from dictionary."""
        return cls(
            supported=data["supported"],
            confidence=data["confidence"],
            source=CapabilitySource(data["source"]),
            details=data.get("details")
        )


@dataclass
class BenchmarkData:
    """
    Benchmark results for a model.

    Attributes:
        bfcl_score: Berkeley Function Calling Leaderboard score (0-1)
        bfcl_rank: Rank on BFCL leaderboard
        bfcl_ast_accuracy: AST accuracy on BFCL
        bfcl_exec_accuracy: Execution accuracy on BFCL
        other_benchmarks: Additional benchmark data
        source_url: URL where this data was found
        retrieved_at: When this data was retrieved
    """
    bfcl_score: Optional[float] = None
    bfcl_rank: Optional[int] = None
    bfcl_ast_accuracy: Optional[float] = None
    bfcl_exec_accuracy: Optional[float] = None
    other_benchmarks: Dict[str, float] = field(default_factory=dict)
    source_url: Optional[str] = None
    retrieved_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {}
        if self.bfcl_score is not None:
            result["bfcl_score"] = self.bfcl_score
        if self.bfcl_rank is not None:
            result["bfcl_rank"] = self.bfcl_rank
        if self.bfcl_ast_accuracy is not None:
            result["bfcl_ast_accuracy"] = self.bfcl_ast_accuracy
        if self.bfcl_exec_accuracy is not None:
            result["bfcl_exec_accuracy"] = self.bfcl_exec_accuracy
        if self.other_benchmarks:
            result["other_benchmarks"] = self.other_benchmarks
        if self.source_url:
            result["source_url"] = self.source_url
        if self.retrieved_at:
            result["retrieved_at"] = self.retrieved_at.isoformat()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BenchmarkData":
        """Create from dictionary."""
        retrieved_at = None
        if data.get("retrieved_at"):
            retrieved_at = datetime.fromisoformat(data["retrieved_at"])
        return cls(
            bfcl_score=data.get("bfcl_score"),
            bfcl_rank=data.get("bfcl_rank"),
            bfcl_ast_accuracy=data.get("bfcl_ast_accuracy"),
            bfcl_exec_accuracy=data.get("bfcl_exec_accuracy"),
            other_benchmarks=data.get("other_benchmarks", {}),
            source_url=data.get("source_url"),
            retrieved_at=retrieved_at
        )


@dataclass
class ModelCapabilities:
    """
    All capabilities of a model.

    Attributes:
        tool_calling: Tool/function calling capability
        vision: Vision/image understanding capability
        structured_output: JSON schema output capability
        reasoning: Deep reasoning/thinking capability
        coding: Code generation/understanding capability
        long_context: Long context window support (>32k)
    """
    tool_calling: Optional[CapabilityScore] = None
    vision: Optional[CapabilityScore] = None
    structured_output: Optional[CapabilityScore] = None
    reasoning: Optional[CapabilityScore] = None
    coding: Optional[CapabilityScore] = None
    long_context: Optional[CapabilityScore] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {}
        for cap_name in ["tool_calling", "vision", "structured_output",
                         "reasoning", "coding", "long_context"]:
            cap = getattr(self, cap_name)
            if cap is not None:
                result[cap_name] = cap.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelCapabilities":
        """Create from dictionary."""
        kwargs = {}
        for cap_name in ["tool_calling", "vision", "structured_output",
                         "reasoning", "coding", "long_context"]:
            if cap_name in data:
                kwargs[cap_name] = CapabilityScore.from_dict(data[cap_name])
        return cls(**kwargs)


@dataclass
class ModelMetadata:
    """
    Complete metadata for a model.

    Attributes:
        model_id: Unique model identifier (e.g., "qwen/qwen3-coder-30b")
        model_type: Type of model (llm or embedding)
        display_name: Human-readable name
        publisher: Model publisher/organization
        model_family: Model family (e.g., "qwen3", "llama", "mistral")
        architecture: Model architecture
        size_billions: Parameter count in billions
        size_bytes: Storage size in bytes
        quantization: Quantization details (e.g., "Q4_K_M", "4bit")
        max_context_length: Maximum context window
        capabilities: Model capabilities
        benchmarks: Benchmark data
        recommended_for: Recommended use cases
        research_status: Status of capability research
        researched_at: When capabilities were last researched
        lms_raw_data: Raw data from LMS CLI (for debugging)
    """
    model_id: str
    model_type: ModelType
    display_name: str
    publisher: str
    model_family: str
    architecture: str
    size_billions: Optional[float] = None
    size_bytes: Optional[int] = None
    estimated_vram_gb: Optional[float] = None  # Estimated VRAM requirement
    quantization: Optional[str] = None
    max_context_length: Optional[int] = None
    is_thinking_model: bool = False  # Models with 'thinking' often ignore tool results
    capabilities: ModelCapabilities = field(default_factory=ModelCapabilities)
    benchmarks: BenchmarkData = field(default_factory=BenchmarkData)
    recommended_for: List[str] = field(default_factory=list)
    research_status: ResearchStatus = ResearchStatus.NOT_RESEARCHED
    researched_at: Optional[datetime] = None
    lms_raw_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "model_id": self.model_id,
            "model_type": self.model_type.value,
            "display_name": self.display_name,
            "publisher": self.publisher,
            "model_family": self.model_family,
            "architecture": self.architecture,
            "research_status": self.research_status.value,
        }

        if self.size_billions is not None:
            result["size_billions"] = self.size_billions
        if self.size_bytes is not None:
            result["size_bytes"] = self.size_bytes
        if self.estimated_vram_gb is not None:
            result["estimated_vram_gb"] = self.estimated_vram_gb
        if self.is_thinking_model:
            result["is_thinking_model"] = self.is_thinking_model
        if self.quantization:
            result["quantization"] = self.quantization
        if self.max_context_length is not None:
            result["max_context_length"] = self.max_context_length

        caps_dict = self.capabilities.to_dict()
        if caps_dict:
            result["capabilities"] = caps_dict

        benchmarks_dict = self.benchmarks.to_dict()
        if benchmarks_dict:
            result["benchmarks"] = benchmarks_dict

        if self.recommended_for:
            result["recommended_for"] = self.recommended_for
        if self.researched_at:
            result["researched_at"] = self.researched_at.isoformat()

        # Don't include raw LMS data in serialization (too verbose)

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelMetadata":
        """Create from dictionary."""
        researched_at = None
        if data.get("researched_at"):
            researched_at = datetime.fromisoformat(data["researched_at"])

        capabilities = ModelCapabilities()
        if "capabilities" in data:
            capabilities = ModelCapabilities.from_dict(data["capabilities"])

        benchmarks = BenchmarkData()
        if "benchmarks" in data:
            benchmarks = BenchmarkData.from_dict(data["benchmarks"])

        return cls(
            model_id=data["model_id"],
            model_type=ModelType(data["model_type"]),
            display_name=data["display_name"],
            publisher=data["publisher"],
            model_family=data["model_family"],
            architecture=data["architecture"],
            size_billions=data.get("size_billions"),
            size_bytes=data.get("size_bytes"),
            estimated_vram_gb=data.get("estimated_vram_gb"),
            quantization=data.get("quantization"),
            is_thinking_model=data.get("is_thinking_model", False),
            max_context_length=data.get("max_context_length"),
            capabilities=capabilities,
            benchmarks=benchmarks,
            recommended_for=data.get("recommended_for", []),
            research_status=ResearchStatus(data.get("research_status", "not_researched")),
            researched_at=researched_at,
            lms_raw_data=data.get("lms_raw_data")
        )

    @classmethod
    def from_lms_data(cls, lms_data: Dict[str, Any]) -> "ModelMetadata":
        """
        Create ModelMetadata from LMS CLI 'lms ls --json' output.

        This parses the rich metadata provided by LM Studio CLI.
        """
        model_id = lms_data.get("modelKey", "")
        model_type = ModelType(lms_data.get("type", "llm"))

        # Extract model family from modelKey (e.g., "qwen/qwen3-coder-30b" -> "qwen3")
        model_family = cls._extract_model_family(model_id, lms_data.get("architecture", ""))

        # Parse size from paramsString (e.g., "30B" -> 30.0)
        size_billions = cls._parse_params_string(lms_data.get("paramsString", ""))

        # Parse quantization
        quantization = None
        if lms_data.get("quantization"):
            quantization = lms_data["quantization"].get("name", "")

        # Build capabilities from LMS metadata
        capabilities = ModelCapabilities()

        # Tool calling from LMS metadata
        if lms_data.get("trainedForToolUse") is not None:
            capabilities.tool_calling = CapabilityScore(
                supported=lms_data["trainedForToolUse"],
                confidence=1.0,  # High confidence - from LMS metadata
                source=CapabilitySource.LMS_METADATA,
                details="From LM Studio model metadata"
            )

        # Vision from LMS metadata
        if lms_data.get("vision") is not None:
            capabilities.vision = CapabilityScore(
                supported=lms_data["vision"],
                confidence=1.0,
                source=CapabilitySource.LMS_METADATA,
                details="From LM Studio model metadata"
            )

        # Long context (>32k tokens)
        max_context = lms_data.get("maxContextLength", 0)
        if max_context > 0:
            capabilities.long_context = CapabilityScore(
                supported=max_context > 32768,
                confidence=1.0,
                source=CapabilitySource.LMS_METADATA,
                details=f"Context length: {max_context}"
            )

        # Infer reasoning capability from model name
        is_reasoning = cls._infer_reasoning_capability(model_id, model_family)
        if is_reasoning is not None:
            capabilities.reasoning = CapabilityScore(
                supported=is_reasoning,
                confidence=0.7,  # Lower confidence - inferred
                source=CapabilitySource.INFERRED,
                details="Inferred from model name"
            )

        # Infer coding capability from model name
        is_coding = cls._infer_coding_capability(model_id, model_family)
        if is_coding is not None:
            capabilities.coding = CapabilityScore(
                supported=is_coding,
                confidence=0.7,
                source=CapabilitySource.INFERRED,
                details="Inferred from model name"
            )

        # Generate recommended_for based on capabilities
        recommended_for = cls._generate_recommendations(capabilities, model_family)

        # Estimate VRAM from size_bytes
        size_bytes = lms_data.get("sizeBytes")
        estimated_vram_gb = cls._estimate_vram_gb(size_bytes, quantization)

        # Detect thinking models (often ignore tool results)
        is_thinking_model = cls._is_thinking_model(model_id)

        return cls(
            model_id=model_id,
            model_type=model_type,
            display_name=lms_data.get("displayName", model_id),
            publisher=lms_data.get("publisher", ""),
            model_family=model_family,
            architecture=lms_data.get("architecture", ""),
            size_billions=size_billions,
            size_bytes=size_bytes,
            estimated_vram_gb=estimated_vram_gb,
            quantization=quantization,
            max_context_length=max_context if max_context > 0 else None,
            is_thinking_model=is_thinking_model,
            capabilities=capabilities,
            benchmarks=BenchmarkData(),
            recommended_for=recommended_for,
            research_status=ResearchStatus.NOT_RESEARCHED,
            lms_raw_data=lms_data
        )

    @staticmethod
    def _extract_model_family(model_id: str, architecture: str) -> str:
        """Extract model family from model ID or architecture."""
        model_lower = model_id.lower()

        # Known families
        families = [
            ("qwen3", ["qwen3", "qwen-3"]),
            ("qwen2", ["qwen2", "qwen-2"]),
            ("qwen", ["qwen"]),
            ("llama3", ["llama-3", "llama3"]),
            ("llama2", ["llama-2", "llama2"]),
            ("llama", ["llama"]),
            ("mistral", ["mistral", "magistral"]),
            ("gemma", ["gemma"]),
            ("phi", ["phi"]),
            ("glm", ["glm"]),
            ("deepseek", ["deepseek"]),
            ("granite", ["granite"]),
            ("gpt", ["gpt"]),
        ]

        for family, patterns in families:
            for pattern in patterns:
                if pattern in model_lower:
                    return family

        # Fall back to architecture
        if architecture:
            return architecture.split("_")[0].lower()

        return "unknown"

    @staticmethod
    def _parse_params_string(params_str: str) -> Optional[float]:
        """Parse parameter string like '30B', '8B', '160x19B' to billions."""
        if not params_str:
            return None

        params_str = params_str.upper().strip()

        # Handle MoE format like "160x19B"
        if "X" in params_str:
            parts = params_str.split("X")
            if len(parts) == 2:
                try:
                    multiplier = float(parts[0])
                    base = parts[1].replace("B", "").replace("M", "")
                    base_val = float(base)
                    if "M" in parts[1]:
                        base_val /= 1000
                    return multiplier * base_val
                except ValueError:
                    pass

        # Standard format like "30B", "8B", "300M"
        try:
            if "B" in params_str:
                return float(params_str.replace("B", ""))
            elif "M" in params_str:
                return float(params_str.replace("M", "")) / 1000
        except ValueError:
            pass

        return None

    @staticmethod
    def _estimate_vram_gb(size_bytes: Optional[int], quantization: Optional[str]) -> Optional[float]:
        """
        Estimate VRAM requirement from model file size.

        VRAM estimation is roughly equal to file size for most quantized models.
        For higher precision (FP16/FP32), VRAM may be higher.

        Args:
            size_bytes: Model file size in bytes
            quantization: Quantization method (e.g., "Q4_K_M", "Q8", "FP16")

        Returns:
            Estimated VRAM requirement in GB, or None if unknown
        """
        if not size_bytes:
            return None

        # Base estimate: file size in GB (most accurate for quantized models)
        base_gb = size_bytes / (1024 ** 3)

        # Adjust for quantization type
        # Q4/Q5/Q6/Q8 models: VRAM ≈ file size
        # FP16: VRAM can be ~1.2x file size due to activations
        # FP32: VRAM can be ~1.5x file size
        multiplier = 1.0
        if quantization:
            quant_lower = quantization.lower()
            if "fp32" in quant_lower or "f32" in quant_lower:
                multiplier = 1.5
            elif "fp16" in quant_lower or "f16" in quant_lower:
                multiplier = 1.2
            # Q4/Q5/Q6/Q8 models: multiplier stays at 1.0

        # Add ~10% overhead for KV cache and runtime buffers
        estimated = base_gb * multiplier * 1.1

        # Round to 1 decimal place
        return round(estimated, 1)

    @staticmethod
    def _is_thinking_model(model_id: str) -> bool:
        """
        Detect if model is a 'thinking' model.

        Thinking models (like QwQ, DeepSeek-R1, o1-style) often have issues with
        tool calling because they tend to ignore tool results and continue reasoning.

        Args:
            model_id: Model identifier

        Returns:
            True if model appears to be a thinking/reasoning model
        """
        model_lower = model_id.lower()

        # Known thinking model patterns
        thinking_patterns = [
            "thinking",
            "qwq",           # QwQ models
            "deepseek-r1",   # DeepSeek R1
            "r1-",           # R1 variants
            "-r1",
            "o1-",           # o1-style models
            "reasoning",
        ]

        return any(pattern in model_lower for pattern in thinking_patterns)

    @staticmethod
    def _infer_reasoning_capability(model_id: str, family: str) -> Optional[bool]:
        """Infer if model has reasoning/thinking capability."""
        model_lower = model_id.lower()

        # Explicit reasoning/thinking models
        if any(kw in model_lower for kw in ["thinking", "reasoning", "r1", "o1"]):
            return True

        # Models known for reasoning
        if any(kw in model_lower for kw in ["magistral", "deepseek-r1"]):
            return True

        return None  # Unknown

    @staticmethod
    def _infer_coding_capability(model_id: str, family: str) -> Optional[bool]:
        """Infer if model has coding capability."""
        model_lower = model_id.lower()

        # Explicit coding models
        if any(kw in model_lower for kw in ["coder", "code", "codellama", "starcoder"]):
            return True

        return None  # Unknown

    @staticmethod
    def _generate_recommendations(caps: ModelCapabilities, family: str) -> List[str]:
        """Generate recommended use cases based on capabilities."""
        recommendations = []

        if caps.tool_calling and caps.tool_calling.supported:
            recommendations.append("tool_use")
            recommendations.append("agents")

        if caps.vision and caps.vision.supported:
            recommendations.append("vision")
            recommendations.append("image_analysis")

        if caps.coding and caps.coding.supported:
            recommendations.append("coding")
            recommendations.append("code_review")

        if caps.reasoning and caps.reasoning.supported:
            recommendations.append("reasoning")
            recommendations.append("analysis")

        if caps.long_context and caps.long_context.supported:
            recommendations.append("long_documents")

        # Default recommendation if nothing specific
        if not recommendations:
            recommendations.append("general")

        return recommendations


@dataclass
class RegistryStats:
    """Statistics about the model registry."""
    total_models: int = 0
    llm_models: int = 0
    embedding_models: int = 0
    researched_models: int = 0
    pending_research: int = 0
    failed_research: int = 0
    last_updated: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "total_models": self.total_models,
            "llm_models": self.llm_models,
            "embedding_models": self.embedding_models,
            "researched_models": self.researched_models,
            "pending_research": self.pending_research,
            "failed_research": self.failed_research,
        }
        if self.last_updated:
            result["last_updated"] = self.last_updated.isoformat()
        return result
