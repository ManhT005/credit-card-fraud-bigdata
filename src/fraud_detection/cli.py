"""CLI entrypoint for initial project checks."""

import argparse

from fraud_detection import __version__


def main(argv: list[str] | None = None) -> int:
    """Show project metadata; pipeline commands arrive in later phases."""
    parser = argparse.ArgumentParser(
        prog="fraud-bigdata",
        description="Credit card fraud — Big Data and imbalanced ML research",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("info", help="Show project and dataset summary")

    args = parser.parse_args(argv)
    if args.command == "info":
        print("Credit Card Fraud Detection — Big Data Analytics")
        print("Dataset: OpenML 1597 (284,807 original transactions)")
        print("Status: project skeleton; no model or benchmark results yet")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
