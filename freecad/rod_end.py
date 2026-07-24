"""
===========================================================
Open Paraglider Tow Winch

Module : rod_end.py

Version : 0.0.1

Placeholder for the internally-threaded (SI-type) M16x2.0 rod
end / spherical rose joint that pivots between the winding
clevis plates and the load cell (picts/Rod End Ball Joint.png).
The real part's 3D files (picts/Rod End Ball Joint 3D/) are
Solid Edge .par/.asm - not importable into FreeCAD - so this is
a dimensioned placeholder envelope, not the real manufacturer
geometry, same approach as loadcell.py.

Eye (spherical bearing housing): OD 42mm, bore 16mm - the pivot
pin passes through here, along the part's own Y axis - axial
thickness 15mm. The shank is perpendicular to the bore axis
(this project's own X once placed), passing through the bore's
own centre, reaching 64mm from the bore centre to the far
(mounting) face of the hex boss - of that 64mm the last 22mm is
the hex boss (27mm across flats), internally threaded M16x2.0
(modelled as a plain blind hole, thread not modelled, same
simplification level as the load cell's own centre hole).

The internal thread here mates with the load cell's own
internal M16 thread via a plain threaded stud, fully recessed
inside both parts once tightened - so no separate stud is
modelled and the two mounting faces sit flush (0mm gap), the
same convention used for unmodelled bolts elsewhere in this
project.

Local convention: bore axis = Y, shank axis = X. (cy, cz) is
the bore centre (the pivot point). x is the bore centre's own X
position; the shank and hex boss extend toward +x, reaching
x + REACH at the hex's mounting face.
===========================================================
"""

import Part
import FreeCAD as App
import math

EYE_OUTER_DIAMETER = 42.0
EYE_BORE_DIAMETER = 16.0
EYE_THICKNESS = 15.0           # along the bore/pivot-pin axis

REACH = 64.0                   # bore centre -> hex mounting face
HEX_LENGTH = 27.0
HEX_ACROSS_FLATS = 22.0
HEX_BORE_DIAMETER = 16.0       # internal M16x2.0, thread not modelled
HEX_BORE_DEPTH = 18.0

NECK_DIAMETER = 20.0
NECK_START = EYE_OUTER_DIAMETER / 2   # neck begins at the eye's own edge

# Worst-case radial reach of anything running along the shank
# axis (the hex boss's corners, wider than the neck) - the eye
# sits between the two clevis plates, but the shank+hex continue
# straight out past the plates' own domed tip, so the plates need
# to be spaced apart by more than this, not just the eye's own
# thickness, or the hex would clip them.
ENVELOPE_RADIUS = HEX_ACROSS_FLATS / math.sqrt(3)

# Tangent-only contact between the eye/neck/hex cylinders won't
# fuse into a single solid (zero-volume overlap), so the neck
# runs 1mm into each neighbour on both ends.
_JOINT_OVERLAP = 1.0


def make(doc, name, cy=0, cz=0, x=0):
    """(cy, cz) is the bore/pivot centre. x is the bore centre's
    own X position; the shank and hex boss extend toward +x,
    reaching x + REACH at the hex's mounting face."""

    bore_axis = App.Vector(0, 1, 0)
    shank_axis = App.Vector(1, 0, 0)

    eye = Part.makeCylinder(EYE_OUTER_DIAMETER / 2, EYE_THICKNESS,
                             App.Vector(x, cy - EYE_THICKNESS / 2, cz), bore_axis)
    bore = Part.makeCylinder(EYE_BORE_DIAMETER / 2, EYE_THICKNESS + 2,
                              App.Vector(x, cy - EYE_THICKNESS / 2 - 1, cz), bore_axis)
    eye = eye.cut(bore)

    neck_start = NECK_START - _JOINT_OVERLAP
    neck_length = (REACH - HEX_LENGTH + _JOINT_OVERLAP) - neck_start
    neck = Part.makeCylinder(NECK_DIAMETER / 2, neck_length,
                              App.Vector(x + neck_start, cy, cz), shank_axis)

    hex_circumradius = HEX_ACROSS_FLATS / math.sqrt(3)
    hex_points = []
    for i in range(6):
        angle = math.pi / 6 + 2 * math.pi * i / 6
        hy = cy + hex_circumradius * math.cos(angle)
        hz = cz + hex_circumradius * math.sin(angle)
        hex_points.append(App.Vector(x + REACH - HEX_LENGTH, hy, hz))
    hex_points.append(hex_points[0])
    hex_face = Part.Face(Part.makePolygon(hex_points))
    hex_boss = hex_face.extrude(App.Vector(HEX_LENGTH, 0, 0))

    hex_hole = Part.makeCylinder(HEX_BORE_DIAMETER / 2, HEX_BORE_DEPTH,
                                  App.Vector(x + REACH, cy, cz), App.Vector(-1, 0, 0))
    hex_boss = hex_boss.cut(hex_hole)

    shape = eye.fuse(neck).fuse(hex_boss)

    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    return obj
