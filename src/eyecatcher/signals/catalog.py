"""
Signal catalog: composable building blocks for any representation.

Categorised primitives (SPATIAL, TEMPORAL, INTERACTION, STRUCTURAL),
derived inputs (DISTANCE), common output sets (RGB_OUTPUTS, TIME_OUTPUT),
and convenience presets matching the current dual-CPPN configuration.

Representations pick from this catalog to build their SensorySystem.
"""

from __future__ import annotations

import math

from .sensory_system import DerivedInput, Output, Signal

# ------------------------------------------------------------------
# Spatial
# ------------------------------------------------------------------

x = Signal("x", "X", 0.0, is_spatial=True, category="spatial")
y = Signal("y", "Y", 0.0, is_spatial=True, category="spatial")
distance = Signal("distance", "distance", 0.0, is_spatial=True, category="spatial")

SPATIAL = (x, y, distance)

# ------------------------------------------------------------------
# Temporal
# ------------------------------------------------------------------

raw_time = Signal("raw_time", "Raw Time", category="temporal")
time = Signal("time", "Time", is_derived=True, category="temporal")

TEMPORAL = (raw_time, time)

# ------------------------------------------------------------------
# Interaction
# ------------------------------------------------------------------

mouse_speed = Signal("mouse_speed", "Mouse Speed", category="interaction")
mouse_dist = Signal("mouse_dist", "Mouse Dist", category="interaction")
activity = Signal("activity", "Activity", category="interaction")
mouse_x = Signal("mouse_x", "Mouse X", category="interaction")
mouse_y = Signal("mouse_y", "Mouse Y", category="interaction")

INTERACTION = (mouse_speed, mouse_dist, activity, mouse_x, mouse_y)

# ------------------------------------------------------------------
# Structural
# ------------------------------------------------------------------

bias = Signal("bias", "Bias", 1.0, is_constant=True, category="structural")

STRUCTURAL = (bias,)

# ------------------------------------------------------------------
# Derived inputs
# ------------------------------------------------------------------

DISTANCE = DerivedInput(
    id="distance",
    deps=("x", "y"),
    compute=lambda x, y: math.sqrt(x * x + y * y),
    render_code="float v_distance = sqrt(v_x * v_x + v_y * v_y);",
)

# ------------------------------------------------------------------
# Common outputs
# ------------------------------------------------------------------

RGB_OUTPUTS = (
    Output("red", "Red"),
    Output("green", "Green"),
    Output("blue", "Blue"),
)

TIME_OUTPUT = (Output("output", "Modified Time"),)

# ------------------------------------------------------------------
# Representation-agnostic presets (use these for new representations)
# ------------------------------------------------------------------

STANDARD_2D_INPUTS = (*SPATIAL, *TEMPORAL, *INTERACTION, *STRUCTURAL)
TEMPORAL_INPUTS = (*TEMPORAL, mouse_speed, mouse_dist, activity, *STRUCTURAL)
MINIMAL_SPATIAL = (*SPATIAL, *STRUCTURAL)

# ------------------------------------------------------------------
# Convenience presets (matching current dual-CPPN behaviour)
# ------------------------------------------------------------------

# Visual network: x, y, distance, time, interaction signals, bias
DUAL_CPPN_VISUAL_INPUTS = (x, y, distance, time, *INTERACTION, bias)

# Time network: raw_time, mouse_speed, mouse_dist, activity, bias
DUAL_CPPN_TIME_INPUTS = (raw_time, mouse_speed, mouse_dist, activity, bias)

# CA interaction: mouse position for cell toggling
CA_INTERACTION_INPUTS = (mouse_x, mouse_y)
