"""Press coverage template — news article about an aviation incident (synthetic only)."""

from .base import BaseTemplate


class PressCoverageTemplate(BaseTemplate):
    doc_type = "press_coverage"
    word_count_range = (600, 1200)
    reliability_range = (0.40, 0.80)

    def _system_prompt(self) -> str:
        return (
            "You are a journalist writing a news article about an aviation accident "
            "for a major news outlet. Write in standard journalistic style using the "
            "inverted pyramid structure — most important information first, supporting "
            "details after. Include quotes from officials and affected parties. "
            "Balance factual reporting with human interest elements."
        )

    def _content_instructions(self) -> str:
        return (
            "DOCUMENT STRUCTURE:\n\n"
            "HEADLINE: Write a concise, informative headline (one line).\n\n"
            "BYLINE: [Reporter Name], [News Outlet]\n"
            "DATELINE: [City, State] —\n\n"
            "BODY (inverted pyramid):\n"
            "- Lead paragraph: Who, what, when, where (most critical facts)\n"
            "- Second paragraph: How, why, immediate impact\n"
            "- Official statements (NTSB, FAA, airline spokesperson quotes)\n"
            "- Background on the aircraft type, operator, route\n"
            "- Expert commentary on possible causes (attributed, speculative)\n"
            "- Passenger/family reactions or statements\n"
            "- Historical context (similar incidents, safety record)\n"
            "- Ongoing investigation status\n\n"
            "STYLE: Accessible to a general audience. Explain technical terms. "
            "Use direct quotes with attribution. Include human elements. "
            "Avoid speculation not attributed to sources. "
            "Write in past tense for events, present tense for ongoing situation."
        )
