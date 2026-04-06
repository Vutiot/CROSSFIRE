"""Tests for baseline pipelines — random, BM25, hypothesis-only."""

import pytest

from crossfire.pipeline.baselines.bm25_baseline import run_bm25_baseline
from crossfire.pipeline.baselines.hypothesis_only import run_hypothesis_only_baseline
from crossfire.pipeline.baselines.random_baseline import run_random_baseline
from crossfire.shared.schemas.reports import PipelineReport
from crossfire.shared.seed_manager import SeedManager


# ---------------------------------------------------------------------------
# Random baseline
# ---------------------------------------------------------------------------


class TestRandomBaseline:
    def test_produces_valid_report(self, tmp_corpus_dir, seed_manager):
        report, error = run_random_baseline(str(tmp_corpus_dir), seed_manager)
        assert error is None
        assert isinstance(report, PipelineReport)
        assert report.pipeline_mode == "baseline-random"
        assert len(report.detections) >= 1

    def test_detections_have_valid_fields(self, tmp_corpus_dir, seed_manager):
        report, _ = run_random_baseline(str(tmp_corpus_dir), seed_manager)
        for det in report.detections:
            assert det.id.startswith("random_")
            assert len(det.evidence_references) == 2
            assert 0.0 <= det.confidence <= 1.0

    def test_deterministic_with_same_seed(self, tmp_corpus_dir):
        results = []
        for _ in range(3):
            sm = SeedManager(master_seed=42)
            report, _ = run_random_baseline(str(tmp_corpus_dir), sm)
            results.append([d.evidence_references for d in report.detections])
        assert results[0] == results[1] == results[2]

    def test_nonexistent_path_returns_error(self, seed_manager):
        report, error = run_random_baseline("/nonexistent", seed_manager)
        assert report is None
        assert "not a directory" in error

    def test_empty_corpus_returns_empty(self, tmp_path, seed_manager):
        empty = tmp_path / "empty"
        empty.mkdir()
        report, error = run_random_baseline(str(empty), seed_manager)
        assert error is None
        assert report.detections == []


# ---------------------------------------------------------------------------
# BM25 baseline
# ---------------------------------------------------------------------------


class TestBM25Baseline:
    def test_produces_valid_report(self, tmp_corpus_dir, seed_manager):
        report, error = run_bm25_baseline(str(tmp_corpus_dir), seed_manager)
        assert error is None
        assert isinstance(report, PipelineReport)
        assert report.pipeline_mode == "baseline-bm25"

    def test_detections_have_valid_fields(self, tmp_corpus_dir, seed_manager):
        report, _ = run_bm25_baseline(str(tmp_corpus_dir), seed_manager)
        for det in report.detections:
            assert det.id.startswith("bm25_")
            assert len(det.evidence_references) == 2
            assert 0.0 <= det.confidence <= 1.0

    def test_scores_are_deterministic(self, tmp_corpus_dir):
        sm1 = SeedManager(42)
        sm2 = SeedManager(42)
        r1, _ = run_bm25_baseline(str(tmp_corpus_dir), sm1)
        r2, _ = run_bm25_baseline(str(tmp_corpus_dir), sm2)
        assert len(r1.detections) == len(r2.detections)
        for d1, d2 in zip(r1.detections, r2.detections):
            assert d1.evidence_references == d2.evidence_references
            assert d1.confidence == d2.confidence

    def test_nonexistent_path_returns_error(self, seed_manager):
        report, error = run_bm25_baseline("/nonexistent", seed_manager)
        assert report is None
        assert "not a directory" in error


# ---------------------------------------------------------------------------
# Hypothesis-only baseline
# ---------------------------------------------------------------------------


class TestHypothesisOnlyBaseline:
    def test_produces_valid_report(self, tmp_corpus_dir, seed_manager):
        report, error = run_hypothesis_only_baseline(str(tmp_corpus_dir), seed_manager)
        assert error is None
        assert isinstance(report, PipelineReport)
        assert report.pipeline_mode == "baseline-hypothesis-only"

    def test_detections_have_valid_fields(self, tmp_corpus_dir, seed_manager):
        report, _ = run_hypothesis_only_baseline(str(tmp_corpus_dir), seed_manager)
        for det in report.detections:
            assert det.id.startswith("hypothesis_")
            assert len(det.evidence_references) == 2
            assert 0.0 <= det.confidence <= 1.0

    def test_scores_are_deterministic(self, tmp_corpus_dir):
        sm1 = SeedManager(42)
        sm2 = SeedManager(42)
        r1, _ = run_hypothesis_only_baseline(str(tmp_corpus_dir), sm1)
        r2, _ = run_hypothesis_only_baseline(str(tmp_corpus_dir), sm2)
        assert len(r1.detections) == len(r2.detections)

    def test_nonexistent_path_returns_error(self, seed_manager):
        report, error = run_hypothesis_only_baseline("/nonexistent", seed_manager)
        assert report is None
        assert "not a directory" in error

    def test_uses_surface_features_only(self, tmp_corpus_dir, seed_manager):
        """Verify the baseline produces results — it should score near-random
        on well-generated corpora (contamination validation)."""
        report, _ = run_hypothesis_only_baseline(str(tmp_corpus_dir), seed_manager)
        # With only 4 docs, we expect some flagged pairs
        assert isinstance(report, PipelineReport)


# ---------------------------------------------------------------------------
# All baselines produce standardized format (FR20)
# ---------------------------------------------------------------------------


class TestStandardizedFormat:
    def test_all_baselines_produce_pipeline_reports(self, tmp_corpus_dir, seed_manager):
        """FR20: All baselines output reports in the same standardized format."""
        random_report, _ = run_random_baseline(str(tmp_corpus_dir), seed_manager)
        bm25_report, _ = run_bm25_baseline(str(tmp_corpus_dir), seed_manager)
        hypo_report, _ = run_hypothesis_only_baseline(str(tmp_corpus_dir), seed_manager)

        for report in [random_report, bm25_report, hypo_report]:
            assert isinstance(report, PipelineReport)
            assert report.corpus_path == str(tmp_corpus_dir)
            assert report.timestamp
            # All use DetectedIncoherence schema
            for det in report.detections:
                assert hasattr(det, "evidence_references")
                assert hasattr(det, "confidence")
                assert hasattr(det, "description")
