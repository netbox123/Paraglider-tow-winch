"""
Giga Display Shield panel-mount frame.

Z convention used throughout this module: Z=0 is the frame's
own front (outward-facing, LCD-visible) face. Everything else
(flange, collar, bosses) extends in -Z, back into the box.
"""

import FreeCAD as App
import Part

import config


def _rounded_rect(length, width, height, radius, z0):
    """A box (length x width x height) centred on the Z axis in
    X/Y, starting at z0 and extending in +Z, with its 4 vertical
    edges filleted to radius."""

    box = Part.makeBox(length, width, height,
                        App.Vector(-length / 2, -width / 2, z0))
    edges = [e for e in box.Edges
              if abs(e.Vertexes[0].Point.z - e.Vertexes[1].Point.z) > height * 0.9]
    return box.makeFillet(radius, edges)


def make(doc):
    # Collar sized off the inner (shield) screw holes' own
    # centres, not the shield's full PCB envelope - only the
    # collar needs to pass through the panel, the PCB itself
    # stays inside the box.
    collar_length = 2 * (config.SHIELD_HOLE_X + config.COLLAR_EDGE_MARGIN)
    collar_width  = 2 * (config.SHIELD_HOLE_Y + config.COLLAR_EDGE_MARGIN)
    flange_length = collar_length + 2 * config.FLANGE_OVERLAP
    flange_width  = collar_width + 2 * config.FLANGE_OVERLAP

    flange = _rounded_rect(flange_length, flange_width, config.FLANGE_THICKNESS,
                            config.FLANGE_CORNER_RADIUS, -config.FLANGE_THICKNESS)
    collar = _rounded_rect(collar_length, collar_width, config.COLLAR_HEIGHT,
                            config.COLLAR_CORNER_RADIUS,
                            -config.FLANGE_THICKNESS - config.COLLAR_HEIGHT)

    body = flange.fuse(collar)

    # LCD cutout - through the full depth, reusing the reference
    # case's own window size/offset so the shield's glass lines
    # up with it exactly.
    cutout = Part.makeBox(
        config.SHIELD_CUTOUT_LENGTH, config.SHIELD_CUTOUT_WIDTH,
        config.FLANGE_THICKNESS + config.COLLAR_HEIGHT + 2,
        App.Vector(config.SHIELD_CUTOUT_OFFSET_X - config.SHIELD_CUTOUT_LENGTH / 2,
                   config.SHIELD_CUTOUT_OFFSET_Y - config.SHIELD_CUTOUT_WIDTH / 2,
                   -config.FLANGE_THICKNESS - config.COLLAR_HEIGHT - 1))
    body = body.cut(cutout)

    # RGB LED (DL1) light-pipe hole - straight through-hole, to
    # be filled with a piece of clear acrylic rod later.
    led_hole = Part.makeCylinder(
        config.LED_HOLE_DIAMETER / 2, config.FLANGE_THICKNESS + config.COLLAR_HEIGHT + 2,
        App.Vector(config.LED_HOLE_X, config.LED_HOLE_Y,
                   -config.FLANGE_THICKNESS - config.COLLAR_HEIGHT - 1),
        App.Vector(0, 0, 1))
    body = body.cut(led_hole)

    # 4 shield mounting holes, reusing the reference case's own
    # bolt pattern - through-hole + front-face counterbore for
    # the screw head.
    hole_depth = config.FLANGE_THICKNESS + config.COLLAR_HEIGHT + 2
    for x_sign in (-1, 1):
        for y_sign in (-1, 1):
            hx = x_sign * config.SHIELD_HOLE_X
            hy = y_sign * config.SHIELD_HOLE_Y

            through = Part.makeCylinder(
                config.SHIELD_HOLE_DIAMETER / 2, hole_depth,
                App.Vector(hx, hy, -config.FLANGE_THICKNESS - config.COLLAR_HEIGHT - 1),
                App.Vector(0, 0, 1))
            body = body.cut(through)

            counterbore = Part.makeCylinder(
                config.SHIELD_HOLE_COUNTERBORE_DIAMETER / 2,
                config.SHIELD_HOLE_COUNTERBORE_DEPTH + 1,
                App.Vector(hx, hy, -config.SHIELD_HOLE_COUNTERBORE_DEPTH),
                App.Vector(0, 0, 1))
            body = body.cut(counterbore)

    # Standoff bosses at the same 4 positions - solid posts from
    # just behind the counterbore down to a tip sitting exactly
    # LCD_TO_PCB_HEIGHT below the front face (Z=0), so the
    # shield's PCB lands at the reference case's own real depth.
    # A blind pilot hole in each tip takes a self-tapping M3
    # screw (the through-hole above already clears the shank).
    boss_top_z = -config.SHIELD_HOLE_COUNTERBORE_DEPTH
    boss_tip_z = -config.LCD_TO_PCB_HEIGHT
    boss_height = boss_top_z - boss_tip_z
    if boss_height <= 0:
        raise ValueError(
            "LCD_TO_PCB_HEIGHT is shallower than the counterbore depth - "
            "no room left for a standoff boss, check config.py")

    for x_sign in (-1, 1):
        for y_sign in (-1, 1):
            hx = x_sign * config.SHIELD_HOLE_X
            hy = y_sign * config.SHIELD_HOLE_Y

            boss = Part.makeCylinder(
                config.BOSS_DIAMETER / 2, boss_height,
                App.Vector(hx, hy, boss_tip_z), App.Vector(0, 0, 1))
            body = body.fuse(boss)

            pilot = Part.makeCylinder(
                config.BOSS_HOLE_DIAMETER / 2, config.BOSS_HOLE_DEPTH,
                App.Vector(hx, hy, boss_tip_z - 1), App.Vector(0, 0, 1))
            body = body.cut(pilot)

    # No flange mounting holes - the frame is glued into the
    # panel, not screwed.

    obj = doc.addObject("Part::Feature", "GigaFrame")
    obj.Shape = body
    return obj
