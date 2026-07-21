import FreeCAD as App
import Part
import importlib

import config
import frame
import tube
import view
import mitres
import battery_box
import drum
import bearing50
import bearing40
import motor
import sprocket
import round_tube
import guide_wheel
import wheel_bracket

importlib.reload(config)
importlib.reload(frame)
importlib.reload(tube)
importlib.reload(view)
importlib.reload(mitres)
importlib.reload(battery_box)
importlib.reload(drum)
importlib.reload(bearing50)
importlib.reload(bearing40)
importlib.reload(motor)
importlib.reload(sprocket)
importlib.reload(round_tube)
importlib.reload(guide_wheel)
importlib.reload(wheel_bracket)

importlib.reload(frame)

def drill_x(doc, obj, name, cy, cz, diameter, x_min, x_max):
    """Cut a round clearance hole through obj, along X, so a
    rotating pipe can pass through a stationary member."""

    cutter_shape = Part.makeCylinder(diameter / 2, (x_max - x_min) + 2,
                                      App.Vector(x_min - 1, cy, cz), App.Vector(1, 0, 0))
    cutter = doc.addObject("Part::Feature", name + "_Cutter")
    cutter.Shape = cutter_shape

    cut = doc.addObject("Part::Cut", name)
    cut.Base = obj
    cut.Tool = cutter
    obj.Visibility = False
    cutter.Visibility = False
    return cut


try:
    App.closeDocument("TowWinch")
except:
    pass

doc = App.newDocument("TowWinch")

frame.make(doc)
frame_objects = list(doc.Objects)

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

# ------------------------------------------------------
# Rope intake: swivel bearing mounted on a plate spanning
# TW_CrossRearTop and a new brace tube 50mm below it, with
# the intake pipe horizontal along X, extending out the
# back of the frame - the whole assembly is meant to freely
# swivel about this axis so it can point toward the rope
# from any angle (left/right and up/down). Rollers/wheels
# on the bracket at the end of the pipe are a follow-up
# step.
# ------------------------------------------------------

INTAKE_PLATE_THICKNESS = 4.0
INTAKE_BRACE_GAP = 50.0
INTAKE_HOLE_DIAMETER = 50.0  # clearance hole for the pipe to spin through

intake_brace_z = (H - T) - INTAKE_BRACE_GAP - T

intake_brace = tube.make(doc, "TW_IntakeMountTube", W - 2 * T, axis="Y", x=L - T, y=T, z=intake_brace_z)

intake_x  = L + INTAKE_PLATE_THICKNESS
intake_cy = W / 2
intake_cz = (H - T) - INTAKE_BRACE_GAP / 2  # centred in the gap between the 2 frame tubes

intake_bearing = bearing40.make(doc, "TW_IntakeBearing", cy=intake_cy, cz=intake_cz, x=intake_x)

# Mounting plate: as wide as the bearing's own footprint,
# tall enough to cover both the brace tube and the existing
# cross tube.
bearing_bb = intake_bearing.Shape.BoundBox
plate_width = bearing_bb.YMax - bearing_bb.YMin

intake_plate = doc.addObject("Part::Box", "TW_IntakeMountPlate")
intake_plate.Length = INTAKE_PLATE_THICKNESS
intake_plate.Width  = plate_width
intake_plate.Height = H - intake_brace_z
intake_plate.Placement.Base = App.Vector(L, intake_cy - plate_width / 2, intake_brace_z)

# Second bearing + plate, mirrored onto the inside of the
# frame - these placeholder bearings aren't rated for
# rotating/dynamic loads on their own, so supporting the
# pipe from both sides spreads the load instead of relying
# on a single bearing to resist bending.
intake_x_inside = (L - T) - INTAKE_PLATE_THICKNESS

intake_bearing_inside = bearing40.make(doc, "TW_IntakeBearingInside", cy=intake_cy, cz=intake_cz,
                                        x=intake_x_inside, flip=True)
bearing_inside_bb = intake_bearing_inside.Shape.BoundBox

intake_plate_inside = doc.addObject("Part::Box", "TW_IntakeMountPlateInside")
intake_plate_inside.Length = INTAKE_PLATE_THICKNESS
intake_plate_inside.Width  = plate_width
intake_plate_inside.Height = H - intake_brace_z
intake_plate_inside.Placement.Base = App.Vector(intake_x_inside, intake_cy - plate_width / 2, intake_brace_z)

# Pipe: extends 10mm past whichever bearing housing ends
# further out on each side - kept short to avoid unneeded
# bending stress on the pipe. It rotates, so it needs
# clearance holes through the tube, brace and both plates
# it passes through.
pipe_x_start = bearing_inside_bb.XMin - 10
pipe_x_end   = bearing_bb.XMax + 10
pipe_diameter = config.INTAKE_PIPE_DIAMETER
hole_diameter = INTAKE_HOLE_DIAMETER

cross_rear_top = doc.getObject("TW_CrossRearTop")
crt_bb = cross_rear_top.Shape.BoundBox
drill_x(doc, cross_rear_top, "TW_CrossRearTop_Bore", intake_cy, intake_cz, hole_diameter, crt_bb.XMin, crt_bb.XMax)

brace_bb = intake_brace.Shape.BoundBox
drill_x(doc, intake_brace, "TW_IntakeMountTube_Bore", intake_cy, intake_cz, hole_diameter, brace_bb.XMin, brace_bb.XMax)

drill_x(doc, intake_plate, "TW_IntakeMountPlate_Bore", intake_cy, intake_cz, hole_diameter,
        intake_plate.Placement.Base.x, intake_plate.Placement.Base.x + INTAKE_PLATE_THICKNESS)

drill_x(doc, intake_plate_inside, "TW_IntakeMountPlateInside_Bore", intake_cy, intake_cz, hole_diameter,
        intake_plate_inside.Placement.Base.x, intake_plate_inside.Placement.Base.x + INTAKE_PLATE_THICKNESS)

intake_pipe = round_tube.make(doc, "TW_IntakePipe", pipe_x_end - pipe_x_start,
                               pipe_diameter, config.INTAKE_PIPE_WALL,
                               axis="X", x=pipe_x_start, y=intake_cy, z=intake_cz)

# Wheel bracket: provisional placement only - orientation and
# exact position will need revisiting once the roller/funnel
# section (between the pipe and this bracket) is designed.
# Near edge of the bracket (local v=+54) placed right at the
# pipe's outer end, extending further out from there. Centred
# on the pipe's own axis in both Y and Z - the bracket's own
# centre isn't at local (u=0, w=0): the u-centre sits at
# WHEEL_SPACING/2 (spans from before wheel1 to past wheel2),
# and the w-centre sits at PLATE_THICKNESS + wheel width/2
# (spans plate + wheel + plate).
wheel_bracket_parts = wheel_bracket.make(doc)
wheel_bracket_u_center = wheel_bracket.WHEEL_SPACING / 2
wheel_bracket_w_center = wheel_bracket.PLATE_THICKNESS + guide_wheel.WIDTH / 2
wheel_bracket_placement = App.Placement(
    App.Vector(pipe_x_end + 54, intake_cy - wheel_bracket_w_center, intake_cz - wheel_bracket_u_center),
    App.Rotation(App.Vector(0, 1, 0), -90))
for wb_obj in wheel_bracket_parts.values():
    wb_obj.Placement = wheel_bracket_placement

intake_group = doc.addObject("App::DocumentObjectGroup", "intake_group")
intake_group.Group = [intake_bearing, intake_plate, intake_bearing_inside, intake_plate_inside,
                       intake_pipe] + list(wheel_bracket_parts.values())

# ------------------------------------------------------
# Frame group: everything frame.make() created (including
# the hidden intermediate mitre cut/cutter objects, which
# would otherwise still clutter the top-level tree even
# though invisible). TW_CrossRearTop was later modified
# into TW_CrossRearTop_Bore by the intake drill above, so
# use that final version instead of the pre-drill original.
# ------------------------------------------------------

frame_group_objects = [
    doc.getObject("TW_CrossRearTop_Bore") if obj.Name == "TW_CrossRearTop" else obj
    for obj in frame_objects
]

frame_group = doc.addObject("App::DocumentObjectGroup", "frame_group")
frame_group.Group = frame_group_objects

# Update the document
doc.recompute()

view.reset()