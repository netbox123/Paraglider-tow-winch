"""
===========================================================
Open Paraglider Tow Winch

Module : pulley.py

Version : 0.0.6

Winding-mechanism pulley: reuses the same 100mm guide wheel as
the rope intake (guide_wheel.py, unmodified), sandwiched
between 2 identical rectangular side plates, wheel centred on
each plate. 130x110mm (X x Z), per the user's own sizing.

3 connection strips (4mm thick) join the 2 plates directly
along the mount side, top and bottom edges - the 4th (far, +x)
edge is left open, since that's the side facing the rope intake
mechanism (the wheel's own rim is exposed there for the rope to
wrap around).

Rope shields (2mm thick, 1mm clearance from the wheel) close the
remaining axial gap around the wheel's own rim, so the rope can't
slip sideways into the pocket between the wheel and the strips -
4 total (2 per plate side: a mount-half piece and an open-half
piece, the shape naturally splits there since the clearance
circle is exactly tangent to the strips' own inner edge).

Local coordinate convention (this whole assembly gets placed as
one piece once the final mounting position is worked out, same
pattern as wheel_bracket.py):

    x = 0 to PLATE_WIDTH, the wheel's own axle sits at x=WHEEL_CX
        (shifted toward the open side, WHEEL_EDGE_CLEARANCE short
        of it, not centred); x=0 is the mount side (attaches to
        the load cell - exact connection still TBD), x=PLATE_WIDTH
        is the open/far side
    y = wheel axle / plate-sandwich axis (matches guide_wheel.py's
        own axis convention directly)
    z = -PLATE_HEIGHT/2 to +PLATE_HEIGHT/2, centred on the wheel's axle

A standard M18 hex nut (27mm across flats, 15mm thick) is welded
onto the mount strip's own outer face (x=0), centred on the
wheel's own axial midpoint - the load cell's own ~18mm threaded
stud (per the user) screws into this nut, welded to the pulley
rather than to the load cell. The nut occupies x=-NUT_HEIGHT to
0, i.e. it sits in front of the mount side, so the whole pulley
assembly needs to be placed NUT_HEIGHT further from the load
cell's tip than a flush touch would be, to leave room for it.
===========================================================
"""

import Part
import FreeCAD as App
import math
import guide_wheel

PLATE_WIDTH  = 130.0
PLATE_HEIGHT = 110.0
PLATE_THICKNESS = 4.0

STRIP_THICKNESS = 4.0

# Wheel shifted toward the open (far) edge, stopping this far
# short of it - not centred on the plate.
WHEEL_EDGE_CLEARANCE = 5.0
WHEEL_CX = PLATE_WIDTH - WHEEL_EDGE_CLEARANCE - guide_wheel.OUTER_DIAMETER / 2

# Rope shields (same idea as wheel_bracket.py's own wheel
# shields): close the gap between the wheel's rim and the strips'
# own inner edge down to just SHIELD_CLEARANCE, so the rope can't
# slip sideways off the wheel into that pocket. The clearance
# circle's own radius happens to land exactly on the strips' inner
# edge at top/bottom (tangent, not overlapping), so this naturally
# splits into 2 pieces per side - one wrapping the mount half of
# the wheel, one wrapping the open half - same as the 4-way split
# found on the intake wheels.
SHIELD_THICKNESS = 2.0
SHIELD_CLEARANCE = 1.0

# Nut welded onto the mount side (the load cell's own ~18mm
# threaded stud screws into it) - standard M18 hex nut (ISO
# 4032/DIN 934: 27mm across flats, 15mm thick). Sits centred on
# the wheel's own axial midpoint, extending into -x (toward the
# load cell) from the mount strip's own outer face.
NUT_ACROSS_FLATS = 27.0
NUT_HEIGHT = 15.0
NUT_BORE_DIAMETER = 18.0
NUT_CY = PLATE_THICKNESS + guide_wheel.WIDTH / 2
NUT_CZ = 0.0

# Wheel axle - matches the wheel's own bore exactly (same
# fastener-abstraction level used elsewhere in this project, e.g.
# the intake rollers), through both plates, sticking out
# AXLE_OVERHANG past each plate's own outer face.
AXLE_DIAMETER = guide_wheel.BORE_DIAMETER
AXLE_OVERHANG = 10.0


def _make_plate(doc, name, y):
    """y is this plate's own near face position along the wheel axle."""

    body = Part.makeBox(PLATE_WIDTH, PLATE_THICKNESS, PLATE_HEIGHT,
                         App.Vector(0, y, -PLATE_HEIGHT / 2))

    obj = doc.addObject("Part::Feature", name)
    obj.Shape = body
    return obj


def _make_strip(doc, name, x, dx, z, dz):
    """Fills the y-gap between the 2 plates (over the wheel's own
    width) across the box (x, x+dx) x (z, z+dz)."""

    body = Part.makeBox(dx, guide_wheel.WIDTH, dz,
                         App.Vector(x, PLATE_THICKNESS, z))
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = body
    return obj


def _make_wheel_shields(doc, name_prefix, y):
    """The plate's own footprint (inside the strips' inner edges),
    minus a wheel_r + SHIELD_CLEARANCE circle around the wheel -
    comes out as 2 separate pieces (see module docstring)."""

    r = guide_wheel.OUTER_DIAMETER / 2 + SHIELD_CLEARANCE
    x_min = STRIP_THICKNESS
    x_max = PLATE_WIDTH
    z_min = -(PLATE_HEIGHT / 2 - STRIP_THICKNESS)
    z_max = PLATE_HEIGHT / 2 - STRIP_THICKNESS

    rect = Part.Face(Part.makePolygon([
        App.Vector(x_min, y, z_min),
        App.Vector(x_max, y, z_min),
        App.Vector(x_max, y, z_max),
        App.Vector(x_min, y, z_max),
        App.Vector(x_min, y, z_min),
    ]))
    circle = Part.Face(Part.Wire(Part.makeCircle(r, App.Vector(WHEEL_CX, y, 0), App.Vector(0, 1, 0))))
    remainder = rect.cut(circle)

    shields = {}
    for f in remainder.Faces:
        face_center_x = (f.BoundBox.XMin + f.BoundBox.XMax) / 2
        suffix = "MountHalf" if face_center_x < WHEEL_CX else "OpenHalf"
        shape = f.extrude(App.Vector(0, SHIELD_THICKNESS, 0))
        obj = doc.addObject("Part::Feature", name_prefix + "_Shield" + suffix)
        obj.Shape = shape
        shields[suffix.lower()] = obj
    return shields


def _make_nut(doc, name, y, z):
    """Hex nut, axis=x, spanning x=-NUT_HEIGHT to 0 (flush against
    the mount strip's own outer face at x=0, extending toward the
    load cell in -x)."""

    r = NUT_ACROSS_FLATS / math.sqrt(3)
    points = []
    for i in range(6):
        angle = math.pi / 6 + 2 * math.pi * i / 6
        points.append(App.Vector(-NUT_HEIGHT, y + r * math.cos(angle), z + r * math.sin(angle)))
    points.append(points[0])
    face = Part.Face(Part.makePolygon(points))
    body = face.extrude(App.Vector(NUT_HEIGHT, 0, 0))

    bore = Part.makeCylinder(NUT_BORE_DIAMETER / 2, NUT_HEIGHT + 2,
                              App.Vector(-NUT_HEIGHT - 1, y, z), App.Vector(1, 0, 0))
    body = body.cut(bore)

    obj = doc.addObject("Part::Feature", name)
    obj.Shape = body
    return obj


def _drill_axle_hole(obj, y_start, length):
    hole = Part.makeCylinder(AXLE_DIAMETER / 2, length,
                              App.Vector(WHEEL_CX, y_start, 0), App.Vector(0, 1, 0))
    obj.Shape = obj.Shape.cut(hole)


def _make_axle(doc, name):
    y_start = -AXLE_OVERHANG
    y_end = 2 * PLATE_THICKNESS + guide_wheel.WIDTH + AXLE_OVERHANG
    shape = Part.makeCylinder(AXLE_DIAMETER / 2, y_end - y_start,
                               App.Vector(WHEEL_CX, y_start, 0), App.Vector(0, 1, 0))
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    return obj


def make(doc, name_prefix="TW_WindingPulley"):
    plate_near = _make_plate(doc, name_prefix + "_PlateNear", 0.0)
    wheel = guide_wheel.make(doc, name_prefix + "_Wheel", cx=WHEEL_CX, cz=0.0, y=PLATE_THICKNESS)
    plate_far = _make_plate(doc, name_prefix + "_PlateFar", PLATE_THICKNESS + guide_wheel.WIDTH)

    _drill_axle_hole(plate_near, -1.0, PLATE_THICKNESS + 2)
    _drill_axle_hole(plate_far, PLATE_THICKNESS + guide_wheel.WIDTH - 1.0, PLATE_THICKNESS + 2)
    axle = _make_axle(doc, name_prefix + "_Axle")

    strip_mount = _make_strip(doc, name_prefix + "_StripMount",
                               0.0, STRIP_THICKNESS, -PLATE_HEIGHT / 2, PLATE_HEIGHT)
    strip_top = _make_strip(doc, name_prefix + "_StripTop",
                             0.0, PLATE_WIDTH, PLATE_HEIGHT / 2 - STRIP_THICKNESS, STRIP_THICKNESS)
    strip_bottom = _make_strip(doc, name_prefix + "_StripBottom",
                                0.0, PLATE_WIDTH, -PLATE_HEIGHT / 2, STRIP_THICKNESS)

    shields_near = _make_wheel_shields(doc, name_prefix + "Near", PLATE_THICKNESS)
    shields_far = _make_wheel_shields(doc, name_prefix + "Far",
                                       PLATE_THICKNESS + guide_wheel.WIDTH - SHIELD_THICKNESS)

    nut = _make_nut(doc, name_prefix + "_Nut", NUT_CY, NUT_CZ)

    parts = {"plate_near": plate_near, "wheel": wheel, "plate_far": plate_far,
             "strip_mount": strip_mount, "strip_top": strip_top, "strip_bottom": strip_bottom,
             "nut": nut, "axle": axle}
    for suffix, obj in shields_near.items():
        parts["shield_near_" + suffix] = obj
    for suffix, obj in shields_far.items():
        parts["shield_far_" + suffix] = obj
    return parts
