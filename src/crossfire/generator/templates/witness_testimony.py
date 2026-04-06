"""Witness testimony template — interview transcript or written statement."""

from .base import BaseTemplate


class WitnessTestimonyTemplate(BaseTemplate):
    doc_type = "witness_testimony"
    word_count_range = (800, 2000)
    reliability_range = (0.50, 0.90)

    def _system_prompt(self) -> str:
        return (
            "You are writing a witness interview transcript or written statement "
            "for an NTSB aviation accident investigation. The document records a "
            "first-person account from someone involved in or who observed the incident. "
            "Write in a natural, conversational style that reflects how real people "
            "speak during formal interviews — including hesitations, self-corrections, "
            "and varying levels of technical knowledge."
        )

    def _content_instructions(self) -> str:
        return (
            "FORMAT: Choose ONE of these formats:\n\n"
            "OPTION A — Interview Transcript (Q&A format):\n"
            "   Begin with header: INTERVIEW OF [NAME/TITLE]\n"
            "   Date, time, location of interview\n"
            "   Interviewer identification\n"
            "   Then Q&A pairs:\n"
            "   Q: [Interviewer question]\n"
            "   A: [Witness answer — use natural speech patterns]\n\n"
            "OPTION B — Written Statement:\n"
            "   STATEMENT OF [NAME/TITLE]\n"
            "   Date of statement\n"
            "   Narrative first-person account\n\n"
            "CONTENT SHOULD INCLUDE:\n"
            "- Witness role/position relative to the incident\n"
            "- Sequence of events as observed\n"
            "- Specific sensory details (what they saw, heard, felt)\n"
            "- Timeline with approximate times\n"
            "- References to other people, equipment, and organizations involved\n"
            "- Level of detail varying by witness knowledge\n\n"
            "STYLE: Natural speech. Some witnesses are pilots with technical vocabulary, "
            "others are passengers or ground personnel with everyday language. "
            "Include realistic imprecision (\"about 10 minutes\", \"I think it was\")."
        )
