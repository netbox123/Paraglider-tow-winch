"""
===========================================================
Giga Display Shield - Panel Mount Frame
Configuration File

All dimensions are in millimetres unless noted otherwise.

Author: netbox123
===========================================================
"""

# =========================================================
# REFERENCE GEOMETRY (measured from
# freecad/drawings/Giga display shield case top.stl via a
# boundary-loop analysis, not eyeballed - see the LCD cutout
# and the 4 mounting hole centres/diameter below). This frame
# reuses those 2 features so the Arduino Giga Display Shield
# mounts onto it exactly like it does onto the original case
# top: same window, same screw pattern.
# =========================================================

# LCD cutout window, centred on SHIELD_CUTOUT_OFFSET relative
# to the mounting-hole bolt pattern's own centroid (which is
# the origin used throughout this file).
SHIELD_CUTOUT_LENGTH = 88.2   # X
SHIELD_CUTOUT_WIDTH  = 52.75  # Y
SHIELD_CUTOUT_OFFSET_X = 0.15
SHIELD_CUTOUT_OFFSET_Y = -1.77

# 4 mounting holes (M3 clearance in the real case; measured
# through-hole was ~3.1mm, bumped to 3.2mm here for a real M3
# screw to pass freely), symmetric bolt pattern at
# (+-SHIELD_HOLE_X, +-SHIELD_HOLE_Y). In the reference case
# these are through-holes with a counterbore on the front
# (outward) face - the screw passes through the lid/frame and
# down into the Giga Display Shield's OWN mounting standoffs
# underneath, so this frame only needs to reuse the hole
# positions, not add its own standoffs/bosses.
SHIELD_HOLE_X = 48.0
SHIELD_HOLE_Y = 35.0
SHIELD_HOLE_DIAMETER = 3.2

# Counterbore for the screw head, front face only (measured
# ~9.7mm dia x ~2.5mm deep in the reference case).
SHIELD_HOLE_COUNTERBORE_DIAMETER = 9.7
SHIELD_HOLE_COUNTERBORE_DEPTH = 2.5

# Distance from the front (LCD-visible) face down to the plane
# where the Giga Display Shield's own PCB sits - measured from
# the reference STL itself: the outer top face sits at
# z=6.39-6.45, and the 4 corner "pad" segments (flat, z=0,
# same XY footprint as the 4 screw holes above) are where the
# shield's PCB corners rest against the case top's own
# standoffs. So 6.45mm is the real, as-designed LCD-glass-to-
# PCB depth for this shield - reused here (not re-guessed) to
# place this frame's own standoff bosses at the correct depth.
LCD_TO_PCB_HEIGHT = 6.45

# RGB LED (DL1, SMLP34RGB2W3) light-pipe hole - straight
# through-hole, same position/diameter as the reference case's
# own hole for it. Confirmed against the official GIGA Display
# Shield datasheet (docs.arduino.cc/resources/datasheets/
# ASX00039-datasheet.pdf, section 6.1 Board Topology): DL1 (LED)
# sits just left of U1 (microphone) in the board's own top-left
# corner, above the display - matching the smaller/further-left
# of the 2 small holes found near the reference case's own top
# edge (the other, larger one at ~(-26.55, 35.60) dia 2.9mm, is
# U1's own microphone port - not made yet, only asked for the
# LED so far).
LED_HOLE_X = -30.35
LED_HOLE_Y = 35.60
LED_HOLE_DIAMETER = 1.9

# =========================================================
# FRAME / BEZEL
#
# Design: a front flange (visible, sits on the OUTSIDE of the
# industrial box's front panel, hiding the jigsaw-cut edges)
# plus a rectangular collar stepping back from it that plugs
# through the jigsaw-cut hole. The collar's own outer envelope
# is what the jigsaw hole needs to be cut to (not the LCD
# window, and NOT the shield's own full PCB envelope - the PCB
# stays inside the box, only this collar needs to pass through
# the panel). 4 printed bosses inside the collar carry the same
# M3 mounting pattern as the reference case, so the display
# shield screws to THIS frame from behind.
#
# PANEL_THICKNESS is a placeholder - depends on which
# industrial box gets used (KKSB case vs a jigsaw-cut sheet
# steel/plastic electrical box, still being decided - see
# docs). Update once that's picked.
# =========================================================

PANEL_THICKNESS = 3.0          # thickness of the box's own front panel

COLLAR_HEIGHT = PANEL_THICKNESS + 0.5  # slightly proud so the flange pulls up snug, not the collar bottoming out first

# Collar's own outer edge, measured from the inner (shield)
# screw holes' own centres - not from the shield's full PCB
# envelope, so the collar/jigsaw hole stays as small as
# possible while still leaving real material around each hole.
COLLAR_EDGE_MARGIN = 8.0

# How far the visible flange extends past the collar on each
# side - the frame is glued into the panel (no flange screws),
# so this is purely the glue-contact lip width.
FLANGE_OVERLAP = 8.0
FLANGE_THICKNESS = 4.0
FLANGE_CORNER_RADIUS = 6.0     # frame's own corner rounding - NOT copied from the reference case, chosen fresh
COLLAR_CORNER_RADIUS = 4.0     # small relief radius so the jigsaw/rotary-tool cut can actually turn each corner

# Standoff bosses printed inside the collar, at the same
# SHIELD_HOLE_X/Y bolt pattern, so the shield's own screws
# (through SHIELD_HOLE_DIAMETER above) have something to bite
# into - there's no separate "case bottom" in this design, the
# industrial box itself is the enclosure, so this frame has to
# supply its own standoff. Each boss's tip sits
# LCD_TO_PCB_HEIGHT below the front face (see above); its own
# blind pilot hole is sized for a self-tapping M3 screw.
BOSS_DIAMETER = 7.0
BOSS_HOLE_DIAMETER = 2.8
BOSS_HOLE_DEPTH = 5.0

SHOW_AXES = True
