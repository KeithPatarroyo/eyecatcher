#!/usr/bin/env python3
"""
Update NEAT config num_inputs/num_outputs in config/neat/*.txt to match the catalog.

Run from repo root: python scripts/update_neat_config.py
Or: make generate-neat (or make generate)

If you store experiment settings in those .txt files (not in config/experiments.json),
they can be overwritten; prefer presets in experiments.json for reproducible settings.
"""

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


def main() -> None:
    root = _repo_root()
    sys.path.insert(0, os.path.join(root, "src"))

    from eyecatcher.experiment import NEAT_CONFIG_PATH, NEAT_TIME_CONFIG_PATH
    from eyecatcher.representation import DualCPPNRepresentation

    rep = DualCPPNRepresentation()
    visual_inputs = list(rep.visual.inputs)
    visual_outputs = list(rep.visual.outputs)
    time_inputs = list(rep.time.inputs)
    time_outputs = list(rep.time.outputs)

    visual_in_count = len(visual_inputs)
    visual_out_count = len(visual_outputs)
    time_in_count = len(time_inputs)
    time_out_count = len(time_outputs)

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
        else:
            updated = _update_neat_counts(path, visual_in_count, visual_out_count)
            if updated:
                print(
                    f"Updated {path} num_inputs={visual_in_count} "
                    f"num_outputs={visual_out_count}",
                    file=sys.stderr,
                )

    # Validate NEAT files match representation
    visual_path = os.path.join(root, NEAT_CONFIG_PATH)
    time_path = os.path.join(root, NEAT_TIME_CONFIG_PATH)
    errors = []
    v_in = _neat_value(visual_path, "num_inputs")
    v_out = _neat_value(visual_path, "num_outputs")
    if v_in is not None and v_in != visual_in_count:
        errors.append(
            f"NEAT config mismatch: num_inputs in {NEAT_CONFIG_PATH} is {v_in}, "
            f"representation has {visual_in_count}."
        )
    if v_out is not None and v_out != visual_out_count:
        errors.append(
            f"NEAT config mismatch: num_outputs in {NEAT_CONFIG_PATH} is {v_out}, "
            f"representation has {visual_out_count}."
        )
    t_in = _neat_value(time_path, "num_inputs")
    t_out = _neat_value(time_path, "num_outputs")
    if t_in is not None and t_in != time_in_count:
        errors.append(
            f"NEAT config mismatch: num_inputs in {NEAT_TIME_CONFIG_PATH} is {t_in}, "
            f"representation has {time_in_count}."
        )
    if t_out is not None and t_out != time_out_count:
        errors.append(
            f"NEAT config mismatch: num_outputs in {NEAT_TIME_CONFIG_PATH} is {t_out}, "
            f"representation has {time_out_count}."
        )
    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
