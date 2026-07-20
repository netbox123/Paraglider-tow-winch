"""
===========================================================
Open Paraglider Tow Winch

Module : drum.py

Version : 0.0.1

Rope drum: hollow core barrel, two end flanges (each with
a shaft hole), and a shaft running through the centre.

The drum's rotation axis is parallel to Y (the frame width
direction). The barrel + flanges are centred along the
shaft's length, leaving equal bare shaft on each side for
the bearings.

No internal stiffener discs yet (config has
DRUM_STIFFENER_COUNT / DRUM_STIFFENER_THICKNESS for later).

===========================================================
"""

import Part
import FreeCAD as App
import config


def make(doc, cx=0, cz=0, y=0):

    T_shell   = config.DRUM_SHELL_THICKNESS
    T_flange  = config.DRUM_FLANGE_THICKNESS

    core_r    = config.DRUM_CORE_DIAMETER / 2
    flange_r  = config.DRUM_FLANGE_DIAMETER / 2
    shaft_r   = config.SHAFT_DIAMETER / 2

    width         = config.DRUM_WIDTH
    shaft_length  = config.SHAFT_LENGTH

    drum_length   = width + 2 * T_flange
    y_drum_start  = y + (shaft_length - drum_length) / 2
    y_barrel_start = y_drum_start + T_flange

    axis = App.Vector(0, 1, 0)

    # ------------------------------------------------------
    # Shaft
    # ------------------------------------------------------

    shaft = Part.makeCylinder(shaft_r, shaft_length, App.Vector(cx, y, cz), axis)
    shaft_obj = doc.addObject("Part::Feature", "TW_DrumShaft")
    shaft_obj.Shape = shaft

    # ------------------------------------------------------
    # Core barrel (hollow tube)
    # ------------------------------------------------------

    outer = Part.makeCylinder(core_r, width, App.Vector(cx, y_barrel_start, cz), axis)
    inner = Part.makeCylinder(core_r - T_shell, width + 2, App.Vector(cx, y_barrel_start - 1, cz), axis)
    barrel_obj = doc.addObject("Part::Feature", "TW_DrumBarrel")
    barrel_obj.Shape = outer.cut(inner)

    # ------------------------------------------------------
    # Flanges (with shaft hole)
    # ------------------------------------------------------

    def make_flange(name, y_pos):
        disc = Part.makeCylinder(flange_r, T_flange, App.Vector(cx, y_pos, cz), axis)
        hole = Part.makeCylinder(shaft_r, T_flange + 2, App.Vector(cx, y_pos - 1, cz), axis)
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = disc.cut(hole)
        return obj

    flange_front = make_flange("TW_DrumFlangeFront", y_drum_start)
    flange_rear  = make_flange("TW_DrumFlangeRear", y_drum_start + T_flange + width)

    return {
        "shaft": shaft_obj,
        "barrel": barrel_obj,
        "flange_front": flange_front,
        "flange_rear": flange_rear,
    }
