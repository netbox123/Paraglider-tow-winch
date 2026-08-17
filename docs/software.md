# Open Paraglider Tow Winch

# Software Architecture

Version 0.1 (first draft - ESP32 mainboard comms layer only, no PID/CAN control logic yet)

---

## Overview

Three firmware nodes, matching the hardware split in [electronics.md](electronics.md):

```
Load Cell ──▶ ESP32 (PID loop) ──CAN──▶ Fardriver Controller ──▶ QS165 Motor
                  │  ▲
              UART│  │UART
                  ▼  │
         Arduino GIGA R1 + Display        LoRa ◀────────────▶ LoRa
              (operator UI)          (winch-side Heltec)   (pilot Heltec)
```

- **ESP32 mainboard** (`firmware/esp32_mainboard/`) - the only node covered by this document's protocol definitions and the only one with firmware started so far. Runs the state machine and (eventually) the PID tension loop and CAN61 link to the Fardriver controller.
- **GIGA R1 + Display** - winch operator UI. Talks to the ESP32 over the `GIGA UART` link (hardware UART0, see "Transports" below). Full command surface, full telemetry. Its own firmware is not started yet.
- **Pilot's Heltec handheld** - talks to the ESP32 *indirectly*, via the winch-side Heltec LoRa module (itself just a UART-attached peripheral of the ESP32, see [electronics.md](electronics.md)'s LoRa section). Minimal command surface (deadman + tree-height button), reduced telemetry (status display only). Neither Heltec's firmware is started yet.

**Both links carry the same JSON protocol** (same message types, same field names) - this is a deliberate design decision carried over from [electronics.md](electronics.md#unified-operator-command-protocol): the ESP32 parses one protocol regardless of which link a message arrived on, rather than maintaining two separate command sets. A message's `src` field (see below) tells the ESP32 which device sent it, which is what actually gates which command fields are honored - not which physical UART it arrived on.

---

## Transports

| Link | ESP32 pins | Arduino object | Notes |
|---|---|---|---|
| GIGA UART | GPIO43 (U0TXD) / GPIO44 (U0RXD) | `Serial0` | Hardware UART0. **Gotcha:** on the ESP32-S3 Arduino core, `Serial` defaults to the native USB-CDC port (GPIO19/20, the DevKitC-1's own USB-C), not this UART - use `Serial0` explicitly for this link, and reserve plain `Serial` for USB debug output only. Don't let the two get mixed up. |
| Heltec (winch-side) UART | GPIO14 (TXD) / GPIO21 (RXD) | `Serial1` | Bridges to the Heltec's own U0TXD/U0RXD (see [electronics.md](electronics.md)'s LoRa section) - the Heltec re-transmits whatever it receives here over LoRa to the pilot's matching Heltec, and forwards whatever it receives over LoRa back over this same UART. The ESP32 firmware doesn't need to know anything about LoRa itself, only that this UART is slower and lossier than the GIGA link. |

**Framing:** one **compact (no whitespace) JSON object per line**, terminated with `\n`. Baud rate 115200 on both links (the Heltec link is bandwidth-limited by the LoRa hop behind it, not by this UART - 115200 just needs to comfortably outrun the LoRa air rate, not match it).

**Why JSON, not a packed binary frame:** this is a human-interaction link (button presses, a display refreshing a few times a second), not the CAN61 link's 20ms real-time control loop - there's no tight timing budget to justify binary framing's added complexity. JSON is trivially debuggable from a serial monitor, which matters a lot for a first version. Revisit only if LoRa airtime/duty-cycle limits become a real constraint once tested on real hardware.

---

## Message Types

Every message has a `type` field that's either `"cmd"` (host -> ESP32) or `"telemetry"` (ESP32 -> host), plus a monotonically increasing `seq` (per-sender counter, wraps at 65535) so a receiver can notice dropped or out-of-order messages.

### `cmd` - host to ESP32

```json
{"type":"cmd","seq":42,"src":"giga","deadman":true,"tree_height":false,"state_cmd":"start_tow","tension_setpoint_kg":70,"fault_reset":false,"operating_mode":"winchman","pilot_weight_kg":85}
```

| Field | Type | Sent by | Meaning |
|---|---|---|---|
| `type` | `"cmd"` | both | message discriminator |
| `seq` | uint16 | both | per-sender sequence counter |
| `src` | `"giga"` \| `"handheld"` | both | **which device sent this** - the ESP32 uses this to decide which of the fields below it's allowed to act on (see "Field authority" below), not which UART it arrived on |
| `deadman` | bool | handheld | pilot is actively holding the deadman control. Safety-critical - see "Deadman timeout" below |
| `tree_height` | bool | handheld | pilot has manually signalled "above tree height" - one-shot trigger, commits the ramp to the selected tow profile (see [control_philosophy.md](control_philosophy.md#launch-philosophy)) |
| `state_cmd` | string, optional | giga | requested state-machine transition: `"calibrate"` (`IDLE`->`CALIBRATING`), `"calibration_done"` (`CALIBRATING`->`READY`, operator confirms the 100kg reference pull is done - see [control_philosophy.md](control_philosophy.md#calibrating)), `"start_tow"`, `"release"`, `"reset_fault"` (clears a latched fault **or** `EMERGENCY_STOPPED`, both return to `IDLE`), `"idle"`, `"emergency_stop"` (operator-triggered e-stop from GIGA - in addition to, not instead of, the mainboard's own local hardware e-stop switch, which forces this transition regardless of what any link is saying). Absent/omitted = no transition requested this message |
| `tension_setpoint_kg` | number, optional | giga | desired tow force, `TOW_FORCE_MIN`-`TOW_FORCE_MAX` kg (see `config.py`). A **numeric override**, not a named profile - profile-name-to-kg resolution, if wanted, happens in the GIGA's own UI, not on the wire (kept simple for this first version) |
| `fault_reset` | bool, optional | giga | acknowledge/clear a latched fault |
| `operating_mode` | `"solo"` \| `"winchman"`, optional | giga | set once at boot (see "Boot Configuration" below) - whether a winchman is operating the GIGA or the pilot is flying solo |
| `pilot_weight_kg` | number, optional | giga | set once at boot (see "Boot Configuration" below) - the pilot's weight for the day |

**Field authority (enforced on the ESP32, not just documented) - symmetric, each `src` is restricted to its own fields:**
- `src:"handheld"` can only affect `deadman` and `tree_height` - `state_cmd`, `tension_setpoint_kg`, `fault_reset`, `operating_mode` and `pilot_weight_kg` are silently ignored if present with that `src`, even if the handheld's own firmware never sends them.
- `src:"giga"` can only affect `state_cmd`, `tension_setpoint_kg`, `fault_reset`, `operating_mode` and `pilot_weight_kg` - `deadman`/`tree_height` from GIGA are likewise ignored, since those fields are meant to be the pilot's own live signal; letting the operator's UI set them too would defeat the point of the deadman check.

This is the wire-level version of the hardware design's own principle (see [electronics.md](electronics.md)'s winchman-remote section) that the pilot's remote gets a deliberately minimal, hard-to-misuse command surface - the ESP32 must not trust the far end's own firmware to self-restrict, since a link (LoRa especially) can be spoofed, glitched, or simply running old/buggy firmware.

### `telemetry` - ESP32 to host

```json
{"type":"telemetry","seq":1337,"state":"NORMAL_TOW","tension_kg":68.4,"tension_setpoint_kg":70,"rope_out_m":210.5,"rpm":842,"motor_current_a":38.2,"fault":false,"fault_code":0,"line_cut":false,"cal_valid":true,"boot_configured":true,"operating_mode":"winchman","pilot_weight_kg":85}
```

| Field | Type | Meaning |
|---|---|---|
| `type` | `"telemetry"` | message discriminator |
| `seq` | uint16 | per-sender sequence counter |
| `state` | string | current state machine state - one of `IDLE`, `CALIBRATING`, `READY`, `LAUNCH`, `UNDER_TREE_HEIGHT`, `NORMAL_TOW`, `PAY_OUT`, `RELEASE`, `RECOVERY`, `EMERGENCY_STOPPED` (see [control_philosophy.md](control_philosophy.md#state-machine)) |
| `tension_kg` | number | measured tow force (load cell) |
| `tension_setpoint_kg` | number | current PID setpoint (may differ from what GIGA last requested, e.g. mid-ramp) |
| `rope_out_m` | number | estimated rope paid out (derived from hall sensors + drum diameter estimate) |
| `rpm` | number | drum RPM (from hall sensors) |
| `motor_current_a` | number | realized motor current, once the CAN61 telemetry frame is wired up - `0` / stale until then |
| `fault` | bool | true if a fault is latched |
| `fault_code` | integer | 0 = no fault; specific codes to be enumerated once fault handling is implemented |
| `line_cut` | bool | true if either line-cut switch has fired (informational - the relay itself fires in hardware regardless of firmware, see [electronics.md](electronics.md)'s line-cut section) |
| `cal_valid` | bool | true once a `CALIBRATING` cycle has completed successfully this session (see [control_philosophy.md](control_philosophy.md#calibrating)) - lets a display warn the operator if a tow is attempted before the day's calibration has been done |
| `boot_configured` | bool | true once both `operating_mode` and `pilot_weight_kg` have been set this power-up (see "Boot Configuration" below) - false blocks `calibrate`, so this tells the GIGA UI whether it still needs to prompt for them |
| `operating_mode` | `"solo"` \| `"winchman"` | the currently-set operating mode - `"winchman"` (the safe default) until the GIGA sets it |
| `pilot_weight_kg` | number | the currently-set pilot weight - `0` until the GIGA sets it |

**Both links receive the exact same telemetry message** - the handheld's own display firmware just picks out the few fields it has room to show (state, tension, fault); it doesn't get a trimmed-down message. Simpler than maintaining two telemetry shapes, and the message is small enough that this isn't a real bandwidth concern at a 1-5 Hz telemetry rate.

**Send rate:** telemetry is broadcast periodically (both links, currently every 200ms in the firmware skeleton - i.e. 5 Hz) rather than only in response to a request. Commands are sent whenever the sender has something new to say (a button changed state) rather than polled.

---

## Deadman Timeout

The handheld's `deadman` field is the pilot's live "I'm still holding this" signal. The ESP32 tracks the time since the **last valid `cmd` with `src:"handheld"`** was received, regardless of what `deadman` was set to in it. If nothing arrives for **`HANDHELD_TIMEOUT_MS`** (firmware constant, currently 1000ms - conservative first guess, not yet tuned against real LoRa latency/loss behavior), the ESP32 treats this exactly like `deadman:false` - i.e. **link loss looks the same as the pilot letting go**, deliberately, since from a safety standpoint an unreachable pilot should never be treated as a "keep towing" signal by omission.

**The GIGA link has no equivalent timeout requirement** - by design (see [electronics.md](electronics.md)'s Overview), the GIGA is a UI node kept out of the actuation loop, so its own link dropping doesn't change what the PID/state-machine authority does. Losing the GIGA link just means the operator stops seeing telemetry until it reconnects.

---

## Boot Configuration

Every power-up, the ESP32 starts with `operating_mode` defaulted to `"winchman"` and `pilot_weight_kg` unset (`0`) - neither is persisted across a reboot, on purpose: stale settings from a previous day or a different pilot must never carry over silently.

`IDLE` is **locked** until the GIGA has actively sent both `operating_mode` and `pilot_weight_kg` at least once this session - `state_cmd:"calibrate"` is refused otherwise. This forces the operator to deliberately (re-)confirm both at the start of every session before a tow can proceed, rather than trusting a default:

- `operating_mode: "winchman"` - the normal case, a winchman operates the GIGA at the winch. `calibrate`/`calibration_done` stay GIGA-only, matching the real-world radio procedure: the pilot at the start location requests calibration by radio, the winchman triggers it.
- `operating_mode: "solo"` - reserved for flying alone, where the pilot launches from a start location up to ~1km from the winch with nobody there to operate the GIGA. Not yet wired into any different authority behavior (`calibrate` is still GIGA-only regardless of mode) - see [firmware/esp32_mainboard/esp32_mainboard.ino](../firmware/esp32_mainboard/esp32_mainboard.ino)'s `OperatingMode` enum, which exists but isn't read anywhere yet. Whether/how `SOLO_TOW` should let the handheld trigger `calibrate` directly is still an open design question.

Check `telemetry`'s `boot_configured` field to know whether the GIGA still needs to prompt the operator for these before a tow can start.

---

## State Machine Reference

The ESP32 firmware's state enum matches [control_philosophy.md](control_philosophy.md#state-machine)'s finite state machine exactly: the linear sequence `IDLE -> CALIBRATING -> READY -> LAUNCH -> UNDER_TREE_HEIGHT -> NORMAL_TOW -> PAY_OUT -> RELEASE -> RECOVERY`, plus `EMERGENCY_STOPPED` - reachable from **any** of those states, never entered automatically as part of the normal sequence, and left only by an explicit `reset_fault` command (back to `IDLE`). See that document for what each state means and what it's allowed to do - this document only defines how state is *reported* and *requested* over the wire, not the transition logic itself (which lives in the firmware, not yet fully implemented - see "Current firmware status" below).

---

## Versioning

No explicit protocol-version field yet (v0.1 of this doc, first draft) - add one (e.g. `"proto":1`) before this protocol needs to support more than one firmware version talking to more than one other firmware version at a time. Not needed while every node's firmware is being written from scratch together.

---

## Current Firmware Status

**First step only - communications skeleton, not the control system.** `firmware/esp32_mainboard/esp32_mainboard.ino` implements:

- Both UART links (`Serial0` for GIGA, `Serial1` for Heltec), parsing/emitting exactly the `cmd`/`telemetry` messages defined above.
- The field-authority rule (handheld `cmd`s can only affect `deadman`/`tree_height`).
- The deadman timeout logic.
- **`EMERGENCY_STOPPED`, `CALIBRATING` and the boot-configuration lock are real, guarded logic, not placeholders:**
  - The local hardware e-stop switch (`GPIO10`) is polled every loop and forces `EMERGENCY_STOPPED` unconditionally while held - independent of, and overriding, anything either UART link says. Leaving `EMERGENCY_STOPPED` requires an explicit `reset_fault`, and that's itself refused if the switch is still physically pressed.
  - `CALIBRATING` implements the real two-point sequencing from [control_philosophy.md](control_philosophy.md#calibrating): `calibrate` (only valid from `IDLE`) captures a tare reading, `calibration_done` (only valid from `CALIBRATING`) captures the second point and computes the counts-per-kg factor, setting `cal_valid`. Only the sensor input feeding this (`readLoadCellRaw()`) is still a stub returning `0` - the sequencing/validation around it is real and ready for when the HX711 is wired up.
  - `calibrate` is additionally refused until the GIGA has set both `operating_mode` and `pilot_weight_kg` this power-up (see "Boot Configuration" above) - a real, enforced lock, not just documented intent.
  - The onboard RGB LED (`GPIO48`) reflects `state` in real time (see `updateStatusLed()`) - useful for bench testing without a display or Serial Monitor open; `EMERGENCY_STOPPED` blinks rather than staying solid.
  - The rest of the state machine (`start_tow`, `release`, `idle`) is still a bare placeholder transition, purely to have something real to show telemetry for - **not the real safety logic** (tree-height gating, force ramps, fault conditions beyond e-stop).
- Telemetry fields that don't have a real sensor behind them yet (`tension_kg`, `rope_out_m`, `rpm`, `motor_current_a`) are sent as `0`/placeholder so the message shape is stable and both display firmwares can be developed against it immediately, without waiting for the sensor/CAN work.

**Testing without real GIGA/Heltec hardware:** the firmware also accepts `cmd` lines typed into the USB Serial Monitor (debug console) and echoes `telemetry` there too, gated behind a `DEBUG_ACCEPT_SERIAL_COMMANDS` compile-time flag (on by default). This lets the whole protocol - state transitions, field authority, deadman timeout - be exercised from a single USB cable before either display firmware exists, by hand-typing lines like `{"type":"cmd","seq":1,"src":"giga","state_cmd":"calibrate"}`. Turn the flag off once real GIGA/Heltec firmware exists, so the debug console stops being able to act as a trusted command source.

**Explicitly not yet implemented (next steps, in roughly the order they unblock each other):**
- HX711 load cell reading (GPIO6/7) -> real `tension_kg`, and a real reading behind `readLoadCellRaw()` so calibration produces a real `countsPerKg` instead of always computing against a stubbed `0`.
- Hall sensor reading (GPIO41/42) -> real `rpm`/`rope_out_m`.
- The remaining safety-relevant state machine (tree-height force limiting, ramp rates, non-e-stop fault conditions) per [control_philosophy.md](control_philosophy.md) - e-stop and calibration are done, the rest of the sequence (`LAUNCH`/`UNDER_TREE_HEIGHT`/`NORMAL_TOW`/`PAY_OUT`/`RELEASE`/`RECOVERY`) is still bare placeholder transitions.
- PID loop (tension error -> torque setpoint).
- CAN61 TX/RX to the Fardriver controller (GPIO4/5) per [electronics.md](electronics.md)'s Motor Controller section - not yet confirmed against real ND961200-CAN hardware.
- Reading the mainboard's remaining local safety GPIOs (tension nudge switches, line-cut sense, relay drive) - direct GPIO, not part of this JSON protocol, but line-cut sense feeds into `telemetry`'s `line_cut` field once wired up. (E-stop, GPIO10, is now read for real - see above.)
- The GIGA and Heltec (both winch-side and pilot-side) firmwares themselves - not started.
