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
import Part
import FreeCAD as App
import config
import mitres
import tube


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
	# All 4 tubes are hollow and mitred 45 degrees at both
	# ends, meeting at the 4 true corners of the 800x800
	# side frame.

    leftBottom = tube.make(doc, "TW_LeftBottom", L, axis="X", x=0, y=0, z=0)
    leftBottom = mitres.mitre_x_bottom(doc, leftBottom, "TW_LeftBottom_Start", 0, 0, 0)
    leftBottom = mitres.mitre_x_bottom(doc, leftBottom, "TW_LeftBottom_End", L, 0, 0)

    leftTop = tube.make(doc, "TW_LeftTop", L, axis="X", x=0, y=0, z=H - T)
    leftTop = mitres.mitre_x_start(doc, leftTop, "TW_LeftTop_Start", 0, 0, H - T)
    leftTop = mitres.mitre_x_end(doc, leftTop, "TW_LeftTop_End", L, 0, H - T)

    leftFront = tube.make(doc, "TW_LeftFront", H, axis="Z", x=0, y=0, z=0)
    leftFront = mitres.mitre_z_front(doc, leftFront, "TW_LeftFront_Bottom", 0, 0, 0)
    leftFront = mitres.mitre_z_front(doc, leftFront, "TW_LeftFront_Top", 0, 0, H)

    leftRear = tube.make(doc, "TW_LeftRear", H, axis="Z", x=L - T, y=0, z=0)
    leftRear = mitres.mitre_z_rear(doc, leftRear, "TW_LeftRear_Bottom", L - T, 0, 0)
    leftRear = mitres.mitre_z_rear(doc, leftRear, "TW_LeftRear_Top", L - T, 0, H)

    # ======================================================
    # Right side frame
    # ======================================================
    # Mirror of the left side frame at y = W - T.

    rightBottom = tube.make(doc, "TW_RightBottom", L, axis="X", x=0, y=W - T, z=0)
    rightBottom = mitres.mitre_x_bottom(doc, rightBottom, "TW_RightBottom_Start", 0, W - T, 0)
    rightBottom = mitres.mitre_x_bottom(doc, rightBottom, "TW_RightBottom_End", L, W - T, 0)

    rightTop = tube.make(doc, "TW_RightTop", L, axis="X", x=0, y=W - T, z=H - T)
    rightTop = mitres.mitre_x_start(doc, rightTop, "TW_RightTop_Start", 0, W - T, H - T)
    rightTop = mitres.mitre_x_end(doc, rightTop, "TW_RightTop_End", L, W - T, H - T)

    rightFront = tube.make(doc, "TW_RightFront", H, axis="Z", x=0, y=W - T, z=0)
    rightFront = mitres.mitre_z_front(doc, rightFront, "TW_RightFront_Bottom", 0, W - T, 0)
    rightFront = mitres.mitre_z_front(doc, rightFront, "TW_RightFront_Top", 0, W - T, H)

    rightRear = tube.make(doc, "TW_RightRear", H, axis="Z", x=L - T, y=W - T, z=0)
    rightRear = mitres.mitre_z_rear(doc, rightRear, "TW_RightRear_Bottom", L - T, W - T, 0)
    rightRear = mitres.mitre_z_rear(doc, rightRear, "TW_RightRear_Top", L - T, W - T, H)

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