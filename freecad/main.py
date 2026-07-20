import FreeCAD as App
import importlib

import config
import frame
import tube
import view
import mitres
import battery_box
import drum
import bearing50

importlib.reload(config)
importlib.reload(frame)
importlib.reload(tube)
importlib.reload(view)
importlib.reload(mitres)
importlib.reload(battery_box)
importlib.reload(drum)
importlib.reload(bearing50)

importlib.reload(frame)

try:
    App.closeDocument("TowWinch")
except:
    pass

doc = App.newDocument("TowWinch")

frame.make(doc)

# ------------------------------------------------------
# Battery boxes: flush against the inside face of the
# rear frame and the outer boundary of the right side
# frame, stacked 2 high, resting on top of the bottom
# rail. The open side frame has no material between the
# rails, so sitting flush with the outer boundary is
# fine and leaves more clearance in front of the packs.
# ------------------------------------------------------

L = config.FRAME_LENGTH
W = config.FRAME_WIDTH
T = config.TUBE_SIZE

battery_x = L - T - config.BATTERY_WIDTH
battery_y = W - config.BATTERY_LENGTH

battery_box.make(doc, "TW_Battery1", x=battery_x, y=battery_y, z=T, rotate=True)
battery_box.make(doc, "TW_Battery2", x=battery_x, y=battery_y, z=T + config.BATTERY_HEIGHT, rotate=True)

# ------------------------------------------------------
# Drum group: drum, shaft bearings and their 4 mounting
# posts. drum_cx is driven by config.DRUM_TO_FRONT_BOUNDARY
# so the whole group can be shifted forward/back later by
# changing a single number. Centred in Y (frame width),
# flange bottom 50 mm above the bottom border.
# ------------------------------------------------------

H = config.FRAME_HEIGHT
flange_r = config.DRUM_FLANGE_DIAMETER / 2

drum_cx = config.DRUM_TO_FRONT_BOUNDARY + flange_r
drum_y  = (W - config.SHAFT_LENGTH) / 2
drum_cz = 50 + flange_r

drum_parts = drum.make(doc, cx=drum_cx, cz=drum_cz, y=drum_y)

bearing1 = bearing50.make(doc, "TW_Bearing1", cx=drum_cx, cz=drum_cz, y=drum_y, flip=False)
bearing2 = bearing50.make(doc, "TW_Bearing2", cx=drum_cx, cz=drum_cz, y=drum_y + config.SHAFT_LENGTH, flip=True)

# Bearing mounting posts: 2 tubes side by side (50x100
# combined) on each side frame, between the top and bottom
# rails. The two pipes of each pair meet exactly on the
# axle centreline, so the pair as a whole is centred on it.

post_height = H - 2 * T

post1 = tube.make(doc, "TW_RightBearingPostFront", post_height, axis="Z",
                   x=drum_cx - T, y=W - T, z=T)
post2 = tube.make(doc, "TW_RightBearingPostRear", post_height, axis="Z",
                   x=drum_cx, y=W - T, z=T)
post3 = tube.make(doc, "TW_LeftBearingPostFront", post_height, axis="Z",
                   x=drum_cx - T, y=0, z=T)
post4 = tube.make(doc, "TW_LeftBearingPostRear", post_height, axis="Z",
                   x=drum_cx, y=0, z=T)

drum_group = doc.addObject("App::DocumentObjectGroup", "drum_group")
drum_group.Group = list(drum_parts.values()) + [bearing1, bearing2, post1, post2, post3, post4]

# Update the document
doc.recompute()

view.reset()