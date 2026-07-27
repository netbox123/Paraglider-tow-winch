"""
===========================================================
Open Paraglider Tow Winch

Module : motor_mount.py

Version : 0.0.4

Placeholder motor mount bracket - no dimensioned drawing for
this part exists, but the motor's own real mounting-bolt
positions do (from the user's manufacturer drawing of the
QS165 connector-end face): 2 real M10.5 holes, 178.68mm apart
centre-to-centre, one 18.27mm higher than the other. Exact
offsets from the shaft axis (HOLE_LEFT / HOLE_RIGHT below):
read directly off the drawing's own dimensions (86.54 + 92.14
horizontal split by the centreline = 178.68 total; 66.27 vs 48
vertical = 18.27 difference) - both numbers matched the user's
own stated totals exactly, so trusted over an earlier, wrong
STL-mesh-forensics guess that placed the holes much closer to
the hub (that mesh anomaly was some other feature, not these
bolts).

Shape per bracket is traced from picts/brackets.jpg: a round
head with the bolt hole, tapering to a flat foot. The photo
shows 2 visibly different brackets - left one smooth-tapered,
right one with a stepped notch partway down - reused here for
the left/right hole respectively. Each bracket is scaled so
its own hole comes out to PLATE_HOLE_DIAMETER (10mm, per the
user - a bit under the real 10.5mm bolt for a snug fit), not
by any other dimension in the photo (which has no scale of its
own).

The shaft end isn't photographed/dimensioned at all - mirrors
the connector end's real offsets as a placeholder assumption
("2 sets of 2 identical plates... motor sandwiched between the
plates", the user's own framing).

Axial (Y) placement: each bracket sits 3mm past the motor
mesh's real axial extent at that end (its absolute Y max at
the connector end, Y min - i.e. past the sprocket - at the
shaft end) - guarantees no collision by construction, without
needing a mesh boolean (the STL isn't watertight enough for
Part.makeOffsetShape, tried and failed earlier).

make_end_brackets(doc, name_prefix, cx, cz, outer_y, direction,
base_plate_top_z) builds the 2 brackets (left+right) for one
motor end. make_base_plate(...) builds the shared base plate.

===========================================================
"""

import FreeCAD as App
import Part


# Real hole offsets from the shaft axis (world X, Z), from the
# manufacturer drawing's own front-view dimensions - see header.
# Both dx shifted -46.08mm from the raw drawing reading: after
# building, the user compared the motor's real (mesh) left
# boundary against the bracket's left boundary on a render and
# found this exact gap - since motor_cx and the bracket offsets
# share the same reference point, this had to be closed by moving
# the brackets, not by re-positioning the motor (shifting motor_cx
# would have moved both together, leaving the gap unchanged - this
# was verified, not assumed, after an earlier wrong attempt).
HOLE_LEFT = (-132.62, -66.27)
HOLE_RIGHT = (46.06, -48.0)

MOTOR_HOLE_DIAMETER = 10.5   # the real bolt, from the drawing
PLATE_HOLE_DIAMETER = 10.0   # the bracket's own hole - per the user

HEAD_RADIUS = 12.0            # roughly 2x the hole diameter, per brackets.jpg proportions

# Straight sides, no taper (per the user - first fix pass on the
# bracket shape) - foot and step width both match the head radius,
# so the sides run parallel from the head straight down to the
# base plate.
FOOT_HALF_WIDTH = HEAD_RADIUS
STEP_HALF_WIDTH = HEAD_RADIUS
STEP_DROP_FRACTION = 0.4      # how far down (head-to-foot) the step sits
BRACKET_THICKNESS = 4.0
BASE_PLATE_THICKNESS = 10.0
BASE_PLATE_MARGIN = 25.0


def _make_bracket(doc, name, cx, cz, dx, dz, outer_y, direction,
                   base_plate_top_z, stepped):
    """One bracket traced from picts/brackets.jpg: round head (bolt
    hole) at (cx+dx, cz+dz), tapering to a flat foot welded onto
    the base plate below. stepped=True uses the right-hand photo's
    silhouette (a rectangular step partway down); False uses the
    left-hand photo's smooth taper. The head's inner face sits at
    outer_y, extending further out along +Y (direction=+1) or -Y
    (direction=-1) - away from the motor, never overlapping it."""

    hole_x = cx + dx
    hole_z = cz + dz
    y0 = outer_y if direction > 0 else outer_y - BRACKET_THICKNESS

    head = Part.makeCylinder(HEAD_RADIUS, BRACKET_THICKNESS,
                              App.Vector(hole_x, y0, hole_z), App.Vector(0, 1, 0))

    if stepped:
        step_z = hole_z - (hole_z - base_plate_top_z) * STEP_DROP_FRACTION
        pts = [
            App.Vector(hole_x - HEAD_RADIUS, y0, hole_z),
            App.Vector(hole_x + HEAD_RADIUS, y0, hole_z),
            App.Vector(hole_x + HEAD_RADIUS, y0, step_z),
            App.Vector(hole_x + STEP_HALF_WIDTH, y0, step_z),
            App.Vector(hole_x + FOOT_HALF_WIDTH, y0, base_plate_top_z),
            App.Vector(hole_x - FOOT_HALF_WIDTH, y0, base_plate_top_z),
            App.Vector(hole_x - HEAD_RADIUS, y0, hole_z),
        ]
    else:
        pts = [
            App.Vector(hole_x - HEAD_RADIUS, y0, hole_z),
            App.Vector(hole_x + HEAD_RADIUS, y0, hole_z),
            App.Vector(hole_x + FOOT_HALF_WIDTH, y0, base_plate_top_z),
            App.Vector(hole_x - FOOT_HALF_WIDTH, y0, base_plate_top_z),
            App.Vector(hole_x - HEAD_RADIUS, y0, hole_z),
        ]

    wire = Part.makePolygon(pts)
    face = Part.Face(wire)
    web = face.extrude(App.Vector(0, BRACKET_THICKNESS, 0))

    combined = head.fuse(web)

    hole = Part.makeCylinder(PLATE_HOLE_DIAMETER / 2, BRACKET_THICKNESS + 2,
                              App.Vector(hole_x, y0 - 1, hole_z), App.Vector(0, 1, 0))
    combined = combined.cut(hole)

    obj = doc.addObject("Part::Feature", name)
    obj.Shape = combined
    return obj


GUSSET_LEG_MAX = 40.0   # both legs equal - a 45/45/90 triangle, same convention
                         # already used for the winding clevis plate gussets
GUSSET_MARGIN = 5.0     # stay clear of the bracket's own head - see _make_gusset


def _make_gusset(doc, name, cx, cz, dx, dz, outer_y, direction, base_plate_top_z):
    """45/45/90 stiffener triangle bracing one bracket (at dx, dz)
    against the base plate - vertical leg flush against the
    bracket's own inner face (facing the other bracket), horizontal
    leg extends toward it. Leg length is capped by this bracket's
    own real height (hole to base plate) minus GUSSET_MARGIN, so it
    never sticks up past the bracket's own head - the 2 brackets
    sit at different real heights (18.27mm apart, per the drawing),
    so the 2 gussets are not necessarily the same size."""

    y0 = outer_y if direction > 0 else outer_y - BRACKET_THICKNESS
    hole_x = cx + dx
    hole_z = cz + dz
    sign = 1 if dx < 0 else -1   # left bracket's inner face is +HEAD_RADIUS, right's is -HEAD_RADIUS
    corner_x = hole_x + sign * HEAD_RADIUS

    leg = min(GUSSET_LEG_MAX, (hole_z - base_plate_top_z) - GUSSET_MARGIN)

    pts = [
        App.Vector(corner_x, y0, base_plate_top_z),
        App.Vector(corner_x + sign * leg, y0, base_plate_top_z),
        App.Vector(corner_x, y0, base_plate_top_z + leg),
        App.Vector(corner_x, y0, base_plate_top_z),
    ]
    wire = Part.makePolygon(pts)
    face = Part.Face(wire)
    solid = face.extrude(App.Vector(0, BRACKET_THICKNESS, 0))

    obj = doc.addObject("Part::Feature", name)
    obj.Shape = solid
    return obj


def make_end_brackets(doc, name_prefix, cx, cz, outer_y, direction, base_plate_top_z):
    """2 brackets (left, smooth-tapered + right, stepped) at one
    motor end, at the real HOLE_LEFT / HOLE_RIGHT offsets, each
    with its own 45/45/90 gusset bracing it against the base
    plate."""
    left = _make_bracket(doc, name_prefix + "_Left", cx, cz, HOLE_LEFT[0], HOLE_LEFT[1],
                          outer_y, direction, base_plate_top_z, stepped=False)
    right = _make_bracket(doc, name_prefix + "_Right", cx, cz, HOLE_RIGHT[0], HOLE_RIGHT[1],
                           outer_y, direction, base_plate_top_z, stepped=True)
    gusset_left = _make_gusset(doc, name_prefix + "_GussetLeft", cx, cz,
                                HOLE_LEFT[0], HOLE_LEFT[1], outer_y, direction, base_plate_top_z)
    gusset_right = _make_gusset(doc, name_prefix + "_GussetRight", cx, cz,
                                 HOLE_RIGHT[0], HOLE_RIGHT[1], outer_y, direction, base_plate_top_z)
    return left, right, gusset_left, gusset_right


CONNECTOR_PLATE_THICKNESS = 4.0


def make_side_connector_plate(doc, name, cx, cz, dx, dz, y_min, y_max, base_plate_top_z):
    """Flat plate bridging the same-side bracket (Left or Right)
    between the shaft-end and connector-end groups, spanning the
    axial gap between them - flush against the bracket's own outer
    (away-from-centre) face, per the user's own sketch. dx's sign
    picks which side is "outer" (negative = left bracket, further
    -X; positive = right bracket, further +X)."""

    hole_x = cx + dx
    hole_z = cz + dz
    if dx < 0:
        plate_x = hole_x - HEAD_RADIUS - CONNECTOR_PLATE_THICKNESS
    else:
        plate_x = hole_x + HEAD_RADIUS

    box = Part.makeBox(CONNECTOR_PLATE_THICKNESS, y_max - y_min, hole_z - base_plate_top_z,
                        App.Vector(plate_x, y_min, base_plate_top_z))

    obj = doc.addObject("Part::Feature", name)
    obj.Shape = box
    return obj


# Reverted to 0 - the +20mm then +40mm width increases (60mm
# total) were, per the user, "widened in the wrong axis". The
# X_max side is back to plain BASE_PLATE_MARGIN, matching the
# original pre-widening state. The X_min side's own flush-to-
# bracket shortening (see make_base_plate) is a separate, later,
# still-wanted change and is unaffected by this reversion - the
# maths below decouples them (see cut_amount).
BASE_PLATE_EXTRA_WIDTH = 0.0

# +40mm - the widening that was meant for X (see above) redone on
# the correct axis instead. Same mechanism: since the mounting
# holes are computed as an offset from y_min/y_max, widening this
# alone moves both the long edges AND the holes 20mm further out
# on each side together.
BASE_PLATE_EXTRA_LENGTH = 40.0

# 4 mounting-screw holes, one per corner - distances measured in
# from each edge, per the user.
MOUNTING_HOLE_DIAMETER = 10.0
MOUNTING_HOLE_FROM_SHORT_SIDE = 50.0   # short side = the X_min/X_max edges (142mm long)
MOUNTING_HOLE_FROM_LONG_SIDE = 17.0    # long side = the Y_min/Y_max edges (272.7mm long)


def make_base_plate(doc, name, cx, y_positions, base_plate_top_z, x_max_target=None,
                     slot_travel=0.0):
    """Flat 10mm foot plate the 4 brackets weld onto. The X_max
    side normally keeps its own real footprint + BASE_PLATE_MARGIN
    + BASE_PLATE_EXTRA_WIDTH/2 margin - or, if x_max_target is
    given (the real inside face of TW_JackshaftCrossBottom, per
    the user - grow the plate to reach it for real support there,
    not just the front cross tube), that value is used directly
    instead, and the right-side mounting holes (computed as an
    offset from x_max) automatically move out with it by the same
    amount. The X_min side - the one nearest TW_CrossFrontBottom -
    is shortened flush to the left bracket's own outer edge instead
    (per the user), and the 2 holes on that side are moved inward
    by the exact same amount that got cut off, so their own
    distance from that bracket stays what it was before the cut.
    Y_min/Y_max get BASE_PLATE_EXTRA_LENGTH split across them
    instead.

    slot_travel: if 0 (default), drills 4 plain round holes. If
    >0, drills 4 X-oriented slots instead, each centred on the
    same nominal hole position but elongated +-slot_travel in X -
    for chain-tensioning adjustment (the bolts stay fixed to the
    frame below; loosening them lets this plate, and the whole
    motor group bolted to it, slide along the slots)."""

    x_min_with_margin = cx + HOLE_LEFT[0] - HEAD_RADIUS - BASE_PLATE_MARGIN - BASE_PLATE_EXTRA_WIDTH / 2
    x_min = cx + HOLE_LEFT[0] - HEAD_RADIUS   # flush with the left bracket's own outer edge
    cut_amount = x_min - x_min_with_margin

    if x_max_target is not None:
        x_max = x_max_target
    else:
        x_max = cx + HOLE_RIGHT[0] + HEAD_RADIUS + BASE_PLATE_MARGIN + BASE_PLATE_EXTRA_WIDTH / 2
    y_min = min(y_positions) - BASE_PLATE_MARGIN - BASE_PLATE_EXTRA_LENGTH / 2
    y_max = max(y_positions) + BASE_PLATE_MARGIN + BASE_PLATE_EXTRA_LENGTH / 2

    box = Part.makeBox(x_max - x_min, y_max - y_min, BASE_PLATE_THICKNESS,
                        App.Vector(x_min, y_min, base_plate_top_z - BASE_PLATE_THICKNESS))

    hole_x_positions = (x_min_with_margin + MOUNTING_HOLE_FROM_SHORT_SIDE + cut_amount,
                         x_max - MOUNTING_HOLE_FROM_SHORT_SIDE)
    hole_y_positions = (y_min + MOUNTING_HOLE_FROM_LONG_SIDE,
                         y_max - MOUNTING_HOLE_FROM_LONG_SIDE)

    cutter_height = BASE_PLATE_THICKNESS + 2
    cutter_z = base_plate_top_z - BASE_PLATE_THICKNESS - 1

    for hx in hole_x_positions:
        for hy in hole_y_positions:
            if slot_travel > 0:
                end_a = Part.makeCylinder(MOUNTING_HOLE_DIAMETER / 2, cutter_height,
                                           App.Vector(hx - slot_travel, hy, cutter_z), App.Vector(0, 0, 1))
                end_b = Part.makeCylinder(MOUNTING_HOLE_DIAMETER / 2, cutter_height,
                                           App.Vector(hx + slot_travel, hy, cutter_z), App.Vector(0, 0, 1))
                middle = Part.makeBox(2 * slot_travel, MOUNTING_HOLE_DIAMETER, cutter_height,
                                       App.Vector(hx - slot_travel, hy - MOUNTING_HOLE_DIAMETER / 2, cutter_z))
                cutter = end_a.fuse(end_b).fuse(middle)
            else:
                cutter = Part.makeCylinder(MOUNTING_HOLE_DIAMETER / 2, cutter_height,
                                            App.Vector(hx, hy, cutter_z), App.Vector(0, 0, 1))
            box = box.cut(cutter)

    obj = doc.addObject("Part::Feature", name)
    obj.Shape = box
    return obj
