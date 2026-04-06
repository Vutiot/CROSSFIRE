"""Investigation report template — formal NTSB factual report."""

from .base import BaseTemplate


class InvestigationReportTemplate(BaseTemplate):
    doc_type = "investigation_report"
    word_count_range = (1500, 3000)
    reliability_range = (0.85, 1.0)

    def _system_prompt(self) -> str:
        return (
            "You are an NTSB investigator writing a formal Group Chairman's Factual Report "
            "for an aviation accident investigation. Write in the official, impersonal, "
            "third-person style used by the National Transportation Safety Board. "
            "Use precise technical language, specific dates, times, and locations. "
            "Reference applicable Federal Aviation Regulations (14 CFR)."
        )

    def _content_instructions(self) -> str:
        return (
            "DOCUMENT STRUCTURE (use UPPERCASE section headers):\n\n"
            "1. ACCIDENT INFORMATION\n"
            "   - Date, time, location of the accident\n"
            "   - Aircraft type, registration, operator\n"
            "   - Nature of the flight (Part 121/135/91)\n\n"
            "2. CREW INFORMATION\n"
            "   - Pilot qualifications, certificates, ratings\n"
            "   - Recent flight experience and training records\n\n"
            "3. AIRCRAFT INFORMATION\n"
            "   - Aircraft make/model, serial number, total time\n"
            "   - Maintenance history, applicable ADs\n"
            "   - Relevant systems and components\n\n"
            "4. METEOROLOGICAL INFORMATION\n"
            "   - Weather conditions at the time of the accident\n"
            "   - METAR/TAF data, pilot reports\n\n"
            "5. WRECKAGE AND IMPACT INFORMATION\n"
            "   - Wreckage distribution, impact marks\n"
            "   - Component examination findings\n\n"
            "6. ADDITIONAL INFORMATION\n"
            "   - Relevant organizational policies\n"
            "   - Previous similar incidents\n"
            "   - Applicable regulations and guidance\n\n"
            "STYLE: Formal, factual, no opinions or probable cause determinations. "
            "Use numbered subsections (1.1, 1.2, etc.) within each section. "
            "Include specific numeric data (altitudes, speeds, temperatures, times)."
        )
