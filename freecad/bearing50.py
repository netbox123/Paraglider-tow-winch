"""
===========================================================
Open Paraglider Tow Winch

Module : bearing50.py

Version : 0.0.2

UCF210 4-bolt flange bearing unit, 50 mm bore.

Loads the real manufacturer STEP file (drawings/bearing50.stp)
- replaces the earlier simplified cylindrical placeholder.
The file's native origin already matches this project's
convention: shaft axis along Y, flange (flat/mounting) face
at local Y=0, housing extending toward +Y.

===========================================================
"""

import Part
import FreeCAD as App
import os

STEP_FILE = os.path.join(os.path.dirname(__file__), "drawings", "bearing50.stp")


def make(doc, name, cx=0, cz=0, y=0, flip=False):
    """
    (cx, cz) is the shaft axis. y is the position of the
    flange (flat) face. By default the housing extends toward
    +Y from there; set flip=True to extend toward -Y instead
    (e.g. so the flange faces outward on both ends of a
    shaft).
    """

    shape = Part.Shape()
    shape.read(STEP_FILE)

    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape

    rotation = App.Rotation(App.Vector(0, 0, 1), 180) if flip else App.Rotation()
    obj.Placement = App.Placement(App.Vector(cx, y, cz), rotation)

    return obj
