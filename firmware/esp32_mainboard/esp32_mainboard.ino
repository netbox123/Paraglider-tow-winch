// ESP32-S3 (N16R8 DevKitC-1) mainboard firmware - communications skeleton.
//
// Implements the JSON protocol defined in docs/software.md (states, `cmd` and
// `telemetry` messages, field authority, deadman timeout). Does NOT yet
// implement the real control system - no HX711/hall-sensor reads, no CAN61,
// no safety-gated state transitions. See docs/software.md's "Current
// Firmware Status" section for the exact list of what's stubbed vs real.
//
// Board setting requirement (Arduino IDE > Tools): "USB CDC On Boot" = Enabled.
// This makes `Serial` the USB-C debug console and `Serial0` the hardware UART0
// on GPIO43/44 (the GIGA link) - get this wrong and the GIGA link silently
// stops working. See docs/software.md's "Transports" table.
//
// Requires the ArduinoJson library (>= 7.0) - install via Library Manager.
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

// Deliberately minimal: enough to exercise the protocol end-to-end so both
// display firmwares (GIGA, Heltec) have something real to talk to. This is
// NOT the real safety-gated transition logic (tree-height limits, force
// ramps, calibration sequencing) - see docs/software.md.
void applyStateCmd(const char* cmd) {
  if (strcmp(cmd, "calibrate") == 0) {
    g_state = WinchState::CALIBRATING;
  } else if (strcmp(cmd, "calibration_done") == 0) {
    g_state = WinchState::READY;
  } else if (strcmp(cmd, "start_tow") == 0) {
    g_state = WinchState::NORMAL_TOW;
  } else if (strcmp(cmd, "release") == 0) {
    g_state = WinchState::RELEASE;
  } else if (strcmp(cmd, "reset_fault") == 0) {
    g_state = WinchState::IDLE;
  } else if (strcmp(cmd, "idle") == 0) {
    g_state = WinchState::IDLE;
  } else if (strcmp(cmd, "emergency_stop") == 0) {
    g_state = WinchState::EMERGENCY_STOPPED;
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
      applyStateCmd(doc["state_cmd"]);
    }
    if (doc["fault_reset"].is<bool>() && doc["fault_reset"].as<bool>()) {
      g_state = WinchState::IDLE;
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

  Serial.println("ESP32 mainboard - comms skeleton starting");
}

void loop() {
  JsonDocument doc;
  if (g_gigaReader.poll(doc)) handleCommand(doc);

  doc.clear();
  if (g_heltecReader.poll(doc)) handleCommand(doc);

#if DEBUG_ACCEPT_SERIAL_COMMANDS
  doc.clear();
  if (g_debugReader.poll(doc)) handleCommand(doc);
#endif

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
