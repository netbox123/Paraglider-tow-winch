"""
tube.py

Version 0.0.1
Creates one hollow square tube.
"""

import FreeCAD as App
import Part
import config


def make(doc, name, length, axis="X", x=0, y=0, z=0):

    T = config.TUBE_SIZE
    W = config.TUBE_WALL

    # Outside
    outside = Part.makeBox(length, T, T)

    # Inside
    inside = Part.makeBox(length + 2, T - 2 * W, T - 2 * W)
    inside.translate(App.Vector(-1, W, W))

    tube = outside.cut(inside)

    obj = doc.addObject("Part::Feature", name)
    obj.Shape = tube

    if axis == "X":
        obj.Placement.Base = App.Vector(x, y, z)

    elif axis == "Y":
        obj.Placement.Rotation = App.Rotation(App.Vector(0, 0, 1), 90)
        obj.Placement.Base = App.Vector(x, y, z)

    elif axis == "Z":
        obj.Placement.Rotation = App.Rotation(App.Vector(0, 1, 0), -90)
        obj.Placement.Base = App.Vector(x, y, z)

    return obj