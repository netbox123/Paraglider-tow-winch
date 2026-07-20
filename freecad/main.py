import FreeCAD as App
import importlib

import frame
import tube
import view
import mitres

importlib.reload(frame)
importlib.reload(tube)
importlib.reload(view)
importlib.reload(mitres)

importlib.reload(frame)

try:
    App.closeDocument("TowWinch")
except:
    pass

doc = App.newDocument("TowWinch")

frame.make(doc)

# Update the document
doc.recompute()

view.reset()