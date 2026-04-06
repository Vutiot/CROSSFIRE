"""Shared fixtures for scraper tests."""

import pytest

# Sample NTSB docket HTML mimicking the real structure
SAMPLE_DOCKET_HTML = """
<html><body>
<table><tr><td>Some header info</td></tr></table>
<table><tr><td>More info</td></tr></table>
<table>
<tr>
  <th>#</th><th>Title</th><th>Pgs</th><th>Photo</th><th>Type</th><th>File</th>
</tr>
<tr>
  <td>1</td>
  <td>2-A OPERATIONAL FACTORS - GROUP CHAIRMAN FACTUAL REPORT</td>
  <td>36</td><td>0</td><td>Text/Image</td>
  <td><a href="/Docket/Document/docBLOB?ID=12345&FileExtension=pdf&FileName=Report.pdf">View</a></td>
</tr>
<tr>
  <td>2</td>
  <td>2-B OPERATIONAL FACTORS - ATTACHMENT 1 - CREW INTERVIEW TRANSCRIPTS</td>
  <td>84</td><td>0</td><td>Text/Image</td>
  <td><a href="/Docket/Document/docBLOB?ID=12346&FileExtension=pdf&FileName=Interviews.pdf">View</a></td>
</tr>
<tr>
  <td>3</td>
  <td>10-A FLIGHT DATA RECORDER REPORT</td>
  <td>25</td><td>0</td><td>Text/Image</td>
  <td><a href="/Docket/Document/docBLOB?ID=12347&FileExtension=pdf&FileName=FDR.pdf">View</a></td>
</tr>
<tr>
  <td>4</td>
  <td>FAA OVERSIGHT PRESENTATION</td>
  <td>15</td><td>0</td><td>Text/Image</td>
  <td><a href="/Docket/Document/docBLOB?ID=12348&FileExtension=pdf&FileName=FAA.pdf">View</a></td>
</tr>
<tr>
  <td>5</td>
  <td>BOEING QUALITY ALERT 2023-0056-AR</td>
  <td>3</td><td>0</td><td>Text/Image</td>
  <td><a href="/Docket/Document/docBLOB?ID=12349&FileExtension=pdf&FileName=Alert.pdf">View</a></td>
</tr>
<tr>
  <td>6</td>
  <td>ALASKA AIRLINES HEARING SUBMISSION</td>
  <td>20</td><td>0</td><td>Text/Image</td>
  <td><a href="/Docket/Document/docBLOB?ID=12350&FileExtension=pdf&FileName=Submission.pdf">View</a></td>
</tr>
<tr>
  <td>7</td>
  <td>FDR TABULAR DATA</td>
  <td>0</td><td>0</td><td>Spreadsheet</td>
  <td><a href="/Docket/Document/docBLOB?ID=12351&FileExtension=csv&FileName=FDR_data.csv">View</a></td>
</tr>
<tr>
  <td>8</td>
  <td>1-A ORDER OF HEARING</td>
  <td>2</td><td>0</td><td>Text/Image</td>
  <td><a href="/Docket/Document/docBLOB?ID=12352&FileExtension=pdf&FileName=Order.pdf">View</a></td>
</tr>
</table>
</body></html>
"""


SAMPLE_EXTRACTED_TEXT = """
NATIONAL TRANSPORTATION SAFETY BOARD
OPERATIONAL FACTORS GROUP CHAIRMAN'S FACTUAL REPORT

1. ACCIDENT INFORMATION

On January 5, 2024, about 1709 Pacific standard time, Alaska Airlines flight 1282,
a Boeing 737-9 (737 MAX 9), N722AL, experienced a rapid decompression event when
the left mid-exit door plug (MED plug) separated from the airplane during climb.

The airplane was operated by Alaska Airlines under the provisions of 14 CFR Part 121
as a regularly scheduled domestic passenger flight from Portland International Airport
(PDX), Portland, Oregon, to Ontario International Airport (ONT), Ontario, California.

2. CREW INFORMATION

The flight crew consisted of a captain and first officer. Both pilots were employed
by Alaska Airlines and held Airline Transport Pilot certificates issued by the
Federal Aviation Administration (FAA).

3. AIRPLANE INFORMATION

The Boeing 737-9 (MAX 9) airplane, serial number 66607, was manufactured by Boeing
at its Renton, Washington facility. The airplane was delivered to Alaska Airlines on
October 31, 2023. The MED plug was installed by Spirit AeroSystems at their Wichita,
Kansas facility during fuselage assembly.

Boeing Commercial Airplanes (BCA) is the manufacturer of the 737 MAX series.
Spirit AeroSystems Holdings is the supplier responsible for the fuselage section.
The FAA issued Airworthiness Directive AD 2024-02-51 grounding all 737 MAX 9
aircraft equipped with MED door plugs following this incident.
"""


@pytest.fixture
def sample_docket_html():
    return SAMPLE_DOCKET_HTML


@pytest.fixture
def sample_extracted_text():
    return SAMPLE_EXTRACTED_TEXT
