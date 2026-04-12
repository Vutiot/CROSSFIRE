"""Tests for the generation bash wrapper scripts.

Validates that generate_case.sh and generate_all.sh exist, are executable,
parse arguments correctly, and produce expected dry-run output.

NOTE: These tests do NOT invoke the actual Claude CLI tool. They verify
script structure, argument validation, and dry-run mode only.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GENERATION_DIR = PROJECT_ROOT / "generation"
GENERATE_CASE = GENERATION_DIR / "generate_case.sh"
GENERATE_ALL = GENERATION_DIR / "generate_all.sh"
SOURCES_DIR = GENERATION_DIR / "sources"
CORPUS_DIR = PROJECT_ROOT / "corpus"


def _run_script(
    script: Path,
    args: list[str],
    *,
    cwd: Path | None = None,
    timeout: int = 30,
) -> subprocess.CompletedProcess:
    """Run a bash script and return the completed process."""
    return subprocess.run(
        ["bash", str(script)] + args,
        capture_output=True,
        text=True,
        cwd=str(cwd or PROJECT_ROOT),
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Script existence and executability
# ---------------------------------------------------------------------------


class TestScriptExistence:
    """Verify scripts exist and are executable."""

    def test_generate_case_exists(self) -> None:
        assert GENERATE_CASE.exists(), f"Missing: {GENERATE_CASE}"

    def test_generate_all_exists(self) -> None:
        assert GENERATE_ALL.exists(), f"Missing: {GENERATE_ALL}"

    def test_generate_case_is_executable(self) -> None:
        assert os.access(GENERATE_CASE, os.X_OK), "generate_case.sh is not executable"

    def test_generate_all_is_executable(self) -> None:
        assert os.access(GENERATE_ALL, os.X_OK), "generate_all.sh is not executable"

    def test_generate_case_has_shebang(self) -> None:
        first_line = GENERATE_CASE.read_text().splitlines()[0]
        assert first_line == "#!/usr/bin/env bash"

    def test_generate_all_has_shebang(self) -> None:
        first_line = GENERATE_ALL.read_text().splitlines()[0]
        assert first_line == "#!/usr/bin/env bash"

    def test_generate_case_has_strict_mode(self) -> None:
        text = GENERATE_CASE.read_text()
        assert "set -euo pipefail" in text

    def test_generate_all_has_strict_mode(self) -> None:
        text = GENERATE_ALL.read_text()
        assert "set -euo pipefail" in text


# ---------------------------------------------------------------------------
# Argument validation / usage messages
# ---------------------------------------------------------------------------


class TestArgumentValidation:
    """Verify scripts produce usage messages on bad arguments."""

    def test_generate_case_no_args_shows_error(self) -> None:
        result = _run_script(GENERATE_CASE, [])
        assert result.returncode != 0
        assert "source" in result.stderr.lower() or "usage" in result.stderr.lower()

    def test_generate_case_help(self) -> None:
        result = _run_script(GENERATE_CASE, ["--help"])
        assert result.returncode == 0
        assert "Usage" in result.stdout

    def test_generate_all_help(self) -> None:
        result = _run_script(GENERATE_ALL, ["--help"])
        assert result.returncode == 0
        assert "Usage" in result.stdout

    def test_generate_case_missing_source(self) -> None:
        result = _run_script(GENERATE_CASE, ["corpus/ntsb/WPR19FA080"])
        assert result.returncode != 0

    def test_generate_case_missing_case_dir(self) -> None:
        result = _run_script(GENERATE_CASE, ["--source", "ntsb"])
        assert result.returncode != 0

    def test_generate_case_invalid_source(self) -> None:
        result = _run_script(
            GENERATE_CASE,
            ["--source", "nonexistent_source", "--dry-run", "corpus/ntsb/WPR19FA080"],
        )
        assert result.returncode != 0
        assert "not found" in result.stderr.lower() or "agent plan" in result.stderr.lower()

    def test_generate_case_invalid_case_dir(self) -> None:
        result = _run_script(
            GENERATE_CASE,
            ["--source", "ntsb", "--dry-run", "/tmp/no_such_case_dir_12345"],
        )
        assert result.returncode != 0
        assert "not exist" in result.stderr.lower() or "does not exist" in result.stderr.lower()


# ---------------------------------------------------------------------------
# Source discovery
# ---------------------------------------------------------------------------


class TestSourceDiscovery:
    """Verify source discovery finds expected sources."""

    def test_sources_directory_exists(self) -> None:
        assert SOURCES_DIR.is_dir()

    def test_ntsb_agent_plan_exists(self) -> None:
        assert (SOURCES_DIR / "ntsb" / "agent_plan.md").is_file()

    def test_grenfell_agent_plan_exists(self) -> None:
        assert (SOURCES_DIR / "grenfell" / "agent_plan.md").is_file()

    def test_copa_agent_plan_exists(self) -> None:
        assert (SOURCES_DIR / "copa" / "agent_plan.md").is_file()

    def test_generate_all_discovers_all_sources(self) -> None:
        """Running generate_all.sh --dry-run should mention all three sources."""
        result = _run_script(GENERATE_ALL, ["--dry-run"])
        combined = result.stdout + result.stderr
        assert "ntsb" in combined.lower()
        assert "grenfell" in combined.lower()
        assert "copa" in combined.lower()

    def test_generate_all_single_source_filter(self) -> None:
        """Running with --source ntsb should only process ntsb cases."""
        result = _run_script(GENERATE_ALL, ["--source", "ntsb", "--dry-run"])
        combined = result.stdout + result.stderr
        assert "ntsb" in combined.lower()
        # Should not mention other sources in the dry-run output per-case lines
        # (they may appear in the "Sources to process" line, but only ntsb)


# ---------------------------------------------------------------------------
# Case discovery
# ---------------------------------------------------------------------------


class TestCaseDiscovery:
    """Verify case discovery finds directories in corpus."""

    def test_corpus_directory_exists(self) -> None:
        assert CORPUS_DIR.is_dir()

    def test_ntsb_cases_exist(self) -> None:
        ntsb_dir = CORPUS_DIR / "ntsb"
        assert ntsb_dir.is_dir()
        cases = [d for d in ntsb_dir.iterdir() if d.is_dir()]
        assert len(cases) > 0, "No NTSB case directories found"

    def test_grenfell_cases_exist(self) -> None:
        grenfell_dir = CORPUS_DIR / "grenfell"
        assert grenfell_dir.is_dir()
        cases = [d for d in grenfell_dir.iterdir() if d.is_dir()]
        assert len(cases) > 0, "No Grenfell case directories found"

    def test_copa_cases_exist(self) -> None:
        copa_dir = CORPUS_DIR / "copa"
        assert copa_dir.is_dir()
        cases = [d for d in copa_dir.iterdir() if d.is_dir()]
        assert len(cases) > 0, "No COPA case directories found"

    def test_generate_all_finds_ntsb_cases(self) -> None:
        result = _run_script(GENERATE_ALL, ["--source", "ntsb", "--dry-run"])
        combined = result.stdout + result.stderr
        # Should find at least WPR19FA080
        assert "WPR19FA080" in combined or "DCA19FA089" in combined


# ---------------------------------------------------------------------------
# Dry-run mode
# ---------------------------------------------------------------------------


class TestDryRunMode:
    """Verify dry-run mode works without invoking Claude CLI."""

    def test_generate_case_dry_run_exits_zero(self) -> None:
        """Dry-run should succeed without invoking Claude CLI."""
        # Pick a real case directory
        ntsb_cases = sorted(d for d in (CORPUS_DIR / "ntsb").iterdir() if d.is_dir())
        if not ntsb_cases:
            pytest.skip("No NTSB case directories available")
        case_dir = ntsb_cases[0]

        result = _run_script(
            GENERATE_CASE,
            ["--source", "ntsb", "--dry-run", str(case_dir)],
        )
        assert result.returncode == 0

    def test_generate_case_dry_run_shows_plan_info(self) -> None:
        """Dry-run output should include source, case, and model info."""
        ntsb_cases = sorted(d for d in (CORPUS_DIR / "ntsb").iterdir() if d.is_dir())
        if not ntsb_cases:
            pytest.skip("No NTSB case directories available")
        case_dir = ntsb_cases[0]

        result = _run_script(
            GENERATE_CASE,
            ["--source", "ntsb", "--dry-run", str(case_dir)],
        )
        assert "[DRY-RUN]" in result.stdout
        assert "ntsb" in result.stdout.lower()
        assert "claude-sonnet-4-20250514" in result.stdout

    def test_generate_all_dry_run_exits_zero(self) -> None:
        """generate_all.sh --dry-run should complete successfully."""
        result = _run_script(GENERATE_ALL, ["--dry-run"])
        assert result.returncode == 0

    def test_generate_all_dry_run_shows_summary(self) -> None:
        """Dry-run should still print the generation summary."""
        result = _run_script(GENERATE_ALL, ["--dry-run"])
        combined = result.stdout + result.stderr
        assert "Generation Summary" in combined
        assert "Total cases" in combined

    def test_generate_all_dry_run_does_not_invoke_claude(self) -> None:
        """Verify no actual Claude CLI invocation in dry-run mode.

        The dry-run output from generate_case.sh includes '[DRY-RUN]' prefix,
        which means the Claude CLI path was never reached.
        """
        result = _run_script(GENERATE_ALL, ["--source", "ntsb", "--dry-run"])
        # Every case should show [DRY-RUN] prefix
        for line in result.stdout.splitlines():
            if "Would process case" in line:
                assert "[DRY-RUN]" in line

    def test_generate_case_dry_run_creates_output_dirs(self) -> None:
        """Dry-run should still create output staging directories."""
        ntsb_cases = sorted(d for d in (CORPUS_DIR / "ntsb").iterdir() if d.is_dir())
        if not ntsb_cases:
            pytest.skip("No NTSB case directories available")
        case_dir = ntsb_cases[0]

        _run_script(
            GENERATE_CASE,
            ["--source", "ntsb", "--dry-run", str(case_dir)],
        )
        # Verify output dirs created
        assert (case_dir / "anonymized_docs").is_dir()
        assert (case_dir / "original_claims").is_dir()
        assert (case_dir / "metadata").is_dir()
