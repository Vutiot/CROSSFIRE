#!/usr/bin/env python3
"""CLI entry point for the NTSB scraping and analysis pipeline."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from loguru import logger

from crossfire.generator.scraper.config import ScraperConfig
from crossfire.generator.scraper.orchestrator import run_pipeline


def main() -> None:
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level:<7} | {message}")

    logger.info("NTSB Scraping & Structure Analysis Pipeline")
    logger.info("=" * 50)

    config = ScraperConfig()
    report, error = run_pipeline(config)

    if error:
        logger.error(f"Pipeline failed: {error}")
        sys.exit(1)

    logger.info("Pipeline completed successfully")
    logger.info(f"Report: {config.analysis_dir / 'analysis_report.json'}")


if __name__ == "__main__":
    main()
