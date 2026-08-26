import os
import sys

# FreeCAD's configured macro path can end up ahead of this
# script's own directory in sys.path, which would otherwise
# resolve "config"/"frame" to the unrelated modules under
# freecad/ (a name collision, not a real dependency on that
# other project). Force this directory first.
_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)
for _mod in ("config", "frame"):
    if _mod in sys.modules and _here not in getattr(sys.modules[_mod], "__file__", ""):
        del sys.modules[_mod]

import FreeCAD as App
import importlib

import config
import frame

importlib.reload(config)
importlib.reload(frame)

try:
    App.closeDocument("GigaDisplayHolder")
except Exception:
    pass

doc = App.newDocument("GigaDisplayHolder")

frame_obj = frame.make(doc)

doc.recompute()

bb = frame_obj.Shape.BoundBox
print("GigaFrame BoundBox:", bb)
print("Length x Width x Height:", bb.XLength, bb.YLength, bb.ZLength)
print("Volume (mm3):", frame_obj.Shape.Volume)
print("Is valid solid:", frame_obj.Shape.isValid())

doc.saveAs(os.path.join(_here, "GigaDisplayHolder.FCStd"))
frame_obj.Shape.exportStl(os.path.join(_here, "giga_display_frame.stl"))
print("Saved GigaDisplayHolder.FCStd and giga_display_frame.stl")
