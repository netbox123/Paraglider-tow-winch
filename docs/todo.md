# TODO

## Frame
- [x] Hollow 50x50x4 tube
- [x] 45° mitres (side frames) - cross members still plain box, not yet hollow/mitred
- [ ] Automatic cut list
- [ ] Weight calculation

## Drum
- [x] 390 mm barrel
- [x] 590 mm flanges
- [x] 50 mm shaft
- [x] Kart sprocket hub (76T chain sprocket + 50T belt sprocket, placeholder envelopes)
- [ ] Inner support discs (config values exist, not yet modelled)

## Drivetrain
- [x] Motor mount + chain drive (motor, 14T/76T sprockets)
- [ ] Motor mount bracket (currently a placeholder envelope, only reference photos exist)
- [ ] **Level-wind belt/jackshaft ratio needs fixing** - current 50T/100T/40T/66T pulley selection gives a 3.3:1 drum:screw ratio, but a 20mm screw lead and 3mm rope needs 6.67:1 for a flush wind (see [rope_calculations.md](rope_calculations.md#level-wind-synchronization-ratio)). Not yet built in real hardware - fix before ordering pulleys.

## Level wind
- [x] Diamond reversing screw (RS2020, real STEP file)
- [x] Hiwin rail (real IGES file)
- [x] Floating guide (rod-end pivot + clevis)
- [x] Load cell pulley

## Electronics
- [x] QS165 motor selected and modelled
- [x] Architecture decided: Fardriver ND961200-CAN controller, ESP32 PID/CAN node, GIGA R1 + Display UI, LoRa handheld (see [electronics.md](electronics.md))
- [x] Resolve Fardriver throttle-by-CAN frame spec - CAN61 protocol obtained from Fardriver support
- [x] Mainboard PCB (ESP32-S3 DevKitC-1) designed, placed, routed, DRC/ERC clean - ordering
- [x] Define GIGA/handheld JSON protocol and state machine (see [software.md](software.md))
- [ ] Build ESP32 PID/CAN node (firmware) - comms skeleton only so far, no PID/CAN/sensor logic yet
- [ ] Build GIGA R1 + Display UI node - mirror the mainboard's RGB status LED (`state` -> color, see esp32_mainboard.ino's `updateStatusLed()`) on the GIGA's own onboard `LEDR`/`LEDG`/`LEDB` pins; `state` is already in every telemetry message, no protocol change needed
- [ ] Build LoRa pilot handheld + winch-side module - pilot handheld confirmed has a WS2812B RGB LED on GPIO38, same status mirroring trick applies there too
- [ ] PID tension control (tuning, once hardware exists)
- [ ] Pre-flight rope proof test

## Safety
- [ ] 40 kg until tree height
- [ ] Ramp to pilot weight
- [ ] Cable break behaviour