"""
===========================================================
Open Paraglider Tow Winch

Module : battery_box.py

Version : 0.0.1

EEL 48V 16S battery box (DIY box, 300A BMS, Seplos BMS).

Source:
https://eelbattery.myshopify.com/products/eel-48v-16s-battery-diy-box-with-300a-bluetooth-smart-v3-0-seplos-bms-for-energy-storage

Outer dimensions: 730 x 415 x 263 mm (L x W x H), ~29 kg each.
Placeholder envelope only - no mounting holes or internal
detail yet (not published by the manufacturer).

===========================================================
"""

import Part
import FreeCAD as App
import config


def make(doc, name, x=0, y=0, z=0, rotate=False):

    obj = doc.addObject("Part::Box", name)

    if rotate:
        # 730 mm dimension runs along Y, 415 mm along X.
        obj.Length = config.BATTERY_WIDTH
        obj.Width  = config.BATTERY_LENGTH
    else:
        # 730 mm dimension runs along X, 415 mm along Y.
        obj.Length = config.BATTERY_LENGTH
        obj.Width  = config.BATTERY_WIDTH

    obj.Height = config.BATTERY_HEIGHT

    obj.Placement.Base = App.Vector(x, y, z)

    return obj
