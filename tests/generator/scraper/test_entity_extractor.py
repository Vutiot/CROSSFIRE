"""Tests for entity extraction."""

from crossfire.generator.scraper.entity_extractor import (
    build_entity_profiles,
    extract_entities_from_text,
)


class TestExtractEntities:
    def test_extracts_organizations(self, sample_extracted_text):
        mentions = extract_entities_from_text(sample_extracted_text, "TEST001", "Test Doc")
        org_names = {m.name for m in mentions if m.entity_type == "organization"}
        assert "Boeing" in org_names
        assert "Alaska Airlines" in org_names
        assert "FAA" in org_names
        assert "Spirit AeroSystems" in org_names

    def test_extracts_equipment(self, sample_extracted_text):
        mentions = extract_entities_from_text(sample_extracted_text, "TEST001", "Test Doc")
        equip_names = {m.name for m in mentions if m.entity_type == "equipment"}
        assert any("737" in n for n in equip_names)

    def test_extracts_regulations(self, sample_extracted_text):
        mentions = extract_entities_from_text(sample_extracted_text, "TEST001", "Test Doc")
        reg_names = {m.name for m in mentions if m.entity_type == "regulation"}
        assert any("14 CFR" in n for n in reg_names)
        assert any("AD" in n for n in reg_names)

    def test_empty_text_returns_empty(self):
        mentions = extract_entities_from_text("", "TEST", "Empty")
        assert mentions == []

    def test_sets_ntsb_id_on_mentions(self, sample_extracted_text):
        mentions = extract_entities_from_text(sample_extracted_text, "DCA24MA063", "Test")
        assert all(m.ntsb_id == "DCA24MA063" for m in mentions)


class TestBuildEntityProfiles:
    def test_deduplicates_across_documents(self, sample_extracted_text):
        mentions1 = extract_entities_from_text(sample_extracted_text, "DOCKET1", "Doc1")
        mentions2 = extract_entities_from_text(sample_extracted_text, "DOCKET2", "Doc2")
        profiles = build_entity_profiles(mentions1 + mentions2)

        boeing = next((p for p in profiles if "boeing" in p.canonical_name), None)
        assert boeing is not None
        assert len(boeing.docket_ids) == 2
        assert "DOCKET1" in boeing.docket_ids
        assert "DOCKET2" in boeing.docket_ids

    def test_sorted_by_docket_count(self, sample_extracted_text):
        mentions1 = extract_entities_from_text(sample_extracted_text, "D1", "Doc1")
        mentions2 = extract_entities_from_text(sample_extracted_text, "D2", "Doc2")
        profiles = build_entity_profiles(mentions1 + mentions2)
        # Most-shared entities come first
        for i in range(len(profiles) - 1):
            assert len(profiles[i].docket_ids) >= len(profiles[i + 1].docket_ids)

    def test_tracks_naming_variations(self, sample_extracted_text):
        mentions = extract_entities_from_text(sample_extracted_text, "D1", "Doc1")
        profiles = build_entity_profiles(mentions)
        # Boeing appears as "Boeing" in the known org list — aliases should include the canonical
        boeing = next((p for p in profiles if "boeing" in p.canonical_name), None)
        assert boeing is not None
        assert len(boeing.aliases) >= 1
