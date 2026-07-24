"""
===========================================================
Open Paraglider Tow Winch

Module : flange_bearing.py

Version : 0.0.1

Real KFL-style self-aligning flange bearing assembly
(drawings/kfl_flange_bearing.STEP - "ASSEMBLY OF KFL CASING AND
BEARING", 12 solids: housing, inner race, several small
fasteners/seals, and 7 ball-bearing balls). Used for the
self-reversing screw's own end supports.

The file's own local origin is nowhere near its geometry (raw
bbox far from 0,0,0) and its native through-bore axis is Y, not
X - both handled here: the shape is recentred on the bearing
pocket's own real centre (found empirically by dumping the
housing's large-radius cylindrical faces and confirming they all
share the same (X, Z) centre - not guessed) before a 90 degree
rotation about Z maps native Y onto this project's own X
convention (screw axis).

The housing's own internal pocket (where the bearing race seats)
steps down to as narrow as 22mm diameter (11mm radius) at each
end in the raw file - found by dumping its own large cylindrical
faces, and matching the SAME 1.25x scale factor as
reversing_screw.py's own SCALE_FACTOR (this bearing was very
likely meant to pair with that screw's own original 20mm
diameter). Scaled uniformly - same reasoning as the screw's own
uniform-vs-non-uniform scaling choice, and it's a single
compound shape (12 solids) rather than one continuous swept
surface, so a uniform Shape.scale() is safe here regardless.
Post-scale, the narrowest pocket point is 27.5mm, comfortably
clear of the 25mm screw.

Bore axis convention: the raw file's own native bore axis is
already Y, so axis="Y" (the level-wind mechanism's own travel
direction, matching the drum/pulley wheel/screw axis convention
used throughout this project) needs no rotation at all beyond
the recentring; axis="X" adds a -90 degree rotation about Z on
top of that. (u, v) is the bore/pivot centre (the 2 axes NOT
along the bore); w is the bore centre's own position along the
bore axis. For axis="X": u=y, v=z, w=x. For axis="Y": u=x, v=z,
w=y.
===========================================================
"""

import Part
import FreeCAD as App
import os

STEP_FILE = os.path.join(os.path.dirname(__file__), "drawings", "kfl_flange_bearing.STEP")

SCALE_FACTOR = 1.25   # matches reversing_screw.py's own SCALE_FACTOR

# Bore pocket centre, found empirically on the RAW (unscaled)
# file (see module docstring) - NOT the raw file's own
# bounding-box centre, which is offset from the true bore by
# several mm. Scaled below along with the rest of the shape.
_NATIVE_BORE_X = 28.58 * SCALE_FACTOR
_NATIVE_BORE_Y = 14.65 * SCALE_FACTOR
_NATIVE_BORE_Z = -35.34 * SCALE_FACTOR

BORE_MIN_DIAMETER = 22.0 * SCALE_FACTOR   # narrowest point in the housing's own stepped pocket


def make(doc, name, u=0, v=0, w=0, axis="Y", flip=False):
    """See module docstring for what (u, v, w) mean for each axis.
    flip mirrors the assembly end-to-end along its own bore axis
    (which face points which way) - achieved by rotating 180
    degrees about Z, an axis PERPENDICULAR to the bore, matching
    bearing50.py's own flip convention. Rotating about the bore
    axis itself would NOT do this - the housing's round flange
    face looks the same either way under that rotation, so a
    first attempt using that axis produced no visible change."""

    shape = Part.Shape()
    shape.read(STEP_FILE)
    shape.scale(SCALE_FACTOR)

    shape.translate(App.Vector(-_NATIVE_BORE_X, -_NATIVE_BORE_Y, -_NATIVE_BORE_Z))
    if axis == "X":
        shape.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), -90)
    elif axis != "Y":
        raise ValueError("axis must be 'X' or 'Y'")
    if flip:
        shape.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 180)

    if axis == "X":
        shape.translate(App.Vector(w, u, v))
    else:
        shape.translate(App.Vector(u, w, v))

    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    return obj
