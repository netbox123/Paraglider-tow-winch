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
- Electronics architecture decided (not yet built): Fardriver CAN motor controller, ESP32 PID/CAN node, GIGA R1 + Display UI, LoRa pilot handheld - see [`docs/electronics.md`](docs/electronics.md)
- Frame fabrication started in parallel with CAD work - see [`docs/build_log.md`](docs/build_log.md)
- [`docs/rope_calculations.md`](docs/rope_calculations.md): drive-train tension/speed analysis, plus a level-wind synchronization ratio check that found the current jackshaft pulley selection runs the screw ~2x too fast for a flush wind - flagged for a fix before ordering real pulleys

Version 0.2

- Mainboard PCB (ESP32-S3 N16R8 DevKitC-1) fully designed, placed and routed - DRC/ERC clean, ready to order (see [`docs/electronics.md`](docs/electronics.md))
- Fardriver throttle-by-CAN protocol (CAN61) resolved - full VCU control/telemetry frame spec obtained from Fardriver support
- Battery architecture revised: single 30-cell string under one BMS, replacing the earlier two-independent-box-in-series plan
- [`docs/control_philosophy.md`](docs/control_philosophy.md): added a daily calibration step (100 kg reference pull - calibrates the load cell and proof-tests the line)
- Documentation pass: cross-checked and updated against current project state, internal file references made clickable throughout

Unreleased

- Operator-display panel-mount frame ([`gigadisplay_holder/`](gigadisplay_holder/)): parametric FreeCAD bezel that mounts the GIGA Display Shield into the winchman box's front panel. All reference dimensions re-measured from the real board and the second test print fits - LCD window, M3 bolt pattern, screw-head counterbore and RGB-LED light-pipe hole. Panel thickness still a placeholder pending the box choice. See its [README](gigadisplay_holder/README.md).

