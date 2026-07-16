import FreeCAD as App
import importlib
import view
import frame

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