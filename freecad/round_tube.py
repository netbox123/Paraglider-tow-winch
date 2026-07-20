"""
round_tube.py

Version 0.0.1
Creates one hollow round tube (pipe).

(x, y, z) is the base/bottom-most point of the tube, on its
own axis - analogous to tube.py's "min corner" convention for
square tube, but for a round cross-section there's no corner,
just the axis start point.
"""

import FreeCAD as App
import Part


def make(doc, name, length, outer_diameter, wall, axis="Z", x=0, y=0, z=0):

    outer_r = outer_diameter / 2
    inner_r = outer_r - wall

    outside = Part.makeCylinder(outer_r, length)
    inside = Part.makeCylinder(inner_r, length + 2)
    inside.translate(App.Vector(0, 0, -1))

    tube = outside.cut(inside)

    obj = doc.addObject("Part::Feature", name)
    obj.Shape = tube

    if axis == "Z":
        obj.Placement.Base = App.Vector(x, y, z)

    elif axis == "X":
        obj.Placement.Rotation = App.Rotation(App.Vector(0, 1, 0), 90)
        obj.Placement.Base = App.Vector(x, y, z)

    elif axis == "Y":
        obj.Placement.Rotation = App.Rotation(App.Vector(1, 0, 0), -90)
        obj.Placement.Base = App.Vector(x, y, z)

    return obj
