"""
Programmatic dual-CPPN API usage: create, render, compile, mutate, crossover, save.
Run from repo root: python examples/api_usage.py
"""

import os

from eyecatcher.algorithm import PREVIEW_RENDER_RESOLUTION, CPPNEngine
from eyecatcher.genome import create_random_dual_genome
from eyecatcher.glsl import ShaderCompiler
from PIL import Image


def main():
    os.makedirs("output", exist_ok=True)
    engine = CPPNEngine()
    engine.create_population()
    compiler = ShaderCompiler()

    # Create a few dual genomes
    dual = create_random_dual_genome(engine.config, engine.time_config, genome_id=0)
    print("Created random dual genome (visual + time signal)")

    # Render one image (time-signal CPPN shapes the result)
    img = engine.render_dual_image(
        dual,
        resolution=PREVIEW_RENDER_RESOLUTION,
        extra_inputs={"raw_time": 0.5},
    )
    Image.fromarray(img, "RGB").save("output/dual_pattern.png")
    print("Saved: output/dual_pattern.png")

    # Compile to GLSL (dual shader)
    shader_code = compiler.compile_dual_to_glsl(dual, engine.config, engine.time_config)
    with open("output/dual_pattern.glsl", "w") as f:
        f.write(shader_code)
    print("Saved: output/dual_pattern.glsl")

    # Export bundle
    compiler.export_dual_shader_bundle(
        dual, engine.config, engine.time_config, "output/dual_pattern_bundle.json"
    )
    print("Saved: output/dual_pattern_bundle.json")

    # Mutate once
    child = engine.mutate_dual_genome(dual, 1)
    img_child = engine.render_dual_image(
        child,
        resolution=PREVIEW_RENDER_RESOLUTION,
        extra_inputs={"raw_time": 0.5},
    )
    Image.fromarray(img_child, "RGB").save("output/dual_mutant.png")
    print("Saved: output/dual_mutant.png (one mutation)")

    # Crossover: two parents -> one offspring
    parent2 = create_random_dual_genome(engine.config, engine.time_config, genome_id=2)
    offspring = engine.crossover_dual_genomes(dual, parent2, 3)
    img_off = engine.render_dual_image(
        offspring,
        resolution=PREVIEW_RENDER_RESOLUTION,
        extra_inputs={"raw_time": 0.5},
    )
    Image.fromarray(img_off, "RGB").save("output/dual_offspring.png")
    print("Saved: output/dual_offspring.png (crossover)")
    print("Done. Check output/ for shader, bundle, and images.")


if __name__ == "__main__":
    main()
