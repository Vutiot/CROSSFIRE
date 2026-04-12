# Contradiction Detection — Curated Case List

## Project Goal
Build an LLM agent that detects factual contradictions across multiple witness documents about the same event. Synthetic contradictions will be injected for benchmarking.

---

## Source 1: Grenfell Tower Inquiry (UK) — RECOMMENDED PRIMARY

### Why it's ideal
- 300+ public hearings, 1,600+ witness statements, all about one event
- Each hearing day is a separate transcript document (20,000–40,000 words each)
- Witnesses routinely contradict each other on factual questions: who knew what, when, and who told whom
- The final report (September 2024) explicitly identifies which witnesses were dishonest, giving **ground truth labels**
- Corporate/regulatory thread avoids the most sensitive personal testimony

### Recommended thread: "Cladding product safety knowledge"

The central factual question: **Did each party know the cladding was dangerous, and when?**

| Party | Role | Their claim | What evidence showed |
|---|---|---|---|
| **Arconic** | Manufactured Reynobond PE cladding panels | Test failure was a "rogue result"; product was safe | Internal emails from 2007 speculating about 60-70 deaths in a tower fire; French sales team ordered to stop selling PE a year before Grenfell |
| **Celotex** | Manufactured RS5000 insulation | Product was tested and safe for high-rise use | Rigged the 2014 fire test by adding hidden components; former manager admitted lying "for commercial gain" |
| **Kingspan** | Manufactured K15 insulation (5% of Grenfell) | Product was properly certified | Marketed using a test certificate from a chemically different older version of the product; current version turned test rig into a "raging inferno" |
| **Studio E** (architect) | Designed the refurbishment | Had "no knowledge" of fire spread risks, never heard of PE burning | Had responsibility for specifying compliant materials; regulatory guidance was available |
| **BRE** (Building Research Establishment) | Fire testing house | Properly conducted tests | Processes were "insufficiently robust" to detect Celotex's fraud; scientific rigour sacrificed for financial sustainability |
| **BBA** (British Board of Agrément) | Issued product certificates | Relied on manufacturer-supplied test data | Arconic obtained certificate on "a false premise" by submitting results for a different product version |
| **RBKC Building Control** | Approved the building design | Relied on the architect and manufacturer certifications | Failed to independently verify compliance |
| **Rydon** (contractor) | Built the refurbishment | Relied on architect and manufacturers | Had emails showing awareness of fire safety concerns |

### Documents to download

**Hearing transcripts** (PDF, each ~20k–40k words):
- Base URL: `https://assets.grenfelltowerinquiry.org.uk/documents/transcript/`
- Format: `Transcript DD Month YYYY.pdf`
- Phase 2, Module 2 (cladding products) — weeks 22–30 are the most contradiction-dense
- Phase 2, Module 1 (design/construction) — Studio E, Rydon, Exova testimony

**Witness statements** (PDF, individually downloadable):
- Base URL: `https://www.grenfelltowerinquiry.org.uk/evidence/`
- Each witness has a dedicated page with statement + exhibits
- Key witnesses: Claude Wehrle (Arconic, refused to testify), Claude Schmidt (Arconic), Jonathan Roper (Celotex), Bruce Sounes (Studio E), Terry Ashton (Exova)

**Final report** (7 volumes, ~1,600 pages):
- `https://assets.publishing.service.gov.uk/` — search "Grenfell Tower Inquiry Phase 2 report"
- Volume 2 (cladding products) and Volume 3 (design/construction) are most relevant
- Contains the inquiry's factual findings — your **ground truth** for which accounts were false

**National Archives** (full evidence archive):
- Series GTI 2 at `https://www.nationalarchives.gov.uk/`
- Includes 200,000+ documents: internal emails, test reports, commercial agreements

### Estimated corpus size for cladding thread
- 15–30 transcript days × ~30,000 words = **450,000–900,000 words**
- 20–40 witness statements × ~5,000 words = **100,000–200,000 words**
- Total: **~500,000–1,000,000 words** across **35–70 separate documents**

### Contradiction types available
1. **Direct factual denial**: "I never saw that email" vs the email is in evidence
2. **Temporal contradictions**: "We only learned about this after the fire" vs internal documents dated years earlier
3. **Attribution contradictions**: "X told us it was safe" vs X saying "we never said that"
4. **Knowledge contradictions**: "I had no knowledge of fire risks" vs conference attendance records
5. **Responsibility shifting**: each party blaming others for the same decision

---

## Source 2: Chicago COPA Officer-Involved Shooting Cases — SECONDARY

### Why it works
- Video Release Policy mandates publication of full document packages per case
- Single event, 10–30 documents per case: FSR, TRRs, OCIR, BWC descriptions, 911 calls, OEMC transmissions
- Multiple officers and civilians give separate accounts of the same incident
- FSR contains explicit credibility assessments

### Best cases (largest document packages)

| Log # | Documents | Key contradiction | Portal link |
|---|---|---|---|
| **2021-0000117** | ~25 (FSR, OCIR, Arrest Report, 3 TRRs, 8 BWCs, 2 ICCs, 3rd-party video, 2 OEMC, 3×911, ShotSpotter) | Officers contradict each other on observation sequence; in-car camera conveniently non-functional | `chicagocopa.org/case/2021-0000117/` |
| **2021-0002232** | ~30+ (FSR, OCIR, 2 TRRs, 6 BWCs, 2 OEMC, 14×911, 2 ShotSpotter) | 14 civilian 911 callers describe same event differently from officer accounts | `chicagocopa.org/case/2021-0002232/` |
| **2021-0003709** | ~20+ (FSR, OCIR, 2 TRRs, 10 BWCs, OEMC, multiple 911) | Fatal OIS: shooting officer vs witness officer perspectives diverge | `chicagocopa.org/case/2021-0003709/` |
| **2020-0001671** | Large FSR, 100+ internal attachments | 6 officers contradict each other on who authorized vehicle search; supervisor failure | `chicagocopa.org/case/2020-0001671/` (FSR published) |

### Limitation
- Text documents per case rarely exceed 15,000 words combined (excluding video/audio)
- Audio (911, OEMC) requires transcription
- Best as a secondary validation corpus, not primary

---

## Comparison

| Criterion | Grenfell Inquiry | COPA OIS Cases |
|---|---|---|
| Documents per event | 35–70+ | 10–30 |
| Words per event | 500k–1M | 5k–15k (text only) |
| Contradiction density | Very high | High |
| Ground truth available | Yes (final report) | Yes (FSR findings) |
| Sensitivity | High (72 deaths) but corporate thread is usable | High (shootings) |
| Download difficulty | Easy (public PDFs) | Easy (public PDFs) |
| Anonymization needed | Minimal (public figures, corporate entities) | Yes (civilian names redacted by COPA, officer names public) |
| Best for | Primary corpus, benchmarking, paper | Secondary validation, diverse contradiction types |

---

## Recommended project architecture

1. **Primary corpus**: Grenfell cladding thread — 40+ documents, ~600k words
2. **Validation corpus**: 3–5 COPA cases — ~15 documents each, ~50k words total
3. **Synthetic injection**: Add fabricated contradictions to both corpora at controlled rates
4. **Evaluation**: Compare agent detection against ground truth (inquiry findings / FSR findings)
5. **Ethical framing**: Position as "corporate accountability testimony analysis" — not trivializing victims

---

## Next steps
- [ ] Scrape Grenfell transcript index for Phase 2 Module 1–2 dates
- [ ] Download witness statements for key parties (Arconic, Celotex, Studio E, BRE, RBKC)
- [ ] Download COPA document packages for selected OIS cases
- [ ] Build PDF parser for both formats
- [ ] Design synthetic contradiction injection taxonomy
- [ ] Build detection agent and evaluation pipeline
