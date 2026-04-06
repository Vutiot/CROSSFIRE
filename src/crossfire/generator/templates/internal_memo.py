"""Internal memo template — organizational communication, quality alerts, process docs."""

from .base import BaseTemplate


class InternalMemoTemplate(BaseTemplate):
    doc_type = "internal_memo"
    word_count_range = (500, 1200)
    reliability_range = (0.55, 0.85)

    def _system_prompt(self) -> str:
        return (
            "You are writing an internal organizational document — a memo, quality alert, "
            "process instruction, or training bulletin — from within an aviation company "
            "(manufacturer, airline, or maintenance organization). The document is an "
            "internal communication that was later entered into the NTSB investigation docket "
            "as evidence. Write in a direct, organizational style."
        )

    def _content_instructions(self) -> str:
        return (
            "DOCUMENT STRUCTURE:\n\n"
            "HEADER:\n"
            "   TO: [Recipients/Department]\n"
            "   FROM: [Author/Department]\n"
            "   DATE: [Date]\n"
            "   SUBJECT: [Concise subject line]\n"
            "   REF: [Reference numbers, prior memos]\n\n"
            "BODY:\n"
            "- PURPOSE: Why this memo is being issued\n"
            "- BACKGROUND: Context and relevant history\n"
            "- DETAILS: Specific instructions, findings, or actions\n"
            "- ACTION REQUIRED: Clear next steps with responsible parties and deadlines\n\n"
            "POSSIBLE DOCUMENT TYPES (choose one):\n"
            "- Quality Alert: flagging a manufacturing or maintenance issue\n"
            "- Process Instruction: updated procedure for a specific task\n"
            "- Training Bulletin: new training requirement or update\n"
            "- Safety Communication: internal safety notice\n"
            "- Nonconformance Report: documenting a deviation from spec\n\n"
            "STYLE: Direct and action-oriented. Use bullet points and numbered lists. "
            "Reference internal document numbers, part numbers, and work orders. "
            "Professional but less formal than external regulatory documents."
        )
