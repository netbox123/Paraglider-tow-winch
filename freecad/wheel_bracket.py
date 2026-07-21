"""
===========================================================
Open Paraglider Tow Winch

Module : wheel_bracket.py

Version : 0.0.4

Rope intake wheel bracket: 2 grooved wheels (guide_wheel.py)
sat side by side, sandwiched between 2 identical flat plates
on cross-pins (pins not modelled yet).

2 guide rollers (roller.py) positioned beyond the wheels'
own flush (far) edge - farthest from the frame of anything
in this assembly, since they're the first thing the rope
touches coming in. Centred on the pipe's own centreline (u).
Shape/size/position only for now - their own mounting plates
are a separate follow-up step, so the existing wheel plates
are untouched (no holes cut for the rollers yet).

Local coordinate convention (this whole assembly gets
reoriented/placed as one piece once the final swivel
placement is worked out):

    u = wheel-to-wheel spacing axis
    v = near/far-from-pipe axis, in the plate's own plane
    w = plate sandwich / wheel+roller axle direction

Each plate is a hexagon: a rectangle below the wheel
centreline (v=0) with WHEEL_MARGIN clearance around each
wheel, flush (0 margin) on the far edge, tapering
symmetrically above the centreline to a flat top segment
exactly as wide as the intake pipe's outer diameter.

    WHEEL_SPACING     101 mm  (100mm wheels, 1mm gap between rims)
    WHEEL_MARGIN      4 mm    (plate edge clearance, except far edge)
    PLATE_THICKNESS   4 mm
    ROLLER_GAP        6 mm    (for the 3mm rope to pass between them)

===========================================================
"""

import Part
import FreeCAD as App
import config
import guide_wheel
import roller

WHEEL_SPACING   = 101.0
WHEEL_MARGIN    = 4.0
PLATE_THICKNESS = 4.0
AXLE_DIAMETER   = 8.0

ROLLER_GAP = 6.0

ROLLER_BRACKET_THICKNESS = 4.0

SHIELD_THICKNESS = 2.0
SHIELD_CLEARANCE = 1.0


def _make_plate(doc, name, w):

    wheel_r = guide_wheel.OUTER_DIAMETER / 2
    pipe_r  = config.INTAKE_PIPE_DIAMETER / 2
    u_min = -wheel_r - WHEEL_MARGIN
    u_max = WHEEL_SPACING + wheel_r + WHEEL_MARGIN
    v_min = -wheel_r
    v_max = wheel_r + WHEEL_MARGIN
    u_center = WHEEL_SPACING / 2

    points = [
        App.Vector(u_min, 0, v_min),
        App.Vector(u_max, 0, v_min),
        App.Vector(u_max, 0, 0),
        App.Vector(u_center + pipe_r, 0, v_max),
        App.Vector(u_center - pipe_r, 0, v_max),
        App.Vector(u_min, 0, 0),
        App.Vector(u_min, 0, v_min),
    ]
    face = Part.Face(Part.makePolygon(points))
    shape = face.extrude(App.Vector(0, PLATE_THICKNESS, 0))
    shape.translate(App.Vector(0, w, 0))

    for u in (0.0, WHEEL_SPACING):
        hole = Part.makeCylinder(AXLE_DIAMETER / 2, PLATE_THICKNESS + 2,
                                  App.Vector(u, w - 1, 0), App.Vector(0, 1, 0))
        shape = shape.cut(hole)

    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    return obj, u_min, u_max, v_min, v_max


def _make_roller_bracket(doc, name, u, w1, w2, v_center, v_in):
    """
    End-cap bracket at one u-extreme (top or bottom of the
    vertical rollers), holding both rollers together and
    tying them back to the plate's own flush edge (v_in).

    Cross-section (in the w/v plane): 2 discs exactly
    matching the roller's own radius, centred on each
    roller's centreline (w1/w2, v_center) - so the bracket's
    outer edge traces the roller's own 20mm circle - fused
    with a connecting web that reaches in to v_in. Extruded
    along u by ROLLER_BRACKET_THICKNESS. AXLE_DIAMETER holes
    through both discs, on the roller centrelines, for the
    same axle pin that passes through the roller.
    """

    r = roller.OUTER_DIAMETER / 2
    t = ROLLER_BRACKET_THICKNESS
    axis = App.Vector(1, 0, 0)

    disc1 = Part.makeCylinder(r, t, App.Vector(u, w1, v_center), axis)
    disc2 = Part.makeCylinder(r, t, App.Vector(u, w2, v_center), axis)
    web = Part.makeBox(t, (w2 - w1) + 2 * r, v_in - v_center,
                        App.Vector(u, w1 - r, v_center))
    shape = disc1.fuse(disc2).fuse(web)

    for w in (w1, w2):
        hole = Part.makeCylinder(AXLE_DIAMETER / 2, t + 2,
                                  App.Vector(u - 1, w, v_center), axis)
        shape = shape.cut(hole)

    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    return obj


def _make_wheel_shields(doc, name_prefix, u_min, u_max, v_min, v_max, u_center, pipe_r, w):
    """
    Small guard plates closing the WHEEL_MARGIN gap down to just
    SHIELD_CLEARANCE (1mm) from each wheel, so the rope can't
    slip sideways off the wheels into the pocket between a
    wheel's own edge and the main plate's edge: the main plate's
    hexagon, minus a wheel_r + SHIELD_CLEARANCE circle around
    each wheel.

    A true single continuous shield around both wheels isn't
    physically possible here, so this naturally comes out as 4
    separate, non-touching pieces (welded on individually rather
    than fused into one): a sliver left of wheel 1, a sliver
    right of wheel 2, a strip connecting under the valley between
    the wheels, and the piece up near the pipe-side taper
    (spanning both wheels). The gaps between them (under each
    wheel at the flush tangent point, and along the taper closest
    to each wheel) sit *inside* the wheel's own 50mm radius - any
    bridging material there would collide with the wheel itself -
    and the one gap clear of both wheels (the valley) is the
    rope's own path up to the pipe.
    """

    wheel_r = guide_wheel.OUTER_DIAMETER / 2
    r = wheel_r + SHIELD_CLEARANCE

    points = [
        App.Vector(u_min, 0, v_min),
        App.Vector(u_max, 0, v_min),
        App.Vector(u_max, 0, 0),
        App.Vector(u_center + pipe_r, 0, v_max),
        App.Vector(u_center - pipe_r, 0, v_max),
        App.Vector(u_min, 0, 0),
        App.Vector(u_min, 0, v_min),
    ]
    hexagon = Part.Face(Part.makePolygon(points))
    circle1 = Part.Face(Part.Wire(Part.makeCircle(r, App.Vector(0, 0, 0), App.Vector(0, 1, 0))))
    circle2 = Part.Face(Part.Wire(Part.makeCircle(r, App.Vector(WHEEL_SPACING, 0, 0), App.Vector(0, 1, 0))))
    remainder = hexagon.cut(circle1).cut(circle2)

    shields = {}
    for f in remainder.Faces:
        u_face_center = (f.BoundBox.XMin + f.BoundBox.XMax) / 2
        v_face_center = (f.BoundBox.ZMin + f.BoundBox.ZMax) / 2
        if v_face_center > 0:
            suffix = "PipeSide"
        elif u_face_center < 0:
            suffix = "LeftMargin"
        elif u_face_center > WHEEL_SPACING:
            suffix = "RightMargin"
        else:
            suffix = "BottomConnector"

        shape = f.extrude(App.Vector(0, SHIELD_THICKNESS, 0))
        shape.translate(App.Vector(0, w, 0))
        obj = doc.addObject("Part::Feature", name_prefix + "_Shield" + suffix)
        obj.Shape = shape
        shields[suffix.lower()] = obj

    return shields


def make(doc, name_prefix="TW_IntakeWheelBracket"):

    wheel_width = guide_wheel.WIDTH

    plate_near, u_min, u_max, v_min, v_max = _make_plate(doc, name_prefix + "_PlateNear", 0.0)
    plate_far, _, _, _, _ = _make_plate(doc, name_prefix + "_PlateFar", PLATE_THICKNESS + wheel_width)

    wheel1 = guide_wheel.make(doc, name_prefix + "_Wheel1", cx=0.0, cz=0.0, y=PLATE_THICKNESS)
    wheel2 = guide_wheel.make(doc, name_prefix + "_Wheel2", cx=WHEEL_SPACING, cz=0.0, y=PLATE_THICKNESS)

    # Rollers stand with their own axis along "u" (vertical,
    # once the whole bracket is placed on the pipe), centred
    # on the pipe's own centreline, spanning the same width
    # as the plate (u_max - u_min, 209mm). The 2 rollers sit
    # side by side along "w", spaced for the ROLLER_GAP the
    # rope passes through, and at v beyond the wheels' flush
    # edge - farthest from the frame of anything in this
    # assembly, since they're the first thing the rope
    # touches coming in.
    u_center = WHEEL_SPACING / 2
    roller_length = u_max - u_min
    roller_u_start = u_center - roller_length / 2
    roller_v = v_min - roller.OUTER_DIAMETER / 2

    w_center = (PLATE_THICKNESS + PLATE_THICKNESS + wheel_width) / 2
    roller_spacing = roller.OUTER_DIAMETER + ROLLER_GAP
    roller_w1 = w_center - roller_spacing / 2
    roller_w2 = w_center + roller_spacing / 2

    roller1 = roller.make(doc, name_prefix + "_Roller1", roller_length, axis="X",
                           x=roller_u_start, y=roller_w1, z=roller_v)
    roller2 = roller.make(doc, name_prefix + "_Roller2", roller_length, axis="X",
                           x=roller_u_start, y=roller_w2, z=roller_v)

    # 2 small end-cap brackets holding both rollers together,
    # one at each u-extreme (top and bottom of the vertical
    # rollers), flush against the roller ends and reaching in
    # as far as the plate's own corner at v=0 - the wheel
    # centreline plane - matching the full length of the
    # plate's edge at that u-extreme, not just its v_min tip.
    bracket_bottom = _make_roller_bracket(
        doc, name_prefix + "_RollerBracketBottom",
        u_min - ROLLER_BRACKET_THICKNESS, roller_w1, roller_w2, roller_v, 0.0)
    bracket_top = _make_roller_bracket(
        doc, name_prefix + "_RollerBracketTop",
        u_max, roller_w1, roller_w2, roller_v, 0.0)

    # 4 small shield plates per side (8 total) closing the
    # WHEEL_MARGIN gap between the wheels and the plate's own
    # edge down to just 1mm - stops the rope slipping sideways
    # off the wheels into that pocket. Mounted flush against
    # each main plate's own wheel-facing surface, thin enough
    # (2mm) to still fit within the wheel-to-plate ring spacer
    # planned for later. These stay as 4 separate parts per side
    # (welded on individually) rather than one fused piece - see
    # the docstring on _make_wheel_shields for why a true single
    # continuous shield isn't physically possible here.
    pipe_r = config.INTAKE_PIPE_DIAMETER / 2
    plate_far_w_start = PLATE_THICKNESS + wheel_width

    shields_near = _make_wheel_shields(
        doc, name_prefix + "Near", u_min, u_max, v_min, v_max, u_center, pipe_r, PLATE_THICKNESS)
    shields_far = _make_wheel_shields(
        doc, name_prefix + "Far", u_min, u_max, v_min, v_max, u_center, pipe_r, plate_far_w_start - SHIELD_THICKNESS)

    result = {
        "plate_near": plate_near,
        "plate_far": plate_far,
        "wheel1": wheel1,
        "wheel2": wheel2,
        "roller1": roller1,
        "roller2": roller2,
        "roller_bracket_bottom": bracket_bottom,
        "roller_bracket_top": bracket_top,
    }
    for suffix, obj in shields_near.items():
        result["shield_near_" + suffix] = obj
    for suffix, obj in shields_far.items():
        result["shield_far_" + suffix] = obj

    return result
