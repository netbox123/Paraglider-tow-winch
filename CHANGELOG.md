0.0.1
- Repository created
- README
- Config.py

0.0.2
- First frame generated

0.0.3
- Drum added

Version 0.0.5

- FreeCAD development environment working
- GitHub launcher working
- Parametric frame generator working
- Hollow tube generator working
- Ready to add 45° mitres

Version 0.1

- Frame: 45° mitres on both side frames, battery boxes
- Drum: barrel, flanges, shaft, bearings, chain and belt sprockets
- Motor mount and chain drivetrain (QS165, 14T/76T, 5.4286:1)
- Rope intake: self-aligning swivel with rollers, guide wheels, line cutter
- Level wind: Hiwin linear rail, self-reversing screw, flange bearings, jackshaft belt reduction
- Winding pulley and load cell mount on a rod-end pivot
- Electronics architecture decided (not yet built): Fardriver CAN motor controller, ESP32 PID/CAN node, GIGA R1 + Display UI, LoRa pilot handheld - see `docs/electronics.md`
- Frame fabrication started in parallel with CAD work - see `docs/build_log.md`
- `docs/rope_calculations.md`: drive-train tension/speed analysis, plus a level-wind synchronization ratio check that found the current jackshaft pulley selection runs the screw ~2x too fast for a flush wind - flagged for a fix before ordering real pulleys

