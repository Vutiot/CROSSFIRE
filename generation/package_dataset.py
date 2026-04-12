#!/usr/bin/env python3
"""Dataset versioning & release packaging (Story 3.5-NEW).

Assembles verified injection outputs into versioned datasets at
``data/datasets/{version}/`` with full metadata and aggregate statistics.

Usage::

    python generation/package_dataset.py --version v1 \\
        --cases corpus/ntsb/WPR19FA080 corpus/ntsb/ERA18FA120

    python generation/package_dataset.py --version v2 \\
        --cases corpus/ntsb/WPR19FA080 \\
        --params-file params.json \\
        --base-version v1

Directory output::

    data/datasets/{version}/
      generation_params.json
      dataset_manifest.json
      {case_id}/
        anonymized_docs/*.txt
        contradictions/
          intra_doc_contradictions.jsonl
          inter_doc_contradictions.jsonl
          all_contradictions.jsonl
        distractors/
          distractor_labels.jsonl
        metadata/
          knowledge_graph.json  (NOT gold eval reference)
          domain_registry.json
          scope_map.json
        validation/
          diff_verification_log.json
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from loguru import logger

# Allow imports from the crossfire package (project root may not be on sys.path)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from crossfire.shared.schemas.config import GenerationParams  # noqa: E402

# Subdirectories to copy from each case directory.
# Each entry is (source_subdir, required).
_CASE_SUBDIRS: list[tuple[str, bool]] = [
    ("anonymized_docs", True),
    ("contradictions", True),
    ("distractors", False),
    ("metadata", False),
    ("validation", False),
]


# ---------------------------------------------------------------------------
# Case copying
# ---------------------------------------------------------------------------


def copy_case(src_case_dir: Path, dest_case_dir: Path) -> None:
    """Copy a source case directory into the dataset version directory.

    Copies the following subdirectories (when present):
      - anonymized_docs/ (.txt files)
      - contradictions/ (verified JSONL files)
      - distractors/ (distractor_labels.jsonl)
      - metadata/ (knowledge_graph.json, domain_registry.json, scope_map.json)
      - validation/ (diff_verification_log.json etc.)

    Args:
        src_case_dir: Path to the source case directory.
        dest_case_dir: Path where the case should be copied to.
    """
    dest_case_dir.mkdir(parents=True, exist_ok=True)

    for subdir_name, required in _CASE_SUBDIRS:
        src_subdir = src_case_dir / subdir_name
        if src_subdir.exists() and src_subdir.is_dir():
            shutil.copytree(src_subdir, dest_case_dir / subdir_name)
        elif required:
            logger.warning(
                f"Required subdirectory {subdir_name}/ missing in {src_case_dir}"
            )


# ---------------------------------------------------------------------------
# Manifest computation
# ---------------------------------------------------------------------------


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL file and return a list of parsed dicts."""
    if not path.exists():
        return []
    items: list[dict[str, Any]] = []
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return items
    for line in text.split("\n"):
        line = line.strip()
        if line:
            items.append(json.loads(line))
    return items


def compute_manifest(version_dir: Path) -> dict[str, Any]:
    """Compute aggregate statistics for a packaged dataset version.

    Scans all case directories within *version_dir* and aggregates:
      - case_count: number of case directories
      - document_count: total .txt files in anonymized_docs/
      - contradictions_per_scope: {intra_doc: N, inter_doc: N}
      - distractor_count: total distractors
      - mechanism_distribution: {mechanism: proportion}
      - detectability_distribution: {detectability: proportion}

    Args:
        version_dir: Path to the dataset version directory.

    Returns:
        Dict with aggregate statistics.
    """
    case_dirs = sorted(
        d for d in version_dir.iterdir()
        if d.is_dir() and d.name not in {"__pycache__"}
    )

    total_docs = 0
    scope_counts: Counter[str] = Counter()
    mechanism_counts: Counter[str] = Counter()
    detectability_counts: Counter[str] = Counter()
    total_distractors = 0

    for case_dir in case_dirs:
        # Count documents (*.txt in anonymized_docs/)
        docs_dir = case_dir / "anonymized_docs"
        if docs_dir.exists():
            total_docs += len(list(docs_dir.glob("*.txt")))

        # Read all_contradictions.jsonl for stats
        all_contra_path = case_dir / "contradictions" / "all_contradictions.jsonl"
        contradictions = _read_jsonl(all_contra_path)
        for c in contradictions:
            scope = c.get("scope", "unknown")
            scope_counts[scope] += 1
            mechanism = c.get("mechanism", "unknown")
            mechanism_counts[mechanism] += 1
            detectability = c.get("detectability", "unknown")
            detectability_counts[detectability] += 1

        # Count distractors
        distractor_path = case_dir / "distractors" / "distractor_labels.jsonl"
        distractors = _read_jsonl(distractor_path)
        total_distractors += len(distractors)

    total_contradictions = sum(scope_counts.values())

    # Compute distributions as proportions
    mechanism_distribution: dict[str, float] = {}
    if total_contradictions > 0:
        for mech, count in mechanism_counts.items():
            mechanism_distribution[mech] = count / total_contradictions

    detectability_distribution: dict[str, float] = {}
    if total_contradictions > 0:
        for det, count in detectability_counts.items():
            detectability_distribution[det] = count / total_contradictions

    return {
        "case_count": len(case_dirs),
        "document_count": total_docs,
        "contradictions_per_scope": {
            "intra_doc": scope_counts.get("intra_doc", 0),
            "inter_doc": scope_counts.get("inter_doc", 0),
        },
        "distractor_count": total_distractors,
        "mechanism_distribution": mechanism_distribution,
        "detectability_distribution": detectability_distribution,
    }


# ---------------------------------------------------------------------------
# Main packaging function
# ---------------------------------------------------------------------------


def package_dataset(
    version: str,
    case_dirs: list[Path],
    output_dir: Path | None = None,
    params_file: Path | None = None,
    base_version: str | None = None,
) -> Path:
    """Package verified case outputs into a versioned dataset.

    Args:
        version: Version identifier (e.g. "v1").
        case_dirs: List of source case directory paths to include.
        output_dir: Root output directory (default: data/datasets/).
        params_file: Optional path to a GenerationParams JSON file.
        base_version: Optional base version for re-injection lineage.

    Returns:
        Path to the created version directory.
    """
    if output_dir is None:
        output_dir = _PROJECT_ROOT / "data" / "datasets"

    version_dir = output_dir / version
    version_dir.mkdir(parents=True, exist_ok=True)

    # Copy each case
    for case_dir in case_dirs:
        case_dir = Path(case_dir)
        case_id = case_dir.name
        dest_case_dir = version_dir / case_id
        logger.info(f"Copying case {case_id} from {case_dir}")
        copy_case(case_dir, dest_case_dir)

    # Write generation_params.json
    if params_file is not None:
        params_data = json.loads(Path(params_file).read_text(encoding="utf-8"))
        params = GenerationParams.model_validate(params_data)
        # Override version_id and base_version from CLI args
        params = params.model_copy(
            update={"version_id": version, "base_version": base_version},
        )
    else:
        params = GenerationParams(
            version_id=version,
            base_version=base_version,
            contradiction_rate_intra_doc=0.0,
            contradiction_rate_inter_doc=0.0,
            distractor_ratio=0.0,
        )

    params_path = version_dir / "generation_params.json"
    params_path.write_text(
        params.model_dump_json(indent=2) + "\n", encoding="utf-8",
    )
    logger.info(f"Wrote {params_path}")

    # Compute and write dataset_manifest.json
    manifest = compute_manifest(version_dir)
    manifest["version"] = version
    manifest["base_version"] = base_version
    manifest_path = version_dir / "dataset_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
    )
    logger.info(f"Wrote {manifest_path}")

    logger.info(
        f"Dataset {version} packaged: "
        f"{manifest['case_count']} cases, "
        f"{manifest['document_count']} documents, "
        f"{sum(manifest['contradictions_per_scope'].values())} contradictions, "
        f"{manifest['distractor_count']} distractors"
    )

    return version_dir


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Package verified injection outputs into a versioned CROSSFIRE dataset.",
    )
    parser.add_argument(
        "--version",
        required=True,
        help="Dataset version identifier (e.g. v1, v2).",
    )
    parser.add_argument(
        "--cases",
        nargs="+",
        required=True,
        type=Path,
        help="One or more case directories to include.",
    )
    parser.add_argument(
        "--params-file",
        type=Path,
        default=None,
        help="Path to GenerationParams JSON file. If not provided, defaults are used.",
    )
    parser.add_argument(
        "--base-version",
        default=None,
        help="Base version for re-injection (records lineage).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: data/datasets/).",
    )

    args = parser.parse_args()

    version_dir = package_dataset(
        version=args.version,
        case_dirs=args.cases,
        output_dir=args.output_dir,
        params_file=args.params_file,
        base_version=args.base_version,
    )
    print(f"Dataset packaged at: {version_dir}")


if __name__ == "__main__":
    main()
