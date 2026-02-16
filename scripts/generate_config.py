#!/usr/bin/env python3
"""
Generate static/js/config.generated.js with unified window.EyecatcherConfig.

Single source: representations (export), signals (per representation id),
defaults (evolution_defaults.json). Replaces generate_signal_config,
generate_representation_config, generate_evolution_config for JS output.
NEAT config is updated by scripts/update_neat_config.py (make generate-neat).

Signals: generated per representation id (one entry per rep's sensory_system).
The frontend must use the entry for the *current* representation_id so that
toggle panels and signal state match the active representation. Adding a new
representation with new controls will automatically expose them when that rep
is selected.

Run from repo root: python scripts/generate_config.py
Or: make generate-config (or make generate)

Optional flags for incremental updates:
  --signals-only       Only (re)generate signals section
  --representations-only  Only (re)generate representations section
  --defaults-only      Only (re)generate defaults section
"""

import argparse
import json
import os
import sys


def _repo_root() -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(script_dir)


def _get_representations(root: str) -> list:
    sys.path.insert(0, os.path.join(root, "src"))
    from eyecatcher.representation.export import export_representations_for_frontend

    return export_representations_for_frontend()


def _get_signals_per_representation(root: str) -> dict:
    """Export signal catalog per representation id.

    Frontend uses signals[representationId] for the current rep.
    """
    sys.path.insert(0, os.path.join(root, "src"))
    from eyecatcher.representation.registry import REPRESENTATIONS, get_representation
    from eyecatcher.signals import export_for_frontend

    result = {}
    for rid in REPRESENTATIONS:
        rep = get_representation(rid, **{})
        result[rid] = export_for_frontend(rep.sensory_system)
    return result


def _get_defaults(root: str) -> dict:
    path = os.path.join(root, "config", "evolution_defaults.json")
    if not os.path.isfile(path):
        print(f"Missing {path}", file=sys.stderr)
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        print("evolution_defaults.json must be a JSON object", file=sys.stderr)
        sys.exit(1)
    frontend_keys = [
        "population_size",
        "max_population_size",
        "min_population_size",
        "crossover_probability",
    ]
    defaults = {k: data.get(k) for k in frontend_keys}
    for k in frontend_keys:
        if defaults[k] is None:
            print(
                f"Missing or null key in evolution_defaults.json: {k}",
                file=sys.stderr,
            )
            sys.exit(1)
    return defaults


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate unified config.generated.js")
    parser.add_argument(
        "--signals-only",
        action="store_true",
        help="Only regenerate signals section (requires existing file)",
    )
    parser.add_argument(
        "--representations-only",
        action="store_true",
        help="Only regenerate representations section",
    )
    parser.add_argument(
        "--defaults-only",
        action="store_true",
        help="Only regenerate defaults section",
    )
    args = parser.parse_args()
    root = _repo_root()
    out_path = os.path.join(root, "static", "js", "config.generated.js")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    if args.representations_only or args.defaults_only or args.signals_only:
        # Incremental: load existing config from file, then overwrite one section
        config = {}
        if os.path.isfile(out_path):
            with open(out_path, encoding="utf-8") as f:
                content = f.read()
            idx = content.find("window.EyecatcherConfig = ")
            if idx >= 0:
                start = content.find("{", idx)
                if start >= 0:
                    depth = 0
                    for i in range(start, len(content)):
                        if content[i] == "{":
                            depth += 1
                        elif content[i] == "}":
                            depth -= 1
                            if depth == 0:
                                try:
                                    config = json.loads(content[start : i + 1])
                                except json.JSONDecodeError:
                                    pass
                                break

        config.setdefault("representations", [])
        config.setdefault("signals", {})  # per representation id
        config.setdefault("defaults", {})

        if args.representations_only:
            config["representations"] = _get_representations(root)
        if args.defaults_only:
            config["defaults"] = _get_defaults(root)
        if args.signals_only:
            config["signals"] = _get_signals_per_representation(root)
    else:
        # Full generation
        config = {
            "representations": _get_representations(root),
            "signals": _get_signals_per_representation(root),
            "defaults": _get_defaults(root),
        }

    js_content = (
        "/* Generated by scripts/generate_config.py - do not edit */\n"
        "/* signals: keyed by rep id; EyecatcherConfig.signals[representationId] */\n"
        "window.EyecatcherConfig = " + json.dumps(config, indent=4) + ";\n"
    )
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(js_content)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
