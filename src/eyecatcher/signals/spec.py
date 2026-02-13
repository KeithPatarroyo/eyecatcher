"""
Signal specification primitives and the SignalSpec container.

Signal, Output, DerivedInput are the building blocks. SignalSpec is the
representation-agnostic declaration of what a representation accepts and
produces -- socket-centric: sockets hold the binding to each input target.

Helper functions (build_glsl_input_map, inputs_array, default_inputs,
apply_derived_inputs) operate on sequences of these primitives.
"""

from __future__ import annotations

import math  # noqa: F401 – used by DerivedInput.compute lambdas
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from .socket import Socket


def _is_toggleable(s: Signal) -> bool:
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

    def _uniform(self) -> str:
        return f"u_{self.id}" if _is_toggleable(self) else ""

    def _glsl_var(self) -> str:
        return f"v_{self.id}"

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
    glsl: str  # GLSL line(s) computing v_{id} from v_{dep} vars


# ------------------------------------------------------------------
# SignalSpec – the representation-agnostic interface declaration
# ------------------------------------------------------------------


def _dedup_inputs(sockets: Sequence[Socket]) -> tuple[Signal, ...]:
    """Union of all socket inputs, deduped by signal id (first occurrence wins)."""
    seen: set[str] = set()
    out: list[Signal] = []
    for sock in sockets:
        for s in sock.inputs:
            if s.id not in seen:
                seen.add(s.id)
                out.append(s)
    return tuple(out)


def _dedup_derived(sockets: Sequence[Socket]) -> tuple[DerivedInput, ...]:
    """Union of all socket derived inputs, deduped by id."""
    seen: set[str] = set()
    out: list[DerivedInput] = []
    for sock in sockets:
        for d in sock.derived:
            if d.id not in seen:
                seen.add(d.id)
                out.append(d)
    return tuple(out)


@dataclass(frozen=True)
class SignalSpec:
    """What a representation accepts and produces.

    Socket-centric: sockets bind signals to each input target (e.g. NEAT network,
    grid). inputs and derived_inputs are computed from sockets. outputs and
    substitutions are representation-level.
    """

    sockets: tuple[Socket, ...] = ()
    outputs: tuple[Output, ...] = ()
    substitutions: dict[str, str] = field(default_factory=dict)

    @property
    def inputs(self) -> tuple[Signal, ...]:
        """All signals the representation accepts (union of socket inputs, deduped)."""
        return _dedup_inputs(self.sockets)

    @property
    def derived_inputs(self) -> tuple[DerivedInput, ...]:
        """Signals computed from other inputs (union of all socket derived, deduped)."""
        return _dedup_derived(self.sockets)

    def socket(self, name: str) -> Socket:
        """Look up socket by name. Raises KeyError if not found."""
        for s in self.sockets:
            if s.name == name:
                return s
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


def build_glsl_input_map(signals: Sequence[Signal]) -> dict[int, str]:
    """Map NEAT negative node IDs to GLSL variable names.

    First signal gets the most-negative ID.
    """
    n = len(signals)
    return {-n + i: signals[i]._glsl_var() for i in range(n)}


def inputs_array(signals: Sequence[Signal], values: dict[str, float]) -> list[float]:
    """Build the ordered input array for a network from a dict of id -> value.

    Missing keys use Signal.default.
    """
    return [values.get(s.id, s.default) for s in signals]


def default_inputs(signals: Sequence[Signal]) -> dict[str, float]:
    """Return a dict of signal id -> default value for all signals."""
    return {s.id: s.default for s in signals}
