"""
Custom activation functions for CPPN patterns.
Adds additional activation functions to NEAT-Python for more interesting visual effects.
"""
import math


def cos_activation(z):
    """Cosine activation function."""
    z = max(-60.0, min(60.0, 5.0 * z))
    return math.cos(z)


def sawtooth_activation(z):
    """Sawtooth wave - creates sharp linear ramps."""
    # Normalize to -1 to 1 range with period of 2π
    return 2.0 * (z / (2.0 * math.pi) - math.floor(0.5 + z / (2.0 * math.pi)))


def triangle_activation(z):
    """Triangle wave - smoother than sawtooth."""
    return 2.0 * abs(sawtooth_activation(z)) - 1.0


def step_activation(z):
    """Step/Heaviside function - creates discrete jumps."""
    return 1.0 if z >= 0.0 else 0.0


def smooth_step_activation(z):
    """Smooth step function (smoothstep) - creates smooth transitions."""
    z = max(-1.0, min(1.0, z))
    return z * z * (3.0 - 2.0 * z)


def quantize_activation(z):
    """Quantize to discrete levels (0, 0.25, 0.5, 0.75, 1.0)."""
    # Clamp to 0-1 and quantize to 4 levels
    z = max(0.0, min(1.0, (z + 1.0) / 2.0))
    return round(z * 4.0) / 4.0


def wave_activation(z):
    """Wave packet - gaussian multiplied by sine."""
    z = max(-3.4, min(3.4, z))
    return math.exp(-2.0 * z ** 2) * math.sin(5.0 * z)


def pulse_activation(z):
    """Pulse function - creates periodic rectangular pulses."""
    period = 2.0 * math.pi
    return 1.0 if (z % period) < (period / 2.0) else -1.0


def register_custom_activations(config):
    """
    Register custom activation functions with a NEAT config.
    Call this after creating your config but before creating population.
    
    Args:
        config: NEAT Config object
        
    Example:
        config = neat.Config(...)
        register_custom_activations(config)
        population = neat.Population(config)
    """
    # Use the official API as per NEAT-Python documentation
    config.genome_config.add_activation('cos', cos_activation)
    config.genome_config.add_activation('sawtooth', sawtooth_activation)
    config.genome_config.add_activation('triangle', triangle_activation)
    config.genome_config.add_activation('step', step_activation)
    config.genome_config.add_activation('smooth_step', smooth_step_activation)
    config.genome_config.add_activation('quantize', quantize_activation)
    config.genome_config.add_activation('wave', wave_activation)
    config.genome_config.add_activation('pulse', pulse_activation)
    
    print("Registered custom activation functions:")
    print("  - cos: Cosine wave")
    print("  - sawtooth: Sharp linear ramps")
    print("  - triangle: Smooth triangular wave")
    print("  - step: Discrete step/Heaviside function")
    print("  - smooth_step: Smooth S-curve transitions")
    print("  - quantize: Discrete levels (posterize effect)")
    print("  - wave: Gaussian wave packet")
    print("  - pulse: Rectangular pulses")
