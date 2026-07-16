"""
===========================================================
Open Paraglider Tow Winch

Frame Generator

Version : 0.0.4

Frame:
2 welded side frames
connected by 4 cross members

1500 x 800 x 800 mm
50x50 mm tubing

===========================================================
"""

import FreeCAD as App
import config


# ----------------------------------------------------------
# Helper
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

    print("Creating frame...")

    L = config.FRAME_LENGTH      # 1500
    W = config.FRAME_WIDTH       # 800
    H = config.FRAME_HEIGHT      # 800

    T = config.TUBE_SIZE         # 50

    # ======================================================
    # LEFT SIDE FRAME
    # ======================================================

    beam_x(doc, "Left_Bottom", 0, 0, 0, L)
    beam_x(doc, "Left_Top",    0, 0, H-T, L)

    beam_z(doc, "Left_Front", 0, 0, T, H-2*T)
    beam_z(doc, "Left_Rear",  L-T, 0, T, H-2*T)

    # ======================================================
    # RIGHT SIDE FRAME
    # ======================================================

    beam_x(doc, "Right_Bottom", 0, W-T, 0, L)
    beam_x(doc, "Right_Top",    0, W-T, H-T, L)

    beam_z(doc, "Right_Front", 0, W-T, T, H-2*T)
    beam_z(doc, "Right_Rear",  L-T, W-T, T, H-2*T)

    # ======================================================
    # CONNECTING TUBES
    # ======================================================

    beam_y(doc, "Cross_Front_Bottom",
           0, T, 0,
           W-2*T)

    beam_y(doc, "Cross_Rear_Bottom",
           L-T, T, 0,
           W-2*T)

    beam_y(doc, "Cross_Front_Top",
           0, T, H-T,
           W-2*T)

    beam_y(doc, "Cross_Rear_Top",
           L-T, T, H-T,
           W-2*T)

    doc.recompute()

    print("Frame finished.")