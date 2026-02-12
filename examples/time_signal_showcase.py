"""
Time-signal CPPN showcase: plot modified time vs raw time for a few dual genomes.
Run from repo root: python examples/time_signal_showcase.py
Requires matplotlib: pip install matplotlib
"""

import os

from eyecatcher.substrate import get_substrate


def main():
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("Install matplotlib to run this demo: pip install matplotlib")
        return

    substrate = get_substrate("dual_cppn")
    n_curves = 3
    individuals = [substrate.create_random(key=i) for i in range(n_curves)]
    raw_times = [(-1.0 + i / 50.0) for i in range(101)]
    plt.figure(figsize=(8, 5))
    for idx, ind in enumerate(individuals):
        modified = []
        for rt in raw_times:
            result = substrate.query_time_output(
                ind,
                {
                    "raw_time": rt,
                    "mouse_speed": 0.0,
                    "mouse_dist": 0.0,
                    "activity": 0.0,
                },
            )
            if result is not None:
                modified.append(result["timeOutput"])
            else:
                modified.append(0.0)
        plt.plot(raw_times, modified, label=f"Genome {idx}")
    plt.xlabel("Raw time")
    plt.ylabel("Modified time (time CPPN output)")
    plt.title("Time signal CPPN: raw time -> modified time (no mouse input)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    os.makedirs("output", exist_ok=True)
    out_path = "output/time_signal_showcase.png"
    plt.savefig(out_path, dpi=120)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
