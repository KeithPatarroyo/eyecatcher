"""
Receptor: representation-agnostic binding of signals to an input target.

A Receptor holds inputs, optional outputs, and optional derived inputs. It provides
to_array(), default_values(), and input_ids() so representations can resolve
signal values into the format their internal computation expects.

This is the base type; NeatReceptor (in representation/receptors.py) adds NEAT
network query, GLSL input mapping, and network stats for CPPN representations.
"""

from dataclasses import dataclass

from .sensory_system import (
    DerivedInput,
    Output,
    Signal,
    apply_derived_inputs,
    default_inputs,
    inputs_array,
)


@dataclass(frozen=True)
class Receptor:
    """Binding of named signals to one representation input target.

    Representation-agnostic: the same Receptor type can feed a NEAT network,
    a grid cell, or another kind of target. Subclasses add target-specific
    behaviour (e.g. NeatReceptor loads config and runs query).

    role: "primary" (produces color output in RuleAssembler), "modifier" (feeds
    into primary). Used by RuleAssembler.from_sensory_system() to pick which
    receptor is visual vs time when assembling GLSL.
    """

    name: str
    inputs: tuple[Signal, ...]
    outputs: tuple[Output, ...] = ()
    derived: tuple[DerivedInput, ...] = ()
    role: str = ""  # "primary" | "modifier" for field/CPPN assemblies

    def to_array(self, values: dict[str, float]) -> list[float]:
        """Build ordered input array for this receptor from id -> value dict.

        Applies derived inputs when dependencies are present. Missing keys
        use each Signal.default.
        """
        full = {s.id: values.get(s.id, s.default) for s in self.inputs}
        apply_derived_inputs(full, self.derived)
        return inputs_array(self.inputs, full)

    def default_values(self) -> dict[str, float]:
        """Return signal id -> default value for all inputs."""
        return default_inputs(self.inputs)

    def input_ids(self) -> list[str]:
        """Ordered list of input signal ids."""
        return [s.id for s in self.inputs]
