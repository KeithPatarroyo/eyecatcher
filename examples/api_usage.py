"""
Programmatic dual-CPPN API usage: create, render, compile, mutate, crossover.
Run from repo root: python examples/api_usage.py
"""

import os

from eyecatcher.experiment import PREVIEW_RENDER_RESOLUTION
from eyecatcher.representation import get_representation
from PIL import Image


def main():
    os.makedirs("output", exist_ok=True)
    representation = get_representation("dual_cppn")

    # Create random individual
    ind = representation.create_random(key=0)
    print("Created random dual genome (visual + time signal)")

    # Render one image
    img = representation.render_to_image(
        ind,
        resolution=PREVIEW_RENDER_RESOLUTION,
        extra_inputs={"raw_time": 0.5},
    )
    if img is not None:
        Image.fromarray(img, "RGB").save("output/dual_pattern.png")
        print("Saved: output/dual_pattern.png")

    # Compile to GLSL
    shader_code = representation.compile_to_shader(ind)
    with open("output/dual_pattern.glsl", "w") as f:
        f.write(shader_code or "")
    print("Saved: output/dual_pattern.glsl")

    # Mutate once
    child = representation.mutate(ind, key=1)
    img_child = representation.render_to_image(
        child,
        resolution=PREVIEW_RENDER_RESOLUTION,
        extra_inputs={"raw_time": 0.5},
    )
    if img_child is not None:
        Image.fromarray(img_child, "RGB").save("output/dual_mutant.png")
        print("Saved: output/dual_mutant.png (one mutation)")

    # Crossover: two parents -> one offspring
    parent2 = representation.create_random(key=2)
    offspring = representation.crossover(ind, parent2, key=3)
    img_off = representation.render_to_image(
        offspring,
        resolution=PREVIEW_RENDER_RESOLUTION,
        extra_inputs={"raw_time": 0.5},
    )
    if img_off is not None:
        Image.fromarray(img_off, "RGB").save("output/dual_offspring.png")
        print("Saved: output/dual_offspring.png (crossover)")
    print("Done. Check output/ for shader and images.")


if __name__ == "__main__":
    main()
