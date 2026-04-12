"""HybridPipeline — orchestrates graph and reasoning strategies for corpus auditing."""

from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from crossfire.pipeline.strategies.base import (
    GraphResult,
    GraphStrategy,
    ReasoningResult,
    ReasoningStrategy,
)
from crossfire.shared.schemas.corpus import Document
from crossfire.shared.schemas.reports import DetectedContradiction, PipelineReport
from crossfire.shared.seed_manager import SeedManager


class HybridPipeline:
    """Auditing pipeline that runs graph and reasoning strategies then merges results.

    Mode switching is via constructor injection:
    - Hybrid: real graph + real reasoning
    - Agentic (FR18): NullGraphStrategy + real reasoning
    - Graph-native (FR19): real graph + NullReasoningStrategy
    """

    def __init__(
        self,
        graph_strategy: GraphStrategy,
        reasoning_strategy: ReasoningStrategy,
        seed_manager: SeedManager,
    ):
        self.graph_strategy = graph_strategy
        self.reasoning_strategy = reasoning_strategy
        self.seed_manager = seed_manager

    def run(self, case_dir: str) -> tuple[PipelineReport | None, str | None]:
        """Run the pipeline against a case directory.

        Returns (PipelineReport, None) on success, (None, error) on failure.
        """
        logger.info(f"Pipeline starting: case_dir={case_dir}")

        # Load corpus documents (AR11: only anonymized_docs JSONL, never gold files)
        documents, error = self._load_corpus(case_dir)
        if error:
            logger.error(f"Corpus loading failed: {error}")
            return None, error

        logger.info(f"Loaded {len(documents)} documents from corpus")

        # Run graph strategy
        graph_result, error = self.graph_strategy.run(case_dir)
        if error:
            logger.warning(f"Graph strategy failed: {error}")
            graph_result = GraphResult()

        # Run reasoning strategy
        reasoning_result, error = self.reasoning_strategy.run(case_dir)
        if error:
            logger.warning(f"Reasoning strategy failed: {error}")
            reasoning_result = ReasoningResult()

        # Merge detections from both strategies
        merged = self._merge_detections(
            graph_result.detected_contradictions,
            reasoning_result.detected_contradictions,
        )

        report = PipelineReport(
            pipeline_mode=self._infer_mode(),
            case_dir=case_dir,
            detections=merged,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        logger.info(f"Pipeline complete: {len(report.detections)} contradictions detected")
        return report, None

    def _load_corpus(self, case_dir: str) -> tuple[list[Document] | None, str | None]:
        """Load corpus documents from anonymized_docs/ subdirectory JSONL files."""
        case_path = Path(case_dir)
        if not case_path.is_dir():
            return None, f"Case directory is not a directory: {case_dir}"

        anon_dir = case_path / "anonymized_docs"
        if not anon_dir.is_dir():
            return None, f"No anonymized_docs/ subdirectory found in: {case_dir}"

        jsonl_files = sorted(anon_dir.glob("*.jsonl"))
        if not jsonl_files:
            return None, f"No JSONL files found in: {anon_dir}"

        documents: list[Document] = []
        for jsonl_path in jsonl_files:
            text = jsonl_path.read_text(encoding="utf-8").strip()
            for line in text.split("\n"):
                if line:
                    doc = Document.model_validate_json(line)
                    documents.append(doc)

        return documents, None

    def _merge_detections(
        self,
        graph_detections: list[DetectedContradiction],
        reasoning_detections: list[DetectedContradiction],
    ) -> list[DetectedContradiction]:
        """Merge detections from both strategies, deduplicating by document_references."""
        if not graph_detections:
            return list(reasoning_detections)
        if not reasoning_detections:
            return list(graph_detections)

        merged: list[DetectedContradiction] = list(graph_detections)
        seen_refs = {frozenset(d.document_references) for d in graph_detections}

        for det in reasoning_detections:
            ref_key = frozenset(det.document_references)
            if ref_key not in seen_refs:
                merged.append(det)
                seen_refs.add(ref_key)
            else:
                # Keep the higher-confidence detection
                for i, existing in enumerate(merged):
                    if frozenset(existing.document_references) == ref_key:
                        if det.confidence > existing.confidence:
                            merged[i] = det
                        break

        return merged

    def _infer_mode(self) -> str:
        """Infer pipeline mode from strategy types for report metadata."""
        from crossfire.pipeline.strategies.null_strategies import (
            NullGraphStrategy,
            NullReasoningStrategy,
        )

        graph_null = isinstance(self.graph_strategy, NullGraphStrategy)
        reasoning_null = isinstance(self.reasoning_strategy, NullReasoningStrategy)

        if graph_null and not reasoning_null:
            return "agentic"
        if reasoning_null and not graph_null:
            return "graph_native"
        return "hybrid"
