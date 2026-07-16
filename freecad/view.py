import FreeCADGui as Gui

def reset():

    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.ActiveDocument.ActiveView.setCameraType("Perspective")
    Gui.SendMsgToActiveView("ViewFit")