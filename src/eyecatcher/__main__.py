"""
CLI entry point for `python -m eyecatcher`.

Commands:
  config --show   Print effective experiment config with provenance.
"""

import argparse
import json
import sys


def _cmd_config_show() -> int:
    """Print effective config with provenance. Returns 0 on success."""
    from .experiment import get_effective_config_with_provenance

    data = get_effective_config_with_provenance()
    print(json.dumps(data, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="eyecatcher",
        description="Eyecatcher CLI: config and helpers.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    config_parser = subparsers.add_parser("config", help="Experiment config")
    config_parser.add_argument(
        "--show",
        action="store_true",
        help="Show effective config with provenance (defaults / preset / runtime).",
    )

    args = parser.parse_args()

    if args.command == "config":
        if args.show:
            return _cmd_config_show()
        config_parser.print_help()
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
