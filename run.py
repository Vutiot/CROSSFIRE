"""CROSSFIRE — Cross-corpus Fact Incoherence Reasoning Evaluation

Entry points for corpus generation, pipeline execution, and evaluation.
"""
import argparse
import sys


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

    # Command dispatch will be implemented in later stories
    print(f"Command '{args.command}' not yet implemented.")


if __name__ == "__main__":
    main()
