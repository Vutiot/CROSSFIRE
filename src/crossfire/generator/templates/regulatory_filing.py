"""Regulatory filing template — FAA correspondence, safety recommendations, compliance docs."""

from .base import BaseTemplate


class RegulatoryFilingTemplate(BaseTemplate):
    doc_type = "regulatory_filing"
    word_count_range = (800, 1500)
    reliability_range = (0.85, 1.0)

    def _system_prompt(self) -> str:
        return (
            "You are writing a regulatory document related to an aviation accident "
            "investigation. This could be an FAA safety recommendation response, "
            "an Airworthiness Directive compliance explanation, a regulatory oversight "
            "report, or formal correspondence between the NTSB and the FAA. "
            "Write in formal regulatory language with precise legal and regulatory references."
        )

    def _content_instructions(self) -> str:
        return (
            "DOCUMENT STRUCTURE (use UPPERCASE section headers):\n\n"
            "1. SUBJECT / REFERENCE\n"
            "   - Specific regulation, AD, or safety recommendation referenced\n"
            "   - NTSB accident number and date\n\n"
            "2. BACKGROUND\n"
            "   - Regulatory context and history\n"
            "   - Applicable Federal Aviation Regulations (cite specific 14 CFR sections)\n"
            "   - Prior related safety recommendations or ADs\n\n"
            "3. FINDINGS / ANALYSIS\n"
            "   - Compliance status of the operator/manufacturer\n"
            "   - Regulatory oversight actions taken\n"
            "   - Gaps identified in regulatory framework\n\n"
            "4. ACTIONS / RECOMMENDATIONS\n"
            "   - Corrective actions required or recommended\n"
            "   - Timeline for compliance\n"
            "   - Follow-up inspection or review schedule\n\n"
            "STYLE: Formal bureaucratic language. Reference specific CFR sections "
            "(e.g., '14 CFR Part 121.344', '14 CFR 25.783'). Use regulatory terminology "
            "(airworthiness, type certificate, supplemental type certificate, MMEL). "
            "Include docket numbers and formal correspondence formatting."
        )
