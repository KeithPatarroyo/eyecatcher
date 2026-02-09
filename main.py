"""
Legacy entry point. Use demos in demos/ instead.
"""

import sys

if __name__ == "__main__":
    print("Demos (dual-CPPN) live in demos/. Examples:", file=sys.stderr)
    print(
        "  python demos/api_usage.py  # create, render, mutate, crossover",
        file=sys.stderr,
    )
    print(
        "  python demos/evolution_batch.py  # batch evolution with proxy fitness",
        file=sys.stderr,
    )
    print(
        "  python demos/time_signal_showcase.py  # time CPPN plot (needs matplotlib)",
        file=sys.stderr,
    )
    sys.exit(1)
