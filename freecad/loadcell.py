"""
===========================================================
Open Paraglider Tow Winch

Module : loadcell.py

Version : 0.0.1

Placeholder for the 500kg-rated compression/tension load cell
(picts/loadcell dimensions.png, picts/loadcell url.txt) - the
same physical envelope covers the whole 30-1000kg range in this
product family, only the internal strain gauge rating differs.
Simplified envelope, not a real manufacturer file: main flanged
disc (ΦA=74mm, H1=30mm) with a smaller raised boss on top
(ΦC=24mm, H-H1=4mm), a threaded M16x1.5 centre hole (modelled as
a plain 16mm hole here), and the 8x Φ9mm mounting bolt holes on
a 63mm (ΦB) bolt circle - counterbore detail (ΦD1=6mm at
7.2mm depth) not modelled, this is a placeholder.

Local convention: axis = X, flange face (mounting face, the
larger ΦA disc) at the given x, body extending toward +X.
===========================================================
"""

import Part
import FreeCAD as App
import math

OUTER_DIAMETER = 74.0
FLANGE_HEIGHT = 30.0       # H1
BOSS_DIAMETER = 24.0       # ΦC
BOSS_HEIGHT = 4.0          # H - H1
TOTAL_HEIGHT = FLANGE_HEIGHT + BOSS_HEIGHT  # H = 34

CENTRE_HOLE_DIAMETER = 16.0  # nominal M16x1.5, modelled as a plain hole

BOLT_HOLE_DIAMETER = 9.0    # ΦD
BOLT_CIRCLE_DIAMETER = 63.0  # ΦB
BOLT_HOLE_COUNT = 8


def make(doc, name, cy=0, cz=0, x=0):
    """(cy, cz) is the load cell's own axis. x is the flange
    (mounting) face position; the body extends toward +x."""

    axis = App.Vector(1, 0, 0)

    flange = Part.makeCylinder(OUTER_DIAMETER / 2, FLANGE_HEIGHT, App.Vector(x, cy, cz), axis)
    boss = Part.makeCylinder(BOSS_DIAMETER / 2, BOSS_HEIGHT,
                              App.Vector(x + FLANGE_HEIGHT, cy, cz), axis)
    shape = flange.fuse(boss)

    centre_hole = Part.makeCylinder(CENTRE_HOLE_DIAMETER / 2, TOTAL_HEIGHT + 2,
                                     App.Vector(x - 1, cy, cz), axis)
    shape = shape.cut(centre_hole)

    bolt_circle_r = BOLT_CIRCLE_DIAMETER / 2
    for i in range(BOLT_HOLE_COUNT):
        angle = 2 * math.pi * i / BOLT_HOLE_COUNT
        hy = cy + bolt_circle_r * math.cos(angle)
        hz = cz + bolt_circle_r * math.sin(angle)
        hole = Part.makeCylinder(BOLT_HOLE_DIAMETER / 2, FLANGE_HEIGHT + 2,
                                  App.Vector(x - 1, hy, hz), axis)
        shape = shape.cut(hole)

    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    return obj
