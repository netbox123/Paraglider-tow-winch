"""
===========================================================
Open Paraglider Tow Winch

Module : bearing50.py

Version : 0.0.1

UCF210 4-bolt flange bearing unit, 50 mm bore.

Simplified as a single concentric cylindrical envelope
(flange diameter, full axial length) with the shaft bore
through the centre - the real unit is an oblong flange plate
with a smaller housing boss, not a plain cylinder. This is a
conservative (never undersized) placeholder for clearance
checks. Swap for the real manufacturer STEP file (e.g. via
TraceParts) before finalizing bolt hole positions.

Dimensions from Timken's published UCF210 datasheet:
https://cad.timken.com/item/u-series---four-bolt-flanged-mounted-bearings--ucf/ucf-four-bolt-flange-units/ucf210

    Bore (shaft)                50 mm   (matches config.SHAFT_DIAMETER)
    Overall flange length (L)   143 mm  -> used as envelope diameter
    Flange thickness (A1)       16 mm
    Housing axial width (A)     40 mm
    Bolt hole spacing (J)       111 mm  (not modelled yet)
    Bolt hole diameter (N)      16 mm   (not modelled yet, M14 bolts)

===========================================================
"""

import Part
import FreeCAD as App
import config

BORE              = config.SHAFT_DIAMETER  # 50 mm
ENVELOPE_DIAMETER = 143.0                  # L
FLANGE_THICKNESS  = 16.0                   # A1
HOUSING_WIDTH     = 40.0                   # A
TOTAL_LENGTH      = FLANGE_THICKNESS + HOUSING_WIDTH


def make(doc, name, cx=0, cz=0, y=0, flip=False):
    """
    (cx, cz) is the shaft axis. y is the position of the
    flange (flat) face. By default the body extends toward
    +Y from there; set flip=True to extend toward -Y instead
    (e.g. so the flange faces outward on both ends of a
    shaft).
    """

    sign = -1 if flip else 1
    axis = App.Vector(0, sign, 0)

    body = Part.makeCylinder(ENVELOPE_DIAMETER / 2, TOTAL_LENGTH, App.Vector(cx, y, cz), axis)
    bore = Part.makeCylinder(BORE / 2, TOTAL_LENGTH + 2, App.Vector(cx, y - sign, cz), axis)

    obj = doc.addObject("Part::Feature", name)
    obj.Shape = body.cut(bore)

    return obj
