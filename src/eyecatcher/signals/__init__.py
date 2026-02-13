"""
Signal definitions and utilities for representation inputs/outputs.

Public API: spec primitives (Signal, Output, DerivedInput, SignalSpec),
catalog presets, and registry helpers that take spec/signal lists explicitly.
"""

from . import catalog
from .registry import (
    apply_derived_inputs,
    build_glsl_input_map,
    default_inputs,
    export_for_frontend,
    get_default_signal_values,
    get_viewer_signal_ids,
    input_labels,
    input_names,
    output_labels,
    parse_time_inputs,
)
from .socket import Socket
from .spec import DerivedInput, Output, Signal, SignalSpec

__all__ = [
    "Signal",
    "Output",
    "DerivedInput",
    "SignalSpec",
    "Socket",
    "catalog",
    "apply_derived_inputs",
    "export_for_frontend",
    "input_labels",
    "output_labels",
    "input_names",
    "build_glsl_input_map",
    "default_inputs",
    "get_default_signal_values",
    "get_viewer_signal_ids",
    "parse_time_inputs",
]
