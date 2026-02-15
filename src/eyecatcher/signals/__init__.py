"""
Signal definitions and utilities for representation inputs/outputs.

Public API: sensory system primitives (Signal, Output, DerivedInput, SensorySystem),
catalog presets, and registry helpers that take sensory_system/signal lists explicitly.
"""

from . import catalog
from .receptor import Receptor
from .registry import (
    apply_derived_inputs,
    default_inputs,
    export_for_frontend,
    get_default_signal_values,
    get_viewer_signal_ids,
    input_labels,
    input_names,
    output_labels,
    parse_time_inputs,
)
from .sensory_system import DerivedInput, Output, SensorySystem, Signal

__all__ = [
    "Signal",
    "Output",
    "DerivedInput",
    "SensorySystem",
    "Receptor",
    "catalog",
    "apply_derived_inputs",
    "export_for_frontend",
    "input_labels",
    "output_labels",
    "input_names",
    "default_inputs",
    "get_default_signal_values",
    "get_viewer_signal_ids",
    "parse_time_inputs",
]
