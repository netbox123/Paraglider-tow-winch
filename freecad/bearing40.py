"""
===========================================================
Open Paraglider Tow Winch

Module : bearing40.py

Version : 0.0.3

Rope intake swivel bearing, 40 mm bore.

No real part sourced yet. Scaled down from the real UCF210
STEP file (drawings/bearing50.stp, 50 mm bore) by 40/50 -
a plausible placeholder for a bearing in the same product
family, not a real manufacturer part. Swap out once a real
40 mm bearing is chosen.

The intake pipe is horizontal, pointing along X (rearward,
out the back of the frame, toward where the rope approaches
from). Bore axis = X: rotated -90 degrees about Z, flange
face at the given x, housing extending toward +X - verified
empirically (see freecad dev notes), not assumed. flip=True
uses the opposite rotation (+90), housing extending toward
-X instead - also verified empirically, needed for the
second (inside-the-frame) bearing supporting the same pipe.

Mounting bracket connecting the bearing to the frame is not
modelled yet.

===========================================================
"""

import Part
import FreeCAD as App
import os

STEP_FILE = os.path.join(os.path.dirname(__file__), "drawings", "bearing50.stp")

SCALE = 40.0 / 50.0


def make(doc, name, cy=0, cz=0, x=0, flip=False):
    """
    (cy, cz) is the intake pipe axis. x is the position of
    the flange (mounting) face. By default the housing
    extends from there toward +X; flip=True extends it
    toward -X instead.
    """

    shape = Part.Shape()
    shape.read(STEP_FILE)
    shape.scale(SCALE)

    angle = 90 if flip else -90
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    obj.Placement = App.Placement(App.Vector(x, cy, cz), App.Rotation(App.Vector(0, 0, 1), angle))

    return obj
