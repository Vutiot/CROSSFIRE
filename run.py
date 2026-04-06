"""CROSSFIRE — Cross-corpus Fact Incoherence Reasoning Evaluation

Entry points for corpus generation, pipeline execution, and evaluation.
"""
import argparse
import sys

import yaml
from loguru import logger

from crossfire.shared.schemas.config import GeneratorConfig


def main():
    parser = argparse.ArgumentParser(description="CROSSFIRE benchmark toolkit")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Generate corpus
    gen_parser = subparsers.add_parser("generate", help="Generate a benchmark corpus")
    gen_parser.add_argument("--config", required=True, help="Path to preset YAML config")
    gen_parser.add_argument("--output", default="output/generated", help="Output directory")
    gen_parser.add_argument("--dry-run", action="store_true", help="Estimate cost without generating")

    # Run pipeline
    pipe_parser = subparsers.add_parser("pipeline", help="Run auditing pipeline")
    pipe_parser.add_argument("--corpus", required=True, help="Path to corpus directory")
    pipe_parser.add_argument("--mode", choices=["hybrid", "agentic", "graph-native"], required=True)
    pipe_parser.add_argument("--output", default="output/reports", help="Output directory")

    # Run evaluation
    eval_parser = subparsers.add_parser("evaluate", help="Evaluate pipeline results")
    eval_parser.add_argument("--report", required=True, help="Path to pipeline report")
    eval_parser.add_argument("--gold", required=True, help="Path to gold annotations directory")
    eval_parser.add_argument("--output", default="output/evaluation", help="Output directory")

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "generate":
        _run_generate(args)
    else:
        print(f"Command '{args.command}' not yet implemented.")


def _run_generate(args):
    """Run corpus generation from a preset YAML config."""
    from crossfire.generator.orchestrator import generate_corpus
    from crossfire.shared.seed_manager import SeedManager

    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level:<7} | {message}")

    with open(args.config) as f:
        preset = yaml.safe_load(f)

    preset["output_dir"] = args.output
    preset["dry_run"] = args.dry_run
    config = GeneratorConfig(**preset)

    seed_mgr = SeedManager(config.master_seed)
    metadata, error = generate_corpus(config, seed_mgr)

    if error:
        logger.error(f"Generation failed: {error}")
        sys.exit(1)

    logger.info(f"Output: {args.output}")


if __name__ == "__main__":
    main()
