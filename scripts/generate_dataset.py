"""Generate a complete gold dataset from a preset configuration.

Chains: corpus generation → incoherence injection → distractor generation
→ gold annotation assembly. Organizes output into the architecture-specified
directory structure: corpus/ + gold/ + metadata.json.

Usage:
    python -m scripts.generate_dataset --config configs/presets/default.yaml --output data/datasets/default
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

import yaml
from loguru import logger

from crossfire.generator.annotator import assemble_gold_annotations
from crossfire.generator.distractor_generator import generate_distractors
from crossfire.generator.injector import inject_incoherences
from crossfire.generator.orchestrator import generate_corpus
from crossfire.shared.llm import llm_call, reset_usage
from crossfire.shared.schemas.config import GeneratorConfig
from crossfire.shared.schemas.entities import EntityGraph
from crossfire.shared.seed_manager import SeedManager


def generate_dataset(
    config: GeneratorConfig,
    llm=None,
) -> tuple[dict | None, str | None]:
    """Generate a complete gold dataset with corpus, incoherences, distractors, and annotations.

    Args:
        config: Generator configuration with output_dir set to the dataset directory.
        llm: LLM call function (defaults to shared llm_call).

    Returns:
        (metadata_dict, None) on success, (None, error_message) on failure.
    """
    if llm is None:
        llm = llm_call

    dataset_dir = Path(config.output_dir)
    corpus_dir = dataset_dir / "corpus"
    gold_dir = dataset_dir / "gold"

    # Reset LLM usage tracking for this dataset
    reset_usage()

    seed_mgr = SeedManager(config.master_seed)

    # --- Step 1: Generate corpus (writes flat to dataset_dir) ---
    logger.info(f"Step 1/4: Generating corpus for preset '{config.name}'")

    # Temporarily set output_dir to dataset_dir for the orchestrator
    metadata, error = generate_corpus(config, seed_mgr, llm=llm)
    if error:
        return None, f"Corpus generation failed: {error}"

    # --- Step 2: Reorganize output into corpus/ and gold/ ---
    logger.info("Reorganizing output into corpus/ and gold/ structure")
    corpus_dir.mkdir(parents=True, exist_ok=True)
    gold_dir.mkdir(parents=True, exist_ok=True)

    # Move subcorpus JSONL files to corpus/
    for jsonl_path in sorted(dataset_dir.glob("subcorpus_*.jsonl")):
        shutil.move(str(jsonl_path), str(corpus_dir / jsonl_path.name))

    # Move entity graph to gold/
    entity_graph_src = dataset_dir / "entity_graph.json"
    if entity_graph_src.exists():
        shutil.move(str(entity_graph_src), str(gold_dir / "entity_graph.json"))

    # metadata.json stays at dataset root (already there from orchestrator)

    # --- Step 3: Load entity graph for injection/distractor steps ---
    entity_graph = EntityGraph.model_validate_json(
        (gold_dir / "entity_graph.json").read_text(encoding="utf-8")
    )

    # --- Step 4: Inject incoherences ---
    logger.info("Step 2/4: Injecting incoherences")
    inc_labels, error = inject_incoherences(
        corpus_dir=corpus_dir,
        config=config,
        entity_graph=entity_graph,
        seed_mgr=seed_mgr,
        llm=llm,
    )
    if error:
        return None, f"Incoherence injection failed: {error}"

    # --- Step 5: Generate distractors ---
    logger.info("Step 3/4: Generating distractors")
    dist_labels, error = generate_distractors(
        corpus_dir=corpus_dir,
        config=config,
        entity_graph=entity_graph,
        incoherence_count=len(inc_labels) if inc_labels else 0,
        seed_mgr=seed_mgr,
        llm=llm,
    )
    if error:
        return None, f"Distractor generation failed: {error}"

    # --- Step 6: Assemble gold annotations ---
    logger.info("Step 4/4: Assembling gold annotations")
    annotation_summary, error = assemble_gold_annotations(
        output_dir=gold_dir,
        incoherence_labels=inc_labels or [],
        distractor_labels=dist_labels or [],
        corpus_dir=corpus_dir,
        version="1.0",
    )
    if error:
        return None, f"Gold annotation assembly failed: {error}"

    # --- Step 7: Update root metadata.json with annotation summary ---
    meta_path = dataset_dir / "metadata.json"
    root_metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    root_metadata["annotation_summary"] = annotation_summary
    root_metadata["version"] = "1.0"
    meta_path.write_text(
        json.dumps(root_metadata, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # Clean up the annotator's duplicate metadata.json in gold/
    gold_meta = gold_dir / "metadata.json"
    if gold_meta.exists():
        gold_meta.unlink()

    logger.info(
        f"Dataset generation complete: {config.name} → {dataset_dir}\n"
        f"  Corpus: {len(list(corpus_dir.glob('subcorpus_*.jsonl')))} subcorpora\n"
        f"  Incoherences: {len(inc_labels or [])}\n"
        f"  Distractors: {len(dist_labels or [])}"
    )

    return root_metadata, None


def main():
    parser = argparse.ArgumentParser(
        description="Generate a complete gold dataset from a preset configuration"
    )
    parser.add_argument(
        "--config", required=True, help="Path to preset YAML config file"
    )
    parser.add_argument(
        "--output", required=True, help="Output directory for the dataset"
    )
    args = parser.parse_args()

    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level:<7} | {message}")

    with open(args.config) as f:
        preset = yaml.safe_load(f)

    preset["output_dir"] = args.output
    config = GeneratorConfig(**preset)

    metadata, error = generate_dataset(config)
    if error:
        logger.error(f"Generation failed: {error}")
        sys.exit(1)

    logger.info("Done.")


if __name__ == "__main__":
    main()
