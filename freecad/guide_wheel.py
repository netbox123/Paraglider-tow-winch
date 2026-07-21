"""
===========================================================
Open Paraglider Tow Winch

Module : wheel.py

Version : 0.0.1

Rope intake guide wheel - 100mm grooved pulley wheel.

Simplified as a plain cylindrical envelope (no V-groove
profile), matching the level of detail used for
sprocket.py. Dimensions from drawings/wheel 100.png:

    Outer diameter    100 mm
    Width             22 mm
    Axle bore         8 mm

===========================================================
"""

import Part
import FreeCAD as App

OUTER_DIAMETER = 100.0
WIDTH          = 22.0
BORE_DIAMETER  = 8.0


def make(doc, name, cx=0, cz=0, y=0):

    axis = App.Vector(0, 1, 0)

    body = Part.makeCylinder(OUTER_DIAMETER / 2, WIDTH, App.Vector(cx, y, cz), axis)
    bore = Part.makeCylinder(BORE_DIAMETER / 2, WIDTH + 2, App.Vector(cx, y - 1, cz), axis)

    obj = doc.addObject("Part::Feature", name)
    obj.Shape = body.cut(bore)

    return obj
