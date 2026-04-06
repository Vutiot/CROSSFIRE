"""Expert deposition template — party submission or expert analysis for hearing."""

from .base import BaseTemplate


class ExpertDepositionTemplate(BaseTemplate):
    doc_type = "expert_deposition"
    word_count_range = (1000, 2500)
    reliability_range = (0.70, 0.95)

    def _system_prompt(self) -> str:
        return (
            "You are writing a party submission or expert analysis document for "
            "an NTSB investigative hearing. This document presents a party's technical "
            "position, supported by evidence and expert reasoning. The author is a "
            "subject-matter expert (engineering, operations, human factors, or maintenance) "
            "representing one of the parties to the investigation (manufacturer, operator, "
            "regulator, or union)."
        )

    def _content_instructions(self) -> str:
        return (
            "DOCUMENT STRUCTURE (use UPPERCASE section headers):\n\n"
            "1. INTRODUCTION\n"
            "   - Party identification and role in the investigation\n"
            "   - Scope of the submission\n\n"
            "2. FACTUAL BACKGROUND\n"
            "   - Key facts relevant to the party's position\n"
            "   - References to docket materials and evidence\n\n"
            "3. TECHNICAL ANALYSIS\n"
            "   - Expert assessment of contributing factors\n"
            "   - Engineering data, test results, operational data\n"
            "   - Comparison with industry standards and best practices\n\n"
            "4. CONCLUSIONS\n"
            "   - Party's position on contributing factors\n"
            "   - Recommended safety improvements\n\n"
            "5. CORRECTIVE ACTIONS\n"
            "   - Actions already taken by the party\n"
            "   - Proposed future improvements\n\n"
            "STYLE: Persuasive but fact-based. Acknowledge complexity while advocating "
            "a position. Reference specific evidence from the docket. Use professional "
            "engineering and safety management terminology. Formal but not as rigid as "
            "the NTSB factual reports."
        )
