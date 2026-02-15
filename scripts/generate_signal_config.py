#!/usr/bin/env python3
"""
Generate evolution_config_signals.generated.js from the Python signal registry.
Single source of truth: catalog + representation sockets. This script updates
NEAT config num_inputs/num_outputs in config/neat/*.txt to match the catalog.
If you store experiment settings in those .txt files (not in config/experiments.json),
they can be overwritten; prefer presets in experiments.json for reproducible settings.

Run from repo root: python scripts/generate_signal_config.py
Or: make generate-signals (or make generate)
"""

import json
import os
import re
import sys


def _repo_root() -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(script_dir)


def _update_neat_counts(path: str, num_inputs: int, num_outputs: int) -> bool:
    """Update num_inputs/num_outputs in a NEAT config file. Returns True if changed."""
    if not os.path.isfile(path):
        return False
    with open(path, encoding="utf-8") as f:
        content = f.read()
    new_content = re.sub(
        r"^(\s*num_inputs\s*=\s*)\d+(\s*)$",
        r"\g<1>" + str(num_inputs) + r"\g<2>",
        content,
        flags=re.MULTILINE,
    )
    new_content = re.sub(
        r"^(\s*num_outputs\s*=\s*)\d+(\s*)$",
        r"\g<1>" + str(num_outputs) + r"\g<2>",
        new_content,
        flags=re.MULTILINE,
    )
    if new_content != content:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return True
    return False


def _neat_value(path: str, key: str) -> int | None:
    """Read a single integer value from a NEAT config file."""
    if not os.path.isfile(path):
        return None
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*=\s*(\d+)\s*$", re.MULTILINE)
    with open(path, encoding="utf-8") as f:
        m = pattern.search(f.read())
    return int(m.group(1)) if m else None


def validate_neat(
    root: str,
    visual_path: str,
    time_path: str,
    visual_inputs: list,
    visual_outputs: list,
    time_inputs: list,
    time_outputs: list,
) -> None:
    """Validate NEAT num_inputs/num_outputs match the representation's signal lists."""
    visual_full = os.path.join(root, visual_path)
    time_full = os.path.join(root, time_path)

    errors = []
    v_in = _neat_value(visual_full, "num_inputs")
    v_out = _neat_value(visual_full, "num_outputs")
    if v_in is not None and v_in != len(visual_inputs):
        errors.append(
            f"NEAT config mismatch: num_inputs in {visual_path} is {v_in}, "
            f"representation has {len(visual_inputs)}. Update the NEAT file."
        )
    if v_out is not None and v_out != len(visual_outputs):
        errors.append(
            f"NEAT config mismatch: num_outputs in {visual_path} is {v_out}, "
            f"representation has {len(visual_outputs)}. Update the NEAT file."
        )

    t_in = _neat_value(time_full, "num_inputs")
    t_out = _neat_value(time_full, "num_outputs")
    if t_in is not None and t_in != len(time_inputs):
        errors.append(
            f"NEAT config mismatch: num_inputs in {time_path} is {t_in}, "
            f"representation has {len(time_inputs)}. Update the NEAT file."
        )
    if t_out is not None and t_out != len(time_outputs):
        errors.append(
            f"NEAT config mismatch: num_outputs in {time_path} is {t_out}, "
            f"representation has {len(time_outputs)}. Update the NEAT file."
        )

    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        sys.exit(1)


def main() -> None:
    root = _repo_root()
    sys.path.insert(0, os.path.join(root, "src"))

    from eyecatcher.experiment import NEAT_CONFIG_PATH, NEAT_TIME_CONFIG_PATH
    from eyecatcher.representation import DualCPPNRepresentation
    from eyecatcher.signals import catalog, export_for_frontend

    # Single source of truth: catalog (same presets dual_cppn uses). Discover NEAT
    # config files in config/neat/ and update each (convention: "time" in filename →
    # time counts, else visual counts). Then representation load won't fail validation.
    visual_in_count = len(catalog.DUAL_CPPN_VISUAL_INPUTS)
    visual_out_count = len(catalog.RGB_OUTPUTS)
    time_in_count = len(catalog.DUAL_CPPN_TIME_INPUTS)
    time_out_count = len(catalog.TIME_OUTPUT)

    neat_dir = os.path.join(root, "config", "neat")
    for filename in sorted(os.listdir(neat_dir)):
        if not filename.endswith(".txt"):
            continue
        path = os.path.join(neat_dir, filename)
        if not os.path.isfile(path):
            continue
        is_time = "time" in filename.lower()
        if is_time:
            updated = _update_neat_counts(path, time_in_count, time_out_count)
            if updated:
                print(
                    f"Updated {path} num_inputs={time_in_count} "
                    f"num_outputs={time_out_count}",
                    file=sys.stderr,
                )
                print(
                    "  (NEAT .txt updated by codegen; use config/experiments.json.)",
                    file=sys.stderr,
                )
        else:
            updated = _update_neat_counts(path, visual_in_count, visual_out_count)
            if updated:
                print(
                    f"Updated {path} num_inputs={visual_in_count} "
                    f"num_outputs={visual_out_count}",
                    file=sys.stderr,
                )
                print(
                    "  (NEAT .txt updated by codegen; use config/experiments.json.)",
                    file=sys.stderr,
                )

    visual_path = NEAT_CONFIG_PATH
    time_path = NEAT_TIME_CONFIG_PATH

    rep = DualCPPNRepresentation()
    validate_neat(
        root,
        visual_path,
        time_path,
        list(rep.visual.inputs),
        list(rep.visual.outputs),
        list(rep.time.inputs),
        list(rep.time.outputs),
    )

    data = export_for_frontend(rep.signal_spec)
    out_path = os.path.join(
        root, "static", "js", "evolution", "config_signals.generated.js"
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    # Emit JS that assigns window.EvolutionConfigSignals
    js_content = (
        "/* Generated by scripts/generate_signal_config.py - do not edit */\n"
        "(function () {\n"
        '    "use strict";\n'
        "    window.EvolutionConfigSignals = " + json.dumps(data, indent=4) + ";\n"
        "})();\n"
    )

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(js_content)

    print(f"Wrote {out_path}")

    # Validate JS activations match Python registry (single source of truth)
    validate_activations_js(root)


def validate_activations_js(root: str) -> None:
    """Ensure cppn_evaluator.js ACTIVATIONS keys match Python activation registry."""
    import importlib.util
    import re

    # Load activation_registry without pulling in glsl.__init__ (avoids circular import)
    reg_path = os.path.join(root, "src", "eyecatcher", "glsl", "activation_registry.py")
    spec = importlib.util.spec_from_file_location("activation_registry", reg_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    get_activation_names = mod.get_activation_names

    js_path = os.path.join(root, "static", "js", "inspection", "cppn_evaluator.js")
    with open(js_path, encoding="utf-8") as f:
        content = f.read()
    keys = re.findall(r"(\w+):\s*function\s*\(", content)
    js_set = set(keys)
    py_set = get_activation_names()
    if js_set != py_set:
        only_js = js_set - py_set
        only_py = py_set - js_set
        print(
            "Activation mismatch: JS cppn_evaluator.js ACTIVATIONS must match "
            "Python glsl.activation_registry.",
            file=sys.stderr,
        )
        if only_js:
            print(f"  Only in JS: {sorted(only_js)}", file=sys.stderr)
        if only_py:
            print(f"  Only in Python: {sorted(only_py)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
