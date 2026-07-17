# Open Paraglider Tow Winch

# History

Version 0.1

---

## The Beginning

Paraglider towing did not start with purpose-built tow winches.

In the early 1980s pilots built their own equipment from whatever was available.

One of the very first systems was remarkably simple.

A car was parked on the beach.

One driven wheel was lifted off the ground and removed.

An empty wheel rim ("velg") was mounted instead.

The tow rope was wrapped around the rim.

A pulley and a spring balance measured the tow force.

The driver watched the spring balance while controlling the engine throttle.

```
Spring Scale
      │
      ▼
     Pulley
      │
      ▼
  Empty Wheel Rim
      │
      ▼
     Car Engine
      │
      ▼
     Pilot
```

Although primitive, the basic principle was already present:

**Control the force applied to the pilot.**

---

## Mechanical Improvements

As towing became more popular, stronger and more reliable winches were built.

Automotive engines with automatic gearboxes became common.

One important discovery was that the torque converter produced a much smoother launch than a direct mechanical connection.

To improve this behaviour even further, additional holes were drilled in the torque converter.

This intentionally increased the slip.

The result was a softer and safer launch.

The purpose was never to reduce performance.

The purpose was to reduce sudden increases in tow force.

---

## Lessons Learned

Many years of practical towing taught an important lesson.

A good tow operator does **not** control rope speed.

A good tow operator continuously controls **tow force**.

The pilot should never notice abrupt changes in pull.

Whether the pilot accelerates, slows down, encounters lift or sink, the tow force should remain predictable.

This philosophy became the foundation of this project.

---

## The Electric Tow Winch

Modern electric motors provide something that mechanical systems never could.

Instead of relying on mechanical slip, the controller can directly regulate the towing force.

The Open Paraglider Tow Winch therefore uses:

- Load cell
- PID controller
- Electric motor
- Motor controller
- Hall sensors
- State machine

The controller continuously adjusts motor current to maintain the desired tow force.

If the force becomes too low, the drum pulls.

If the force becomes too high, the drum can pay rope out under control.

The behaviour is the same as the experienced tow operators and modified torque converters of earlier generations.

Only the technology has changed.

---

## Design Philosophy

This project is not an attempt to build the fastest tow winch.

It is an attempt to build the safest and most predictable tow winch.

The goal is to reproduce decades of towing experience using modern electronics while keeping the behaviour familiar to experienced operators.

---

## Acknowledgement

This project is dedicated to all the pilots and builders who experimented on beaches, airfields and grass strips during the early years of paragliding.

Without their creativity, practical experience and willingness to experiment, modern tow systems would not exist.

This repository attempts to preserve not only the hardware, but also the engineering philosophy that evolved over more than forty years.