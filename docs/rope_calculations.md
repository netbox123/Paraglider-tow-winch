# Open Paraglider Tow Winch

# Rope / Drive Train Calculations

Version 0.1

---

## Purpose

Estimate rope tension and rope speed available from the QS165 motor, through the internal gearbox and the 428 chain reduction, across the drum's full range of wound diameter.

This matters because the drum diameter is not constant: it grows from the bare core to the full flange diameter as rope winds on. Available torque at the rope is diameter-dependent even though the PID controller (see `control_philosophy.md`) holds tow force constant within whatever range is actually available.

---

## Inputs

**Motor** (QS165 60H V3, "QSJ165A-60-10KW"). Figures below are for the motor's own output shaft, i.e. already after its internal 2.37:1 gearbox - this is the shaft the 14T sprocket sits on.

- Rated (continuous) speed: 2280 RPM
- Rated (continuous) power: 10,000 W
- Peak power (short bursts only): 20,000 W
- Max speed: 3165 RPM
- Max torque: 170 N·m

Sourced from QS Motor's own listings and retailers for this exact variant - the manufacturer's spec table is published as an image and could not be extracted directly, so treat these as approximate, not datasheet-certified.

**Chain reduction**: motor sprocket 14T, drum sprocket 76T -> ratio 76/14 = 5.4286

**Drum diameter** (`config.py`): core 390 mm (empty) to flange 590 mm (full of rope). Radius 0.195 m to 0.295 m.

---

## Stall Tension (0 km/h)

Drum shaft torque = motor max torque x chain ratio = 170 x 5.4286 = **923 N·m**

Force = torque / drum radius:

| Drum state | Radius | Force |
|---|---|---|
| Core (empty) | 0.195 m | 4733 N = **483 kgf** |
| Flange (full) | 0.295 m | 3129 N = **319 kgf** |

Both far exceed `TOW_FORCE_MAX` (100 kg). This headroom is expected - the motor is not sized to run at its own limit, the PID loop limits actual tow force electronically.

---

## Maximum Rope Speed

Drum shaft max speed = motor max speed / chain ratio = 3165 / 5.4286 = 583 RPM = 61.05 rad/s

Rope speed = drum angular speed x radius:

| Drum state | Radius | Rope speed |
|---|---|---|
| Core (empty) | 0.195 m | 11.9 m/s = **42.9 km/h** |
| Flange (full) | 0.295 m | 18.0 m/s = **64.8 km/h** |

Maximum achievable rope speed itself depends on how much rope is wound on. A drum that starts a tow near-empty cannot reach 50 km/h until enough rope has wound back in to bring the effective diameter up to roughly 455 mm.

---

## Tension at 50 km/h

At 583 RPM (drum shaft), the motor is well above its rated 420 RPM (drum shaft rated speed = 2280 / 5.4286). Above rated speed the motor is power-limited, not torque-limited: available torque falls as speed rises to hold power constant.

Radius needed for 50 km/h (13.89 m/s) at max drum speed (61.05 rad/s): r = 13.89 / 61.05 = 0.2275 m (diameter ~455 mm - partway through a tow, not at a bare drum).

Torque = power / angular speed, at that operating point:

| Power basis | Torque | Force |
|---|---|---|
| Rated (continuous), 10 kW | 164 N·m | 720 N = **73 kgf** |
| Peak (short bursts), 20 kW | 328 N·m | 1440 N = **147 kgf**, not sustainable |

---

## Tension at 40 km/h (more realistic max, no wind)

50 km/h assumes still air; a more realistic no-wind maximum is closer to 40 km/h (13.89 -> 11.11 m/s). This case is meaningfully better than the 50 km/h figure because the torque/power-limited boundary depends on drum diameter, and 40 km/h falls on different sides of that boundary depending on how much rope is wound on.

Rated drum shaft speed (420 RPM) is reached, at 40 km/h, at a drum diameter of about **505 mm** - partway between core and flange.

| Drum state | Radius | Drum RPM | Regime | Force |
|---|---|---|---|---|
| Core (empty), Ø390mm | 0.195 m | 544 RPM | power-limited | 900 N = **92 kgf** continuous (184 kgf peak) |
| >Ø505mm (partway wound) | - | <420 RPM | full torque | **319 kgf** (same as stall) |
| Flange (full), Ø590mm | 0.295 m | 360 RPM | full torque | **319 kgf** |

So at 40 km/h, the full `TOW_FORCE_MAX` (100 kg) is available for most of the drum's fill range - only near a bare/empty drum does it drop, to about 92 kgf continuous, still close to the 100 kg target (and 184 kgf is available in short bursts even then).

---

## Sustained Stall / High-Wind Hold Margin

Wind at altitude can be stronger than at ground level. Since the winch controls tension, not drum speed (see `control_philosophy.md`), the drum speed is whatever the wind and pilot's position demand - including, in strong/gusty conditions, dropping to zero or briefly reversing (paying out) to hold the tension setpoint.

Holding torque at zero RPM is harder on a PMSM than running under load: current concentrates continuously in whichever winding phases are aligned with the rotor's fixed position, instead of commutating evenly across all three phases while spinning. This is why continuous stall torque ratings are normally well below the dynamic/peak torque figure used above.

The reassuring part: holding `TOW_FORCE_MAX` (100 kg) at zero RPM only requires a fraction of the available stall torque (923 N·m at the drum, from the Stall Tension section above):

| Drum state | Max stall force | 100 kg as % of max |
|---|---|---|
| Core (empty) | 483 kgf | **20.7%** |
| Flange (full) | 319 kgf | **31.3%** |

So a sustained high-wind hold needs only about 21-31% of the motor's dynamic stall torque, depending on drum fill. That is a meaningful thermal margin, though it should still be checked against the motor controller's actual continuous-stall current/thermal-foldback rating (not yet found - the QS165 spec sheet publishes this as an image) before treating it as fully confirmed.

---

## Implication

Stall force is comfortably more than needed (319-483 kgf available vs. 100 kg target), so launch force is not a concern.

50 km/h is a somewhat unrealistic worst case - a more realistic no-wind maximum is closer to **40 km/h**, and at that speed the full `TOW_FORCE_MAX` (100 kg) holds for most of the drum's fill range, only easing to about 92 kgf continuous (184 kgf peak) when the drum is nearly empty.

The 50 km/h figure is kept above as the theoretical worst case: **above roughly 31-47 km/h** (depending on drum fill - the speed at which the motor reaches its rated 420 RPM drum-shaft speed and becomes power-limited), sustained tow force does fall below 100 kg, reaching about 73 kgf continuous at 50 km/h. If a hard 100 kg-at-50km/h requirement ever matters, the drive train would need a larger reduction (more teeth on the drum sprocket, or a lower gearbox ratio) - at the cost of a lower maximum rope speed for the same motor RPM limit. Given real tows are closer to 40 km/h, this is not currently a practical concern.

---

*Every figure in this document assumes the 14T motor sprocket / 76T drum sprocket pair (5.4286:1 chain ratio). If the drum sprocket tooth count changes, all tension and speed numbers here need to be recalculated - they do not scale in an obvious way (tension scales up, speed scales down, and the torque/power-limited crossover points shift too). Also depends on `config.py` (`GEARBOX_RATIO`, `DRUM_CORE_DIAMETER`, `DRUM_FLANGE_DIAMETER`) and the motor spec assumptions above.*
