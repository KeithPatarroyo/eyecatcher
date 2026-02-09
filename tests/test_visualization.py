"""
Test genome visualization.
"""

import os
import shutil
from pathlib import Path

import neat
import pytest
from eyecatcher.cppn_engine import create_random_genome
from PIL import Image


def _save_genome_as_text(
    genome: neat.DefaultGenome, filepath: str, config: neat.Config
):
    """Save a genome to a human-readable text file for debugging."""
    num_inputs = config.genome_config.num_inputs
    num_outputs = config.genome_config.num_outputs
    input_names = ["x", "y", "distance", "angle", "sin(a)", "cos(a)", "time", "bias"]
    output_names = ["R", "G", "B"]

    with open(filepath, "w") as f:
        f.write(f"Genome ID: {genome.key}\n")
        f.write(f"Fitness: {genome.fitness}\n")
        in_range = f"nodes -{num_inputs} to -1: {', '.join(input_names[:num_inputs])}"
        f.write(f"\nInputs: {num_inputs} ({in_range})\n")
        out_range = (
            f"nodes 0 to {num_outputs - 1}: {', '.join(output_names[:num_outputs])}"
        )
        f.write(f"Outputs: {num_outputs} ({out_range})\n")
        f.write(f"\n{'=' * 60}\n")
        f.write(f"NODES ({len(genome.nodes)} hidden nodes)\n")
        f.write(f"{'=' * 60}\n\n")
        for node_id, node in sorted(genome.nodes.items()):
            f.write(f"Node {node_id}:\n")
            f.write(f"  Activation: {node.activation}\n")
            f.write(f"  Bias: {node.bias:.6f}\n")
            f.write(f"  Response: {node.response:.6f}\n")
            f.write(f"  Aggregation: {node.aggregation}\n\n")
        f.write(f"{'=' * 60}\n")
        f.write(f"CONNECTIONS ({len(genome.connections)} total)\n")
        f.write(f"{'=' * 60}\n\n")
        enabled_conns = [c for c in genome.connections.values() if c.enabled]
        for conn in enabled_conns:
            src, dst = conn.key
            f.write(f"  {src} -> {dst}: weight={conn.weight:.6f}\n")

    return filepath


@pytest.mark.slow
def test_visualization(tmp_path, cppn_engine):
    """Save pkl, text, optional PDF, and render PNG into tmp_path.

    Set EYECATCHER_KEEP_VISUALIZATION_ARTIFACTS=1 to copy outputs to output/test/
    so you can open the PDF (and other files) after the test.
    """
    genome = create_random_genome(cppn_engine.config, genome_id=42)
    for _ in range(5):
        genome = cppn_engine.mutate_genome(genome)

    pkl_path = tmp_path / "test_genome.pkl"
    txt_path = tmp_path / "test_genome.txt"
    png_path = tmp_path / "test_pattern.png"

    cppn_engine.save_genome(genome, str(pkl_path), visualize=True)
    _save_genome_as_text(genome, str(txt_path), cppn_engine.config)

    img = cppn_engine.render_image(genome, resolution=64, time=0.5)
    Image.fromarray(img).save(str(png_path))

    assert pkl_path.exists()
    assert pkl_path.stat().st_size > 0

    assert txt_path.exists()
    assert txt_path.stat().st_size > 0
    text = txt_path.read_text()
    assert "Genome ID:" in text
    assert "NODES" in text
    assert "CONNECTIONS" in text

    assert png_path.exists()
    assert png_path.stat().st_size > 0

    viz_pdf = tmp_path / "test_genome_network.pdf"
    if viz_pdf.exists():
        assert viz_pdf.stat().st_size > 0

    # Optional: keep artifacts in output/test/ for inspection (e.g. open the PDF)
    if os.environ.get("EYECATCHER_KEEP_VISUALIZATION_ARTIFACTS"):
        out_dir = Path(__file__).resolve().parent.parent / "output" / "test"
        out_dir.mkdir(parents=True, exist_ok=True)
        for name in ["test_genome.pkl", "test_genome.txt", "test_pattern.png"]:
            src = tmp_path / name
            if src.exists():
                shutil.copy2(src, out_dir / name)
        if viz_pdf.exists():
            shutil.copy2(viz_pdf, out_dir / "test_genome_network.pdf")
            print(f"\nVisualization PDF: {out_dir.resolve()}/test_genome_network.pdf")
