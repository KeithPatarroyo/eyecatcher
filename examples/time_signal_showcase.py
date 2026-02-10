"""
Time-signal CPPN showcase: plot modified time vs raw time for a few dual genomes.
Shows how each individual's time CPPN transforms the raw clock (the "heartbeat").
Run from repo root: python examples/time_signal_showcase.py
Requires matplotlib: pip install matplotlib
"""

import os

from eyecatcher.evolution import CPPNEngine, create_random_dual_genome


def main():
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("Install matplotlib to run this demo: pip install matplotlib")
        return

    engine = CPPNEngine()
    engine.create_population()
    n_curves = 3
    duals = [create_random_dual_genome(engine, genome_id=i) for i in range(n_curves)]
    raw_times = [(-1.0 + i / 50.0) for i in range(101)]
    plt.figure(figsize=(8, 5))
    for idx, dual in enumerate(duals):
        modified = [
            engine.query_time_signal(
                dual.time_signal,
                {
                    "raw_time": rt,
                    "mouse_speed": 0.0,
                    "mouse_distance": 0.0,
                    "inactivity": 0.0,
                },
            )
            for rt in raw_times
        ]
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
