# Open Paraglider Tow Winch

# Control Philosophy

Version 0.2

---

## Design Goal

The objective of the tow winch is **not to control rope speed**.

The objective is to control **tow force**.

A skilled tow operator does not think in terms of rope speed. He constantly adjusts the throttle to maintain the correct pull on the pilot.

The electronic controller shall reproduce this behaviour.

---

# Primary Control Loop

The load cell is the primary control sensor.

The controller continuously compares:

Measured Tow Force

with

Desired Tow Force

The difference is processed by a PID controller.

The PID output is **motor current**.

Motor current produces motor torque.

Motor torque produces drum torque.

Drum movement is therefore a consequence of regulating tow force.

The controller never directly commands drum speed.

```
Desired Force
      │
      ▼
Compare with Load Cell
      │
      ▼
      PID
      │
      ▼
Requested Motor Current
      │
      ▼
Fardriver Motor Controller
      │
      ▼
QS165 Motor
      │
      ▼
Drum Torque
      │
      ▼
Tow Force
      │
      └───────────────┐
                      │
                 Load Cell
```

---

# Drum Behaviour

Three operating conditions naturally exist.

## Pull

Measured force is below the desired value.

The PID increases motor current.

Motor torque increases.

The drum pulls rope in.

---

## Hold

Measured force equals the desired value.

Motor torque balances rope tension.

The drum may rotate slowly or stop completely.

---

## Pay Out

Measured force exceeds the desired value.

The PID reduces motor current.

If required, motor torque becomes negative (or commands controlled payout depending on the motor controller).

The drum rotates forward.

The rope force decreases until the desired value is reached again.

This electronically replaces the force limiting behaviour that was previously obtained by modifying the slip characteristics of automotive torque converters.

---

# Sensors

## Primary Control Sensor

Load Cell

Purpose:

Close the force control loop.

This is the only sensor directly controlling the tow force.

---

## State Sensors

Hall sensors mounted on the drum provide machine state information.

Examples:

- Drum RPM
- Drum direction
- Rope payout
- Remaining rope
- Estimated drum diameter
- Estimated line speed

These sensors do **not** regulate tow force.

They inform the controller about the current operating condition.

---

# State Machine

The complete controller operates as a finite state machine.

Each state has its own preset parameters and safety limits.

Example:

```
IDLE

↓

CALIBRATING

↓

READY

↓

LAUNCH

↓

UNDER TREE HEIGHT

↓

NORMAL TOW

↓

PAY OUT

↓

RELEASE

↓

RECOVERY
```

**EMERGENCY STOPPED** is not part of the linear sequence above - it can be entered from **any** state, immediately, the moment an e-stop is triggered (local switch or operator command). It is a dead end, not a step: the system stays there, tow force released, until an operator explicitly clears it, and only then returns to `IDLE`. Nothing about it is time-based or automatic-recovery - see the [software.md](software.md) protocol doc for how a fault-reset command clears it.

The PID controller remains active in every state.

Each state modifies:

- Desired tow force
- Maximum motor current
- Maximum payout speed
- Force ramp rate
- Safety limits
- Allowed operator actions

The state machine determines *how* the system behaves.

The PID determines *how much motor current is required*.

---

# Calibrating

Every winch day should start with a short calibration step.

At the start location, the line is hooked to a calibrated electronic scale, and tension is raised to 100 kg.

This serves two purposes:

- The load cell is calibrated against a known reference force.
- The line itself is proof-tested to 100 kg, confirming it can safely take the force needed to get a pilot above tree height.

---

# Launch Philosophy

During launch and while the pilot is below tree height:

Maximum tow force shall be limited to just enough force to get the pilot into the air.

After the pilot is safely above tree height:

Tow force is smoothly ramped to the selected towing profile, approx pilot weight

No sudden increase in tow force is permitted.

---

# Design Philosophy

The system is fundamentally a **Tow Force Controller**.

The mechanics (motor, gearbox, drum and frame) provide the physical capability.

The load cell, PID controller and state machine provide the behaviour.

The objective is to reproduce the actions of an experienced human tow operator while providing repeatable, adjustable and predictable towing performance.

Design principle: Control force directly. Let speed be the result.