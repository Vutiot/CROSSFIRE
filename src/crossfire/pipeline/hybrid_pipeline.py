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
from crossfire.shared.schemas.reports import DetectedIncoherence, PipelineReport
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

    def run(self, corpus_path: str) -> tuple[PipelineReport | None, str | None]:
        """Run the pipeline against a corpus directory.

        Returns (PipelineReport, None) on success, (None, error) on failure.
        """
        logger.info(f"Pipeline starting: corpus_path={corpus_path}")

        # Load corpus documents (AR11: only subcorpus JSONL, never gold files)
        documents, error = self._load_corpus(corpus_path)
        if error:
            logger.error(f"Corpus loading failed: {error}")
            return None, error

        logger.info(f"Loaded {len(documents)} documents from corpus")

        # Run graph strategy
        graph_result, error = self.graph_strategy.run(corpus_path)
        if error:
            logger.warning(f"Graph strategy failed: {error}")
            graph_result = GraphResult()

        # Run reasoning strategy
        reasoning_result, error = self.reasoning_strategy.run(corpus_path)
        if error:
            logger.warning(f"Reasoning strategy failed: {error}")
            reasoning_result = ReasoningResult()

        # Merge detections from both strategies
        merged = self._merge_detections(
            graph_result.detected_incoherences,
            reasoning_result.detected_incoherences,
        )

        report = PipelineReport(
            pipeline_mode=self._infer_mode(),
            corpus_path=corpus_path,
            detections=merged,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        logger.info(f"Pipeline complete: {len(report.detections)} incoherences detected")
        return report, None

    def _load_corpus(self, corpus_path: str) -> tuple[list[Document] | None, str | None]:
        """Load corpus documents from subcorpus JSONL files."""
        corpus_dir = Path(corpus_path)
        if not corpus_dir.is_dir():
            return None, f"Corpus path is not a directory: {corpus_path}"

        jsonl_files = sorted(corpus_dir.glob("subcorpus_*.jsonl"))
        if not jsonl_files:
            return None, f"No subcorpus JSONL files found in: {corpus_path}"

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
        graph_detections: list[DetectedIncoherence],
        reasoning_detections: list[DetectedIncoherence],
    ) -> list[DetectedIncoherence]:
        """Merge detections from both strategies, deduplicating by evidence_references."""
        if not graph_detections:
            return list(reasoning_detections)
        if not reasoning_detections:
            return list(graph_detections)

        merged: list[DetectedIncoherence] = list(graph_detections)
        seen_refs = {frozenset(d.evidence_references) for d in graph_detections}

        for det in reasoning_detections:
            ref_key = frozenset(det.evidence_references)
            if ref_key not in seen_refs:
                merged.append(det)
                seen_refs.add(ref_key)
            else:
                # Keep the higher-confidence detection
                for i, existing in enumerate(merged):
                    if frozenset(existing.evidence_references) == ref_key:
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
            return "graph-native"
        return "hybrid"
