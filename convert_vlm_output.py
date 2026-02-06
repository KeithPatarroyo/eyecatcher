#!/usr/bin/env python
"""
Convert VLM evolution output to website-importable format.
"""
import json
import os
import argparse
from glob import glob


def convert_vlm_output_to_population(
    input_dir: str,
    output_path: str,
    name: str = "VLM Evolution Population",
    use_final: bool = True,
):
    """
    Convert VLM evolution output directory to website population format.

    Parameters
    ----------
    input_dir : str
        Path to VLM evolution output directory (e.g., output/vlm_evolution)
    output_path : str
        Path for output JSON file
    name : str
        Name for the population
    use_final : bool
        If True, use final_population/. If False, use latest gen_*/
    """
    genomes = []

    if use_final:
        # Load from final_population/
        pattern = os.path.join(input_dir, "final_population", "genome_*.json")
    else:
        # Find latest generation directory
        gen_dirs = sorted(glob(os.path.join(input_dir, "gen_*")))
        if not gen_dirs:
            raise FileNotFoundError(f"No generation directories found in {input_dir}")
        latest_gen = gen_dirs[-1]
        pattern = os.path.join(latest_gen, "genome_*.json")
        print(f"Using latest generation: {os.path.basename(latest_gen)}")

    genome_files = sorted(glob(pattern))
    if not genome_files:
        raise FileNotFoundError(f"No genome files found matching {pattern}")

    print(f"Found {len(genome_files)} genome files")

    for filepath in genome_files:
        with open(filepath) as f:
            genome = json.load(f)
            genomes.append(genome)

    # Determine generation number
    generation = 0
    history_path = os.path.join(input_dir, "evolution_history.json")
    if os.path.exists(history_path):
        with open(history_path) as f:
            history = json.load(f)
            if history:
                generation = history[-1].get("generation", 0) + 1

    # Create population structure
    population = {
        "name": name,
        "generation": generation,
        "genomes": genomes,
    }

    # Write output
    with open(output_path, "w") as f:
        json.dump(population, f, indent=2)

    print(f"Saved {len(genomes)} genomes to {output_path}")
    print(f"Import this file using the website's Import button")


def main():
    parser = argparse.ArgumentParser(
        description="Convert VLM evolution output to website format"
    )
    parser.add_argument(
        "--input",
        type=str,
        default="output/vlm_evolution",
        help="Path to VLM evolution output directory",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="vlm_population.json",
        help="Output JSON file path",
    )
    parser.add_argument(
        "--name",
        type=str,
        default="VLM Evolution Population",
        help="Name for the population",
    )
    parser.add_argument(
        "--use-generation",
        action="store_true",
        help="Use latest gen_* instead of final_population",
    )

    args = parser.parse_args()

    convert_vlm_output_to_population(
        input_dir=args.input,
        output_path=args.output,
        name=args.name,
        use_final=not args.use_generation,
    )


if __name__ == "__main__":
    main()
