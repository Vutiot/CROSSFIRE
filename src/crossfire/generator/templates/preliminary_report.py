"""Preliminary report template — initial findings, procedural documents, board materials."""

from .base import BaseTemplate


class PreliminaryReportTemplate(BaseTemplate):
    doc_type = "preliminary_report"
    word_count_range = (600, 1500)
    reliability_range = (0.70, 0.95)

    def _system_prompt(self) -> str:
        return (
            "You are writing a preliminary or procedural document for an NTSB aviation "
            "accident investigation. This is an early-stage document produced before the "
            "full investigation is complete. It summarizes initial findings, establishes "
            "the investigation scope, or documents procedural decisions."
        )

    def _content_instructions(self) -> str:
        return (
            "DOCUMENT STRUCTURE (use UPPERCASE section headers):\n\n"
            "1. SYNOPSIS\n"
            "   - Brief summary of the accident (2-3 sentences)\n"
            "   - Date, time, location, aircraft, operator\n\n"
            "2. INITIAL FINDINGS\n"
            "   - Preliminary factual information gathered\n"
            "   - Initial witness accounts\n"
            "   - Weather conditions at the time\n"
            "   - Damage assessment\n\n"
            "3. INVESTIGATION STATUS\n"
            "   - Groups activated (operations, structures, systems, etc.)\n"
            "   - Parties to the investigation\n"
            "   - Evidence secured and examinations planned\n\n"
            "4. NEXT STEPS\n"
            "   - Planned investigative activities\n"
            "   - Timeline for further updates\n\n"
            "STYLE: Concise and cautious. Emphasize that findings are preliminary "
            "and subject to change. Avoid conclusions or probable cause language. "
            "Use hedging language ('initial information indicates', 'preliminary "
            "examination revealed'). Formal NTSB tone."
        )
