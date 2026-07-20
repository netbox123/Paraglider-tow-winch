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
import motor
import sprocket

importlib.reload(config)
importlib.reload(frame)
importlib.reload(tube)
importlib.reload(view)
importlib.reload(mitres)
importlib.reload(battery_box)
importlib.reload(drum)
importlib.reload(bearing50)
importlib.reload(motor)
importlib.reload(sprocket)

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

# Bearing mounting posts: 2 tubes on each side frame,
# between the top and bottom rails, separated by
# BEARING_POST_GAP and centred on the axle centreline -
# leaves room to drill the bearing bolt holes clear of the
# seam between the tubes.

post_height = H - 2 * T
post_half_gap = config.BEARING_POST_GAP / 2

post1 = tube.make(doc, "TW_RightBearingPostFront", post_height, axis="Z",
                   x=drum_cx - T - post_half_gap, y=W - T, z=T)
post2 = tube.make(doc, "TW_RightBearingPostRear", post_height, axis="Z",
                   x=drum_cx + post_half_gap, y=W - T, z=T)
post3 = tube.make(doc, "TW_LeftBearingPostFront", post_height, axis="Z",
                   x=drum_cx - T - post_half_gap, y=0, z=T)
post4 = tube.make(doc, "TW_LeftBearingPostRear", post_height, axis="Z",
                   x=drum_cx + post_half_gap, y=0, z=T)

drum_group = doc.addObject("App::DocumentObjectGroup", "drum_group")
drum_group.Group = list(drum_parts.values()) + [bearing1, bearing2, post1, post2, post3, post4]

# ------------------------------------------------------
# Motor group: QS165 motor + 14T sprocket, front zone,
# resting MOTOR_REST_HEIGHT above the bottom rail. Motor
# mount bracket not modelled yet - no dimensioned drawing
# available, only reference photos.
#
# motor_y is fixed via config.MOTOR_SHAFT_Y, independent of
# DRUM_WIDTH, so the motor doesn't move if the drum changes
# size. The future axle_sprocket needs to be coplanar with
# it (same Y) for the chain.
# ------------------------------------------------------

motor_cx = config.MOTOR_SHAFT_X
motor_cz = config.MOTOR_REST_HEIGHT + motor.BELOW_SHAFT_Z
motor_y  = config.MOTOR_SHAFT_Y

motor_obj = motor.make(doc, "TW_Motor", cx=motor_cx, cz=motor_cz, y=motor_y)
sprocket_obj = sprocket.make(doc, "TW_MotorSprocket", cx=motor_cx, cz=motor_cz, y=motor_y)

motor_group = doc.addObject("App::DocumentObjectGroup", "motor_group")
motor_group.Group = [motor_obj, sprocket_obj]

# Update the document
doc.recompute()

view.reset()