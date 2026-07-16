"""
===========================================================
Open Paraglider Tow Winch

Module : frame.py

Version : 0.0.4

Creates the basic frame.

Frame size:
1500 x 800 x 800 mm

===========================================================
"""

import FreeCAD as App
import config


# ----------------------------------------------------------
# Helper functions
# ----------------------------------------------------------

def beam_x(doc, name, x, y, z, length):

    obj = doc.addObject("Part::Box", name)

    obj.Length = length
    obj.Width = config.TUBE_SIZE
    obj.Height = config.TUBE_SIZE

    obj.Placement.Base = App.Vector(x, y, z)

    return obj


def beam_y(doc, name, x, y, z, length):

    obj = doc.addObject("Part::Box", name)

    obj.Length = config.TUBE_SIZE
    obj.Width = length
    obj.Height = config.TUBE_SIZE

    obj.Placement.Base = App.Vector(x, y, z)

    return obj


def beam_z(doc, name, x, y, z, length):

    obj = doc.addObject("Part::Box", name)

    obj.Length = config.TUBE_SIZE
    obj.Width = config.TUBE_SIZE
    obj.Height = length

    obj.Placement.Base = App.Vector(x, y, z)

    return obj


# ----------------------------------------------------------
# Main
# ----------------------------------------------------------

def make(doc):

    L = config.FRAME_LENGTH
    W = config.FRAME_WIDTH
    H = config.FRAME_HEIGHT
    T = config.TUBE_SIZE

    # ======================================================
    # Left side frame
    # ======================================================

    beam_x(doc, "TW_LeftBottom", 0, 0, 0, L)
    beam_x(doc, "TW_LeftTop",    0, 0, H - T, L)

    beam_z(doc, "TW_LeftFront", 0,     0, T, H - 2 * T)
    beam_z(doc, "TW_LeftRear",  L - T, 0, T, H - 2 * T)

    # ======================================================
    # Right side frame
    # ======================================================

    beam_x(doc, "TW_RightBottom", 0, W - T, 0, L)
    beam_x(doc, "TW_RightTop",    0, W - T, H - T, L)

    beam_z(doc, "TW_RightFront", 0,     W - T, T, H - 2 * T)
    beam_z(doc, "TW_RightRear",  L - T, W - T, T, H - 2 * T)

    # ======================================================
    # Connecting members (750 mm)
    # ======================================================

    beam_y(doc, "TW_CrossFrontBottom",
           0, T, 0,
           W - 2 * T)

    beam_y(doc, "TW_CrossRearBottom",
           L - T, T, 0,
           W - 2 * T)

    beam_y(doc, "TW_CrossFrontTop",
           0, T, H - T,
           W - 2 * T)

    beam_y(doc, "TW_CrossRearTop",
           L - T, T, H - T,
           W - 2 * T)

    doc.recompute()

    print("Tow winch frame created.")