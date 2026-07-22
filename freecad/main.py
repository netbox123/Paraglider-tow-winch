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
import hwin30_rail
import loadcell

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
importlib.reload(hwin30_rail)
importlib.reload(loadcell)

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

# 4 short reinforcement tubes framing the bearing, 2x2
# (upper-left/right, lower-left/right), each running parallel
# to the pipe (X). They sit INSIDE the frame, flush with the
# FAR (outer) face of the existing 700mm frame tubes
# (TW_CrossRearTop / TW_IntakeMountTube - they share the same
# X range, L-T to L) and extending further into the frame from
# there - not overlapping through those tubes' own 50mm depth,
# and not outward toward the bearing/pipe side either (that
# would collide with the bearing housing and its mounting
# plate, both of which sit outside the frame at X >= L).
# Centred on the pipe's own centreline (intake_cy, intake_cz)
# in Y/Z. 50mm clear gap between the top pair and bottom pair
# (vertical); 100mm clear gap between the inside faces of the
# left and right tubes (horizontal). Uses tube.py as-is since
# the main frame's own tube size (50x50x4,
# config.TUBE_SIZE/TUBE_WALL) already matches what's needed
# here.
INTAKE_REINFORCEMENT_LENGTH = 300.0
INTAKE_REINFORCEMENT_V_GAP = 50.0
INTAKE_REINFORCEMENT_H_GAP = 120.0

reinforcement_x = L - config.TUBE_SIZE - INTAKE_REINFORCEMENT_LENGTH

intake_reinforcement_tubes = []
for y_sign, z_sign, name in (
    (1, 1, "TW_IntakeReinforceUpperRight"),
    (-1, 1, "TW_IntakeReinforceUpperLeft"),
    (1, -1, "TW_IntakeReinforceLowerRight"),
    (-1, -1, "TW_IntakeReinforceLowerLeft"),
):
    if y_sign > 0:
        y = intake_cy + INTAKE_REINFORCEMENT_H_GAP / 2
    else:
        y = intake_cy - INTAKE_REINFORCEMENT_H_GAP / 2 - config.TUBE_SIZE
    if z_sign > 0:
        z = intake_cz + INTAKE_REINFORCEMENT_V_GAP / 2
    else:
        z = intake_cz - INTAKE_REINFORCEMENT_V_GAP / 2 - config.TUBE_SIZE
    intake_reinforcement_tubes.append(
        tube.make(doc, name, INTAKE_REINFORCEMENT_LENGTH, axis="X",
                  x=reinforcement_x, y=y, z=z))

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

# 2 line-cutter guide tubes, crosswise to the round intake pipe
# but horizontal (Y-axis, same direction as TW_CrossRearTop /
# TW_IntakeMountTube) rather than vertical - one from each side,
# each stopping exactly 20mm off the pipe's own centreline, which
# is exactly the pipe's own radius (config.INTAKE_PIPE_DIAMETER/2
# = 20mm) - so they come right up to the pipe's outer surface
# without overlapping it, leaving the middle clear for the rope
# to pass. X depth moved inward, clear of the inside bearing
# (bearing_inside_bb) rather than flush with the reinforcement
# tubes' outer edge, which would have collided with it.
# short_cutting_pipe reaches out to the outer (far) edge of the
# left reinforcement tube pair; long_cutting_pipe is a fixed
# 300mm reaching out from the pipe's surface on the right.
cutting_pipe_x = bearing_inside_bb.XMin - config.TUBE_SIZE - 10.0
cutting_pipe_z = intake_cz - config.TUBE_SIZE / 2
pipe_r = config.INTAKE_PIPE_DIAMETER / 2

left_reinforcement_tube_outer_y = intake_cy - INTAKE_REINFORCEMENT_H_GAP / 2 - config.TUBE_SIZE
short_cutting_pipe_y = left_reinforcement_tube_outer_y
short_cutting_pipe_length = (intake_cy - pipe_r) - short_cutting_pipe_y
short_cutting_pipe = tube.make(doc, "TW_ShortCuttingPipe", short_cutting_pipe_length, axis="Y",
                                x=cutting_pipe_x, y=short_cutting_pipe_y, z=cutting_pipe_z)

# End caps for the short pipe - the "anvil" side of the line
# cutter, closed off at both ends. 42x42x4mm plates fit snugly
# inside the tube's own hollow bore (50mm outer - 2x4mm wall =
# 42mm inner), welded in flush with each end, extending 4mm
# inward (matching TUBE_WALL) from the outer face.
short_pipe_bb = short_cutting_pipe.Shape.BoundBox
cap_inset = config.TUBE_SIZE - 2 * config.TUBE_WALL
short_cap_x = short_pipe_bb.XMin + config.TUBE_WALL
short_cap_z = short_pipe_bb.ZMin + config.TUBE_WALL

short_cutting_pipe_cap_far = doc.addObject("Part::Box", "TW_ShortCuttingPipeCapFar")
short_cutting_pipe_cap_far.Length = cap_inset
short_cutting_pipe_cap_far.Width = config.TUBE_WALL
short_cutting_pipe_cap_far.Height = cap_inset
short_cutting_pipe_cap_far.Placement.Base = App.Vector(short_cap_x, short_pipe_bb.YMin, short_cap_z)

short_cutting_pipe_cap_near = doc.addObject("Part::Box", "TW_ShortCuttingPipeCapNear")
short_cutting_pipe_cap_near.Length = cap_inset
short_cutting_pipe_cap_near.Width = config.TUBE_WALL
short_cutting_pipe_cap_near.Height = cap_inset
short_cutting_pipe_cap_near.Placement.Base = App.Vector(
    short_cap_x, short_pipe_bb.YMax - config.TUBE_WALL, short_cap_z)

LONG_CUTTING_PIPE_LENGTH = 300.0
long_cutting_pipe_y = intake_cy + pipe_r
long_cutting_pipe = tube.make(doc, "TW_LongCuttingPipe", LONG_CUTTING_PIPE_LENGTH, axis="Y",
                               x=cutting_pipe_x, y=long_cutting_pipe_y, z=cutting_pipe_z)

# First pair of 4 intake rollers - the 2 closest to the line
# cutter, running parallel to the cutting pipes (Y-axis), 2mm
# clear of them in X. 8mm axle bore, 120mm long, centred on the
# pipe's own centreline (intake_cy for their length, intake_cz
# for the up/down stack), with a 7mm gap between them for the
# rope to pass through. Diameter increased from an original 50mm
# - the roller's Z position is derived from intake_cz, and at
# 50mm the axle hole through the reinforcement tube (its own
# axle continues through and is drilled through that tube)
# landed only 3.5mm from the tube's edge. 61mm would give exactly
# the requested 5mm clearance; 63mm is used instead as a real
# orderable stock pipe size, giving slightly more (6mm) rather
# than less.
ROLLER_DIAMETER = 63.0
ROLLER_AXLE_DIAMETER = 8.0
ROLLER_LENGTH = 120.0
ROLLER_LINE_GAP = 7.0
roller_r = ROLLER_DIAMETER / 2

roller_cutter_x = cutting_pipe_x - 2.0 - roller_r
roller_cutter_y_start = intake_cy - ROLLER_LENGTH / 2
roller_cutter_z_top = intake_cz + ROLLER_LINE_GAP / 2 + roller_r
roller_cutter_z_bottom = intake_cz - ROLLER_LINE_GAP / 2 - roller_r


def make_roller(doc, name, cx, y_start, cz):
    axis = App.Vector(0, 1, 0)
    base = App.Vector(cx, y_start, cz)
    body = Part.makeCylinder(roller_r, ROLLER_LENGTH, base, axis)
    bore = Part.makeCylinder(ROLLER_AXLE_DIAMETER / 2, ROLLER_LENGTH + 2,
                              base - axis, axis)
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = body.cut(bore)
    return obj


roller_cutter_top = make_roller(doc, "TW_IntakeRollerCutterTop",
                                 roller_cutter_x, roller_cutter_y_start, roller_cutter_z_top)
roller_cutter_bottom = make_roller(doc, "TW_IntakeRollerCutterBottom",
                                    roller_cutter_x, roller_cutter_y_start, roller_cutter_z_bottom)

# Solid 8mm axles through each roller's own bore, continuing
# through both nearby reinforcement tubes (clearance holes cut
# through each) and extending 15mm past those tubes' own outer
# faces - not just past the roller's own ends, which would stop
# short inside the tubes' solid material.
ROLLER_AXLE_OVERHANG = 15.0


def make_roller_axle_through_tubes(doc, name, cx, cz, left_tube, right_tube):
    axis = App.Vector(0, 1, 0)
    y_start = left_tube.Shape.BoundBox.YMin - ROLLER_AXLE_OVERHANG
    y_end = right_tube.Shape.BoundBox.YMax + ROLLER_AXLE_OVERHANG
    length = y_end - y_start
    shape = Part.makeCylinder(ROLLER_AXLE_DIAMETER / 2, length, App.Vector(cx, y_start, cz), axis)
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape

    hole = Part.makeCylinder(ROLLER_AXLE_DIAMETER / 2, length + 2,
                              App.Vector(cx, y_start - 1, cz), axis)
    for tube_obj in (left_tube, right_tube):
        tube_obj.Shape = tube_obj.Shape.cut(hole)

    return obj


reinforce_upper_left = doc.getObject("TW_IntakeReinforceUpperLeft")
reinforce_upper_right = doc.getObject("TW_IntakeReinforceUpperRight")
reinforce_lower_left = doc.getObject("TW_IntakeReinforceLowerLeft")
reinforce_lower_right = doc.getObject("TW_IntakeReinforceLowerRight")

roller_cutter_top_axle = make_roller_axle_through_tubes(
    doc, "TW_IntakeRollerCutterTopAxle", roller_cutter_x, roller_cutter_z_top,
    reinforce_upper_left, reinforce_upper_right)
roller_cutter_bottom_axle = make_roller_axle_through_tubes(
    doc, "TW_IntakeRollerCutterBottomAxle", roller_cutter_x, roller_cutter_z_bottom,
    reinforce_lower_left, reinforce_lower_right)

# Second pair of 4 intake rollers - vertical (Z-axis), sitting
# side by side left/right, squeezing the rope with a 7mm gap
# (same convention as the horizontal pair's own line gap). 50mm
# diameter - fits within the 120mm gap between the left/right
# reinforcement tubes' inner faces with room to spare
# ((120-7)/2 = 56.5mm available per side), confirmed by
# shrinking a test radius until collision volume hit exactly
# zero at r=25mm. But at the SAME X depth as the horizontal
# roller pair, the two pairs collide with each other instead
# (both occupy overlapping Z ranges) - so the vertical rollers
# get their own X-slice after all, on the drum side, 2mm clear
# of the horizontal rollers (same pattern as the reinforcement
# tube axles' own clearance).
VERTICAL_ROLLER_DIAMETER = 50.0
VERTICAL_ROLLER_LENGTH = 142.0
VERTICAL_ROLLER_LINE_GAP = 7.0
VERTICAL_ROLLER_X_CLEARANCE = 2.0
VERTICAL_ROLLER_AXLE_DIAMETER = 8.0
vertical_roller_r = VERTICAL_ROLLER_DIAMETER / 2

vertical_roller_z_start = intake_cz - VERTICAL_ROLLER_LENGTH / 2
vertical_roller_cx = (roller_cutter_x - roller_r) - VERTICAL_ROLLER_X_CLEARANCE - vertical_roller_r
vertical_roller_left_y = intake_cy - VERTICAL_ROLLER_LINE_GAP / 2 - vertical_roller_r
vertical_roller_right_y = intake_cy + VERTICAL_ROLLER_LINE_GAP / 2 + vertical_roller_r


def make_vertical_roller(doc, name, cx, cy, z_start):
    axis = App.Vector(0, 0, 1)
    base = App.Vector(cx, cy, z_start)
    body = Part.makeCylinder(vertical_roller_r, VERTICAL_ROLLER_LENGTH, base, axis)
    bore = Part.makeCylinder(VERTICAL_ROLLER_AXLE_DIAMETER / 2, VERTICAL_ROLLER_LENGTH + 2,
                              base - axis, axis)
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = body.cut(bore)
    return obj


vertical_roller_left = make_vertical_roller(
    doc, "TW_IntakeVerticalRollerLeft", vertical_roller_cx, vertical_roller_left_y,
    vertical_roller_z_start)
vertical_roller_right = make_vertical_roller(
    doc, "TW_IntakeVerticalRollerRight", vertical_roller_cx, vertical_roller_right_y,
    vertical_roller_z_start)

# Top and bottom mounting plates spanning both vertical rollers,
# 120 (Y) x 54 (X) x 4mm (Z, thickness), flush against the
# rollers' own top/bottom faces. 8mm axles through each roller
# continue through both plates and extend 15mm past each plate's
# outer face (142 roller + 4 + 4 plates + 15 + 15 overhang =
# 180mm total).
VERTICAL_ROLLER_PLATE_Y = 120.0
VERTICAL_ROLLER_PLATE_X = 54.0
VERTICAL_ROLLER_PLATE_THICKNESS = 4.0
VERTICAL_ROLLER_AXLE_OVERHANG = 15.0
VERTICAL_ROLLER_AXLE_LENGTH = (VERTICAL_ROLLER_LENGTH + 2 * VERTICAL_ROLLER_PLATE_THICKNESS
                                + 2 * VERTICAL_ROLLER_AXLE_OVERHANG)

vertical_roller_plate_x = vertical_roller_cx - VERTICAL_ROLLER_PLATE_X / 2
vertical_roller_plate_y = intake_cy - VERTICAL_ROLLER_PLATE_Y / 2
vertical_roller_z_top = vertical_roller_z_start + VERTICAL_ROLLER_LENGTH

vertical_roller_plate_bottom = doc.addObject("Part::Box", "TW_IntakeVerticalRollerPlateBottom")
vertical_roller_plate_bottom.Length = VERTICAL_ROLLER_PLATE_X
vertical_roller_plate_bottom.Width = VERTICAL_ROLLER_PLATE_Y
vertical_roller_plate_bottom.Height = VERTICAL_ROLLER_PLATE_THICKNESS
vertical_roller_plate_bottom.Placement.Base = App.Vector(
    vertical_roller_plate_x, vertical_roller_plate_y, vertical_roller_z_start - VERTICAL_ROLLER_PLATE_THICKNESS)

vertical_roller_plate_top = doc.addObject("Part::Box", "TW_IntakeVerticalRollerPlateTop")
vertical_roller_plate_top.Length = VERTICAL_ROLLER_PLATE_X
vertical_roller_plate_top.Width = VERTICAL_ROLLER_PLATE_Y
vertical_roller_plate_top.Height = VERTICAL_ROLLER_PLATE_THICKNESS
vertical_roller_plate_top.Placement.Base = App.Vector(
    vertical_roller_plate_x, vertical_roller_plate_y, vertical_roller_z_top)


def make_vertical_roller_axle(doc, name, cx, cy):
    axis = App.Vector(0, 0, 1)
    z_start = vertical_roller_z_start - VERTICAL_ROLLER_PLATE_THICKNESS - VERTICAL_ROLLER_AXLE_OVERHANG
    shape = Part.makeCylinder(VERTICAL_ROLLER_AXLE_DIAMETER / 2, VERTICAL_ROLLER_AXLE_LENGTH,
                               App.Vector(cx, cy, z_start), axis)
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    return obj


vertical_roller_left_axle = make_vertical_roller_axle(
    doc, "TW_IntakeVerticalRollerLeftAxle", vertical_roller_cx, vertical_roller_left_y)
vertical_roller_right_axle = make_vertical_roller_axle(
    doc, "TW_IntakeVerticalRollerRightAxle", vertical_roller_cx, vertical_roller_right_y)

# Shorten the 4 reinforcement tubes back to where the vertical
# roller mounting plate begins (its low-X, drum-facing edge) -
# they no longer need to extend all the way to their original
# start, since the plate now sits there instead.
reinforcement_tube_trim = Part.makeBox(
    vertical_roller_plate_x - reinforcement_x, 2000, 2000,
    App.Vector(reinforcement_x, -1000, -1000))
for tube_obj in intake_reinforcement_tubes:
    tube_obj.Shape = tube_obj.Shape.cut(reinforcement_tube_trim)

# Cover plate on the drum side of the 4 trimmed reinforcement
# tubes - 220 (Y) x 150 (Z) x 4mm, matching the tubes' own outer
# envelope exactly (Y 290-510, Z 650-800), with a 120 (Y) x 50
# (Z) hole cut through the middle matching the existing gap
# between the 4 tubes (Y 340-460, Z 700-750), so the rope/roller
# mechanism still has clearance while each tube end is capped.
REINFORCEMENT_COVER_Y = 220.0
REINFORCEMENT_COVER_Z = 150.0
REINFORCEMENT_COVER_THICKNESS = 4.0
REINFORCEMENT_COVER_HOLE_Y = 120.0
REINFORCEMENT_COVER_HOLE_Z = 50.0

reinforcement_cover = doc.addObject("Part::Feature", "TW_IntakeReinforcementCover")
cover_body = Part.makeBox(
    REINFORCEMENT_COVER_THICKNESS, REINFORCEMENT_COVER_Y, REINFORCEMENT_COVER_Z,
    App.Vector(vertical_roller_plate_x - REINFORCEMENT_COVER_THICKNESS,
               intake_cy - REINFORCEMENT_COVER_Y / 2, intake_cz - REINFORCEMENT_COVER_Z / 2))
cover_hole = Part.makeBox(
    REINFORCEMENT_COVER_THICKNESS + 2, REINFORCEMENT_COVER_HOLE_Y, REINFORCEMENT_COVER_HOLE_Z,
    App.Vector(vertical_roller_plate_x - REINFORCEMENT_COVER_THICKNESS - 1,
               intake_cy - REINFORCEMENT_COVER_HOLE_Y / 2, intake_cz - REINFORCEMENT_COVER_HOLE_Z / 2))
reinforcement_cover.Shape = cover_body.cut(cover_hole)

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
                       intake_pipe] + list(wheel_bracket_parts.values()) + intake_reinforcement_tubes + \
                      [short_cutting_pipe, long_cutting_pipe,
                       short_cutting_pipe_cap_far, short_cutting_pipe_cap_near,
                       roller_cutter_top, roller_cutter_bottom,
                       roller_cutter_top_axle, roller_cutter_bottom_axle,
                       vertical_roller_left, vertical_roller_right,
                       vertical_roller_plate_bottom, vertical_roller_plate_top,
                       vertical_roller_left_axle, vertical_roller_right_axle,
                       reinforcement_cover]

# ------------------------------------------------------
# Winding mechanism (level wind / diamond screw) - just
# starting out. First piece: a guide rail tube stacked
# directly on top of TW_CrossFrontTop (same 700mm length,
# same X/Y position, sitting flush on its top face at z=H).
# ------------------------------------------------------

winding_rail = tube.make(doc, "TW_WindingRail", W - 2 * T, axis="Y", x=0, y=T, z=H - 100)

# HWIN HGW30 linear guide rail, mounted on the winding rail
# tube's face pointing toward the intake (its higher-X face) -
# 3 real 200mm segments end to end (600mm total), centred
# within the tube's own 700mm length, on the tube's own Z
# centreline.
winding_rail_bb = winding_rail.Shape.BoundBox
HWIN_RAIL_SEGMENT_COUNT = 3
hwin_rail_x = winding_rail_bb.XMax
hwin_rail_z = (winding_rail_bb.ZMin + winding_rail_bb.ZMax) / 2
hwin_rail_y = winding_rail_bb.YMin + (winding_rail_bb.YLength
                                       - HWIN_RAIL_SEGMENT_COUNT * hwin30_rail.SEGMENT_LENGTH) / 2

hwin_rail_segments = hwin30_rail.make_segments(
    doc, "TW_HwinRailSegment", HWIN_RAIL_SEGMENT_COUNT, hwin_rail_x, hwin_rail_y, hwin_rail_z)

# Carriage block, centred on the middle rail segment (index 1
# of 0/1/2) - same (x, y, z) args as make_segments so it lines
# up on the same rail run.
hwin_block = hwin30_rail.make_block(
    doc, "TW_HwinBlock", 1, hwin_rail_x, hwin_rail_y, hwin_rail_z)

# Mounting plate on top of the block - same footprint and same
# 4 mounting holes as the block itself, 10mm thick.
hwin_mounting_plate = hwin30_rail.make_mounting_plate(
    doc, "TW_HwinMountingPlate", 10.0, 1, hwin_rail_x, hwin_rail_y, hwin_rail_z)

# Load cell, centred on the mounting plate, flange face flush
# against the plate's own top face - clearance hole drilled
# through the plate's centre matching the load cell's own M16
# centre hole, for whatever rod/bolt connects through it.
plate_bb = hwin_mounting_plate.Shape.BoundBox
loadcell_cy = (plate_bb.YMin + plate_bb.YMax) / 2
loadcell_cz = (plate_bb.ZMin + plate_bb.ZMax) / 2

plate_centre_hole = Part.makeCylinder(
    loadcell.CENTRE_HOLE_DIAMETER / 2, plate_bb.XLength + 2,
    App.Vector(plate_bb.XMin - 1, loadcell_cy, loadcell_cz), App.Vector(1, 0, 0))
hwin_mounting_plate.Shape = hwin_mounting_plate.Shape.cut(plate_centre_hole)

hwin_loadcell = loadcell.make(doc, "TW_LoadCell", cy=loadcell_cy, cz=loadcell_cz, x=plate_bb.XMax)

winding_group = doc.addObject("App::DocumentObjectGroup", "winding_group")
winding_group.Group = [winding_rail] + hwin_rail_segments + \
    [hwin_block, hwin_mounting_plate, hwin_loadcell]

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