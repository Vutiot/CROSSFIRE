"""Tests for text extraction quality scoring."""

from crossfire.generator.scraper.config import QualityThresholds
from crossfire.generator.scraper.extractor import assess_quality


class TestAssessQuality:
    def test_good_text_passes(self, sample_extracted_text):
        thresholds = QualityThresholds()
        quality = assess_quality(sample_extracted_text, thresholds)
        assert quality.passed is True
        assert quality.word_count > 100
        assert quality.char_ratio > 0.9

    def test_empty_text_fails(self):
        thresholds = QualityThresholds()
        quality = assess_quality("", thresholds)
        assert quality.passed is False
        assert quality.word_count == 0

    def test_short_text_fails(self):
        thresholds = QualityThresholds(min_word_count=100)
        quality = assess_quality("This is a short text.", thresholds)
        assert quality.passed is False
        assert quality.word_count < 100

    def test_garbled_text_fails(self):
        thresholds = QualityThresholds()
        garbled = "\x00\x01\x02" * 200  # non-printable chars
        quality = assess_quality(garbled, thresholds)
        assert quality.passed is False
        assert quality.char_ratio < 0.5

    def test_avg_word_length_computed(self, sample_extracted_text):
        thresholds = QualityThresholds()
        quality = assess_quality(sample_extracted_text, thresholds)
        assert 2.5 <= quality.avg_word_length <= 12.0

    def test_line_count_computed(self, sample_extracted_text):
        thresholds = QualityThresholds()
        quality = assess_quality(sample_extracted_text, thresholds)
        assert quality.line_count > 1
