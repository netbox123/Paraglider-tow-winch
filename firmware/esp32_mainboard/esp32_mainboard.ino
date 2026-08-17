// ESP32-S3 (N16R8 DevKitC-1) mainboard firmware - communications skeleton.
//
// Implements the JSON protocol defined in docs/software.md (states, `cmd` and
// `telemetry` messages, field authority, deadman timeout). EMERGENCY_STOPPED
// (local hardware e-stop switch + operator command) and CALIBRATING (two-
// point load-cell calibration sequencing) are real, guarded logic, not just
// placeholder transitions. Everything else that depends on real sensors is
// still stubbed - no HX711/hall-sensor reads, no CAN61, no PID, no tree-
// height/force-ramp logic. See docs/software.md's "Current Firmware Status"
// section for the exact list of what's stubbed vs real.
//
// Board setting requirement (Arduino IDE > Tools): "USB CDC On Boot" = Enabled.
// This makes `Serial` the USB-C debug console and `Serial0` the hardware UART0
// on GPIO43/44 (the GIGA link) - get this wrong and the GIGA link silently
// stops working. See docs/software.md's "Transports" table.
//
// Requires the ArduinoJson library (>= 7.0) - install via Library Manager.
//
// The DevKitC-1's onboard RGB LED (GPIO48) shows the current state at a
// glance - see updateStatusLed() - useful on the bench with no display
// hardware wired up yet.
//
// TESTING WITHOUT REAL GIGA/HELTEC HARDWARE: with DEBUG_ACCEPT_SERIAL_COMMANDS
// below, the USB Serial Monitor doubles as a stand-in for both of them - type
// a `cmd` JSON line (e.g. {"type":"cmd","seq":1,"src":"giga","state_cmd":
// "calibrate"}) and hit enter, and it's handled exactly like a real message
// from that link. Telemetry is echoed to the same console so you can watch
// `state` etc. change in response, no extra hardware required. Set to 0 once
// real GIGA/Heltec firmware exists, so the debug console stops doubling as a
// trusted command source.
#define DEBUG_ACCEPT_SERIAL_COMMANDS 1

#include <ArduinoJson.h>

// ---------------------------------------------------------------------------
// Pins (see docs/electronics.md's pin map table)
// ---------------------------------------------------------------------------
static const int PIN_HELTEC_TXD = 14;  // ESP32 -> Heltec RXD
static const int PIN_HELTEC_RXD = 21;  // ESP32 <- Heltec TXD
// GIGA link uses hardware UART0 (GPIO43/44) via Serial0 - fixed pins, no remap.
static const int PIN_ESTOP_SENSE = 10;  // active-low, winchman remote e-stop switch
static const int PIN_STATUS_LED = 48;   // onboard addressable RGB LED (DevKitC-1)

// ---------------------------------------------------------------------------
// Timing
// ---------------------------------------------------------------------------
static const uint32_t TELEMETRY_INTERVAL_MS = 200;   // 5 Hz, see docs/software.md
static const uint32_t HANDHELD_TIMEOUT_MS   = 1000;  // deadman link-loss timeout

// ---------------------------------------------------------------------------
// State machine (see docs/control_philosophy.md "State Machine")
// ---------------------------------------------------------------------------
enum class WinchState : uint8_t {
  IDLE,
  CALIBRATING,
  READY,
  LAUNCH,
  UNDER_TREE_HEIGHT,
  NORMAL_TOW,
  PAY_OUT,
  RELEASE,
  RECOVERY,
  EMERGENCY_STOPPED,
};

const char* stateToString(WinchState s) {
  switch (s) {
    case WinchState::IDLE:              return "IDLE";
    case WinchState::CALIBRATING:       return "CALIBRATING";
    case WinchState::READY:             return "READY";
    case WinchState::LAUNCH:            return "LAUNCH";
    case WinchState::UNDER_TREE_HEIGHT: return "UNDER_TREE_HEIGHT";
    case WinchState::NORMAL_TOW:        return "NORMAL_TOW";
    case WinchState::PAY_OUT:           return "PAY_OUT";
    case WinchState::RELEASE:           return "RELEASE";
    case WinchState::RECOVERY:          return "RECOVERY";
    case WinchState::EMERGENCY_STOPPED: return "EMERGENCY_STOPPED";
    default:                            return "UNKNOWN";
  }
}

WinchState g_state = WinchState::IDLE;

// ---------------------------------------------------------------------------
// Status LED (onboard RGB, GPIO48) - one glance at the board tells you the
// state without a Serial Monitor open. EMERGENCY_STOPPED blinks rather than
// stays solid so it can't be mistaken for a dim/miswired LED at a glance.
// ---------------------------------------------------------------------------
void updateStatusLed(WinchState s) {
  if (s == WinchState::EMERGENCY_STOPPED) {
    bool on = (millis() / 250) % 2;  // ~2 Hz blink
    rgbLedWrite(PIN_STATUS_LED, on ? 255 : 0, 0, 0);
    return;
  }
  switch (s) {
    case WinchState::IDLE:              rgbLedWrite(PIN_STATUS_LED, 20, 20, 20);  break;  // dim white
    case WinchState::CALIBRATING:       rgbLedWrite(PIN_STATUS_LED, 0, 0, 255);   break;  // blue
    case WinchState::READY:             rgbLedWrite(PIN_STATUS_LED, 0, 255, 0);   break;  // green
    case WinchState::LAUNCH:            rgbLedWrite(PIN_STATUS_LED, 255, 0, 255); break;  // magenta
    case WinchState::UNDER_TREE_HEIGHT: rgbLedWrite(PIN_STATUS_LED, 255, 255, 0); break;  // yellow
    case WinchState::NORMAL_TOW:        rgbLedWrite(PIN_STATUS_LED, 0, 255, 100); break;  // teal
    case WinchState::PAY_OUT:           rgbLedWrite(PIN_STATUS_LED, 255, 100, 0); break;  // orange
    case WinchState::RELEASE:           rgbLedWrite(PIN_STATUS_LED, 150, 0, 255); break;  // purple
    case WinchState::RECOVERY:          rgbLedWrite(PIN_STATUS_LED, 0, 200, 255); break;  // cyan
    default:                            rgbLedWrite(PIN_STATUS_LED, 0, 0, 0);     break;
  }
}

// ---------------------------------------------------------------------------
// Shared command state, updated by handleCommand(), read by sendTelemetry()
// and (eventually) the real control loop.
// ---------------------------------------------------------------------------
struct CommandState {
  bool deadman = false;
  bool treeHeight = false;
  float tensionSetpointKg = 0;
  uint32_t lastHandheldCmdMillis = 0;  // 0 = never received
};
CommandState g_cmd;

uint16_t g_telemetrySeq = 0;

// ---------------------------------------------------------------------------
// Load cell calibration (see docs/control_philosophy.md "Calibrating"): a
// two-point calibration against a 100kg reference pull on an external scale.
// The sequencing/data model here is real; the sensor input feeding it is a
// stub until the HX711 is wired up (GPIO6/7) - see readLoadCellRaw() below.
// ---------------------------------------------------------------------------
struct LoadCellCalibration {
  bool valid = false;
  long rawAtZero = 0;
  float countsPerKg = 0;  // (rawAt100kg - rawAtZero) / 100.0
};
LoadCellCalibration g_cal;

// TODO: replace with a real HX711 read (GPIO6/7, see docs/electronics.md).
// Returns 0 for now - every caller of this is real logic, only this one
// function is a stub, so it's a single place to fill in later.
long readLoadCellRaw() {
  return 0;
}

// ---------------------------------------------------------------------------
// Line-buffered JSON reader - one instance per UART link. Each incoming
// message is exactly one line (see docs/software.md "Transports": one
// compact JSON object per line, '\n'-terminated).
// ---------------------------------------------------------------------------
class JsonLineReader {
 public:
  explicit JsonLineReader(Stream& stream) : _stream(stream) {}

  // Call every loop(). Returns true if a full line was parsed into `doc`.
  bool poll(JsonDocument& doc) {
    while (_stream.available()) {
      char c = _stream.read();
      if (c == '\n') {
        bool got = false;
        if (_len > 0) {
          _buf[_len] = '\0';
          DeserializationError err = deserializeJson(doc, _buf);
          if (err) {
            Serial.printf("JSON parse error: %s\n", err.c_str());
          } else {
            got = true;
          }
        }
        _len = 0;
        if (got) return true;
      } else if (c != '\r' && _len < sizeof(_buf) - 1) {
        _buf[_len++] = c;
      }
      // else: overlong line, character silently dropped rather than overflowing
    }
    return false;
  }

 private:
  Stream& _stream;
  char _buf[256];
  size_t _len = 0;
};

JsonLineReader g_gigaReader(Serial0);
JsonLineReader g_heltecReader(Serial1);
#if DEBUG_ACCEPT_SERIAL_COMMANDS
JsonLineReader g_debugReader(Serial);
#endif

// ---------------------------------------------------------------------------
// Command handling
// ---------------------------------------------------------------------------

// Active-low: the switch pulls the pin to GND when pressed. The board's own
// schematic already has an external 10k pull-up to 3V3 (see
// docs/electronics.md) - the internal INPUT_PULLUP set in setup() is
// redundant there, but makes bench-testing this file alone easier (a bare
// wire to GND simulates a press, no external resistor needed).
bool estopSwitchPressed() {
  return digitalRead(PIN_ESTOP_SENSE) == LOW;
}

// The real, guarded state-transition logic (see docs/software.md and
// docs/control_philosophy.md "State Machine"/"Calibrating"). Unlike the rest
// of this skeleton, EMERGENCY_STOPPED and CALIBRATING are implemented for
// real here, not just placeholder transitions - only the sensor input behind
// calibration (readLoadCellRaw()) is still a stub.
void requestStateTransition(const char* cmd) {
  // Reachable from ANY state, immediately - see control_philosophy.md.
  if (strcmp(cmd, "emergency_stop") == 0) {
    g_state = WinchState::EMERGENCY_STOPPED;
    return;
  }

  if (g_state == WinchState::EMERGENCY_STOPPED) {
    // A dead end: only reset_fault leaves it, and only once the local
    // e-stop switch has actually been released - you can't clear an e-stop
    // while the button is still held down.
    if (strcmp(cmd, "reset_fault") == 0) {
      if (estopSwitchPressed()) {
        Serial.println("reset_fault ignored: e-stop switch still pressed");
        return;
      }
      g_state = WinchState::IDLE;
    } else {
      Serial.printf("state_cmd '%s' ignored while EMERGENCY_STOPPED\n", cmd);
    }
    return;
  }

  if (strcmp(cmd, "calibrate") == 0) {
    if (g_state != WinchState::IDLE) {
      Serial.println("calibrate only valid from IDLE");
      return;
    }
    // Tare point: assumes no load on the line yet, matching the real
    // procedure (hook up the scale, THEN raise tension to 100kg).
    g_cal.valid = false;
    g_cal.rawAtZero = readLoadCellRaw();
    g_state = WinchState::CALIBRATING;

  } else if (strcmp(cmd, "calibration_done") == 0) {
    if (g_state != WinchState::CALIBRATING) {
      Serial.println("calibration_done only valid from CALIBRATING");
      return;
    }
    // Operator has raised tension until the EXTERNAL reference scale reads
    // 100kg (see control_philosophy.md "Calibrating") and is confirming it
    // now - capture that as the second calibration point.
    // TODO once HX711 is real: reject this if rawAtZero/rawAt100 are
    // suspiciously close together (no real load detected) - not worth
    // guarding yet while readLoadCellRaw() is a stub that always returns 0.
    long rawAt100 = readLoadCellRaw();
    g_cal.countsPerKg = (rawAt100 - g_cal.rawAtZero) / 100.0f;
    g_cal.valid = true;
    g_state = WinchState::READY;

  } else if (strcmp(cmd, "start_tow") == 0) {
    g_state = WinchState::NORMAL_TOW;
  } else if (strcmp(cmd, "release") == 0) {
    g_state = WinchState::RELEASE;
  } else if (strcmp(cmd, "reset_fault") == 0) {
    g_state = WinchState::IDLE;
  } else if (strcmp(cmd, "idle") == 0) {
    g_state = WinchState::IDLE;
  } else {
    Serial.printf("Unknown state_cmd: %s\n", cmd);
  }
}

// Applies a parsed `cmd` message, enforcing field authority by `src`
// (see docs/software.md "Field authority"). Fields outside a sender's
// authority are silently ignored, not just left undocumented - the far end's
// own firmware is never trusted to self-restrict, especially over LoRa.
void handleCommand(const JsonDocument& doc) {
  const char* type = doc["type"] | "";
  if (strcmp(type, "cmd") != 0) return;  // not a command message, ignore

  const char* src = doc["src"] | "";
  bool isHandheld = strcmp(src, "handheld") == 0;
  bool isGiga = strcmp(src, "giga") == 0;

  if (!isHandheld && !isGiga) {
    Serial.printf("cmd with unknown src '%s' ignored\n", src);
    return;
  }

  // deadman / tree_height: handheld-only. A GIGA-sent deadman would defeat
  // the whole point of the deadman check (it's meant to be the pilot's own
  // live signal), so it's ignored even from the trusted GIGA link.
  if (isHandheld) {
    g_cmd.lastHandheldCmdMillis = millis();
    if (doc["deadman"].is<bool>())     g_cmd.deadman = doc["deadman"];
    if (doc["tree_height"].is<bool>()) g_cmd.treeHeight = doc["tree_height"];
  }

  // state_cmd / tension_setpoint_kg / fault_reset: GIGA-only.
  if (isGiga) {
    if (doc["tension_setpoint_kg"].is<float>()) {
      g_cmd.tensionSetpointKg = doc["tension_setpoint_kg"];
    }
    if (doc["state_cmd"].is<const char*>()) {
      requestStateTransition(doc["state_cmd"]);
    }
    if (doc["fault_reset"].is<bool>() && doc["fault_reset"].as<bool>()) {
      // Routed through the same guarded path as state_cmd:"reset_fault" so
      // the "can't clear e-stop while the switch is still pressed" check
      // applies no matter which field the sender used.
      requestStateTransition("reset_fault");
    }
  }
}

// True deadman state after applying the link-loss timeout (see
// docs/software.md "Deadman Timeout") - link silence reads as "pilot let go",
// never as "keep towing".
bool effectiveDeadman() {
  if (g_cmd.lastHandheldCmdMillis == 0) return false;  // never heard from handheld
  if (millis() - g_cmd.lastHandheldCmdMillis > HANDHELD_TIMEOUT_MS) return false;
  return g_cmd.deadman;
}

// ---------------------------------------------------------------------------
// Telemetry - identical message broadcast on both links, see docs/software.md.
// ---------------------------------------------------------------------------
void sendTelemetry() {
  JsonDocument doc;
  doc["type"] = "telemetry";
  doc["seq"] = g_telemetrySeq++;
  doc["state"] = stateToString(g_state);

  // TODO: replace with real HX711 / hall-sensor / CAN61 readings once wired
  // up (see docs/software.md "Current Firmware Status"). Placeholder 0s keep
  // the message shape stable so both display firmwares can be developed
  // against it now, without waiting for the sensor/CAN work.
  doc["tension_kg"] = 0;
  doc["tension_setpoint_kg"] = g_cmd.tensionSetpointKg;
  doc["rope_out_m"] = 0;
  doc["rpm"] = 0;
  doc["motor_current_a"] = 0;
  doc["fault"] = (g_state == WinchState::EMERGENCY_STOPPED);
  doc["fault_code"] = 0;
  doc["line_cut"] = false;
  doc["cal_valid"] = g_cal.valid;

  serializeJson(doc, Serial0);
  Serial0.write('\n');
  serializeJson(doc, Serial1);
  Serial1.write('\n');
#if DEBUG_ACCEPT_SERIAL_COMMANDS
  serializeJson(doc, Serial);
  Serial.write('\n');
#endif
}

// ---------------------------------------------------------------------------
// Arduino entry points
// ---------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);   // USB-CDC, debug console only (see board-setting note above)
  Serial0.begin(115200);  // GIGA UART, native UART0 pins (GPIO43/44)
  Serial1.begin(115200, SERIAL_8N1, PIN_HELTEC_RXD, PIN_HELTEC_TXD);  // Heltec UART
  pinMode(PIN_ESTOP_SENSE, INPUT_PULLUP);

  Serial.println("ESP32 mainboard - comms skeleton starting");
}

void loop() {
  // Checked first, every loop, and re-asserted unconditionally while held -
  // not just on the rising edge. This is the local hardware e-stop's own
  // authority, independent of both UART links (see docs/electronics.md's
  // line-cut/e-stop reasoning): even if a command somehow changed the state
  // away from EMERGENCY_STOPPED in the same loop iteration, the very next
  // iteration puts it straight back for as long as the switch is down.
  static bool lastEstopPressed = false;
  bool estopPressed = estopSwitchPressed();
  if (estopPressed) {
    if (!lastEstopPressed) Serial.println("Local e-stop switch pressed -> EMERGENCY_STOPPED");
    g_state = WinchState::EMERGENCY_STOPPED;
  }
  lastEstopPressed = estopPressed;

  JsonDocument doc;
  if (g_gigaReader.poll(doc)) handleCommand(doc);

  doc.clear();
  if (g_heltecReader.poll(doc)) handleCommand(doc);

#if DEBUG_ACCEPT_SERIAL_COMMANDS
  doc.clear();
  if (g_debugReader.poll(doc)) handleCommand(doc);
#endif

  updateStatusLed(g_state);  // every loop, not just on change - EMERGENCY_STOPPED needs to blink

  static uint32_t lastTelemetryMillis = 0;
  uint32_t now = millis();
  if (now - lastTelemetryMillis >= TELEMETRY_INTERVAL_MS) {
    lastTelemetryMillis = now;
    sendTelemetry();
  }

  // Exercised here just to keep it visible in debug output for now - the
  // real actuation loop will consume effectiveDeadman() once it exists.
  static bool lastDeadman = false;
  bool dm = effectiveDeadman();
  if (dm != lastDeadman) {
    Serial.printf("effective deadman: %s\n", dm ? "true" : "false");
    lastDeadman = dm;
  }
}
