"""
===========================================================
Open Paraglider Tow Winch

Frame Generator

Creates the steel frame.

Version : 0.0.2
===========================================================
"""

import FreeCAD as App
import Part
import config


def make_tube(doc, name, length, x, y, z):
    """
    Create one solid square tube.
    (Version 0.0.2 uses a solid bar.
    Later this will become a hollow 50x50x4 tube.)
    """

    tube = Part.makeBox(
        length,
        config.TUBE_SIZE,
        config.TUBE_SIZE
    )

    obj = doc.addObject("Part::Feature", name)
    obj.Shape = tube
    obj.Placement.Base = App.Vector(x, y, z)

    return obj


def make(doc):
    """
    Create the frame.
    """

    # Left lower rail

    make_tube(
        doc,
        "TW_LeftBottom",
        config.FRAME_LENGTH,
        0,
        0,
        0
    )

    doc.recompute()