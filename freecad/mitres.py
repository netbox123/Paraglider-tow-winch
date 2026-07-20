"""
===========================================================
Open Paraglider Tow Winch

Module : mitres.py

Version : 0.0.5

45 degree tube mitres.

Every function cuts a single 45 degree plane through a pivot
point that is the true outer corner of the frame at that
joint. The outer corner stays sharp (full length); the inner
face recedes by exactly one TUBE_SIZE. Two beams meeting at
the same frame corner are cut with the same pivot point, so
they mate along the same plane.

Pivot point and cutter rotation angle for each of the 4
corners of a rectangular frame (in the X-Z plane) were
determined empirically (see freecad dev notes / build log),
since the correct angle depends on both the pivot location
and which side the beam's material sits on:

    corner            pivot        angle
    front-bottom      (x0,   z0)     -45
    front-top         (x0,   z1)     135
    rear-bottom       (x1,   z0)     -45
    rear-top          (x1,   z1)     135
    (front post ends, either z)  (x0, z)   45
    (rear post ends,  either z)  (x1, z) -135

===========================================================
"""

import FreeCAD as App
import config

CUTTER = 200


def _make_cut(doc, beam, name, px, py, pz, angle):

    cutter = doc.addObject("Part::Box", name + "_Cutter")

    cutter.Length = CUTTER
    cutter.Width  = CUTTER
    cutter.Height = CUTTER

    cutter.Placement.Base = App.Vector(px, py - CUTTER / 2, pz)
    cutter.Placement.Rotation = App.Rotation(App.Vector(0, 1, 0), angle)

    cut = doc.addObject("Part::Cut", name)
    cut.Base = beam
    cut.Tool = cutter

    doc.recompute()

    beam.Visibility = False
    cutter.Visibility = False

    return cut


# ----------------------------------------------------------
# Horizontal (X) beams - top rail
# ----------------------------------------------------------
# (x, y, z) is the beam's own placement origin (its low
# corner). The pivot is the outer-top corner of the end
# face, one TUBE_SIZE above z. The top face stays sharp; the
# bottom face recedes.

def mitre_x_start(doc, beam, name, x, y, z):

    return _make_cut(doc, beam, name, x, y, z + config.TUBE_SIZE, 135)


def mitre_x_end(doc, beam, name, x, y, z):

    return _make_cut(doc, beam, name, x, y, z + config.TUBE_SIZE, 135)


# ----------------------------------------------------------
# Horizontal (X) beams - bottom rail
# ----------------------------------------------------------
# (x, y, z) is the beam's own placement origin, with z being
# the bottom (outer) face already - no offset needed. The
# bottom face stays sharp; the top face recedes. Call once
# per end (x = start, then x = start + length).

def mitre_x_bottom(doc, beam, name, x, y, z):

    return _make_cut(doc, beam, name, x, y, z, -45)


# ----------------------------------------------------------
# Vertical (Z) beams - front (low X) posts
# ----------------------------------------------------------
# (x, y, z) is the beam's own placement origin, x being the
# front (outer) face already - no offset needed. The front
# face stays sharp; the rear face recedes. Call once per end
# (z = 0, then z = height).

def mitre_z_front(doc, beam, name, x, y, z):

    return _make_cut(doc, beam, name, x, y, z, 45)


# ----------------------------------------------------------
# Vertical (Z) beams - rear (high X) posts
# ----------------------------------------------------------
# (x, y, z) is the beam's own placement origin. The pivot is
# the outer-rear face, one TUBE_SIZE past x. The rear face
# stays sharp; the front face recedes. Call once per end
# (z = 0, then z = height).

def mitre_z_rear(doc, beam, name, x, y, z):

    return _make_cut(doc, beam, name, x + config.TUBE_SIZE, y, z, -135)