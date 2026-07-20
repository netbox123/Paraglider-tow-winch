"""
===========================================================
Open Paraglider Tow Winch

Module : sprocket.py

Version : 0.0.1

428 pitch, 14 tooth sprocket, splined for the QS165 motor
output shaft.

Simplified as a plain cylindrical envelope (no tooth profile
modelled) with a through bore. Outer diameter and width are
from the sprocket's own drawing; the bore is sized to the
QS165's D20 spline (from motor.py / the motor's own drawing)
since the sprocket drawing's "32mm" dimension could not be
confirmed as the actual bore (photo of the drawing sheet was
partially cropped) - swap for the real value if you have the
full drawing.

    Outer diameter    61 mm
    Width             13 mm
    Bore              19.8 mm (QS165 spline OD, see motor.py)

===========================================================
"""

import Part
import FreeCAD as App
import motor

OUTER_DIAMETER = 61.0
WIDTH          = 13.0
BORE_DIAMETER  = motor.SHAFT_SPLINE_DIAMETER


def make(doc, name, cx=0, cz=0, y=0):

    axis = App.Vector(0, 1, 0)

    body = Part.makeCylinder(OUTER_DIAMETER / 2, WIDTH, App.Vector(cx, y, cz), axis)
    bore = Part.makeCylinder(BORE_DIAMETER / 2, WIDTH + 2, App.Vector(cx, y - 1, cz), axis)

    obj = doc.addObject("Part::Feature", name)
    obj.Shape = body.cut(bore)

    return obj
