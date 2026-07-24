"""
===========================================================
Open Paraglider Tow Winch

Module : reversing_screw.py

Version : 0.0.1

Real self-reversing lead screw for the level-wind traversing
drive (drawings/RS2020-200L600.stp - "RS2020" per the original
filename, a 20mm nominal/root diameter screw). Scaled UNIFORMLY
(both diameter and length together) up to a 25mm shaft diameter
- a non-uniform (radial-only) scale was tried first and gave a
badly distorted result (OCCT can't represent a
non-uniformly-scaled helical thread surface exactly), so uniform
scaling is the only clean option. This makes the working length
750mm (was 600mm) - not yet trimmed to a final length, since the
screw needs to stick out through one of its 2 end supports for a
belt sprocket to mount on, and that exact protrusion hasn't been
decided yet.

Local/native convention: axis = X (matches the file's own native
orientation, verified via BoundBox - a much longer X extent than
Y/Z). axis="Y" (the level-wind mechanism's own travel direction,
matching the drum/pulley wheel axis convention used throughout
this project) rotates the whole thing 90 degrees about Z so it
runs along Y instead - same reference-point meaning either way,
just with u/v/w relabelled to match.

(u, v) is the screw's own shaft axis (the 2 axes NOT along the
screw); w is the position of the file's own local origin point
along the screw (NOT either end - the raw file's bbox is
asymmetric around its own origin), body extending both ways from
there per the file's own native geometry. For axis="X" (default):
u=y, v=z, w=x. For axis="Y": u=x, v=z, w=y.
===========================================================
"""

import Part
import FreeCAD as App
import os

STEP_FILE = os.path.join(os.path.dirname(__file__), "drawings", "RS2020-200L600.stp")

NATIVE_ROOT_DIAMETER = 20.0
TARGET_ROOT_DIAMETER = 25.0
SCALE_FACTOR = TARGET_ROOT_DIAMETER / NATIVE_ROOT_DIAMETER

ROOT_DIAMETER = TARGET_ROOT_DIAMETER


def make(doc, name, u=0, v=0, w=0, axis="X"):
    """See module docstring for what (u, v, w) mean for each axis."""

    shape = Part.Shape()
    shape.read(STEP_FILE)
    shape.scale(SCALE_FACTOR)

    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape

    if axis == "X":
        obj.Placement = App.Placement(App.Vector(w, u, v), App.Rotation())
    elif axis == "Y":
        obj.Placement = App.Placement(App.Vector(u, w, v), App.Rotation(App.Vector(0, 0, 1), 90))
    else:
        raise ValueError("axis must be 'X' or 'Y'")

    return obj
