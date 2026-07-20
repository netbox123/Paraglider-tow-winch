"""
===========================================================
Open Paraglider Tow Winch
Configuration File

All dimensions are in millimetres unless noted otherwise.

Changing values in this file should regenerate the complete
FreeCAD model.

Author: netbox123 + ChatGPT
===========================================================
"""

# =========================================================
# FRAME
# =========================================================

FRAME_LENGTH = 1500.0      # Overall length
FRAME_WIDTH  = 800.0       # Overall width
FRAME_HEIGHT = 800.0       # Overall height

# Square tube

TUBE_SIZE = 50.0           # 50x50 tube
TUBE_WALL = 4.0            # 4 mm wall thickness

# Calculated

FRAME_CONNECTOR = FRAME_WIDTH - TUBE_SIZE


# =========================================================
# BATTERY BOXES (EEL)
# =========================================================

BATTERY_LENGTH = 730.0
BATTERY_WIDTH  = 415.0
BATTERY_HEIGHT = 263.0

BATTERY_COUNT = 2


# =========================================================
# DRUM
# =========================================================

DRUM_WIDTH            = 400.0

DRUM_CORE_DIAMETER    = 390.0
DRUM_FLANGE_DIAMETER  = 590.0

DRUM_SHELL_THICKNESS  = 5.0
DRUM_FLANGE_THICKNESS = 5.0

DRUM_STIFFENER_COUNT      = 2
DRUM_STIFFENER_THICKNESS  = 5.0

SHAFT_DIAMETER = 50.0
SHAFT_LENGTH   = 700.0

# Distance from the front frame boundary (X=0) to the near
# face of the front drum flange. Change this to shift the
# whole drum group forward/back.
DRUM_TO_FRONT_BOUNDARY = 250.0

# Gap between the 2 tubes of each bearing mounting post
# pair, centred on the axle. Leaves room to drill the
# bearing bolt holes clear of the seam between the tubes.
BEARING_POST_GAP = 40.0


# =========================================================
# LEVEL WIND
# =========================================================

ROPE_DIAMETER = 3.0

LEVELWIND_TRAVEL = DRUM_WIDTH

# Placeholder until the self-reversing screw is selected.

LEVELWIND_SCREW_LEAD = 20.0


# =========================================================
# MOTOR
# =========================================================

MOTOR_NAME = "QS165"

GEARBOX_RATIO = 2.37

# Placement (front zone, clear of the drum). Shaft axis X
# position, height the motor's lowest point rests above
# Z=0, and the shaft/sprocket Y position. MOTOR_SHAFT_Y is
# fixed independently of DRUM_WIDTH on purpose - the motor
# shouldn't shift if the drum gets narrower. Currently set
# to the centre of the front bare shaft section with the
# drum sizes in this file; when the axle_sprocket is added
# it should be positioned to match this value, not the
# other way round.

MOTOR_SHAFT_X     = 100.0
MOTOR_REST_HEIGHT = 50.0
MOTOR_SHAFT_Y     = 122.5


# =========================================================
# ROPE
# =========================================================

ROPE_LENGTH = 1500.0

TOW_FORCE_MIN = 40.0      # kg
TOW_FORCE_MAX = 100.0     # kg


# =========================================================
# BEARINGS
# =========================================================

# Placeholder values

BEARING_SPACING = 500.0


# =========================================================
# DISPLAY
# =========================================================

SHOW_AXES = True
SHOW_HELPER_GEOMETRY = True