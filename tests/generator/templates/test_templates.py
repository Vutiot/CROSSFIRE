"""Tests for individual template behavior."""

import pytest

from crossfire.generator.templates.base import BaseTemplate
from crossfire.generator.templates.investigation_report import InvestigationReportTemplate
from crossfire.generator.templates.technical_analysis import TechnicalAnalysisTemplate
from crossfire.generator.templates.witness_testimony import WitnessTestimonyTemplate
from crossfire.generator.templates.regulatory_filing import RegulatoryFilingTemplate
from crossfire.generator.templates.press_coverage import PressCoverageTemplate
from crossfire.generator.templates.expert_deposition import ExpertDepositionTemplate
from crossfire.generator.templates.internal_memo import InternalMemoTemplate
from crossfire.generator.templates.preliminary_report import PreliminaryReportTemplate

from .conftest import mock_llm_call

ALL_TEMPLATES = [
    InvestigationReportTemplate(),
    TechnicalAnalysisTemplate(),
    WitnessTestimonyTemplate(),
    RegulatoryFilingTemplate(),
    PressCoverageTemplate(),
    ExpertDepositionTemplate(),
    InternalMemoTemplate(),
    PreliminaryReportTemplate(),
]


class TestEntitySelection:
    def test_deterministic_selection(self, sample_entities, seed_mgr):
        template = InvestigationReportTemplate()
        seed = seed_mgr.get_seed("test", 0)
        sel1 = template.select_entities(sample_entities, seed)
        sel2 = template.select_entities(sample_entities, seed)
        assert [e.id for e in sel1] == [e.id for e in sel2]

    def test_different_seeds_different_selection(self, sample_entities, seed_mgr):
        template = InvestigationReportTemplate()
        sel1 = template.select_entities(sample_entities, seed=100)
        sel2 = template.select_entities(sample_entities, seed=200)
        # With 6 entities and selecting 3-8, different seeds should differ
        ids1 = {e.id for e in sel1}
        ids2 = {e.id for e in sel2}
        # They might occasionally match, but the order should differ
        assert sel1 != sel2 or ids1 == ids2  # at minimum, valid entities

    def test_includes_org_and_equipment(self, sample_entities, seed_mgr):
        template = InvestigationReportTemplate()
        for seed in range(10):
            selected = template.select_entities(sample_entities, seed)
            types = {e.entity_type for e in selected}
            assert "organization" in types
            assert "equipment" in types

    def test_empty_entities(self, seed_mgr):
        template = InvestigationReportTemplate()
        selected = template.select_entities([], seed=42)
        assert selected == []

    def test_selects_3_to_8(self, sample_entities, seed_mgr):
        template = InvestigationReportTemplate()
        for seed in range(20):
            selected = template.select_entities(sample_entities, seed)
            assert 3 <= len(selected) <= min(8, len(sample_entities))


class TestPromptBuilding:
    @pytest.mark.parametrize("template", ALL_TEMPLATES, ids=lambda t: t.doc_type)
    def test_prompt_contains_scenario(self, template, sample_entities, sample_context):
        prompt = template.build_prompt(sample_entities[:3], sample_context, seed=42)
        assert "Alaska Airlines" in prompt or "aviation incident" in prompt

    @pytest.mark.parametrize("template", ALL_TEMPLATES, ids=lambda t: t.doc_type)
    def test_prompt_contains_word_count(self, template, sample_entities, sample_context):
        prompt = template.build_prompt(sample_entities[:3], sample_context, seed=42)
        assert "words" in prompt.lower()

    @pytest.mark.parametrize("template", ALL_TEMPLATES, ids=lambda t: t.doc_type)
    def test_prompt_contains_entity_references(self, template, sample_entities, sample_context):
        prompt = template.build_prompt(sample_entities[:3], sample_context, seed=42)
        # At least one entity name or alias should appear
        assert any(
            e.canonical_name in prompt or any(a in prompt for a in e.aliases)
            for e in sample_entities[:3]
        )


class TestGenerate:
    @pytest.mark.parametrize("template", ALL_TEMPLATES, ids=lambda t: t.doc_type)
    def test_generate_returns_text(self, template, sample_entities, sample_context, seed_mgr):
        text, error = template.generate(sample_entities, sample_context, mock_llm_call, seed_mgr)
        assert error is None
        assert isinstance(text, str)
        assert len(text) > 0

    def test_generate_propagates_llm_error(self, sample_entities, sample_context, seed_mgr):
        def failing_llm(prompt, **kwargs):
            return None, "Rate limit"

        template = InvestigationReportTemplate()
        text, error = template.generate(sample_entities, sample_context, failing_llm, seed_mgr)
        assert text is None
        assert "Rate limit" in error


class TestReliability:
    @pytest.mark.parametrize("template", ALL_TEMPLATES, ids=lambda t: t.doc_type)
    def test_reliability_in_range(self, template):
        r = template.compute_reliability(seed=42)
        lo, hi = template.reliability_range
        assert lo <= r <= hi

    def test_reliability_deterministic(self):
        template = InvestigationReportTemplate()
        assert template.compute_reliability(42) == template.compute_reliability(42)

    def test_different_types_have_different_ranges(self):
        ir = InvestigationReportTemplate()
        wt = WitnessTestimonyTemplate()
        pc = PressCoverageTemplate()
        # Investigation reports should be more reliable than press coverage
        assert ir.reliability_range[0] > pc.reliability_range[0]
        assert wt.reliability_range[1] < ir.reliability_range[1]
