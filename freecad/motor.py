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

===========================================================
"""

import FreeCAD as App
import Mesh
import os

STL_FILE = os.path.join(os.path.dirname(__file__), "drawings", "QSMotor_QS165_60H_v3.stl")

LOCAL_SHAFT_X    = 146.20
LOCAL_SHAFT_Z    = 102.22
LOCAL_SHAFT_TIP_Y = -109.0

# Distance from the shaft axis down to the mesh's lowest
# point - use to rest the motor at a given height (e.g. on
# top of the bottom rail): cz = rest_height + BELOW_SHAFT_Z
BELOW_SHAFT_Z = 85.75

SHAFT_SPLINE_DIAMETER = 19.8  # from the QS165 drawing, "D20" nominal spline


def make(doc, name, cx=0, cz=0, y=0):

    mesh = Mesh.Mesh(STL_FILE)

    obj = doc.addObject("Mesh::Feature", name)
    obj.Mesh = mesh

    base = App.Vector(cx - LOCAL_SHAFT_X, y - LOCAL_SHAFT_TIP_Y, cz - LOCAL_SHAFT_Z)
    obj.Placement = App.Placement(base, App.Rotation())

    return obj
