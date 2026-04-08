"""Validate pre-generated gold datasets against Pydantic schemas.

Checks that all JSONL lines parse as Document models, entity graph parses as
EntityGraph, and gold labels parse as IncoherenceLabel/DistractorLabel.

Usage:
    python -m scripts.validate_datasets [--path data/datasets]
"""

import argparse
import json
import sys
from pathlib import Path

from loguru import logger

from crossfire.shared.schemas.corpus import Document
from crossfire.shared.schemas.entities import EntityGraph
from crossfire.shared.schemas.incoherences import DistractorLabel, IncoherenceLabel


def validate_dataset(dataset_dir: Path) -> dict:
    """Validate a single dataset directory.

    Returns a dict with 'valid' (bool), 'errors' (list[str]), and counts.
    """
    dataset_dir = Path(dataset_dir)
    errors: list[str] = []
    counts = {
        "documents": 0,
        "entities": 0,
        "edges": 0,
        "incoherences": 0,
        "distractors": 0,
    }

    corpus_dir = dataset_dir / "corpus"
    gold_dir = dataset_dir / "gold"
    meta_path = dataset_dir / "metadata.json"

    # Check directory structure
    if not corpus_dir.is_dir():
        errors.append(f"Missing corpus directory: {corpus_dir}")
    if not gold_dir.is_dir():
        errors.append(f"Missing gold directory: {gold_dir}")
    if not meta_path.is_file():
        errors.append(f"Missing metadata.json: {meta_path}")

    if errors:
        return {"valid": False, "errors": errors, "counts": counts}

    # Validate corpus JSONL files
    jsonl_files = sorted(corpus_dir.glob("subcorpus_*.jsonl"))
    if not jsonl_files:
        errors.append("No subcorpus JSONL files found in corpus/")
    else:
        for jsonl_path in jsonl_files:
            try:
                lines = jsonl_path.read_text(encoding="utf-8").strip().split("\n")
                for i, line in enumerate(lines):
                    if not line:
                        continue
                    try:
                        Document.model_validate_json(line)
                        counts["documents"] += 1
                    except Exception as e:
                        errors.append(f"{jsonl_path.name} line {i + 1}: {e}")
            except Exception as e:
                errors.append(f"Failed to read {jsonl_path.name}: {e}")

    # Validate entity graph
    entity_graph_path = gold_dir / "entity_graph.json"
    if not entity_graph_path.is_file():
        errors.append("Missing gold/entity_graph.json")
    else:
        try:
            graph = EntityGraph.model_validate_json(
                entity_graph_path.read_text(encoding="utf-8")
            )
            counts["entities"] = len(graph.nodes)
            counts["edges"] = len(graph.edges)
        except Exception as e:
            errors.append(f"entity_graph.json validation failed: {e}")

    # Validate incoherence labels
    inc_path = gold_dir / "gold_incoherence_labels.json"
    if not inc_path.is_file():
        errors.append("Missing gold/gold_incoherence_labels.json")
    else:
        try:
            inc_data = json.loads(inc_path.read_text(encoding="utf-8"))
            for i, item in enumerate(inc_data):
                try:
                    IncoherenceLabel.model_validate(item)
                    counts["incoherences"] += 1
                except Exception as e:
                    errors.append(f"incoherence label {i}: {e}")
        except json.JSONDecodeError as e:
            errors.append(f"gold_incoherence_labels.json is not valid JSON: {e}")

    # Validate distractor labels
    dist_path = gold_dir / "gold_distractor_labels.json"
    if not dist_path.is_file():
        errors.append("Missing gold/gold_distractor_labels.json")
    else:
        try:
            dist_data = json.loads(dist_path.read_text(encoding="utf-8"))
            for i, item in enumerate(dist_data):
                try:
                    DistractorLabel.model_validate(item)
                    counts["distractors"] += 1
                except Exception as e:
                    errors.append(f"distractor label {i}: {e}")
        except json.JSONDecodeError as e:
            errors.append(f"gold_distractor_labels.json is not valid JSON: {e}")

    # Validate metadata
    try:
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        required_fields = ["benchmark_version", "master_seed"]
        for field in required_fields:
            if field not in metadata:
                errors.append(f"metadata.json missing required field: {field}")
    except json.JSONDecodeError as e:
        errors.append(f"metadata.json is not valid JSON: {e}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "counts": counts,
    }


def validate_all_datasets(datasets_dir: Path) -> dict[str, dict]:
    """Validate all datasets in a directory."""
    datasets_dir = Path(datasets_dir)
    results = {}

    for child in sorted(datasets_dir.iterdir()):
        if child.is_dir() and not child.name.startswith("."):
            results[child.name] = validate_dataset(child)

    return results


def main():
    parser = argparse.ArgumentParser(description="Validate pre-generated gold datasets")
    parser.add_argument(
        "--path",
        default="data/datasets",
        help="Path to datasets directory (default: data/datasets)",
    )
    args = parser.parse_args()

    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level:<7} | {message}")

    datasets_dir = Path(args.path)
    if not datasets_dir.is_dir():
        logger.error(f"Datasets directory not found: {datasets_dir}")
        sys.exit(1)

    results = validate_all_datasets(datasets_dir)

    if not results:
        logger.warning(f"No datasets found in {datasets_dir}")
        sys.exit(1)

    all_valid = True
    for name, result in results.items():
        status = "PASS" if result["valid"] else "FAIL"
        counts = result["counts"]
        logger.info(
            f"  {status} {name}: "
            f"{counts['documents']} docs, "
            f"{counts['entities']} entities, "
            f"{counts['edges']} edges, "
            f"{counts['incoherences']} incoherences, "
            f"{counts['distractors']} distractors"
        )
        if not result["valid"]:
            all_valid = False
            for err in result["errors"]:
                logger.error(f"    {err}")

    if not all_valid:
        logger.error("Validation FAILED")
        sys.exit(1)

    logger.info("All datasets passed validation.")


if __name__ == "__main__":
    main()
