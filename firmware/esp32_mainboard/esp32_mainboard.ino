// ESP32-S3 (N16R8 DevKitC-1) mainboard firmware - communications skeleton.
//
// Implements the JSON protocol defined in docs/software.md (states, `cmd` and
// `telemetry` messages, field authority, deadman timeout). EMERGENCY_STOPPED
// (local hardware e-stop switch + operator command) and CALIBRATING (two-
// point load-cell calibration sequencing) are real, guarded logic, not just
// placeholder transitions. A physical release switch (GPIO2, the winchman
// remote's 7th pin on J8, own dedicated pull-up R35) lets the winchman end
// a tow without the GIGA link, same as the hardware e-stop. IDLE itself is
// boot-locked: the GIGA must set
// operating_mode, pilot_name and pilot_weight_kg (once per power-up) before
// "calibrate" is accepted; in WINCHMAN_AVAILABLE mode, pilot_name and
// pilot_weight_kg are forgotten again after every release/fault, forcing a
// fresh confirmation for whoever tows next (SOLO_TOW keeps them for the
// session, same pilot throughout) - pilot_name exists for tow-log
// administration (who flew which tow), same reasoning as pilot_weight_kg.
// The GIGA
// can also push a whole tunable config (ramp/reduction %, PID gains, and
// optionally a saved calibration via use_saved_calibration) at boot, read
// from its own SD card - see TowConfig - so these don't need a firmware
// reflash to tune. None of the ramp/PID values are acted on by the control
// loop yet. Handheld lat/lon/baro_alt_m are relayed straight into telemetry,
// log-only, for the GIGA to write out - never used for control here.
// Everything else that depends on real sensors is still stubbed - no
// HX711/hall-sensor reads, no CAN61, no PID, no tree-height/force-ramp
// logic. See docs/software.md's "Current Firmware Status" section for the
// exact list of what's stubbed vs real.
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

// OTA firmware updates over WiFi (ArduinoOTA, bundled with the esp32 board
// package - no separate Library Manager install needed, unlike ArduinoJson).
// Bench/development convenience ONLY - see setup()'s connectWifiForOta() for
// why this must never be allowed to block or delay boot: the winch runs at
// a real flying field with no WiFi at all, and the safety-critical control
// firmware must come up exactly the same whether or not a network exists.
// Never trigger an OTA upload while a tow is actually in progress - flashing
// pauses the whole loop (including e-stop polling) for the duration of the
// write, same as any other firmware update; only do this on the bench.
// Set to 0 to strip WiFi/OTA out of the build entirely (e.g. a field build).
#define ENABLE_OTA 1

#include <ArduinoJson.h>
#if ENABLE_OTA
#include <WiFi.h>
#include <ArduinoOTA.h>
#include "secrets.h"  // WIFI_SSID / WIFI_PASSWORD - gitignored, fill in yourself
#endif

// ---------------------------------------------------------------------------
// Pins (see docs/electronics.md's pin map table)
// ---------------------------------------------------------------------------
static const int PIN_HELTEC_TXD = 14;  // ESP32 -> Heltec RXD
static const int PIN_HELTEC_RXD = 21;  // ESP32 <- Heltec TXD
// GIGA link uses hardware UART0 (GPIO43/44) via Serial0 - fixed pins, no remap.
static const int PIN_ESTOP_SENSE = 10;  // active-low, winchman remote e-stop switch
static const int PIN_STATUS_LED = 48;   // onboard addressable RGB LED (DevKitC-1)

// Physical "release" trigger - lets the winchman end a tow cleanly by hand,
// without depending on the GIGA link (see docs/software.md "Field authority":
// state_cmd is otherwise GIGA-only). Wired to J8 (winchman remote, 7-pin)
// pin 7 / SPARE_GPIO2, with its own dedicated 10k pull-up (R35, see
// docs/electronics.md) - same convention as the other four winchman-remote
// switches, not an internal-pull-up-only bodge. GPIO1 (still reachable via
// J6, the spare-I/O connector) remains free for a future addition.
static const int PIN_RELEASE_SENSE = 2;

// Winchman remote tension+5kg/-5kg buttons. Real intended use (per project
// discussion, not yet in docs/electronics.md): live field recalibration -
// while towing, the winchman nudges the load-cell reading by 1kg per press
// to match an external reference scale at the start location, then confirms
// the new 100kg point with the reset-to-programmed/Set button (that third
// button isn't wired into logic yet, only these two nudge buttons are).
static const int PIN_TENSION_PLUS_SENSE  = 11;
static const int PIN_TENSION_MINUS_SENSE = 12;

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
// Operating mode - reserved for the still-undecided question of whether the
// pilot handheld should be allowed to trigger calibrate/calibration_done
// (currently GIGA-only, see requestStateTransition()/handleCommand()).
//
// With a winchman present, GIGA-only calibrate authority matches the real
// procedure: the start-location person requests calibration by radio, the
// winchman triggers it. Flying solo, there's no winchman to relay to and no
// one at the winch at all, so that restriction would block calibration
// entirely - hence this mode flag, to eventually let the handheld act
// directly in SOLO_TOW.
//
// Not wired into any logic yet - defaults to the current (safe, unchanged)
// behavior. Nothing reads this yet.
enum class OperatingMode : uint8_t {
  WINCHMAN_AVAILABLE,  // current behavior: calibrate is GIGA/winchman-only
  SOLO_TOW,            // reserved: handheld should be able to calibrate directly
};
OperatingMode g_operatingMode = OperatingMode::WINCHMAN_AVAILABLE;

// Set once by the GIGA at boot (operating_mode + pilot_name + pilot_weight_kg,
// see handleCommand()) - all three are required before IDLE will accept
// "calibrate", so a tow can't proceed without the operator having
// deliberately confirmed them for the day. pilot_name/pilot_weight_kg are
// entered live on the winchman controller (GIGA touchscreen) at the winch,
// per tow - never prepared ahead of time from elsewhere, since they change
// with whoever's flying next. None of the three are persisted across a
// reboot; every power-up starts unconfigured, on purpose - stale settings
// from a previous day/pilot must never carry over silently.
struct BootConfig {
  bool operatingModeSet = false;
  bool pilotNameSet = false;
  char pilotName[32] = "";
  bool pilotWeightSet = false;
  float pilotWeightKg = 0;
};
BootConfig g_bootConfig;

bool bootConfigured() {
  return g_bootConfig.operatingModeSet && g_bootConfig.pilotNameSet && g_bootConfig.pilotWeightSet;
}

// Winchman-mode-only: after a tow ends (release) or a fault (e-stop), forget
// pilot_name/pilot_weight_kg so the boot-config lock re-engages before the
// *next* tow - forces the winchman to actively (re-)confirm who's flying and
// their weight, rather than silently reusing the previous pilot's info
// (pilot_name matters for tow-log administration with students, same
// reasoning pilot_weight_kg already had for the tow-force calc). Skipped in
// SOLO_TOW: same pilot for the whole session, so both should persist across
// repeat tows instead of forcing re-entry each time.
void resetPilotInfoIfWinchman() {
  if (g_operatingMode != OperatingMode::WINCHMAN_AVAILABLE) return;
  g_bootConfig.pilotNameSet = false;
  g_bootConfig.pilotName[0] = '\0';
  g_bootConfig.pilotWeightSet = false;
  g_bootConfig.pilotWeightKg = 0;
}

// Tunable control-loop parameters, sent once at boot from the GIGA's SD-card
// config file (see docs/software.md "Boot Configuration") rather than
// hardcoded here - these will need dialing in over real flights/tows, and a
// field-editable file beats a firmware reflash for that. None of these are
// acted on by the control loop yet (PID/ramp logic isn't implemented - see
// docs/software.md "Current Firmware Status") - captured now so the wire
// format and boot flow are ready ahead of that work landing.
struct TowConfig {
  bool loaded = false;
  float underTreeHeightReductionPct = 0;
  float startReductionPct = 0;
  float treeheightToFullTowRampS = 0;
  float startToTreeheightRampS = 0;
  float releaseBeforeTakingInS = 0;
  float pidKp = 0;
  float pidKi = 0;
  float pidKd = 0;
};
TowConfig g_towConfig;

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
  // Handheld GPS/baro, relayed into telemetry for the GIGA to log - the
  // mainboard doesn't act on these itself, just passes them through (see
  // docs/software.md's GPS/logging design). hasPosition guards against
  // relaying stale 0,0 before the handheld's first fix arrives.
  bool hasPosition = false;
  float lat = 0;
  float lon = 0;
  float baroAltM = 0;
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
  // 512, not 256: the boot-time config push from the GIGA (operating_mode +
  // pilot_name + pilot_weight_kg + calibration + ramp/PID tunables, see
  // BootConfig/TowConfig below) is a wide single-line message - a truncated line here
  // fails to parse silently (see poll() below) and leaves the boot-config
  // lock permanently engaged with no obvious cause, so this needs real
  // headroom, not just enough for today's fields.
  char _buf[512];
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

// Active-low, same convention as the e-stop switch above.
bool releaseSwitchPressed() {
  return digitalRead(PIN_RELEASE_SENSE) == LOW;
}

bool tensionPlusSwitchPressed() {
  return digitalRead(PIN_TENSION_PLUS_SENSE) == LOW;
}

bool tensionMinusSwitchPressed() {
  return digitalRead(PIN_TENSION_MINUS_SENSE) == LOW;
}

// ---------------------------------------------------------------------------
// SIMULATED tension_kg - bench-test stand-in for the real HX711 reading
// (readLoadCellRaw() above is still a stub returning 0, see its own TODO).
// This is deliberately a separate, simple kg-value simulation rather than
// routed through readLoadCellRaw()/g_cal, so it can be exercised on the
// bench (button box + GIGA gauge) before any real load-cell math exists.
//
// Real procedure being simulated (per project discussion): once the tare
// point is set (state_cmd:"calibrate"), the winch ramps tow force up to the
// 100kg calibration reference over a few seconds, then the winchman fine-
// tunes with the +5kg/-5kg buttons against an external reference scale
// before confirming with calibration_done (in real use this ramp would
// rarely land on an exact 100 - e.g. ~96kg is a realistic real-world
// result - which is exactly why the nudge buttons and the GIGA's own
// Set-time cal_raw_100kg correction exist at all).
// ---------------------------------------------------------------------------
static const float    SIM_CALIBRATION_TARGET_KG = 100.0f;
static const uint32_t SIM_RAMP_UP_DURATION_MS    = 6000;
static const uint32_t SIM_RAMP_DOWN_DURATION_MS  = 5000;
static const float    SIM_TENSION_MIN_KG         = 0.0f;
static const float    SIM_TENSION_MAX_KG         = 150.0f;

static float    g_simulatedTensionKg = 0;
static bool     g_simRampActive      = false;
static uint32_t g_simRampStartMillis = 0;
static uint32_t g_simRampDurationMs  = 0;
static float    g_simRampStartKg     = 0;
static float    g_simRampTargetKg    = 0;

// Generic ramp start - used both for the ZERO-point Set's ramp up to
// SIM_CALIBRATION_TARGET_KG and for the ramp back down to 0 once
// calibration_done fires (see requestStateTransition()'s own calls below).
void startSimulatedTensionRamp(float fromKg, float toKg, uint32_t durationMs) {
  g_simulatedTensionKg = fromKg;
  g_simRampStartKg = fromKg;
  g_simRampTargetKg = toKg;
  g_simRampDurationMs = durationMs;
  g_simRampStartMillis = millis();
  g_simRampActive = true;
}

// Call every loop(). A manual +5kg/-5kg nudge (see loop()) cancels the ramp
// so the button takes direct control from that point on, rather than being
// overwritten by the next ramp tick.
void updateSimulatedTensionRamp() {
  if (!g_simRampActive) return;
  uint32_t elapsed = millis() - g_simRampStartMillis;
  if (elapsed >= g_simRampDurationMs) {
    g_simulatedTensionKg = g_simRampTargetKg;
    g_simRampActive = false;
    return;
  }
  float frac = (float)elapsed / (float)g_simRampDurationMs;
  g_simulatedTensionKg = g_simRampStartKg + frac * (g_simRampTargetKg - g_simRampStartKg);
}

// ---------------------------------------------------------------------------
// Line paid-out distance (rope_out_m) - a real tracked variable now (was a
// literal hardcoded 900 in sendTelemetry() before), still a fixed test
// placeholder ahead of real hall-sensor pulse counting, but having it as a
// variable lets the CALIBRATING safety check below compare against it. It
// never actually changes yet, so that check stays dormant until a real
// sensor reading replaces this placeholder.
// ---------------------------------------------------------------------------
static float g_ropeOutM = 900.0f;

// Safety check for the CALIBRATING ramp: reeling in more than this much line
// just to reach the 100kg reference means the line likely isn't properly
// anchored at the start location (a correctly anchored line needs very
// little travel to build tension) - cancel back to IDLE rather than
// continuing to ramp toward a load that shouldn't need this much travel.
static const float CALIBRATION_MAX_ROPE_IN_M = 10.0f;
static float        g_calibrationStartRopeOutM = 0;

void checkCalibrationRopeInSafety() {
  if (g_state != WinchState::CALIBRATING) return;
  float ropeInM = g_calibrationStartRopeOutM - g_ropeOutM;  // positive = reeled in
  if (ropeInM > CALIBRATION_MAX_ROPE_IN_M) {
    Serial.printf("Calibration cancelled: %.1fm reeled in without reaching target - line likely not anchored\n", ropeInM);
    g_simRampActive = false;
    g_simulatedTensionKg = 0;
    g_state = WinchState::IDLE;
  }
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
    resetPilotInfoIfWinchman();
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
    // Boot-config lock: the operator must have set operating_mode, pilot_name
    // and pilot_weight_kg from the GIGA this session before IDLE will let go.
    if (!bootConfigured()) {
      Serial.println("calibrate refused: set operating_mode, pilot_name and pilot_weight_kg first");
      return;
    }
    // Tare point: assumes no load on the line yet, matching the real
    // procedure (hook up the scale, THEN raise tension to 100kg).
    g_cal.valid = false;
    g_cal.rawAtZero = readLoadCellRaw();
    g_state = WinchState::CALIBRATING;
    g_calibrationStartRopeOutM = g_ropeOutM;  // baseline for checkCalibrationRopeInSafety()
    startSimulatedTensionRamp(0, SIM_CALIBRATION_TARGET_KG, SIM_RAMP_UP_DURATION_MS);  // bench-test stand-in, see its own comment above

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
    // No need to keep holding tension once calibration is captured -
    // simulated release back to slack over 5s (bench-test stand-in, real
    // motor control doesn't exist yet either).
    startSimulatedTensionRamp(g_simulatedTensionKg, 0, SIM_RAMP_DOWN_DURATION_MS);

  } else if (strcmp(cmd, "start_tow") == 0) {
    g_state = WinchState::NORMAL_TOW;
  } else if (strcmp(cmd, "release") == 0) {
    g_state = WinchState::RELEASE;
    resetPilotInfoIfWinchman();
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
    // lat/lon/baro_alt_m: log-only, relayed straight into telemetry for the
    // GIGA to write to its SD card - never used for control here (see
    // "GPS is kept ... for track logging only" in docs/electronics.md).
    if (doc["lat"].is<float>() && doc["lon"].is<float>()) {
      g_cmd.lat = doc["lat"];
      g_cmd.lon = doc["lon"];
      g_cmd.hasPosition = true;
    }
    if (doc["baro_alt_m"].is<float>()) {
      g_cmd.baroAltM = doc["baro_alt_m"];
    }
  }

  // state_cmd / tension_setpoint_kg / fault_reset / operating_mode /
  // pilot_name / pilot_weight_kg / use_saved_calibration / cal_raw_* /
  // tow-config tunables: GIGA-only.
  if (isGiga) {
    if (doc["operating_mode"].is<const char*>()) {
      const char* mode = doc["operating_mode"];
      if (strcmp(mode, "solo") == 0) {
        g_operatingMode = OperatingMode::SOLO_TOW;
        g_bootConfig.operatingModeSet = true;
      } else if (strcmp(mode, "winchman") == 0) {
        g_operatingMode = OperatingMode::WINCHMAN_AVAILABLE;
        g_bootConfig.operatingModeSet = true;
      } else {
        Serial.printf("unknown operating_mode '%s' ignored\n", mode);
      }
    }
    if (doc["pilot_name"].is<const char*>()) {
      const char* name = doc["pilot_name"];
      strncpy(g_bootConfig.pilotName, name, sizeof(g_bootConfig.pilotName) - 1);
      g_bootConfig.pilotName[sizeof(g_bootConfig.pilotName) - 1] = '\0';
      g_bootConfig.pilotNameSet = true;
    }
    if (doc["pilot_weight_kg"].is<float>()) {
      g_bootConfig.pilotWeightKg = doc["pilot_weight_kg"];
      g_bootConfig.pilotWeightSet = true;
    }
    // use_saved_calibration: GIGA boot-UI switch, default off (see
    // docs/control_philosophy.md "Calibrating") - only takes effect together
    // with cal_raw_zero/cal_raw_100kg, and marks calibration valid
    // immediately instead of requiring a fresh CALIBRATING cycle this
    // session. Off (the default/absent case) leaves the mandatory-live-
    // calibration behavior from before completely unchanged.
    if (doc["use_saved_calibration"].is<bool>() && doc["use_saved_calibration"].as<bool>()
        && doc["cal_raw_zero"].is<long>() && doc["cal_raw_100kg"].is<long>()) {
      long rawZero = doc["cal_raw_zero"];
      long raw100 = doc["cal_raw_100kg"];
      g_cal.rawAtZero = rawZero;
      g_cal.countsPerKg = (raw100 - rawZero) / 100.0f;
      g_cal.valid = true;
      Serial.println("Loaded saved calibration from GIGA config (use_saved_calibration:true)");
    }
    if (doc["under_tree_height_reduction_pct"].is<float>()) {
      g_towConfig.underTreeHeightReductionPct = doc["under_tree_height_reduction_pct"];
      g_towConfig.loaded = true;
    }
    if (doc["start_reduction_pct"].is<float>()) {
      g_towConfig.startReductionPct = doc["start_reduction_pct"];
      g_towConfig.loaded = true;
    }
    if (doc["treeheight_to_full_tow_ramp_s"].is<float>()) {
      g_towConfig.treeheightToFullTowRampS = doc["treeheight_to_full_tow_ramp_s"];
      g_towConfig.loaded = true;
    }
    if (doc["start_to_treeheight_ramp_s"].is<float>()) {
      g_towConfig.startToTreeheightRampS = doc["start_to_treeheight_ramp_s"];
      g_towConfig.loaded = true;
    }
    if (doc["release_before_taking_in_s"].is<float>()) {
      g_towConfig.releaseBeforeTakingInS = doc["release_before_taking_in_s"];
      g_towConfig.loaded = true;
    }
    if (doc["pid_kp"].is<float>()) g_towConfig.pidKp = doc["pid_kp"];
    if (doc["pid_ki"].is<float>()) g_towConfig.pidKi = doc["pid_ki"];
    if (doc["pid_kd"].is<float>()) g_towConfig.pidKd = doc["pid_kd"];
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
  // up (see docs/software.md "Current Firmware Status"). tension_kg is the
  // bench-test simulation above (button-nudge + calibration ramp) until the
  // HX711 is real; rope_out_m is a fixed test placeholder (900m) for
  // exercising the GIGA's distance display ahead of real hall-sensor pulse
  // counting; rpm/motor_current_a stay placeholder 0s.
  doc["tension_kg"] = g_simulatedTensionKg;
  doc["tension_setpoint_kg"] = g_cmd.tensionSetpointKg;
  doc["rope_out_m"] = g_ropeOutM;
  doc["rpm"] = 0;
  doc["motor_current_a"] = 0;
  doc["fault"] = (g_state == WinchState::EMERGENCY_STOPPED);
  doc["fault_code"] = 0;
  doc["line_cut"] = false;
  doc["cal_valid"] = g_cal.valid;
  doc["boot_configured"] = bootConfigured();
  doc["operating_mode"] = (g_operatingMode == OperatingMode::SOLO_TOW) ? "solo" : "winchman";
  doc["pilot_name"] = g_bootConfig.pilotName;
  doc["pilot_weight_kg"] = g_bootConfig.pilotWeightKg;
  doc["tow_config_loaded"] = g_towConfig.loaded;

  // Handheld GPS/baro passthrough for GIGA logging (see docs/software.md's
  // GPS/logging design) - omitted entirely until the first handheld fix
  // arrives, rather than sending misleading 0,0 placeholders.
  if (g_cmd.hasPosition) {
    doc["lat"] = g_cmd.lat;
    doc["lon"] = g_cmd.lon;
    doc["baro_alt_m"] = g_cmd.baroAltM;
  }

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
#if ENABLE_OTA
static const uint32_t WIFI_CONNECT_TIMEOUT_MS = 8000;  // bounded - see ENABLE_OTA comment above
static bool g_otaReady = false;

// Bounded, best-effort - tries for WIFI_CONNECT_TIMEOUT_MS then gives up and
// returns, leaving g_otaReady false. Called once from setup(), never again -
// no retry loop here, so a WiFi outage mid-session can't cost control-loop
// time later. Skipped entirely if WIFI_SSID is empty (secrets.h unfilled).
static void connectWifiForOta() {
  if (strlen(WIFI_SSID) == 0) {
    Serial.println("OTA: WIFI_SSID empty, skipping WiFi/OTA");
    return;
  }
  Serial.printf("OTA: connecting to WiFi '%s'...\n", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < WIFI_CONNECT_TIMEOUT_MS) {
    delay(200);
  }
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("OTA: WiFi connect timed out, continuing without it");
    WiFi.mode(WIFI_OFF);
    return;
  }
  Serial.print("OTA: WiFi connected, IP ");
  Serial.println(WiFi.localIP());

  ArduinoOTA.setHostname("winch-mainboard");
  ArduinoOTA.begin();
  g_otaReady = true;
  Serial.println("OTA: ready (Arduino IDE > Tools > Port > Network Ports)");
}
#endif

void setup() {
  Serial.begin(115200);   // USB-CDC, debug console only (see board-setting note above)
  Serial0.begin(115200);  // GIGA UART, native UART0 pins (GPIO43/44)
  Serial1.begin(115200, SERIAL_8N1, PIN_HELTEC_RXD, PIN_HELTEC_TXD);  // Heltec UART
  pinMode(PIN_ESTOP_SENSE, INPUT_PULLUP);
  pinMode(PIN_RELEASE_SENSE, INPUT_PULLUP);
  pinMode(PIN_TENSION_PLUS_SENSE, INPUT_PULLUP);
  pinMode(PIN_TENSION_MINUS_SENSE, INPUT_PULLUP);

  Serial.println("ESP32 mainboard - comms skeleton starting");

#if ENABLE_OTA
  connectWifiForOta();

  // Boot-test marker (bright white below is distinct from IDLE's own
  // dim-white (20,20,20) - see updateStatusLed()): 1s green if WiFi/OTA
  // came up, 1s red if it didn't, then 1s white before falling through to
  // the normal state-driven LED (loop()'s own updateStatusLed() call sets
  // the real dim IDLE colour immediately after). Lets you confirm at a
  // glance, without the USB serial monitor, whether this exact build got
  // a WiFi/OTA connection before trying an actual OTA upload.
  if (g_otaReady) {
    rgbLedWrite(PIN_STATUS_LED, 0, 255, 0);
  } else {
    rgbLedWrite(PIN_STATUS_LED, 255, 0, 0);
  }
  delay(1000);
  rgbLedWrite(PIN_STATUS_LED, 255, 255, 255);
  delay(1000);
#endif
}

void loop() {
#if ENABLE_OTA
  // Cheap/non-blocking when idle - just checks for an incoming OTA request.
  // Only meaningfully does anything if connectWifiForOta() actually got a
  // connection at boot; g_otaReady stays false (and this is a no-op)
  // whenever WiFi wasn't available, e.g. out at the field.
  if (g_otaReady) ArduinoOTA.handle();
#endif

  // Checked first, every loop, and re-asserted unconditionally while held -
  // not just on the rising edge. This is the local hardware e-stop's own
  // authority, independent of both UART links (see docs/electronics.md's
  // line-cut/e-stop reasoning): even if a command somehow changed the state
  // away from EMERGENCY_STOPPED in the same loop iteration, the very next
  // iteration puts it straight back for as long as the switch is down.
  static bool lastEstopPressed = false;
  bool estopPressed = estopSwitchPressed();
  if (estopPressed) {
    if (!lastEstopPressed) {
      Serial.println("Local e-stop switch pressed -> EMERGENCY_STOPPED");
      resetPilotInfoIfWinchman();
    }
    g_state = WinchState::EMERGENCY_STOPPED;
  }
  lastEstopPressed = estopPressed;

  // Physical release trigger - one press requests "release" once (not held
  // continuously like e-stop's override above), same guarded path as the
  // GIGA's own state_cmd:"release" (see requestStateTransition()). Lets the
  // winchman end a tow cleanly by hand even with the GIGA link dead.
  static bool lastReleasePressed = false;
  bool releasePressed = releaseSwitchPressed();
  if (releasePressed && !lastReleasePressed) {
    Serial.println("Local release switch pressed -> requesting RELEASE");
    requestStateTransition("release");
  }
  lastReleasePressed = releasePressed;

  // Tension +5kg/-5kg buttons - simulated 1kg-per-press nudge (see
  // g_simulatedTensionKg's own comment above). A press cancels any
  // in-progress calibration ramp so it doesn't get overwritten next tick.
  static bool lastTensionPlusPressed = false;
  bool tensionPlusPressed = tensionPlusSwitchPressed();
  if (tensionPlusPressed && !lastTensionPlusPressed) {
    g_simRampActive = false;
    g_simulatedTensionKg = min(SIM_TENSION_MAX_KG, g_simulatedTensionKg + 1.0f);
    Serial.printf("Simulated tension +1kg -> %.0f kg\n", g_simulatedTensionKg);
  }
  lastTensionPlusPressed = tensionPlusPressed;

  static bool lastTensionMinusPressed = false;
  bool tensionMinusPressed = tensionMinusSwitchPressed();
  if (tensionMinusPressed && !lastTensionMinusPressed) {
    g_simRampActive = false;
    g_simulatedTensionKg = max(SIM_TENSION_MIN_KG, g_simulatedTensionKg - 1.0f);
    Serial.printf("Simulated tension -1kg -> %.0f kg\n", g_simulatedTensionKg);
  }
  lastTensionMinusPressed = tensionMinusPressed;

  updateSimulatedTensionRamp();
  checkCalibrationRopeInSafety();

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
