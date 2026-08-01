import FreeCAD as App
import Part
import importlib
import math

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
import rod_end
import pulley
import reversing_screw
import flange_bearing
import motor_mount

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
importlib.reload(rod_end)
importlib.reload(pulley)
importlib.reload(reversing_screw)
importlib.reload(flange_bearing)
importlib.reload(motor_mount)

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
battery_y = (W - config.BATTERY_LENGTH) / 2

battery_box.make(doc, "TW_Battery1", x=battery_x, y=battery_y, z=T, rotate=True)
battery_box.make(doc, "TW_Battery2", x=battery_x, y=battery_y, z=T + config.BATTERY_HEIGHT, rotate=True)

# 2 vertical stop tubes, flush against the battery boxes' own
# front (drum-facing) edge, one on each side rail - the rear
# cross tube already stops them from the other end, so this
# traps them from sliding fore/aft.
battery_stop_x = battery_x - T
battery_stop_height = config.FRAME_HEIGHT - 2 * T

battery_stop_left = tube.make(doc, "TW_BatteryStopLeft", battery_stop_height, axis="Z",
                               x=battery_stop_x, y=0, z=T)
battery_stop_right = tube.make(doc, "TW_BatteryStopRight", battery_stop_height, axis="Z",
                                x=battery_stop_x, y=W - T, z=T)

# 2 cross tubes (parallel to the drum axle, same Y-axis
# convention as TW_CrossFrontBottom/TW_CrossRearBottom) for the
# batteries to rest on directly - neither existing bottom cross
# tube actually sits under the battery footprint (X=battery_x to
# battery_x+BATTERY_WIDTH); TW_CrossRearBottom is adjacent to it,
# not underneath, so the batteries currently only touch the 2
# outer side rails. One at the battery's own front edge, one at
# its rear edge, both flush with the battery's own bottom face.
battery_cross_front = tube.make(doc, "TW_BatteryCrossFront", W - 2 * T, axis="Y",
                                 x=battery_x, y=T, z=0)
battery_cross_rear = tube.make(doc, "TW_BatteryCrossRear", W - 2 * T, axis="Y",
                                x=battery_x + config.BATTERY_WIDTH - T, y=T, z=0)

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
# Lowered 5.25mm from the original "50mm above the bottom
# border" position so the flange's own top point sits exactly
# 10mm above the winding pulley wheel's lowest point (was 15.25mm
# - measured via freecadcmd, not eyeballed).
drum_cz = 50 + flange_r - 5.25

# Each bearing sits BEARING_MOUNT_PLATE_THICKNESS further in
# from its post pair than before, to leave room for the new
# mounting plates - config.SHAFT_LENGTH itself still represents
# the fixed post-to-post span, so the physical shaft is now
# 2x BEARING_MOUNT_PLATE_THICKNESS shorter than that span.
bearing1_y = drum_y + config.BEARING_MOUNT_PLATE_THICKNESS
bearing2_y = drum_y + config.SHAFT_LENGTH - config.BEARING_MOUNT_PLATE_THICKNESS
actual_shaft_length = config.SHAFT_LENGTH - 2 * config.BEARING_MOUNT_PLATE_THICKNESS

drum_parts = drum.make(doc, cx=drum_cx, cz=drum_cz, y=bearing1_y, shaft_length=actual_shaft_length)

bearing1 = bearing50.make(doc, "TW_Bearing1", cx=drum_cx, cz=drum_cz, y=bearing1_y, flip=False)
bearing2 = bearing50.make(doc, "TW_Bearing2", cx=drum_cx, cz=drum_cz, y=bearing2_y, flip=True)

# Bearing mounting posts: 2 tubes on each side frame, between
# the top and bottom rails, separated by BEARING_POST_GAP -
# sized (config.py) so each post's own centreline lines up with
# one of the bearing's 2 real bolt-hole X-positions.

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


def _make_bearing_mount(doc, name_prefix, bearing_obj, plate_y0, front_post, rear_post, overhang_dir):
    """2 plates (config.BEARING_MOUNT_PLATE_THICKNESS thick each,
    sized to the bearing's own real footprint): an inner one
    filling the gap between the bearing's flange and its post
    pair, and an outer one flush against the post pair's own far
    face, for stiffening the posts around the bolt holes. 4 bolt
    holes drilled through both plates AND the posts at the
    bearing's own real bolt pattern, each filled with a plain
    cylindrical bolt/axle placeholder that sticks out
    config.BEARING_BOLT_OVERHANG past the OUTER plate's own far
    face.

    plate_y0 is the inner plate's own low-Y face. overhang_dir is
    -1 if the posts (and the outer plate/bolt overhang) are on
    the low-Y side of the inner plate, +1 if on the high-Y side -
    the bearing's own flange face is always on the OTHER side of
    the inner plate from the posts.
    """

    plate_thickness = config.BEARING_MOUNT_PLATE_THICKNESS
    bb = bearing_obj.Shape.BoundBox
    # front_post and rear_post share the same Y range (built with
    # the same y/height args), so either one gives the post pair's
    # own outer face position.
    post_bb_ref = front_post.Shape.BoundBox

    inner_plate_body = Part.makeBox(bb.XLength, plate_thickness, bb.ZLength,
                                     App.Vector(bb.XMin, plate_y0, bb.ZMin))

    if overhang_dir < 0:
        outer_plate_y0 = post_bb_ref.YMin - plate_thickness
    else:
        outer_plate_y0 = post_bb_ref.YMax
    outer_plate_body = Part.makeBox(bb.XLength, plate_thickness, bb.ZLength,
                                     App.Vector(bb.XMin, outer_plate_y0, bb.ZMin))

    bolt_r = config.BEARING_BOLT_DIAMETER / 2
    half_spacing = config.BEARING_BOLT_SPACING / 2
    overhang = config.BEARING_BOLT_OVERHANG

    bolt_objs = []
    bolt_index = 0
    for x_sign, post in ((-1, front_post), (1, rear_post)):
        for z_sign in (-1, 1):
            bolt_index += 1
            bx = drum_cx + x_sign * half_spacing
            bz = drum_cz + z_sign * half_spacing

            if overhang_dir < 0:
                bolt_end_y = plate_y0 + plate_thickness
                bolt_start_y = outer_plate_y0 - overhang
            else:
                bolt_start_y = plate_y0
                bolt_end_y = outer_plate_y0 + plate_thickness + overhang

            bolt_length = bolt_end_y - bolt_start_y
            hole_cyl = Part.makeCylinder(bolt_r, bolt_length + 2,
                                          App.Vector(bx, bolt_start_y - 1, bz), App.Vector(0, 1, 0))
            inner_plate_body = inner_plate_body.cut(hole_cyl)
            outer_plate_body = outer_plate_body.cut(hole_cyl)
            post.Shape = post.Shape.cut(hole_cyl)

            bolt_shape = Part.makeCylinder(bolt_r, bolt_length, App.Vector(bx, bolt_start_y, bz), App.Vector(0, 1, 0))
            bolt_obj = doc.addObject("Part::Feature", f"{name_prefix}_Bolt{bolt_index}")
            bolt_obj.Shape = bolt_shape
            bolt_objs.append(bolt_obj)

    inner_plate_obj = doc.addObject("Part::Feature", name_prefix + "_MountPlate")
    inner_plate_obj.Shape = inner_plate_body
    outer_plate_obj = doc.addObject("Part::Feature", name_prefix + "_StiffenerPlate")
    outer_plate_obj.Shape = outer_plate_body
    return inner_plate_obj, outer_plate_obj, bolt_objs


left_mount_plate, left_stiffener_plate, left_bolts = _make_bearing_mount(
    doc, "TW_LeftBearing", bearing1, drum_y, post3, post4, overhang_dir=-1)
right_mount_plate, right_stiffener_plate, right_bolts = _make_bearing_mount(
    doc, "TW_RightBearing", bearing2, bearing2_y, post1, post2, overhang_dir=1)

# ------------------------------------------------------
# Drum axle sprocket (76T, placeholder) - the motor's own chain
# connects here, 428 pitch matching TW_MotorSprocket's 14T (per
# buy_parts.md, 5.4286:1 ratio). Simplified envelope, no tooth
# profile, same convention as sprocket.py's 14T. Outer diameter
# calibrated from the REAL 14T sprocket's own addendum (61mm OD
# vs its 56.6mm theoretical pitch diameter = 2.2mm addendum per
# side) rather than naively scaling the 14T's OD ratio - tooth
# height above the pitch circle is set by the chain pitch, not
# tooth count, so addendum stays ~constant across sprocket sizes
# for the same #428 chain (311.64mm OD here, not a proportional
# 331mm). Bore uses the drum shaft's real 50mm diameter + 5mm
# margin, same convention as TW_DrumSprocket50T.
#
# Y position: 50mm clear of the front drum flange (Y=270), per
# the user - NOT yet coplanar with TW_MotorSprocket (Y=82.5) for
# the chain; motor_y is expected to move to match this next.
# ------------------------------------------------------

DRUM_AXLE_SPROCKET_TEETH = 76
DRUM_AXLE_SPROCKET_PITCH = 12.7  # 428 chain, 1/2 inch
DRUM_AXLE_SPROCKET_WIDTH = 13.0  # matches TW_MotorSprocket's width (chain-standard, not tooth-count-dependent)
DRUM_AXLE_SPROCKET_ADDENDUM = 2.2  # calibrated from the real 14T sprocket, see comment above
DRUM_AXLE_SPROCKET_BORE_DIAMETER = config.SHAFT_DIAMETER + 5.0
DRUM_AXLE_SPROCKET_MARGIN = 50.0  # clear gap to the front drum flange

drum_axle_sprocket_radius = (DRUM_AXLE_SPROCKET_TEETH * DRUM_AXLE_SPROCKET_PITCH
                              / (2 * math.pi)) + DRUM_AXLE_SPROCKET_ADDENDUM
drum_flange_front_y = doc.getObject("TW_DrumFlangeFront").Shape.BoundBox.YMin
drum_axle_sprocket_y = (drum_flange_front_y - DRUM_AXLE_SPROCKET_MARGIN
                         - DRUM_AXLE_SPROCKET_WIDTH)

drum_axle_sprocket_shape = Part.makeCylinder(
    drum_axle_sprocket_radius, DRUM_AXLE_SPROCKET_WIDTH,
    App.Vector(drum_cx, drum_axle_sprocket_y, drum_cz), App.Vector(0, 1, 0))
drum_axle_sprocket_bore = Part.makeCylinder(
    DRUM_AXLE_SPROCKET_BORE_DIAMETER / 2, DRUM_AXLE_SPROCKET_WIDTH + 2,
    App.Vector(drum_cx, drum_axle_sprocket_y - 1, drum_cz), App.Vector(0, 1, 0))
drum_axle_sprocket = doc.addObject("Part::Feature", "TW_DrumAxleSprocket76T")
drum_axle_sprocket.Shape = drum_axle_sprocket_shape.cut(drum_axle_sprocket_bore)

drum_group = doc.addObject("App::DocumentObjectGroup", "drum_group")
drum_group.Group = list(drum_parts.values()) + \
    [bearing1, bearing2, drum_axle_sprocket] + \
    left_bolts + right_bolts
# post1-4 (the 4 700mm bearing mounting posts) and the 4 bearing
# mount/stiffener plates are frame structure, not part of the drum
# itself - grouped under frame_group instead, see below.

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
# Motor mount bracket (placeholder - no dimensioned drawing,
# see motor_mount.py header). 4 small brackets, 2 per motor
# end, bolt to the motor's own real end-face holes (connector
# end per the user's photo; shaft end mirrored as a
# placeholder assumption). All 4 weld onto one base plate.
# ------------------------------------------------------

motor_mount_shaft_end_y = motor_y + config.MOTOR_MOUNT_SHAFT_END_Y_OFFSET
motor_mount_connector_end_y = motor_y + config.MOTOR_MOUNT_CONNECTOR_END_Y_OFFSET
motor_mount_base_top_z = T + motor_mount.BASE_PLATE_THICKNESS

(motor_mount_shaft_left, motor_mount_shaft_right,
 motor_mount_shaft_gusset_left, motor_mount_shaft_gusset_right) = motor_mount.make_end_brackets(
    doc, "TW_MotorMountShaftEnd", motor_cx, motor_cz,
    motor_mount_shaft_end_y, -1, motor_mount_base_top_z)
(motor_mount_conn_left, motor_mount_conn_right,
 motor_mount_conn_gusset_left, motor_mount_conn_gusset_right) = motor_mount.make_end_brackets(
    doc, "TW_MotorMountConnectorEnd", motor_cx, motor_cz,
    motor_mount_connector_end_y, 1, motor_mount_base_top_z)
# TW_MotorMountBasePlate itself is built much later (after
# TW_JackshaftCrossBottom exists - see near its own construction),
# since the user wants the plate to grow to reach that tube's real
# position, which isn't known yet at this point in the script. It
# gets appended into motor_mount_group.Group down there too.

# 2 plates tying the shaft-end and connector-end groups together -
# one connecting the 2 lower (HOLE_LEFT) brackets, one connecting
# the 2 higher (HOLE_RIGHT) brackets, each flush on the outer face.
motor_mount_lower_connector = motor_mount.make_side_connector_plate(
    doc, "TW_MotorMountLowerConnector", motor_cx, motor_cz,
    motor_mount.HOLE_LEFT[0], motor_mount.HOLE_LEFT[1],
    motor_mount_shaft_end_y, motor_mount_connector_end_y, motor_mount_base_top_z)
motor_mount_upper_connector = motor_mount.make_side_connector_plate(
    doc, "TW_MotorMountUpperConnector", motor_cx, motor_cz,
    motor_mount.HOLE_RIGHT[0], motor_mount.HOLE_RIGHT[1],
    motor_mount_shaft_end_y, motor_mount_connector_end_y, motor_mount_base_top_z)

motor_mount_group = doc.addObject("App::DocumentObjectGroup", "motor_mount_group")
motor_mount_group.Group = [
    motor_mount_shaft_left, motor_mount_shaft_right,
    motor_mount_shaft_gusset_left, motor_mount_shaft_gusset_right,
    motor_mount_conn_left, motor_mount_conn_right,
    motor_mount_conn_gusset_left, motor_mount_conn_gusset_right,
    motor_mount_lower_connector, motor_mount_upper_connector,
]

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

# Cover was originally meant to be welded flush across all 4
# reinforcement tube ends - but that blocks the access needed to
# mount the vertical/horizontal rollers inside, so instead each
# tube gets its own welded end cap (42x42x4mm, matching the
# tube's own inner bore/wall - cap_inset/TUBE_WALL, already
# computed above for the short-cutting-pipe caps) sitting just
# behind the cover, one tube-wall-thickness further in. Each cap
# is closed except for a single 8mm centre hole, and the cover
# gets 4 matching 8mm holes drilled through it in the same
# positions - so the cover can be bolted to the caps (not welded)
# and removed later for roller access, while the tube ends
# themselves stay permanently capped/welded.
REINFORCEMENT_CAP_HOLE_DIAMETER = 8.0

reinforcement_caps = []
reinforcement_cap_centers = []
for tube_obj in intake_reinforcement_tubes:
    tube_bb = tube_obj.Shape.BoundBox
    cy = (tube_bb.YMin + tube_bb.YMax) / 2
    cz = (tube_bb.ZMin + tube_bb.ZMax) / 2
    reinforcement_cap_centers.append((cy, cz))

    cap_body = Part.makeBox(
        config.TUBE_WALL, cap_inset, cap_inset,
        App.Vector(tube_bb.XMin, tube_bb.YMin + config.TUBE_WALL, tube_bb.ZMin + config.TUBE_WALL))
    cap_hole = Part.makeCylinder(
        REINFORCEMENT_CAP_HOLE_DIAMETER / 2, config.TUBE_WALL + 2,
        App.Vector(tube_bb.XMin - 1, cy, cz), App.Vector(1, 0, 0))
    cap_obj = doc.addObject("Part::Feature", tube_obj.Name + "Cap")
    cap_obj.Shape = cap_body.cut(cap_hole)
    reinforcement_caps.append(cap_obj)

cover_body_bolted = reinforcement_cover.Shape
for cy, cz in reinforcement_cap_centers:
    bolt_hole = Part.makeCylinder(
        REINFORCEMENT_CAP_HOLE_DIAMETER / 2, REINFORCEMENT_COVER_THICKNESS + 2,
        App.Vector(vertical_roller_plate_x - REINFORCEMENT_COVER_THICKNESS - 1, cy, cz),
        App.Vector(1, 0, 0))
    cover_body_bolted = cover_body_bolted.cut(bolt_hole)
reinforcement_cover.Shape = cover_body_bolted

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
intake_mount_tube_bore = drill_x(doc, intake_brace, "TW_IntakeMountTube_Bore", intake_cy, intake_cz, hole_diameter, brace_bb.XMin, brace_bb.XMax)

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
# The 4 reinforcement tubes, their end caps and the cover plate are
# frame structure (welded/bolted to the frame), not part of the
# rope-handling mechanism itself - grouped under frame_group
# instead, alongside the other structural tubes/plates moved there
# (see frame_group assembly below).
intake_group.Group = [intake_bearing, intake_plate, intake_bearing_inside, intake_plate_inside,
                       intake_pipe] + list(wheel_bracket_parts.values()) + \
                      [short_cutting_pipe, long_cutting_pipe,
                       short_cutting_pipe_cap_far, short_cutting_pipe_cap_near,
                       roller_cutter_top, roller_cutter_bottom,
                       roller_cutter_top_axle, roller_cutter_bottom_axle,
                       vertical_roller_left, vertical_roller_right,
                       vertical_roller_plate_bottom, vertical_roller_plate_top,
                       vertical_roller_left_axle, vertical_roller_right_axle]

# ------------------------------------------------------
# Winding mechanism (level wind / diamond screw) - just
# starting out. First piece: a guide rail tube stacked
# directly on top of TW_CrossFrontTop (same 700mm length,
# same X/Y position, sitting flush on its top face at z=H).
# ------------------------------------------------------

winding_rail = tube.make(doc, "TW_WindingRail", W - 2 * T, axis="Y", x=0, y=T, z=H - config.WINDING_RAIL_Z_DROP)

# HWIN HGW30 linear guide rail, mounted on the winding rail
# tube's face pointing toward the intake (its higher-X face) -
# 2 real 200mm segments end to end (400mm total), centred
# within the tube's own 700mm length, on the tube's own Z
# centreline. Sized for ~300mm of HWIN block travel (rail length
# minus the block's own ~110.75mm length) - real segments only
# come in 200mm units, so this lands at ~289.25mm rather than
# exactly 300mm; a 3rd segment would overshoot to ~489mm instead.
winding_rail_bb = winding_rail.Shape.BoundBox

# Backing plate between TW_WindingRail and the HWIN rail - tapping
# the HWIN rail's own mounting screws directly into the tube's 4mm
# wall didn't feel like enough thread engagement to the user. This
# plate is welded flat onto the tube's own face instead, giving the
# screws real solid material to bite into; the whole HWIN
# rail/carriage/downstream winding assembly (everything anchored to
# hwin_rail_x below) shifts outward by its thickness automatically.
HWIN_BACKING_PLATE_LENGTH = 500.0
HWIN_BACKING_PLATE_WIDTH = 46.0
HWIN_BACKING_PLATE_THICKNESS = 4.0

hwin_backing_plate = doc.addObject("Part::Box", "TW_HwinBackingPlate")
hwin_backing_plate.Length = HWIN_BACKING_PLATE_THICKNESS
hwin_backing_plate.Width = HWIN_BACKING_PLATE_LENGTH
hwin_backing_plate.Height = HWIN_BACKING_PLATE_WIDTH
hwin_backing_plate.Placement.Base = App.Vector(
    winding_rail_bb.XMax,
    (winding_rail_bb.YMin + winding_rail_bb.YMax) / 2 - HWIN_BACKING_PLATE_LENGTH / 2,
    (winding_rail_bb.ZMin + winding_rail_bb.ZMax) / 2 - HWIN_BACKING_PLATE_WIDTH / 2)

HWIN_RAIL_SEGMENT_COUNT = 2
hwin_rail_x = winding_rail_bb.XMax + HWIN_BACKING_PLATE_THICKNESS
hwin_rail_z = (winding_rail_bb.ZMin + winding_rail_bb.ZMax) / 2
hwin_rail_y = winding_rail_bb.YMin + (winding_rail_bb.YLength
                                       - HWIN_RAIL_SEGMENT_COUNT * hwin30_rail.SEGMENT_LENGTH) / 2

hwin_rail_segments = hwin30_rail.make_segments(
    doc, "TW_HwinRailSegment", HWIN_RAIL_SEGMENT_COUNT, hwin_rail_x, hwin_rail_y, hwin_rail_z)

# 2 mounting tubes for the self-reversing screw's own end
# supports - welded onto TW_WindingRail's own top face (the same
# tube the HWIN rail connects to, but its top rather than the
# side face HWIN mounts on, so this clears the HWIN hardware
# entirely), parallel to the intake pipe (X axis), 350mm between
# their insides. First placement only - not yet tied to the real
# screw's own mounting dimensions (screw 3D file not modelled
# yet).
SCREW_MOUNT_LENGTH = 200.0

# Real gap between the 2 screw mount tubes' own inner faces is
# 350mm (SCREW_MOUNT_GAP_NOMINAL) plus 2x FLANGE_MOUNT_PLATE_THICKNESS
# extra - the tubes themselves are pushed that much further apart so
# a real mounting plate (added later, between each tube and its own
# flange bearing) fits in the new gap WITHOUT moving either bearing
# off its own carefully-calibrated axial position relative to the
# reversing screw. Moving the bearings themselves outward instead
# was tried first and reintroduced a real ~2254mm3 screw/housing
# collision that had already been fixed once (by scaling both parts
# 1.25x, see flange_bearing.py) - moving the tubes instead keeps
# that fit exactly intact while still giving the plates real room.
FLANGE_MOUNT_PLATE_THICKNESS = 4.0
SCREW_MOUNT_GAP_NOMINAL = 350.0
SCREW_MOUNT_GAP = SCREW_MOUNT_GAP_NOMINAL + 2 * FLANGE_MOUNT_PLATE_THICKNESS

screw_mount_y_center = (winding_rail_bb.YMin + winding_rail_bb.YMax) / 2
screw_mount_x = hwin_rail_x - 50.0

# Riser tube, parallel to the drum axle (Y axis) - not enough
# clearance between the reversing screw and the HWIN mounting
# plate for the belt sprocket, so this drops the screw mount
# tubes one more tube thickness (T = 50mm) further away from
# TW_WindingRail. Sits flush against TW_WindingRail's own bottom
# face, in the exact spot the screw mount tubes used to occupy;
# 450mm long - the screw mount tubes' own outside-to-outside span
# (SCREW_MOUNT_GAP + 2*T).
SCREW_RISER_LENGTH = SCREW_MOUNT_GAP + 2 * T

screw_riser = tube.make(doc, "TW_ScrewRiser", SCREW_RISER_LENGTH, axis="Y",
                         x=screw_mount_x,
                         y=screw_mount_y_center - SCREW_MOUNT_GAP / 2 - T,
                         z=winding_rail_bb.ZMax - 100.0)

screw_mount_z = winding_rail_bb.ZMax - 100.0 - T

screw_mount_near = tube.make(doc, "TW_ScrewMountNear", SCREW_MOUNT_LENGTH, axis="X",
                             x=screw_mount_x, y=screw_mount_y_center - SCREW_MOUNT_GAP / 2 - T,
                             z=screw_mount_z)
screw_mount_far = tube.make(doc, "TW_ScrewMountFar", SCREW_MOUNT_LENGTH, axis="X",
                            x=screw_mount_x, y=screw_mount_y_center + SCREW_MOUNT_GAP / 2,
                            z=screw_mount_z)

# Self-reversing screw, running along Y (the level-wind travel
# axis, matching the drum/pulley wheel convention). Only needs to
# pass through the far mount tube - that's the end the belt
# sprocket goes on, exact protrusion still TBD. The near tube is
# just an end support (via TW_FlangeBearingNear), so no clearance
# hole is drilled there any more and the screw's near end is
# trimmed off flush with that tube's own outer face instead of
# sticking through it. The screw's own body isn't symmetric
# around its local origin (raw file's own bbox is offset), so
# it's centred on the frame by its own body midpoint (+125mm from
# its "w" reference), not just by setting w to the frame's own
# centreline.
# Screw's own centreline is shifted from the mount tubes' own
# centreline (toward higher X, the plate's own outer face -
# the one actually facing the intake group, which sits at much
# higher X, not the face that was tried first) - the tubes
# themselves stay put (their outer end is already flush with the
# frame's own front edge, X=0, with no margin to give up), but the
# screw, follower block and both flange bearings all move
# together so the follower pin (see below) lands exactly tangent
# to that face. Found empirically: 6.75mm past the tube's own
# centre puts the pin right on the plate's own XMax face.
SCREW_OUTWARD_SHIFT = 6.75
screw_bore_x = (screw_mount_near.Shape.BoundBox.XMin + screw_mount_near.Shape.BoundBox.XMax) / 2 + SCREW_OUTWARD_SHIFT
screw_bore_z = (screw_mount_near.Shape.BoundBox.ZMin + screw_mount_near.Shape.BoundBox.ZMax) / 2
screw_near_face_y = screw_mount_near.Shape.BoundBox.YMax
screw_far_face_y = screw_mount_far.Shape.BoundBox.YMin
SCREW_BODY_MIDPOINT_OFFSET = 125.0   # from its own local-origin ("w") reference - see reversing_screw.py
screw_y_center = W / 2 - SCREW_BODY_MIDPOINT_OFFSET

SCREW_HOLE_DIAMETER = 30.0   # 25mm shaft + 5mm margin so it doesn't rub

hole = Part.makeCylinder(SCREW_HOLE_DIAMETER / 2, T + 2,
                          App.Vector(screw_bore_x, screw_mount_far.Shape.BoundBox.YMin - 1, screw_bore_z),
                          App.Vector(0, 1, 0))
screw_mount_far.Shape = screw_mount_far.Shape.cut(hole)

reversing_screw_obj = reversing_screw.make(
    doc, "TW_ReversingScrew", u=screw_bore_x, v=screw_bore_z, w=screw_y_center, axis="Y")

screw_near_trim_y = screw_mount_near.Shape.BoundBox.YMax   # near tube's own inner (gap-facing) face
screw_bb = reversing_screw_obj.Shape.BoundBox
trim_box = Part.makeBox(screw_bb.XLength + 20, screw_near_trim_y - (screw_bb.YMin - 20), screw_bb.ZLength + 20,
                         App.Vector(screw_bb.XMin - 10, screw_bb.YMin - 20, screw_bb.ZMin - 10))
reversing_screw_obj.Shape = reversing_screw_obj.Shape.cut(trim_box)

# Flange bearings shifted off each tube's own inside face so the
# whole housing sits clear of the tube's solid material (in the
# 350mm gap only) rather than straddling into it - the housing's
# own shape isn't symmetric around its "w" reference either (same
# reason as the screw), found empirically (post-scaling): its
# smaller offset is 4.998mm and its larger one is 9.6395mm, on
# opposite sides - which side is which swaps with flip=True (the
# near bearing needs flip=True to face the right way, per the
# user's own visual check; the far one is correct unflipped).
FLANGE_BEARING_OFFSET_SMALL = 4.998
FLANGE_BEARING_OFFSET_LARGE = 9.6395

# Mounting plates between each screw mount tube's own inner face
# and its flange bearing - tapping the bearing's own bolt holes
# straight into a 4mm tube wall wasn't felt to be strong enough
# (same concern as TW_HwinBackingPlate above), so each bearing now
# bolts to a proper flat plate instead, welded flush onto the
# tube's inner face. 80(X)x46(Z)x4mm - covers the housing's own
# real footprint (58.125 x 33.75mm, queried from the bearing's own
# geometry) with margin on all sides. Both bearings shift further
# into the gap by the plate's own thickness so they still sit
# flush against the new outer face rather than the bare tube. Only
# the far plate needs a hole - the screw's own shaft continues
# through the far tube and plate on its way to the sprocket; it's
# trimmed off flush at the near tube's face, so nothing passes
# through the near plate.
FLANGE_MOUNT_PLATE_X = 80.0
FLANGE_MOUNT_PLATE_Z = 46.0
# FLANGE_MOUNT_PLATE_THICKNESS already defined above, next to
# SCREW_MOUNT_GAP (the tubes were pushed apart by exactly that much
# to make room for these plates).

flange_mount_plate_near = doc.addObject("Part::Box", "TW_FlangeMountPlateNear")
flange_mount_plate_near.Length = FLANGE_MOUNT_PLATE_X
flange_mount_plate_near.Width = FLANGE_MOUNT_PLATE_THICKNESS
flange_mount_plate_near.Height = FLANGE_MOUNT_PLATE_Z
flange_mount_plate_near.Placement.Base = App.Vector(
    screw_bore_x - FLANGE_MOUNT_PLATE_X / 2, screw_near_face_y, screw_bore_z - FLANGE_MOUNT_PLATE_Z / 2)

flange_mount_plate_far_body = Part.makeBox(
    FLANGE_MOUNT_PLATE_X, FLANGE_MOUNT_PLATE_THICKNESS, FLANGE_MOUNT_PLATE_Z,
    App.Vector(screw_bore_x - FLANGE_MOUNT_PLATE_X / 2, screw_far_face_y - FLANGE_MOUNT_PLATE_THICKNESS,
               screw_bore_z - FLANGE_MOUNT_PLATE_Z / 2))
flange_mount_plate_far_hole = Part.makeCylinder(
    SCREW_HOLE_DIAMETER / 2, FLANGE_MOUNT_PLATE_THICKNESS + 2,
    App.Vector(screw_bore_x, screw_far_face_y - FLANGE_MOUNT_PLATE_THICKNESS - 1, screw_bore_z),
    App.Vector(0, 1, 0))
flange_mount_plate_far = doc.addObject("Part::Feature", "TW_FlangeMountPlateFar")
flange_mount_plate_far.Shape = flange_mount_plate_far_body.cut(flange_mount_plate_far_hole)

flange_bearing_near = flange_bearing.make(
    doc, "TW_FlangeBearingNear", u=screw_bore_x, v=screw_bore_z,
    w=screw_near_face_y + FLANGE_MOUNT_PLATE_THICKNESS + FLANGE_BEARING_OFFSET_SMALL, axis="Y", flip=True)
flange_bearing_far = flange_bearing.make(
    doc, "TW_FlangeBearingFar", u=screw_bore_x, v=screw_bore_z,
    w=screw_far_face_y - FLANGE_MOUNT_PLATE_THICKNESS - FLANGE_BEARING_OFFSET_SMALL, axis="Y", flip=False)

# 3rd bearing on the OTHER side of TW_ScrewMountFar - the side the
# reversing screw actually exits toward the sprocket, not the
# gap-facing side TW_FlangeBearingFar already covers. Same 80x46x4
# mounting-plate convention as the other 2 (with a hole, since the
# screw continues straight through it on its way to the sprocket),
# and a 2nd bearing on this tube, flipped relative to
# TW_FlangeBearingFar so its housing faces the right way here.
screw_far_outer_face_y = screw_mount_far.Shape.BoundBox.YMax

flange_mount_plate_far_outer_body = Part.makeBox(
    FLANGE_MOUNT_PLATE_X, FLANGE_MOUNT_PLATE_THICKNESS, FLANGE_MOUNT_PLATE_Z,
    App.Vector(screw_bore_x - FLANGE_MOUNT_PLATE_X / 2, screw_far_outer_face_y,
               screw_bore_z - FLANGE_MOUNT_PLATE_Z / 2))
flange_mount_plate_far_outer_hole = Part.makeCylinder(
    SCREW_HOLE_DIAMETER / 2, FLANGE_MOUNT_PLATE_THICKNESS + 2,
    App.Vector(screw_bore_x, screw_far_outer_face_y - 1, screw_bore_z),
    App.Vector(0, 1, 0))
flange_mount_plate_far_outer = doc.addObject("Part::Feature", "TW_FlangeMountPlateFarOuter")
flange_mount_plate_far_outer.Shape = flange_mount_plate_far_outer_body.cut(flange_mount_plate_far_outer_hole)

flange_bearing_far_outer = flange_bearing.make(
    doc, "TW_FlangeBearingFarOuter", u=screw_bore_x, v=screw_bore_z,
    w=screw_far_outer_face_y + FLANGE_MOUNT_PLATE_THICKNESS + FLANGE_BEARING_OFFSET_SMALL, axis="Y", flip=True)

# Shorten both screw mount tubes now that we know exactly where
# their own bearing sits - the original 200mm length was never
# tied to real dimensions, just a first placeholder. Their near
# end (X=0) stays put, welded to TW_ScrewRiser; the far end is cut
# back to 10mm past its own bearing's own outer (mounting-foot)
# extent in X.
SCREW_MOUNT_TUBE_CLEARANCE = 10.0

near_tube_trim_x = flange_bearing_near.Shape.BoundBox.XMax + SCREW_MOUNT_TUBE_CLEARANCE
far_tube_trim_x = flange_bearing_far.Shape.BoundBox.XMax + SCREW_MOUNT_TUBE_CLEARANCE

near_trim_box = Part.makeBox(
    300, T + 2, T + 2,
    App.Vector(near_tube_trim_x, screw_mount_near.Shape.BoundBox.YMin - 1, screw_mount_z - 1))
screw_mount_near.Shape = screw_mount_near.Shape.cut(near_trim_box)

far_trim_box = Part.makeBox(
    300, T + 2, T + 2,
    App.Vector(far_tube_trim_x, screw_mount_far.Shape.BoundBox.YMin - 1, screw_mount_z - 1))
screw_mount_far.Shape = screw_mount_far.Shape.cut(far_trim_box)

# End caps closing both screw mount tubes and the riser tube on
# every open end - same convention as TW_ShortCuttingPipe's own
# caps: 42x42x4mm plates (cap_inset already defined above) fitting
# snugly inside each tube's own hollow bore, flush with the cut
# end, extending TUBE_WALL inward.
near_tube_bb = screw_mount_near.Shape.BoundBox
far_tube_bb = screw_mount_far.Shape.BoundBox
riser_bb = screw_riser.Shape.BoundBox


def _make_axis_x_cap(name, tube_bb, x_at_min_end):
    cap = doc.addObject("Part::Box", name)
    cap.Length = config.TUBE_WALL
    cap.Width = cap_inset
    cap.Height = cap_inset
    x = tube_bb.XMin if x_at_min_end else tube_bb.XMax - config.TUBE_WALL
    cap.Placement.Base = App.Vector(x, tube_bb.YMin + config.TUBE_WALL, tube_bb.ZMin + config.TUBE_WALL)
    return cap


def _make_axis_y_cap(name, tube_bb, y_at_min_end):
    cap = doc.addObject("Part::Box", name)
    cap.Length = cap_inset
    cap.Width = config.TUBE_WALL
    cap.Height = cap_inset
    y = tube_bb.YMin if y_at_min_end else tube_bb.YMax - config.TUBE_WALL
    cap.Placement.Base = App.Vector(tube_bb.XMin + config.TUBE_WALL, y, tube_bb.ZMin + config.TUBE_WALL)
    return cap


screw_mount_near_cap_inner = _make_axis_x_cap("TW_ScrewMountNearCapInner", near_tube_bb, True)
screw_mount_near_cap_outer = _make_axis_x_cap("TW_ScrewMountNearCapOuter", near_tube_bb, False)
screw_mount_far_cap_inner = _make_axis_x_cap("TW_ScrewMountFarCapInner", far_tube_bb, True)
screw_mount_far_cap_outer = _make_axis_x_cap("TW_ScrewMountFarCapOuter", far_tube_bb, False)
screw_riser_cap_near = _make_axis_y_cap("TW_ScrewRiserCapNear", riser_bb, True)
screw_riser_cap_far = _make_axis_y_cap("TW_ScrewRiserCapFar", riser_bb, False)

# Carriage block, centred on the frame's own midpoint (segment
# index 0.5 - the boundary between the 2 rail segments, not
# either segment's own centre) - just a representative resting
# position for this visualisation, not a modelled travel range -
# same (x, y, z) args as make_segments so it lines up on the
# same rail run.
hwin_block = hwin30_rail.make_block(
    doc, "TW_HwinBlock", 0.5, hwin_rail_x, hwin_rail_y, hwin_rail_z)

# Mounting plate on top of the block - same footprint and same
# 4 mounting holes as the block itself, 10mm thick.
hwin_mounting_plate = hwin30_rail.make_mounting_plate(
    doc, "TW_HwinMountingPlate", 10.0, 0.5, hwin_rail_x, hwin_rail_y, hwin_rail_z)

# Load cell, hung off a rod end ball joint instead of bolted
# rigidly to the mounting plate - lets it tilt as the rope's
# angle off the drum changes with layer build-up. Two clevis
# ("ear") plates are welded flat-side-down onto the mounting
# plate's own outer face, standing proud of it; a pivot pin
# through both plates and the rod end's own eye bore (its own Y
# axis) gives the tilt axis, matching the winding travel axis
# (Y) so the tilt happens in the X-Z plane, the plane the rope
# angle actually changes in. The rod end's shank then continues
# straight out in X, past the plates' own domed tip, so the
# plates have to be spaced wide enough to clear the rod end's hex
# boss (the widest thing running out that way), not just the
# eye's own thickness, or the hex would clip them -
# config.WINDING_CLEVIS_GAP is set to the hex's own across-flats
# width (a snug slide fit, not extra clearance - the hex doesn't
# sweep through an arc like the eye does, it just has to fit).
# The load cell's flange sits flush against the hex's mounting
# face (0mm gap - the M16 stud that connects them is fully
# recessed inside both parts, so nothing is modelled between
# them, the same convention as unmodelled bolts elsewhere in this
# project).
plate_bb = hwin_mounting_plate.Shape.BoundBox
loadcell_cy = (plate_bb.YMin + plate_bb.YMax) / 2
loadcell_cz = (plate_bb.ZMin + plate_bb.ZMax) / 2

# Follower block placeholder - the real block (with a 25mm bore
# for the screw and a threaded hole for a separate wear-part
# "follower" that rides in the screw's own helical groove) isn't
# modelled yet, so this just stands in for its outer envelope:
# 10mm clearance off the screw's own surface on the left, right
# and bottom, reaching up to 10mm below the HWIN mounting plate's
# own underside. That last 10mm is a deliberate air gap - only a
# separate soft-coupling pin (not modelled yet either) will
# actually bridge block and plate, not the block's own body. 40mm
# wide along the screw's own travel axis (Y), centred on the
# mounting plate's own Y centreline.
FOLLOWER_BLOCK_CLEARANCE = 10.0
FOLLOWER_BLOCK_WIDTH = 40.0

screw_bb = reversing_screw_obj.Shape.BoundBox
follower_block_x0 = screw_bb.XMin - FOLLOWER_BLOCK_CLEARANCE
follower_block_x1 = screw_bb.XMax + FOLLOWER_BLOCK_CLEARANCE
follower_block_z0 = screw_bb.ZMin - FOLLOWER_BLOCK_CLEARANCE
follower_block_z1 = plate_bb.ZMin - FOLLOWER_BLOCK_CLEARANCE

follower_block = doc.addObject("Part::Feature", "TW_FollowerBlock")
follower_block.Shape = Part.makeBox(
    follower_block_x1 - follower_block_x0,
    FOLLOWER_BLOCK_WIDTH,
    follower_block_z1 - follower_block_z0,
    App.Vector(follower_block_x0, loadcell_cy - FOLLOWER_BLOCK_WIDTH / 2, follower_block_z0))

# Snug through-bore for the screw itself (27.6mm - the screw's
# own crest/outer diameter, not its 25mm root/nominal size, so
# the threads aren't clipped), running the block's full 40mm
# width along Y.
FOLLOWER_BLOCK_BORE_DIAMETER = 27.6

follower_block_bore = Part.makeCylinder(
    FOLLOWER_BLOCK_BORE_DIAMETER / 2, FOLLOWER_BLOCK_WIDTH + 2,
    App.Vector(screw_bore_x, loadcell_cy - FOLLOWER_BLOCK_WIDTH / 2 - 1, screw_bore_z),
    App.Vector(0, 1, 0))
follower_block.Shape = follower_block.Shape.cut(follower_block_bore)

# Soft-coupling pin between the follower block and the HWIN
# mounting plate - ties the screw-driven follower to the HWIN
# carriage while also acting as the follower's own anti-rotation
# feature. Lies flat (tangent) against the mounting plate's own
# face pointing toward the intake group, for a plain fillet weld
# along its length rather than sitting inside a drilled hole - the
# screw assembly is shifted by SCREW_OUTWARD_SHIFT above precisely
# so its own centreline lands 5mm (its own radius) off that face.
# Runs 20mm up alongside the plate's face (the weld run), spans
# the 10mm air gap above the follower block, then goes into a
# 10.5mm hole in the block's own top centre (0.5mm clearance - the
# "soft" side).
PIN_DIAMETER = 10.0
PIN_PLATE_WELD_RUN = 20.0
# 40mm would reach past the screw's own top surface and into it -
# only ~31mm of the block's own material actually clears the
# screw before the block's top face, so this is shortened to
# leave a couple mm of margin instead.
PIN_BLOCK_DEPTH = follower_block_z1 - screw_bb.ZMax - 2.0
PIN_BLOCK_HOLE_CLEARANCE = 0.5

pin_top_z = plate_bb.ZMin + PIN_PLATE_WELD_RUN
pin_bottom_z = follower_block_z1 - PIN_BLOCK_DEPTH

follower_pin = doc.addObject("Part::Feature", "TW_FollowerPin")
follower_pin.Shape = Part.makeCylinder(
    PIN_DIAMETER / 2, pin_top_z - pin_bottom_z,
    App.Vector(screw_bore_x, loadcell_cy, pin_bottom_z), App.Vector(0, 0, 1))

block_pin_hole = Part.makeCylinder(
    (PIN_DIAMETER + PIN_BLOCK_HOLE_CLEARANCE) / 2, PIN_BLOCK_DEPTH + 1,
    App.Vector(screw_bore_x, loadcell_cy, follower_block_z1 + 1), App.Vector(0, 0, -1))
follower_block.Shape = follower_block.Shape.cut(block_pin_hole)

clevis_gap = config.WINDING_CLEVIS_GAP
clevis_pin_x = plate_bb.XMax + config.WINDING_CLEVIS_PLATE_SIZE / 2


def _make_clevis_plate(name, y_near):
    """y_near is the plate's own Y face closest to the centreline;
    the plate's thickness runs away from the centreline from there."""

    rect = Part.makeBox(
        config.WINDING_CLEVIS_PLATE_SIZE / 2, config.WINDING_CLEVIS_PLATE_THICKNESS,
        config.WINDING_CLEVIS_PLATE_SIZE,
        App.Vector(plate_bb.XMax, y_near, loadcell_cz - config.WINDING_CLEVIS_PLATE_SIZE / 2))
    dome = Part.makeCylinder(
        config.WINDING_CLEVIS_PLATE_SIZE / 2, config.WINDING_CLEVIS_PLATE_THICKNESS,
        App.Vector(clevis_pin_x, y_near, loadcell_cz), App.Vector(0, 1, 0))
    body = rect.fuse(dome)

    pin_hole = Part.makeCylinder(
        rod_end.EYE_BORE_DIAMETER / 2, config.WINDING_CLEVIS_PLATE_THICKNESS + 2,
        App.Vector(clevis_pin_x, y_near - 1, loadcell_cz), App.Vector(0, 1, 0))
    body = body.cut(pin_hole)

    obj = doc.addObject("Part::Feature", name)
    obj.Shape = body
    return obj


clevis_plate_near = _make_clevis_plate("TW_WindingClevisPlateNear", loadcell_cy - clevis_gap / 2 - config.WINDING_CLEVIS_PLATE_THICKNESS)
clevis_plate_far = _make_clevis_plate("TW_WindingClevisPlateFar", loadcell_cy + clevis_gap / 2)

hwin_rod_end = rod_end.make(doc, "TW_RodEnd", cy=loadcell_cy, cz=loadcell_cz, x=clevis_pin_x)

hwin_loadcell = loadcell.make(
    doc, "TW_LoadCell", cy=loadcell_cy, cz=loadcell_cz, x=clevis_pin_x + rod_end.REACH)

# Pivot axle/pin through both clevis plates and the rod end's own
# eye bore (already sized to it - see pin_hole above), sticking
# out past each plate's own outer face by
# config.WINDING_CLEVIS_AXLE_OVERHANG.
clevis_axle_y_start = clevis_plate_near.Shape.BoundBox.YMin - config.WINDING_CLEVIS_AXLE_OVERHANG
clevis_axle_y_end = clevis_plate_far.Shape.BoundBox.YMax + config.WINDING_CLEVIS_AXLE_OVERHANG
clevis_axle = doc.addObject("Part::Feature", "TW_WindingClevisAxle")
clevis_axle.Shape = Part.makeCylinder(
    rod_end.EYE_BORE_DIAMETER / 2, clevis_axle_y_end - clevis_axle_y_start,
    App.Vector(clevis_pin_x, clevis_axle_y_start, loadcell_cz), App.Vector(0, 1, 0))

# Gussets bracing each clevis plate against the HWIN mounting
# plate, one near the top and one near the bottom of each plate
# (4 total) - 45/45/90 right triangle, one leg flush against the
# plate's own outer (exposed) face, the other flush against the
# mounting plate's face, right-angle corner where the two meet.
# Positioned in from the plate's own edge, toward the axle's own
# centreline (config.WINDING_CLEVIS_GUSSET_Z_OFFSET from centre) -
# not flush at the very top/bottom tip, matching the user's
# reference picture (picts/stiffner.jpg), where the ribs sit
# noticeably inset from the plate's own edges rather than right at
# them.
gusset_top_z = loadcell_cz + config.WINDING_CLEVIS_GUSSET_Z_OFFSET
gusset_bottom_z = loadcell_cz - config.WINDING_CLEVIS_GUSSET_Z_OFFSET


def _make_gusset(name, y_outer, y_sign, z_edge, z_sign):
    leg = config.WINDING_CLEVIS_GUSSET_LEG
    p0 = App.Vector(plate_bb.XMax, y_outer, z_edge)
    p1 = App.Vector(plate_bb.XMax + leg, y_outer, z_edge)
    p2 = App.Vector(plate_bb.XMax, y_outer + y_sign * leg, z_edge)
    face = Part.Face(Part.makePolygon([p0, p1, p2, p0]))
    body = face.extrude(App.Vector(0, 0, z_sign * config.WINDING_CLEVIS_GUSSET_THICKNESS))
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = body
    return obj


clevis_gusset_near_top = _make_gusset(
    "TW_WindingClevisGussetNearTop", clevis_plate_near.Shape.BoundBox.YMin, -1, gusset_top_z, 1)
clevis_gusset_near_bottom = _make_gusset(
    "TW_WindingClevisGussetNearBottom", clevis_plate_near.Shape.BoundBox.YMin, -1, gusset_bottom_z, -1)
clevis_gusset_far_top = _make_gusset(
    "TW_WindingClevisGussetFarTop", clevis_plate_far.Shape.BoundBox.YMax, 1, gusset_top_z, 1)
clevis_gusset_far_bottom = _make_gusset(
    "TW_WindingClevisGussetFarBottom", clevis_plate_far.Shape.BoundBox.YMax, 1, gusset_bottom_z, -1)

# Pulley, connected to the load cell's own ~18mm threaded stud
# via a nut welded to the pulley (pulley.py's own NUT_HEIGHT/
# NUT_BORE_DIAMETER) - so the pulley's mount side sits NUT_HEIGHT
# further out than a flush touch would be, leaving room for the
# nut to occupy that gap. Wheel axle set to Y (parallel to the
# drum), so its own local (x, y, z) map straight onto world
# (X, Y, Z) with no rotation needed.
loadcell_tip_x = clevis_pin_x + rod_end.REACH + loadcell.TOTAL_HEIGHT
pulley_parts = pulley.make(doc, "TW_WindingPulley")
pulley_y_span = pulley.PLATE_THICKNESS * 2 + guide_wheel.WIDTH
pulley_placement = App.Placement(
    App.Vector(loadcell_tip_x + pulley.NUT_HEIGHT, loadcell_cy - pulley_y_span / 2, loadcell_cz),
    App.Rotation())
for pulley_obj in pulley_parts.values():
    pulley_obj.Placement = pulley_placement

winding_group = doc.addObject("App::DocumentObjectGroup", "winding_group")
# winding_rail, screw_riser, both screw mount tubes and their end
# caps moved to frame_group instead (frame structure, not
# mechanism) - see below.
winding_group.Group = hwin_rail_segments + \
    [hwin_backing_plate, hwin_block, hwin_mounting_plate,
     clevis_plate_near, clevis_plate_far,
     hwin_rod_end, clevis_axle, hwin_loadcell] + list(pulley_parts.values()) + [
     clevis_gusset_near_top, clevis_gusset_near_bottom,
     clevis_gusset_far_top, clevis_gusset_far_bottom]

# ------------------------------------------------------
# Belt reduction jackshaft - the idle shaft between the 2
# HTD-5M belt stages that reduce the drum's own rotation
# down to the reversing screw's much slower travel speed
# (50T->100T then 40T->66T, 3.3:1 overall, validated on
# paper only so far). All 3 pulleys here (both on the
# jackshaft, plus the screw's own sprocket below) are
# placeholder envelopes only (plain discs, no teeth, same
# simplification already used for sprocket.py) - real
# HTD-5M pulley dimensions haven't been sourced yet, so
# their outer diameter comes from the standard pitch-
# diameter formula (PD = teeth x pitch / pi) rather than a
# real drawing. Bearings reuse flange_bearing.py unmodified
# (already scaled for a 25mm bore). No supporting frame
# structure is modelled yet for these bearings - the user's
# own plan is to add a simple frame extension later, once
# the axle/bearing positions below are confirmed to be
# right.
# ------------------------------------------------------

JACKSHAFT_DIAMETER = 25.0
HTD5M_PITCH = 5.0
JACKSHAFT_LARGE_PULLEY_TEETH = 100
JACKSHAFT_SMALL_PULLEY_TEETH = 40
SCREW_SPROCKET_TEETH = 66
JACKSHAFT_PULLEY_WIDTH = 15.0   # placeholder, real HTD-5M pulleys not yet sourced
JACKSHAFT_PULLEY_BORE_DIAMETER = 30.0   # 25mm shaft + 5mm margin, same convention as SCREW_HOLE_DIAMETER

jackshaft_large_pulley_radius = JACKSHAFT_LARGE_PULLEY_TEETH * HTD5M_PITCH / (2 * math.pi)
jackshaft_small_pulley_radius = JACKSHAFT_SMALL_PULLEY_TEETH * HTD5M_PITCH / (2 * math.pi)
screw_sprocket_radius = SCREW_SPROCKET_TEETH * HTD5M_PITCH / (2 * math.pi)

# The screw's own sprocket (66T) mounts past TW_ScrewMountFar's
# outer face with 10mm clearance, plus an extra 20mm shift further
# outside the frame - freed up by moving the sprocket, this same
# 20mm cascades through to the jackshaft's small pulley (belt
# coplanarity), the large pulley (fixed 15mm gap from the small
# one) and the near bearing (fixed 20mm margin from the large
# pulley), moving the whole assembly 20mm further from the drum's
# spinning rear flange - which is what TW_JackshaftPostNear needed
# to actually clear it. The screw itself is trimmed relative to
# this same position (see below), so it comes out 20mm longer too.
SCREW_SPROCKET_CLEARANCE = 10.0
SCREW_SPROCKET_OUTWARD_SHIFT = 20.0
screw_sprocket_y0 = screw_mount_far.Shape.BoundBox.YMax + SCREW_SPROCKET_CLEARANCE + SCREW_SPROCKET_OUTWARD_SHIFT
screw_sprocket_shape = Part.makeCylinder(
    screw_sprocket_radius, JACKSHAFT_PULLEY_WIDTH,
    App.Vector(screw_bore_x, screw_sprocket_y0, screw_bore_z), App.Vector(0, 1, 0))
screw_sprocket_bore = Part.makeCylinder(
    JACKSHAFT_PULLEY_BORE_DIAMETER / 2, JACKSHAFT_PULLEY_WIDTH + 2,
    App.Vector(screw_bore_x, screw_sprocket_y0 - 1, screw_bore_z), App.Vector(0, 1, 0))
screw_sprocket = doc.addObject("Part::Feature", "TW_ScrewSprocket66T")
screw_sprocket.Shape = screw_sprocket_shape.cut(screw_sprocket_bore)

# Screw trimmed to its final length now that the sprocket position
# is known - 10mm past the sprocket's own outer face.
SCREW_TRIM_PAST_SPROCKET = 10.0
screw_final_trim_y = screw_sprocket_y0 + JACKSHAFT_PULLEY_WIDTH + SCREW_TRIM_PAST_SPROCKET
screw_far_trim_box = Part.makeBox(
    screw_bb.XLength + 20, 300, screw_bb.ZLength + 20,
    App.Vector(screw_bb.XMin - 10, screw_final_trim_y, screw_bb.ZMin - 10))
reversing_screw_obj.Shape = reversing_screw_obj.Shape.cut(screw_far_trim_box)

# X: midway between the drum's own shaft and the reversing
# screw. Z: the larger pulley's own lowest point sits
# config.TUBE_SIZE (bottom frame tube height) + 20mm margin
# above the ground, i.e. the axle centreline is that height
# plus the large pulley's own radius. Y: shifted to the same
# side of the frame the reversing screw sticks through
# (high-Y side) - the outer (far) bearing's own outer face
# sits flush with the frame's own right side rail (W - T,
# i.e. 50mm in from the absolute outside boundary, using the
# rail's own thickness as the natural stop rather than an
# arbitrary gap to open air). The small pulley is centred on
# the screw sprocket's own Y (belt alignment); the large
# pulley's own Y is still provisional - the drum's own
# matching sprocket isn't built yet.
jackshaft_x = (drum_cx + screw_bore_x) / 2
jackshaft_bottom_clearance = T + 20.0
jackshaft_z = jackshaft_bottom_clearance + jackshaft_large_pulley_radius

JACKSHAFT_PULLEY_GAP = 15.0      # margin between the 2 pulleys on the jackshaft

# flange_bearing.py's own housing isn't symmetric around its "w"
# reference - same empirically-measured offsets already used for
# the screw's own 2 bearings (FLANGE_BEARING_OFFSET_SMALL/_LARGE),
# reused here since it's the exact same scaled module.
jackshaft_bearing_far_w = (W - T) - FLANGE_BEARING_OFFSET_SMALL

jackshaft_small_pulley_y = screw_sprocket_y0
jackshaft_large_pulley_y = jackshaft_small_pulley_y - JACKSHAFT_PULLEY_GAP - JACKSHAFT_PULLEY_WIDTH

# Near bearing: moved close to the large (100T) pulley - only
# 20mm margin between the bearing's own outer face and the
# pulley's own near face (was 30mm, floating at a flange-clearance
# minimum with no particular reason to be that far off). Still
# clears the drum's rear flange (295mm radius, real collision risk
# found earlier) with plenty of room to spare since it's now
# further from the drum than before, not closer.
JACKSHAFT_AXLE_OVERHANG = 20.0
JACKSHAFT_BEARING_PULLEY_MARGIN = 20.0
jackshaft_bearing_near_w = jackshaft_large_pulley_y - JACKSHAFT_BEARING_PULLEY_MARGIN - FLANGE_BEARING_OFFSET_LARGE

# The near end is now cut flush with the bearing's own drum-facing
# face (no overhang past it) rather than sticking out
# JACKSHAFT_AXLE_OVERHANG further, like the far end still does -
# with the bearing this close to its own support tube (added
# later, standing right under it), an overhanging axle stub there
# would run straight into that tube.
jackshaft_near_end_y = jackshaft_bearing_near_w - FLANGE_BEARING_OFFSET_SMALL
jackshaft_length = (jackshaft_bearing_far_w + JACKSHAFT_AXLE_OVERHANG) - jackshaft_near_end_y
jackshaft_y_start = jackshaft_near_end_y

jackshaft_axle = doc.addObject("Part::Feature", "TW_JackshaftAxle")
jackshaft_axle.Shape = Part.makeCylinder(
    JACKSHAFT_DIAMETER / 2, jackshaft_length,
    App.Vector(jackshaft_x, jackshaft_y_start, jackshaft_z), App.Vector(0, 1, 0))

jackshaft_bearing_near = flange_bearing.make(
    doc, "TW_JackshaftBearingNear", u=jackshaft_x, v=jackshaft_z, w=jackshaft_bearing_near_w, axis="Y", flip=True)
jackshaft_bearing_far = flange_bearing.make(
    doc, "TW_JackshaftBearingFar", u=jackshaft_x, v=jackshaft_z, w=jackshaft_bearing_far_w, axis="Y", flip=False)

# Rotated 90 degrees about their own bore axis (Y) so the housing's
# own long dimension (the direction its 2 mounting-screw holes
# spread along) runs vertically along Z - the post's own long
# direction - instead of sideways along X. A rotation about the
# bore axis doesn't change the housing's own Y-extent (its axial
# thickness), so this is safe to do before anything below reads
# these bearings' own Y bounding box for the plates/posts/axle.
JACKSHAFT_BEARING_ROTATE = 90
for _b in (jackshaft_bearing_near, jackshaft_bearing_far):
    _shape = _b.Shape.copy()
    _shape.rotate(App.Vector(jackshaft_x, 0, jackshaft_z), App.Vector(0, 1, 0), JACKSHAFT_BEARING_ROTATE)
    _b.Shape = _shape


def _make_jackshaft_pulley(name, radius, y0):
    shape = Part.makeCylinder(radius, JACKSHAFT_PULLEY_WIDTH,
                               App.Vector(jackshaft_x, y0, jackshaft_z), App.Vector(0, 1, 0))
    bore = Part.makeCylinder(JACKSHAFT_PULLEY_BORE_DIAMETER / 2, JACKSHAFT_PULLEY_WIDTH + 2,
                              App.Vector(jackshaft_x, y0 - 1, jackshaft_z), App.Vector(0, 1, 0))
    shape = shape.cut(bore)
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    return obj


jackshaft_large_pulley = _make_jackshaft_pulley(
    "TW_JackshaftPulley100T", jackshaft_large_pulley_radius, jackshaft_large_pulley_y)
jackshaft_small_pulley = _make_jackshaft_pulley(
    "TW_JackshaftPulley40T", jackshaft_small_pulley_radius, jackshaft_small_pulley_y)

# Drum's own belt sprocket (50T) - Y matches the jackshaft's large
# pulley exactly (belt alignment), X/Z match the drum shaft's own
# centreline. Bore uses the drum shaft's real 50mm diameter (+5mm
# margin), not the 25mm jackshaft/screw convention.
DRUM_SPROCKET_TEETH = 50
DRUM_SPROCKET_BORE_DIAMETER = config.SHAFT_DIAMETER + 5.0

drum_sprocket_radius = DRUM_SPROCKET_TEETH * HTD5M_PITCH / (2 * math.pi)
drum_sprocket_y0 = jackshaft_large_pulley_y
drum_sprocket_shape = Part.makeCylinder(
    drum_sprocket_radius, JACKSHAFT_PULLEY_WIDTH,
    App.Vector(drum_cx, drum_sprocket_y0, drum_cz), App.Vector(0, 1, 0))
drum_sprocket_bore = Part.makeCylinder(
    DRUM_SPROCKET_BORE_DIAMETER / 2, JACKSHAFT_PULLEY_WIDTH + 2,
    App.Vector(drum_cx, drum_sprocket_y0 - 1, drum_cz), App.Vector(0, 1, 0))
drum_sprocket = doc.addObject("Part::Feature", "TW_DrumSprocket50T")
drum_sprocket.Shape = drum_sprocket_shape.cut(drum_sprocket_bore)

# ------------------------------------------------------
# Belt placeholders - flat, thin strips following the real
# external-tangent line between each pulley pair (not just a
# center-to-center line), so they at least visually hug the
# pulleys correctly. No wrap-around arcs modelled, just the
# straight run.
# ------------------------------------------------------

BELT_THICKNESS = 3.0
BELT_COLOR = (0.35, 0.2, 0.05)


def _external_tangent_points(c1, r1, c2, r2):
    """Both external tangent lines (a belt loop has 2 straight runs,
    one on each side of the pulleys, not just one). Also returns
    each pair's own outward normal (the same direction used to
    reach the tangent point from each pulley's own centre), so the
    belt's thickness can be added outward from that point instead
    of split around it (which would dip half the thickness back
    into the pulley's own material)."""
    dx = c2[0] - c1[0]
    dz = c2[1] - c1[1]
    d = math.hypot(dx, dz)
    phi = math.atan2(dz, dx)
    alpha = math.asin((r1 - r2) / d)
    pairs = []
    for theta in (phi + math.pi / 2 - alpha, phi - math.pi / 2 + alpha):
        nx, nz = math.cos(theta), math.sin(theta)
        t1 = (c1[0] + r1 * nx, c1[1] + r1 * nz)
        t2 = (c2[0] + r2 * nx, c2[1] + r2 * nz)
        pairs.append((t1, t2, (nx, nz)))
    return pairs


def _make_belt_strip(t1, t2, normal, y0, width):
    nx, nz = normal
    p0 = App.Vector(t1[0], y0, t1[1])
    p1 = App.Vector(t1[0] + nx * BELT_THICKNESS, y0, t1[1] + nz * BELT_THICKNESS)
    p2 = App.Vector(t2[0] + nx * BELT_THICKNESS, y0, t2[1] + nz * BELT_THICKNESS)
    p3 = App.Vector(t2[0], y0, t2[1])
    face = Part.Face(Part.makePolygon([p0, p1, p2, p3, p0]))
    return face.extrude(App.Vector(0, width, 0))


def _make_belt(name, c1, r1, c2, r2, y0, width):
    pairs = _external_tangent_points(c1, r1, c2, r2)
    strip_a = _make_belt_strip(pairs[0][0], pairs[0][1], pairs[0][2], y0, width)
    strip_b = _make_belt_strip(pairs[1][0], pairs[1][1], pairs[1][2], y0, width)
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = strip_a.fuse(strip_b)
    return obj


belt_drum_to_jackshaft = _make_belt(
    "TW_BeltDrumToJackshaft",
    (drum_cx, drum_cz), drum_sprocket_radius,
    (jackshaft_x, jackshaft_z), jackshaft_large_pulley_radius,
    drum_sprocket_y0, JACKSHAFT_PULLEY_WIDTH)

belt_jackshaft_to_screw = _make_belt(
    "TW_BeltJackshaftToScrew",
    (jackshaft_x, jackshaft_z), jackshaft_small_pulley_radius,
    (screw_bore_x, screw_bore_z), screw_sprocket_radius,
    jackshaft_small_pulley_y, JACKSHAFT_PULLEY_WIDTH)

# 428 chain, motor to drum - placeholder (real 3D reference files
# for the chain are Autodesk Inventor format, not importable into
# FreeCAD here). Reuses the exact same tangent-line technique as
# the belts above (both runs, not just one - the same lesson
# already learned building those) rather than modelling individual
# links. TW_MotorSprocket and TW_DrumAxleSprocket76T are already
# coplanar (both Y 207-220, aligned earlier for this exact chain),
# so one shared y0/width works for both ends.
chain_motor_to_drum = _make_belt(
    "TW_ChainMotorToDrum",
    (motor_cx, motor_cz), sprocket.OUTER_DIAMETER / 2,
    (drum_cx, drum_cz), drum_axle_sprocket_radius,
    motor_y, sprocket.WIDTH)

# ------------------------------------------------------
# Jackshaft frame extension - real support structure for the 2
# jackshaft bearings (still floating in space until now). First
# a new 700mm cross tube straight under the axle, spanning the
# same run as TW_CrossFrontBottom/TW_CrossRearBottom; then 2
# vertical posts rising to meet each bearing - one welded onto
# this new cross tube (near bearing, drum side), one welded onto
# the existing TW_RightBottom_End rail directly (far bearing).
# No holes needed: each bearing mounts flush against its own
# post's inner face (the face pointing toward the other post),
# same convention as the reversing screw's own mount tubes - the
# post's own solid body stops right where the bearing starts,
# rather than reaching past it. This let the near post move
# closer to the drum (post ends where the bearing begins, instead
# of straddling it) and let the far post land fully on top of
# TW_RightBottom_End instead of only partly overlapping it.
# ------------------------------------------------------

right_bottom_rail = doc.getObject("TW_RightBottom_End")
left_bottom_rail = doc.getObject("TW_LeftBottom_End")

jackshaft_cross_x = jackshaft_x - T / 2
jackshaft_cross_tube = tube.make(doc, "TW_JackshaftCrossBottom", W - 2 * T, axis="Y",
                                  x=jackshaft_cross_x, y=T, z=0)

# TW_MotorMountBasePlate, deferred from the motor mount section
# above - grows to reach this tube's own real inside (near) face,
# per the user, for real support there in addition to
# TW_CrossFrontBottom. The 2 right-side mounting holes move out
# with it automatically (see make_base_plate).
motor_mount_base_plate = motor_mount.make_base_plate(
    doc, "TW_MotorMountBasePlate", motor_cx,
    [motor_mount_shaft_end_y, motor_mount_connector_end_y], motor_mount_base_top_z,
    x_max_target=jackshaft_cross_tube.Shape.BoundBox.XMin)

# Second plate, identical footprint, stacked directly under the
# first (10mm lower - exactly BASE_PLATE_THICKNESS, so it touches
# flush, no gap) - per the user, fits in the same gap between
# TW_CrossFrontBottom and TW_JackshaftCrossBottom. Its 4 holes are
# slots instead (+-25mm in X) for chain tensioning - the bolts stay
# fixed to the frame, this plate (and the whole motor group bolted
# to it) slides along them.
CHAIN_TENSION_SLOT_TRAVEL = 25.0

motor_mount_lower_plate = motor_mount.make_base_plate(
    doc, "TW_MotorMountBasePlateLower", motor_cx,
    [motor_mount_shaft_end_y, motor_mount_connector_end_y],
    motor_mount_base_top_z - motor_mount.BASE_PLATE_THICKNESS,
    x_max_target=jackshaft_cross_tube.Shape.BoundBox.XMin,
    slot_travel=CHAIN_TENSION_SLOT_TRAVEL)

# 2 standard 50x50 tubes connecting TW_CrossFrontBottom and
# TW_JackshaftCrossBottom, one flush against each Y-edge of
# motor_mount_lower_plate - sandwiching it between them, per the
# user. Same X-span as the plates themselves (the gap between the
# 2 cross tubes), same Z-height convention as every other frame
# tube in this project (Z 0-50).
_lower_plate_bb = motor_mount_lower_plate.Shape.BoundBox
_sandwich_x = _lower_plate_bb.XMin
_sandwich_length = _lower_plate_bb.XMax - _lower_plate_bb.XMin
motor_mount_sandwich_near = tube.make(
    doc, "TW_MotorMountSandwichNear", _sandwich_length, axis="X",
    x=_sandwich_x, y=_lower_plate_bb.YMin - T, z=0)
motor_mount_sandwich_far = tube.make(
    doc, "TW_MotorMountSandwichFar", _sandwich_length, axis="X",
    x=_sandwich_x, y=_lower_plate_bb.YMax, z=0)

motor_mount_group.Group = list(motor_mount_group.Group) + [motor_mount_base_plate]
# motor_mount_lower_plate and the 2 sandwich tubes are frame
# structure (bolted to TW_CrossFrontBottom/TW_JackshaftCrossBottom,
# not part of the motor mount itself) - grouped under frame_group
# instead, see below.

JACKSHAFT_POST_FEET_MARGIN = 20.0
jackshaft_post_height = (jackshaft_bearing_near.Shape.BoundBox.ZMax + JACKSHAFT_POST_FEET_MARGIN) - T

# Mounting plates between each jackshaft post and its own bearing -
# same tapping-into-a-4mm-wall concern as the reversing screw's own
# mounts, same 80x46x4mm convention (reusing FLANGE_MOUNT_PLATE_X/Z/
# THICKNESS), but no holes needed here - the jackshaft axle only
# spans between the 2 bearings themselves, it never reaches either
# post. Each post is pushed FLANGE_MOUNT_PLATE_THICKNESS further out
# so the bearings stay at their own already-calibrated axial
# position (unchanged) while a real plate now sits in the gap that
# opens up.
jackshaft_bearing_near_bb = jackshaft_bearing_near.Shape.BoundBox
jackshaft_bearing_far_bb = jackshaft_bearing_far.Shape.BoundBox

jackshaft_post_near = tube.make(
    doc, "TW_JackshaftPostNear", jackshaft_post_height, axis="Z",
    x=jackshaft_cross_x, y=jackshaft_bearing_near_bb.YMin - FLANGE_MOUNT_PLATE_THICKNESS - T, z=T)
jackshaft_post_far = tube.make(
    doc, "TW_JackshaftPostFar", jackshaft_post_height, axis="Z",
    x=jackshaft_cross_x, y=jackshaft_bearing_far_bb.YMax + FLANGE_MOUNT_PLATE_THICKNESS, z=T)

# Rotated 90 degrees to match the bearings above - FLANGE_MOUNT_PLATE_Z
# (46, the housing's own short dimension) now runs along X, and
# FLANGE_MOUNT_PLATE_X (80, the housing's long dimension) runs along
# Z, vertically in the post's own direction.
jackshaft_mount_plate_near = doc.addObject("Part::Box", "TW_JackshaftMountPlateNear")
jackshaft_mount_plate_near.Length = FLANGE_MOUNT_PLATE_Z
jackshaft_mount_plate_near.Width = FLANGE_MOUNT_PLATE_THICKNESS
jackshaft_mount_plate_near.Height = FLANGE_MOUNT_PLATE_X
jackshaft_mount_plate_near.Placement.Base = App.Vector(
    jackshaft_x - FLANGE_MOUNT_PLATE_Z / 2, jackshaft_bearing_near_bb.YMin - FLANGE_MOUNT_PLATE_THICKNESS,
    jackshaft_z - FLANGE_MOUNT_PLATE_X / 2)

jackshaft_mount_plate_far = doc.addObject("Part::Box", "TW_JackshaftMountPlateFar")
jackshaft_mount_plate_far.Length = FLANGE_MOUNT_PLATE_Z
jackshaft_mount_plate_far.Width = FLANGE_MOUNT_PLATE_THICKNESS
jackshaft_mount_plate_far.Height = FLANGE_MOUNT_PLATE_X
jackshaft_mount_plate_far.Placement.Base = App.Vector(
    jackshaft_x - FLANGE_MOUNT_PLATE_Z / 2, jackshaft_bearing_far_bb.YMax,
    jackshaft_z - FLANGE_MOUNT_PLATE_X / 2)


def _make_axis_z_top_cap(name, tube_bb):
    cap = doc.addObject("Part::Box", name)
    cap.Length = cap_inset
    cap.Width = cap_inset
    cap.Height = config.TUBE_WALL
    cap.Placement.Base = App.Vector(
        tube_bb.XMin + config.TUBE_WALL, tube_bb.YMin + config.TUBE_WALL, tube_bb.ZMax - config.TUBE_WALL)
    return cap


jackshaft_post_near_cap = _make_axis_z_top_cap("TW_JackshaftPostNearCap", jackshaft_post_near.Shape.BoundBox)
jackshaft_post_far_cap = _make_axis_z_top_cap("TW_JackshaftPostFarCap", jackshaft_post_far.Shape.BoundBox)

# Axle shortened to just the span between the 2 bearings' own
# inner-facing ends, instead of overhanging past either one. Used
# to reference the posts' own inner faces directly (before the
# mounting plates above existed, post face == bearing face, so it
# was the same thing) - now that each post has moved out to make
# room for a plate, this must reference the bearings themselves,
# which haven't moved.
jackshaft_axle.Shape = Part.makeCylinder(
    JACKSHAFT_DIAMETER / 2,
    jackshaft_bearing_far_bb.YMax - jackshaft_bearing_near_bb.YMin,
    App.Vector(jackshaft_x, jackshaft_bearing_near_bb.YMin, jackshaft_z), App.Vector(0, 1, 0))

# jackshaft_cross_tube, jackshaft_post_near/far and their caps are
# frame structure, not mechanism - grouped/coloured under
# frame_group instead, see below.
jackshaft_group = doc.addObject("App::DocumentObjectGroup", "jackshaft_group")
jackshaft_group.Group = [jackshaft_axle, jackshaft_bearing_near, jackshaft_bearing_far,
                          jackshaft_large_pulley, jackshaft_small_pulley, screw_sprocket,
                          drum_sprocket, belt_drum_to_jackshaft, belt_jackshaft_to_screw]

# ------------------------------------------------------
# Screw-hole placeholder pins, all 5 flange_bearing mountings (the
# 3 on the reversing screw's tubes + the 2 on the jackshaft posts) -
# a fabrication aid, not a real fastener: marks exactly where the
# plate and tube behind it need drilling for the real mounting
# screws, since the tube ends get welded shut and can't be reached
# afterward (same reasoning as the mounting plates themselves).
# Each bearing's own real screw holes are found empirically on its
# ALREADY-PLACED shape (matching radius ~3.12mm, the same real bolt
# holes originally found on the raw STEP file) rather than hand-
# tracking them through each bearing's own flip/rotate/translate -
# this way it's correct regardless of flip or the extra 90 degree
# rotation applied to the jackshaft bearings above.
# ------------------------------------------------------


def _find_bearing_screw_holes(shape):
    """Returns one (x, z, y_min, y_max) tuple per real mounting screw
    hole (2 expected) on a flange_bearing housing, by scanning its
    own circular edges for the known ~3.12mm radius and clustering
    by (x, z) position - the same technique used to discover this
    bolt pattern in the first place (see flange_bearing.py)."""
    candidates = []
    for e in shape.Edges:
        try:
            curve = e.Curve
        except Exception:
            continue
        if curve.TypeId == "Part::GeomCircle" and 3.0 < curve.Radius < 3.3:
            candidates.append(curve.Center)
    clusters = []
    for c in candidates:
        for cluster in clusters:
            if abs(cluster[0].x - c.x) < 1.0 and abs(cluster[0].z - c.z) < 1.0:
                cluster.append(c)
                break
        else:
            clusters.append([c])
    holes = []
    for cluster in clusters:
        xs = [p.x for p in cluster]
        zs = [p.z for p in cluster]
        ys = [p.y for p in cluster]
        holes.append((sum(xs) / len(xs), sum(zs) / len(zs), min(ys), max(ys)))
    return holes


def _make_bearing_screw_pins(doc, name_prefix, bearing_obj, plate_obj, tube_obj, away_sign):
    """away_sign: +1 if the bearing sits on the tube/post's +Y side
    (extending further away from it in +Y), -1 if on its -Y side.
    Builds a BEARING_SCREW_PIN_DIAMETER placeholder pin through each
    of the bearing's 2 real screw holes, spanning from
    BEARING_SCREW_PIN_OVERHANG past the hole's own outer (away from
    the tube) opening to the same overhang past the tube/post's own
    near wall inner surface - and drills a matching clearance hole
    through the plate and that tube/post wall using the pin itself
    as the cutting tool."""
    pin_r = config.BEARING_SCREW_PIN_DIAMETER / 2
    overhang = config.BEARING_SCREW_PIN_OVERHANG
    # The bearing sits flush against whichever tube/post face is on
    # its OWN side (away_sign>0 means the bearing is on the tube's
    # +Y/YMax face, so that's the wall it's touching) - the "inner
    # surface" is that SAME wall, one TUBE_WALL deeper into the
    # tube's own hollow interior, not the tube's opposite face.
    tube_bb = tube_obj.Shape.BoundBox
    if away_sign > 0:
        tube_wall_inner_y = tube_bb.YMax - config.TUBE_WALL
    else:
        tube_wall_inner_y = tube_bb.YMin + config.TUBE_WALL

    pins = []
    holes = _find_bearing_screw_holes(bearing_obj.Shape)
    for i, (x, z, y_min, y_max) in enumerate(holes):
        outer_y = y_max if away_sign > 0 else y_min
        pin_outer = outer_y + away_sign * overhang
        pin_inner = tube_wall_inner_y - away_sign * overhang
        y_start = min(pin_outer, pin_inner)
        length = abs(pin_outer - pin_inner)

        pin_shape = Part.makeCylinder(pin_r, length, App.Vector(x, y_start, z), App.Vector(0, 1, 0))
        plate_obj.Shape = plate_obj.Shape.cut(pin_shape)
        tube_obj.Shape = tube_obj.Shape.cut(pin_shape)

        pin_obj = doc.addObject("Part::Feature", f"{name_prefix}_Pin{i + 1}")
        pin_obj.Shape = pin_shape
        pins.append(pin_obj)
    return pins


screw_bearing_pins = (
    _make_bearing_screw_pins(doc, "TW_FlangeBearingNear", flange_bearing_near, flange_mount_plate_near,
                              screw_mount_near, away_sign=1)
    + _make_bearing_screw_pins(doc, "TW_FlangeBearingFar", flange_bearing_far, flange_mount_plate_far,
                                screw_mount_far, away_sign=-1)
    + _make_bearing_screw_pins(doc, "TW_FlangeBearingFarOuter", flange_bearing_far_outer,
                                flange_mount_plate_far_outer, screw_mount_far, away_sign=1)
)

jackshaft_bearing_pins = (
    _make_bearing_screw_pins(doc, "TW_JackshaftBearingNear", jackshaft_bearing_near, jackshaft_mount_plate_near,
                              jackshaft_post_near, away_sign=1)
    + _make_bearing_screw_pins(doc, "TW_JackshaftBearingFar", jackshaft_bearing_far, jackshaft_mount_plate_far,
                                jackshaft_post_far, away_sign=-1)
)

jackshaft_group.Group = list(jackshaft_group.Group) + jackshaft_bearing_pins

# ------------------------------------------------------
# Frame group: everything frame.make() created (including
# the hidden intermediate mitre cut/cutter objects, which
# would otherwise still clutter the top-level tree even
# though invisible). TW_CrossRearTop was later modified
# into TW_CrossRearTop_Bore by the intake drill above, so
# use that final version instead of the pre-drill original.
# Also includes the 4 bearing mounting posts (post1-4) and,
# by request, several other structural tubes/plates that were
# originally grouped with their own mechanism (battery stops,
# the intake mount tube, and the winding rail/screw riser/screw
# mount tubes + their end caps) - frame structure, not part of
# those mechanisms.
# ------------------------------------------------------

frame_group_objects = [
    doc.getObject("TW_CrossRearTop_Bore") if obj.Name == "TW_CrossRearTop" else obj
    for obj in frame_objects
] + [post1, post2, post3, post4,
     intake_mount_tube_bore, battery_stop_left, battery_stop_right,
     winding_rail, screw_riser, screw_mount_far, screw_mount_near,
     flange_mount_plate_near, flange_mount_plate_far, flange_mount_plate_far_outer,
     screw_mount_near_cap_inner, screw_mount_near_cap_outer,
     screw_mount_far_cap_inner, screw_mount_far_cap_outer,
     screw_riser_cap_near, screw_riser_cap_far,
     left_mount_plate, left_stiffener_plate, right_mount_plate, right_stiffener_plate,
     battery_cross_front, battery_cross_rear,
     jackshaft_cross_tube, jackshaft_post_near, jackshaft_post_far,
     jackshaft_post_near_cap, jackshaft_post_far_cap,
     jackshaft_mount_plate_near, jackshaft_mount_plate_far,
     motor_mount_lower_plate, motor_mount_sandwich_near, motor_mount_sandwich_far] + \
    screw_bearing_pins + \
    intake_reinforcement_tubes + reinforcement_caps + [reinforcement_cover]

# Mitre construction leftovers (the pre-cut original beams and the
# cutter boxes) already have their own Visibility=False, set by
# mitres.py at creation time - but a DocumentObjectGroup's own
# visibility toggle overrides each member's individual state, so
# they were reappearing whenever frame_group itself got toggled
# visible. Split them into a separate, permanently-hidden group so
# toggling frame_group no longer cascades to them.
frame_visible_objects = [o for o in frame_group_objects if o.Visibility]
frame_hidden_objects = [o for o in frame_group_objects if not o.Visibility]

frame_group = doc.addObject("App::DocumentObjectGroup", "frame_group")
frame_group.Group = frame_visible_objects

frame_construction_group = doc.addObject("App::DocumentObjectGroup", "frame_group_construction")
frame_construction_group.Group = frame_hidden_objects
frame_construction_group.Visibility = False

# ------------------------------------------------------
# Colours - purely cosmetic, no effect on geometry. Guarded
# against headless (freecadcmd) runs, where ViewObject is
# None (no GUI, nothing to colour).
# ------------------------------------------------------


def _set_color(obj, rgb):
    if obj.ViewObject is not None:
        obj.ViewObject.ShapeColor = rgb


FRAME_COLOR = (0.3, 0.3, 0.3)  # dark grey, not pure black - keeps edge lines readable against it - one tint lighter than the original 0.2
DRUM_COLOR = (0.8, 0.0, 0.0)
STEEL_COLOR = (0.75, 0.75, 0.75)

for obj in frame_visible_objects:
    _set_color(obj, FRAME_COLOR)

for name in ("barrel", "flange_front", "flange_rear"):
    _set_color(drum_parts[name], DRUM_COLOR)

for obj in (drum_parts["shaft"], bearing1, bearing2):
    _set_color(obj, STEEL_COLOR)

for obj in (belt_drum_to_jackshaft, belt_jackshaft_to_screw, chain_motor_to_drum):
    _set_color(obj, BELT_COLOR)

# Update the document
doc.recompute()

view.reset()