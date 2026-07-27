"""
===========================================================
Open Paraglider Tow Winch

Module : motor.py

Version : 0.0.1

QS165 60H motor - real STL mesh
(drawings/QSMotor_QS165_60H_v3.stl), not a placeholder.

The mesh's own local origin is not on the shaft axis, so the
offsets below were calibrated directly from the mesh geometry:

    - shaft axis is parallel to Y
    - splined output shaft (where the sprocket mounts) is at
      the local Y minimum (-109.0); the fan/tail end is at
      the local Y maximum (133.0)
    - shaft rotation axis centre, in local X/Z: (146.20, 102.22)

make(doc, cx, cz, y) places the mesh so the shaft axis passes
through global (cx, cz), with the shaft tip at global Y=y.
The body extends toward +Y (toward the fan end).

The mesh is spun 180 degrees about its own shaft axis (a pure
rotation, doesn't swap which end is which) - the user found the
real mounting-boss orientation was wrong side up in the first
build. FLIP_ROTATION is applied about the shaft axis line itself
(App.Placement's 3-argument form, rotation center in the mesh's
own pre-translation local frame), not the mesh's arbitrary local
origin, so it doesn't disturb the cx/cz/y placement math above.

===========================================================
"""

import FreeCAD as App
import Mesh
import os

STL_FILE = os.path.join(os.path.dirname(__file__), "drawings", "QSMotor_QS165_60H_v3.stl")

LOCAL_SHAFT_X    = 146.20
LOCAL_SHAFT_Z    = 102.22
LOCAL_SHAFT_TIP_Y = -109.0

FLIP_ROTATION = App.Rotation(App.Vector(0, 1, 0), 180)

# Distance from the shaft axis down to the mesh's lowest point
# after the 180 degree flip above - use to rest the motor at a
# given height (e.g. on top of the bottom rail):
# cz = rest_height + BELOW_SHAFT_Z. Re-measured via freecadcmd
# after the flip (was 85.75 before it - flipping swapped the
# below/above distances, so the old value is now ABOVE_SHAFT_Z).
BELOW_SHAFT_Z = 99.25

SHAFT_SPLINE_DIAMETER = 19.8  # from the QS165 drawing, "D20" nominal spline


def make(doc, name, cx=0, cz=0, y=0):

    mesh = Mesh.Mesh(STL_FILE)

    obj = doc.addObject("Mesh::Feature", name)
    obj.Mesh = mesh

    base = App.Vector(cx - LOCAL_SHAFT_X, y - LOCAL_SHAFT_TIP_Y, cz - LOCAL_SHAFT_Z)
    rotation_center = App.Vector(LOCAL_SHAFT_X, 0, LOCAL_SHAFT_Z)
    obj.Placement = App.Placement(base, FLIP_ROTATION, rotation_center)

    return obj
