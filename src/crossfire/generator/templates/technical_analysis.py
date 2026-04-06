"""Technical analysis template — specialist factual report (FDR, CVR, materials, structures)."""

from .base import BaseTemplate


class TechnicalAnalysisTemplate(BaseTemplate):
    doc_type = "technical_analysis"
    word_count_range = (1200, 2500)
    reliability_range = (0.80, 1.0)

    def _system_prompt(self) -> str:
        return (
            "You are an NTSB specialist (flight data recorder, materials, structures, "
            "or powerplants group) writing a Specialist's Factual Report for an aviation "
            "accident investigation. Write with deep technical expertise, referencing "
            "specific measurements, test procedures, material properties, and engineering "
            "standards. Use the formal NTSB report style."
        )

    def _content_instructions(self) -> str:
        return (
            "DOCUMENT STRUCTURE (use UPPERCASE section headers):\n\n"
            "1. INTRODUCTION\n"
            "   - Scope of the specialist examination\n"
            "   - Items examined, date and location of examination\n\n"
            "2. BACKGROUND\n"
            "   - Relevant system/component description\n"
            "   - Design specifications, certification basis\n"
            "   - Operational history of the specific unit\n\n"
            "3. EXAMINATION AND FINDINGS\n"
            "   - Detailed description of physical examination\n"
            "   - Test procedures performed and results\n"
            "   - Measurements, photographs referenced\n"
            "   - Material analysis (metallurgical, chemical)\n\n"
            "4. DATA ANALYSIS\n"
            "   - Interpretation of recorded data (FDR/CVR/QAR parameters)\n"
            "   - Timeline reconstruction from data sources\n"
            "   - Comparison with normal operational parameters\n\n"
            "5. SUMMARY\n"
            "   - Key technical findings (factual, no probable cause)\n\n"
            "STYLE: Highly technical. Include specific units (PSI, ft-lbs, °C, knots, ft MSL), "
            "part numbers, serial numbers, and test standard references. "
            "Reference manufacturer specifications and engineering data."
        )
