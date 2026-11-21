"""CLI for project metadata and Phase 1 read-only data inspection."""

import argparse

from fraud_detection import __version__


def main(argv: list[str] | None = None) -> int:
    """Run project info or a local dataset profile."""
    parser = argparse.ArgumentParser(
        prog="fraud-bigdata",
        description="Credit card fraud — Big Data and imbalanced ML research",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("info", help="Show project and dataset summary")
    profile = commands.add_parser("profile", help="Run Phase 1 read-only CSV profiling")
    profile.add_argument("--input", default="data/raw/creditcard.csv")
    profile.add_argument("--output", default="artifacts/phase_01")
    profile.add_argument(
        "--subset",
        action="store_true",
        help="Skip original dataset size/class-count reference warnings",
    )

    args = parser.parse_args(argv)
    if args.command == "info":
        print("Credit Card Fraud Detection — Big Data Analytics")
        print("Dataset: OpenML 1597 (284,807 original transactions)")
        print("Status: skeleton and Phase 1 tools; no model or benchmark results yet")
        return 0

    if args.command == "profile":
        # Import pandas only when data extras are needed.
        from fraud_detection.ingestion.profiling import run_profile

        report = run_profile(args.input, args.output, check_reference=not args.subset)
        print(f"Profiled {report['rows']} transactions")
        print(f"Fraud count: {report['class_counts']['1']}")
        print(f"Findings: {len(report['findings'])}; valid: {report['valid']}")
        print(f"Outputs: {args.output}")
        return 0 if report["valid"] else 2

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
