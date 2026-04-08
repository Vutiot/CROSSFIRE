"""Generate all pre-generated gold datasets from preset configurations.

Iterates over all preset configs in configs/presets/ and generates a complete
dataset for each one in data/datasets/{preset_name}/.

Usage:
    python -m scripts.generate_all_datasets [--presets default,low_connectivity]
"""

import argparse
import sys
from pathlib import Path

import yaml
from loguru import logger

from crossfire.shared.llm import log_usage_summary, reset_usage
from crossfire.shared.schemas.config import GeneratorConfig

from .generate_dataset import generate_dataset

# Presets to generate (excluding example_custom.yaml)
_PRESET_NAMES = ["default", "low_connectivity", "high_connectivity", "stress_test"]

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_PRESETS_DIR = _PROJECT_ROOT / "configs" / "presets"
_DATASETS_DIR = _PROJECT_ROOT / "data" / "datasets"


def generate_all(preset_names: list[str] | None = None) -> dict[str, str | None]:
    """Generate datasets for all specified presets.

    Args:
        preset_names: List of preset names to generate. Defaults to all 4.

    Returns:
        Dict of preset_name → error_message (None if successful).
    """
    names = preset_names or _PRESET_NAMES
    results: dict[str, str | None] = {}

    for i, name in enumerate(names):
        config_path = _PRESETS_DIR / f"{name}.yaml"
        output_dir = _DATASETS_DIR / name

        if not config_path.is_file():
            logger.error(f"Preset config not found: {config_path}")
            results[name] = f"Config not found: {config_path}"
            continue

        logger.info(f"[{i + 1}/{len(names)}] Generating dataset: {name}")

        with open(config_path) as f:
            preset = yaml.safe_load(f)

        preset["output_dir"] = str(output_dir)
        config = GeneratorConfig(**preset)

        reset_usage()
        metadata, error = generate_dataset(config)

        if error:
            logger.error(f"  FAILED: {error}")
            results[name] = error
        else:
            log_usage_summary()
            results[name] = None
            logger.info(f"  Dataset '{name}' generated at {output_dir}")

    # Summary
    passed = sum(1 for v in results.values() if v is None)
    failed = sum(1 for v in results.values() if v is not None)
    logger.info(f"Generation complete: {passed} succeeded, {failed} failed")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Generate all pre-generated gold datasets"
    )
    parser.add_argument(
        "--presets",
        default=None,
        help="Comma-separated list of preset names (default: all 4)",
    )
    args = parser.parse_args()

    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level:<7} | {message}")

    preset_names = args.presets.split(",") if args.presets else None
    results = generate_all(preset_names)

    if any(v is not None for v in results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
