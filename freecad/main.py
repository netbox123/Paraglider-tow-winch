import FreeCAD as App
import sys
import importlib

project = "/Users/mac/Documents/GitHub/Paraglider-tow-winch/freecad"

if project not in sys.path:
    sys.path.insert(0, project)

import tube
importlib.reload(tube)

doc = App.newDocument("TubeTest")

tube.make(doc, "Tube", 1500)

doc.recompute()


import tube

doc = App.newDocument("TubeTest")

tube.make(doc, "Tube", 1500)

doc.recompute()