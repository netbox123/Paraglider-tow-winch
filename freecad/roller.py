"""
===========================================================
Open Paraglider Tow Winch

Module : roller.py

Version : 0.0.2

Rope intake funnel roller - 20mm diameter guide roller.

(x, y, z) is the min-corner-along-axis point (same
convention as round_tube.py / tube.py).

===========================================================
"""

import Part
import FreeCAD as App

OUTER_DIAMETER = 20.0
BORE_DIAMETER  = 8.0

_AXES = {
    "X": App.Vector(1, 0, 0),
    "Y": App.Vector(0, 1, 0),
    "Z": App.Vector(0, 0, 1),
}


def make(doc, name, length, axis="Y", x=0, y=0, z=0):

    direction = _AXES[axis]
    base = App.Vector(x, y, z)

    body = Part.makeCylinder(OUTER_DIAMETER / 2, length, base, direction)
    bore = Part.makeCylinder(BORE_DIAMETER / 2, length + 2, base - direction, direction)

    obj = doc.addObject("Part::Feature", name)
    obj.Shape = body.cut(bore)

    return obj
