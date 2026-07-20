"""
===========================================================
Open Paraglider Tow Winch

Module : mitres.py

Version : 0.0.2

45 degree tube mitres

===========================================================
"""

import FreeCAD as App

CUTTER = 200

def _make_cut(doc, beam, name, x, y, z, rx, ry, rz):

    cutter = doc.addObject("Part::Box", name + "_Cutter")

    cutter.Length = CUTTER
    cutter.Width  = CUTTER
    cutter.Height = CUTTER

    cutter.Placement.Base = App.Vector(x, y, z)
    cutter.Placement.Rotation = App.Rotation(rx, ry, rz)

    cutter.ViewObject.ShapeColor = (1.0, 0.0, 0.0)

    doc.recompute()

    return cutter


# ----------------------------------------------------------
# X beam - start
# ----------------------------------------------------------

def mitre_x_start(doc, beam, name, x, y, z):

    return _make_cut(
        doc,
        beam,
        name,
        x - CUTTER,
        y - CUTTER / 2,
        z - CUTTER / 2,
        0,
        45,
        0
    )


# ----------------------------------------------------------
# X beam - end
# ----------------------------------------------------------

def mitre_x_end(doc, beam, name, x, y, z):

    return _make_cut(
        doc,
        beam,
        name,
        x,
        y - CUTTER / 2,
        z - CUTTER / 2,
        0,
        -45,
        0
    )