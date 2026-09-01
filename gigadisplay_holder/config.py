"""
===========================================================
Giga Display Shield - Panel Mount Frame
Configuration File

All dimensions are in millimetres unless noted otherwise.

Author: netbox123
===========================================================
"""

# =========================================================
# REFERENCE GEOMETRY
#
# Updated 2026-09-01 from the REAL Arduino Giga Display Shield
# (the first test print, whose numbers came from a boundary-loop
# analysis of freecad/drawings/Giga display shield case top.stl,
# printed fine but the window size/position were off). Measured
# board: 106 (X) x 80 (Y). Mounting holes 5mm in from every
# board edge -> the board centre, the hole-pattern centroid and
# this file's origin all coincide.
#
# Viewing convention: looking at the front (LCD-visible) face,
# +X is to the right, +Y is up.
# =========================================================

# LCD cutout window - this is the VIEWPORT we want left visible
# (the shield's glass module measures 98 x 58; the whole of it
# shows through, the frame sits right at the glass edge). Centred
# on SHIELD_CUTOUT_OFFSET relative to the origin.
#
# Screen sits 2.4mm from the right board edge / 5.6mm from the
# left  -> +1.6mm off centre in X.
# Screen sits 11mm from the top board edge / 11mm from the
# bottom -> centred in Y.
SHIELD_CUTOUT_LENGTH = 98.0   # X
SHIELD_CUTOUT_WIDTH  = 58.0   # Y
SHIELD_CUTOUT_OFFSET_X = 1.6
SHIELD_CUTOUT_OFFSET_Y = 0.0

# 4 mounting holes, symmetric bolt pattern at
# (+-SHIELD_HOLE_X, +-SHIELD_HOLE_Y). Measured hole pattern on
# the real board is 96 x 70 -> +-48 / +-35, which confirms the
# original STL-derived values exactly (no change). M3 clearance:
# measured through-hole ~3.1mm, kept at 3.2mm so a real M3 screw
# passes freely.
SHIELD_HOLE_X = 48.0
SHIELD_HOLE_Y = 35.0
SHIELD_HOLE_DIAMETER = 3.2

# Counterbore for the screw head, front face only. Sized
# 2026-09-01 to the real M3 bolt from the shed: head 5.5mm dia
# x 2.5mm high. Bore = 5.5 + 0.7 clearance; depth 2.8 so the
# head seats just below flush. (Was 9.7 x 2.5, from the old
# reference case - far too wide.)
SHIELD_HOLE_COUNTERBORE_DIAMETER = 6.2
SHIELD_HOLE_COUNTERBORE_DEPTH = 2.8

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
# through-hole. Measured 2026-09-01 on the real board: 3mm down
# from the top board edge, 26.5mm in from the left board edge
# (assumed to the hole centre). Board top edge Y=+40, left edge
# X=-53  ->  centre at (-53 + 26.5, 40 - 3) = (-26.5, 37.0).
# Sits in the solid strip above the LCD cutout, as expected for
# DL1 in the board's top-left corner above the display.
LED_HOLE_X = -26.5
LED_HOLE_Y = 37.0
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
