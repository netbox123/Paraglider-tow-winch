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

DRUM_WIDTH            = 250.0

DRUM_CORE_DIAMETER    = 390.0
DRUM_FLANGE_DIAMETER  = 590.0

DRUM_SHELL_THICKNESS  = 5.0
DRUM_FLANGE_THICKNESS = 5.0

DRUM_STIFFENER_COUNT      = 2
DRUM_STIFFENER_THICKNESS  = 5.0

SHAFT_DIAMETER = 50.0

# Fixed span between the 2 bearing post pairs' own bolting
# faces (doesn't move when plates are inserted between the
# bearings and the posts) - the actual physical shaft is
# shorter than this by 2x BEARING_MOUNT_PLATE_THICKNESS, see
# main.py.
SHAFT_LENGTH   = 700.0

# Distance from the front frame boundary (X=0) to the near
# face of the front drum flange. Change this to shift the
# whole drum group forward/back.
DRUM_TO_FRONT_BOUNDARY = 250.0

# Real UCF210 bearing bolt pattern, found by inspecting the
# actual STEP file (drawings/bearing50.stp) for circular edges
# with a repeated, consistent radius - 4 through holes, 17mm
# diameter, at (+-55.5, +-55.5) from the shaft axis (a clean
# 111mm square bolt pattern), not read off a drawing.
BEARING_BOLT_SPACING  = 111.0
BEARING_BOLT_DIAMETER = 17.0

# Gap between the 2 tubes of each bearing mounting post pair,
# centred on the axle - set so each post's own centreline lands
# exactly on one of the 2 real bolt-hole X-positions
# (BEARING_BOLT_SPACING apart), not just "wide enough to clear
# the seam" like the original guessed 40mm value.
BEARING_POST_GAP = BEARING_BOLT_SPACING - TUBE_SIZE

# Mounting plate between each bearing's flange and its post
# pair, and how far the bolt/axle placeholders stick out past
# the post's own outer face.
BEARING_MOUNT_PLATE_THICKNESS = 4.0
BEARING_BOLT_OVERHANG = 15.0

# Placeholder pins through the real screw holes of every 25mm
# flange_bearing.py mounting (both reversing-screw mounts and both
# jackshaft mounts) - a fabrication aid, not a real fastener: marks
# exactly where the plate + tube behind it need drilling for the
# real mounting screws. 4mm diameter (smaller than the bearing's
# own real ~6.24mm bolt hole, so it passes through with clearance),
# sticking out this far past the bearing's own outer hole opening
# on one end and past the tube's own near wall (inner surface) on
# the other.
BEARING_SCREW_PIN_DIAMETER = 4.0
BEARING_SCREW_PIN_OVERHANG = 10.0


# =========================================================
# LEVEL WIND
# =========================================================

ROPE_DIAMETER = 3.0

LEVELWIND_TRAVEL = DRUM_WIDTH

# Placeholder until the self-reversing screw is selected.

LEVELWIND_SCREW_LEAD = 20.0


# =========================================================
# ROPE INTAKE
# =========================================================

# Self-aligning swivel: the intake pipe, 2 x 200mm rollers
# and 2 x 100mm wheels all rotate together around a bearing
# bolted to the frame, letting the rope's own pull steer the
# assembly toward the direction it's coming from.

INTAKE_PIPE_DIAMETER = 40.0
INTAKE_PIPE_WALL     = 3.0

# Pipe length is not a free choice - it's derived in main.py
# from the frame tube it passes through and where the
# bearing housing ends.


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

# Shifted -35mm from 229.62 - after the plate's left side got
# shortened flush to the bracket (a later change), its own edge
# had drifted to 85mm from the frame boundary (X=0), not the 50mm
# it was originally set to. This moves the whole group back out
# (away from the drum) so the edge sits at exactly 50mm again.
MOTOR_SHAFT_X     = 194.62

# Raised from the original 50mm (bare tube-top height) once the
# motor mount bracket's own 10mm base plate was added - the motor's
# lowest point now needs to clear the plate (tube top 50 + plate
# 10 = 60), not just the bare tube. 65 gives 5mm margin above it.
MOTOR_REST_HEIGHT = 65.0

# Shifted from 82.5 to 207.0 - aligns TW_MotorSprocket's Y-span
# with TW_DrumAxleSprocket76T's (Y 207-220) for a straight chain
# run, per the user. NOTE: this moves the motor mesh's own Y-span
# (207-449) back into winding_group's Y range (200-600) - the
# exact overlap the earlier -40mm move was meant to avoid - not
# yet re-verified for real collisions at time of writing this
# comment.
MOTOR_SHAFT_Y     = 207.0

# Motor mount bracket (placeholder, see motor_mount.py) - each
# bracket's outer (motor-facing) Y face, as an offset from
# MOTOR_SHAFT_Y so they stay put if the motor's Y position ever
# moves. User asked to pull both groups in from the axial
# extremes to a 92mm gap between them, centred on the motor's own
# axial midpoint (local Y 12) - NOT YET VERIFIED clear of the real
# mesh at this tighter spacing, unlike the previous "3mm past the
# absolute tip" values which were.
# +40mm from 75.0/167.0 - the user asked to move the base plate
# + 4 brackets (not the motor) parallel to the drum axle (Y), the
# opposite direction from the last motor Y move, 40mm - the mesh
# itself has been too irregular/hard to precisely align brackets
# to (measuring tool didn't help either), so this is a simple,
# reversible group shift rather than another mesh-chase.
# -6mm fine-tune from 115.0/207.0 - "almost perfect, move back 6mm".
# Creates a small, shallow real overlap with the motor mesh at the
# connector end (a few isolated mesh points inside
# TW_MotorMountConnectorEnd_Left/Right, not a large volume) -
# flagged and knowingly accepted by the user rather than backed
# off, since this whole assembly is still a placeholder.
MOTOR_MOUNT_SHAFT_END_Y_OFFSET = 109.0
MOTOR_MOUNT_CONNECTOR_END_Y_OFFSET = 201.0


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
# WINDING MECHANISM
# =========================================================

# Vertical drop of the winding rail's own Z position below
# TW_CrossFrontTop's top face (H) - the whole winding assembly
# (rail, HWIN rail/block/plate, clevis, rod end, load cell,
# pulley) is built up from this single value, so raising/
# lowering the entire mechanism is just this one number.
# Lowered an extra 50mm (100 -> 150) so the rope path from the
# intake to the top of the winding pulley's wheel runs horizontal.
WINDING_RAIL_Z_DROP = 150.0

# Clevis/ear plates welded onto the HWIN mounting plate, that
# the rod end ball joint pivots inside of (lets the load cell
# tilt as the rope's angle off the drum changes with layer
# build-up, instead of bolting it on rigidly).

WINDING_CLEVIS_PLATE_SIZE      = 75.0    # square + domed top, outer envelope
WINDING_CLEVIS_PLATE_THICKNESS = 8.0
WINDING_CLEVIS_GAP             = 22.0    # matches the rod end's own hex-across-flats width
WINDING_CLEVIS_AXLE_OVERHANG   = 15.0    # each side, past the plates' own outer faces

# Triangular gussets bracing each clevis plate against the HWIN
# mounting plate - 45/45/90 right triangle, both legs equal.
WINDING_CLEVIS_GUSSET_LEG       = 40.0
WINDING_CLEVIS_GUSSET_THICKNESS = 4.0
WINDING_CLEVIS_GUSSET_Z_OFFSET  = 20.0    # from the axle's own centreline, not the plate's edge


# =========================================================
# DISPLAY
# =========================================================

SHOW_AXES = True
SHOW_HELPER_GEOMETRY = True