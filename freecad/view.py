import FreeCADGui as Gui

def reset():

    if getattr(Gui, "ActiveDocument", None) is None:
        return

    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.ActiveDocument.ActiveView.setCameraType("Perspective")
    Gui.SendMsgToActiveView("ViewFit")