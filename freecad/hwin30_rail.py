"""
===========================================================
Open Paraglider Tow Winch

Module : hwin30_rail.py

Version : 0.0.2

HWIN HGW30 linear guide rail and its carriage block (the
level-wind carriage rides on this). Loads the real manufacturer
IGES file (drawings/hwin30_block_and_rail.igs), which contains
both shapes together: a 200mm rail sample and its block. This
project needs 600mm of rail, so 3 real, unmodified 200mm
segments are placed end to end rather than stretching the
sample (which would distort its mounting-hole spacing).

The file imports as an unsewn surface model (no solids, just
raw faces) - normal for this particular IGES export, but it
still displays and positions fine as a Part::Feature.

Local axes as imported: X = rail width (~30mm), Y = mounting/
height axis (base at the more-negative extreme, working face at
the more-positive extreme), Z = length/travel direction (200mm
for the rail sample, 110.75mm for the block). Rotating -120
degrees about (1,1,1) remaps this to the convention used here:
mounting axis -> X, length -> Y, width -> Z (verified
empirically, not hand-derived - see freecad dev notes for the
axis-mapping check).

In the source file the block sits centred on the rail sample's
own Y-span (rail Z 100-300, block Z 144-254.8, centres within
0.6mm of each other) - `make_segments` and `make_block` both
position relative to the same (rail_bb.XMin, rail_bb.YMin)
reference point, so a block placed against a given segment index
lines up correctly on that segment without needing to re-derive
the offset by hand.
===========================================================
"""

import Part
import FreeCAD as App
import os

IGES_FILE = os.path.join(os.path.dirname(__file__), "drawings", "hwin30_block_and_rail.igs")

SEGMENT_LENGTH = 200.0

# The block's own top (mounting) face has ~60 small circular
# features (grease-fitting holes, chamfers, fillets) at wildly
# varying radii - these 4 are the real through-holes for bolting
# something to the top: identical 8.5mm diameter, right at the
# mounting surface (X = block's own XMax), forming a clean
# rectangle. Found by dumping every circular edge near the top
# face and picking out the ones that repeat with an identical
# radius - not read off a drawing, so if the real block ever
# needs re-measuring this is where to redo it.
_BLOCK_MOUNTING_HOLE_DIAMETER = 8.5
_BLOCK_MOUNTING_HOLE_YZ = [
    (219.72, -37.34),
    (167.72, -37.34),
    (167.72, 34.66),
    (219.72, 34.66),
]


def _load_shapes(doc):
    """
    Imports into the caller's own working document (not a
    separate temporary one) so as not to disturb
    App.ActiveDocument - creating and closing a second document
    changes which document is active as a side effect, which
    broke later code relying on App.ActiveDocument the first
    time this was tried. Returns (rail_shape, block_shape),
    both rotated, still in the original shared coordinate frame
    (not yet translated to any placement).
    """

    before = set(doc.Objects)
    Part.insert(IGES_FILE, doc.Name)
    imported = [o for o in doc.Objects if o not in before and hasattr(o, "Shape")]

    rail_obj = min(imported, key=lambda o: len(o.Shape.Faces))
    block_obj = max(imported, key=lambda o: len(o.Shape.Faces))

    rail_shape = rail_obj.Shape.copy()
    block_shape = block_obj.Shape.copy()
    for shape in (rail_shape, block_shape):
        shape.rotate(App.Vector(0, 0, 0), App.Vector(1, 1, 1), -120)

    for o in imported:
        doc.removeObject(o.Name)

    return rail_shape, block_shape


def make_segments(doc, name_prefix, count, x, y, z):
    """
    Places `count` real 200mm rail segments end to end, starting
    at (x, y, z): x is the mounting-face position (rail extends
    further toward +x from there), y is the start of the first
    segment's length (each subsequent segment continues at
    y + n*SEGMENT_LENGTH), z is the rail's own width centreline.
    """

    rail_shape, _ = _load_shapes(doc)
    bb = rail_shape.BoundBox

    segments = []
    for i in range(count):
        shape = rail_shape.copy()
        shape.translate(App.Vector(
            x - bb.XMin,
            y - bb.YMin + i * SEGMENT_LENGTH,
            z - (bb.ZMin + bb.ZMax) / 2))
        obj = doc.addObject("Part::Feature", f"{name_prefix}{i + 1}")
        obj.Shape = shape
        segments.append(obj)

    return segments


def make_block(doc, name, segment_index, x, y, z):
    """
    Places the carriage block centred on the given rail segment
    index (0-based, matching make_segments' own numbering) - (x,
    y, z) must be the exact same arguments passed to
    make_segments, so the block lines up on the same rail run.
    """

    rail_shape, block_shape = _load_shapes(doc)
    bb = rail_shape.BoundBox

    shape = block_shape.copy()
    shape.translate(App.Vector(
        x - bb.XMin,
        y - bb.YMin + segment_index * SEGMENT_LENGTH,
        z - (bb.ZMin + bb.ZMax) / 2))
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    return obj


def make_mounting_plate(doc, name, thickness, segment_index, x, y, z):
    """
    Flat plate on top of the block, same overall (Y, Z) size as
    the block's own bounding box and the same 4 mounting holes,
    `thickness` mm thick, flush against the block's own top
    (mounting) face. (x, y, z) must be the same arguments passed
    to make_segments/make_block so it lines up on the same rail
    run and block.

    The plate is centred on the 4 holes' own centre, not the
    block's raw bounding box - the block's real shape isn't
    symmetric about its bounding box (its Y centre is 5.7mm off
    from the holes' own centre, Z is already symmetric), which
    first showed up as a visibly uneven edge margin between the
    two sides once built and viewed.
    """

    rail_shape, block_shape = _load_shapes(doc)
    rail_bb = rail_shape.BoundBox
    block_bb = block_shape.BoundBox

    offset = App.Vector(
        x - rail_bb.XMin,
        y - rail_bb.YMin + segment_index * SEGMENT_LENGTH,
        z - (rail_bb.ZMin + rail_bb.ZMax) / 2)

    hole_y_center = sum(hy for hy, hz in _BLOCK_MOUNTING_HOLE_YZ) / len(_BLOCK_MOUNTING_HOLE_YZ)
    hole_z_center = sum(hz for hy, hz in _BLOCK_MOUNTING_HOLE_YZ) / len(_BLOCK_MOUNTING_HOLE_YZ)

    plate_x = block_bb.XMax + offset.x
    plate_y = hole_y_center - block_bb.YLength / 2 + offset.y
    plate_z = hole_z_center - block_bb.ZLength / 2 + offset.z

    body = Part.makeBox(thickness, block_bb.YLength, block_bb.ZLength,
                         App.Vector(plate_x, plate_y, plate_z))

    hole_r = _BLOCK_MOUNTING_HOLE_DIAMETER / 2
    for hy, hz in _BLOCK_MOUNTING_HOLE_YZ:
        hole = Part.makeCylinder(hole_r, thickness + 2, App.Vector(plate_x - 1, hy + offset.y, hz + offset.z),
                                  App.Vector(1, 0, 0))
        body = body.cut(hole)

    obj = doc.addObject("Part::Feature", name)
    obj.Shape = body
    return obj
