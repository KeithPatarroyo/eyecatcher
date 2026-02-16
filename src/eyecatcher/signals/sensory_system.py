"""
SensorySystem: the organism's complete apparatus for sensing and transducing signals.

Signal, Output, DerivedInput are the building blocks. SensorySystem is the
representation-agnostic declaration of what signals flow into the organism --
receptor-centric: receptors hold the binding to each input target.

Helper functions (inputs_array, default_inputs, apply_derived_inputs)
operate on sequences of these primitives.
"""

import math  # noqa: F401 – used by DerivedInput.compute lambdas
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .receptor import Receptor


def _is_toggleable(s: "Signal") -> bool:
    """True if this signal has a value uniform (not spatial, not constant)."""
    return not s.is_spatial and not s.is_constant


# ------------------------------------------------------------------
# Primitives
# ------------------------------------------------------------------


@dataclass(frozen=True)
class Signal:
    """One named value that flows *into* a representation."""

    id: str
    label: str
    default: float = 0.0
    is_spatial: bool = False
    is_constant: bool = False  # always same value, no uniform (e.g. bias)
    is_derived: bool = False  # value from internal computation, not external
    category: str = ""  # spatial | temporal | interaction | structural

    def _is_derived(self) -> bool:
        return self.is_derived


@dataclass(frozen=True)
class Output:
    """One named value that flows *out of* a representation."""

    id: str
    label: str


@dataclass(frozen=True)
class DerivedInput:
    """A signal computed from other inputs (e.g. distance from x, y)."""

    id: str
    deps: tuple[str, ...]
    compute: Callable[..., float]
    render_code: (
        str  # Code snippet computing this input from dependencies (e.g. for rendering)
    )


# ------------------------------------------------------------------
# SensorySystem – the organism's sensory apparatus
# ------------------------------------------------------------------


def _dedup_inputs(receptors: Sequence["Receptor"]) -> tuple[Signal, ...]:
    """Union of all receptor inputs, deduped by signal id (first occurrence wins)."""
    seen: set[str] = set()
    out: list[Signal] = []
    for r in receptors:
        for s in r.inputs:
            if s.id not in seen:
                seen.add(s.id)
                out.append(s)
    return tuple(out)


def _dedup_derived(receptors: Sequence["Receptor"]) -> tuple[DerivedInput, ...]:
    """Union of all receptor derived inputs, deduped by id."""
    seen: set[str] = set()
    out: list[DerivedInput] = []
    for r in receptors:
        for d in r.derived:
            if d.id not in seen:
                seen.add(d.id)
                out.append(d)
    return tuple(out)


@dataclass(frozen=True)
class SensorySystem:
    """The organism's sensory apparatus: receptors and signal bindings.

    Receptor-centric: receptors bind signals to each input target (e.g. NEAT network,
    grid). inputs and derived_inputs are computed from receptors. outputs and
    substitutions are representation-level.
    """

    receptors: tuple["Receptor", ...] = ()
    outputs: tuple[Output, ...] = ()
    substitutions: dict[str, str] = field(default_factory=dict)

    @property
    def inputs(self) -> tuple[Signal, ...]:
        """All signals the representation accepts (union of receptor inputs)."""
        return _dedup_inputs(self.receptors)

    @property
    def derived_inputs(self) -> tuple[DerivedInput, ...]:
        """Signals computed from other inputs (union of receptor derived, deduped)."""
        return _dedup_derived(self.receptors)

    def receptor(self, name: str) -> "Receptor":
        """Look up receptor by name. Raises KeyError if not found."""
        for r in self.receptors:
            if r.name == name:
                return r
        raise KeyError(name)

    def input_ids(self) -> list[str]:
        """Return ordered list of input signal ids."""
        return [s.id for s in self.inputs]

    def has_signal(self, signal_id: str) -> bool:
        """Check whether the spec declares an input with this id."""
        return any(s.id == signal_id for s in self.inputs)

    def has_category(self, category: str) -> bool:
        """True if any input signal has this category."""
        return any(s.category == category for s in self.inputs)


# ------------------------------------------------------------------
# Helper functions (operate on signal sequences)
# ------------------------------------------------------------------


def apply_derived_inputs(
    values: dict[str, float], derived: Sequence[DerivedInput]
) -> None:
    """Fill in derived signal values when dependencies are present.

    Mutates *values* in place.
    """
    for d in derived:
        if d.id in values:
            continue
        if all(dep in values for dep in d.deps):
            values[d.id] = float(d.compute(*[values[dep] for dep in d.deps]))


def input_labels(signals: Sequence[Signal]) -> list[str]:
    """Return label strings for a list of signals."""
    return [s.label for s in signals]


def output_labels(outputs: Sequence[Output]) -> list[str]:
    """Return label strings for a list of outputs."""
    return [o.label for o in outputs]


def input_names(signals: Sequence[Signal]) -> list[str]:
    """Return id strings for a list of signals."""
    return [s.id for s in signals]


def inputs_array(signals: Sequence[Signal], values: dict[str, float]) -> list[float]:
    """Build the ordered input array for a network from a dict of id -> value.

    Missing keys use Signal.default.
    """
    return [values.get(s.id, s.default) for s in signals]


def default_inputs(signals: Sequence[Signal]) -> dict[str, float]:
    """Return a dict of signal id -> default value for all signals."""
    return {s.id: s.default for s in signals}
