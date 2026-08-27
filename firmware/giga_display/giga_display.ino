/*
  GIGA Display Shield - winchman UI

  Splash screen (Arduino teal background, yellow logo) for
  5 seconds, then switches to the homepage. Homepage is a
  placeholder - the real winch UI isn't built yet.

  Same library stack as Arduino's own LVGLDemo example
  (Arduino_H7_Video + Arduino_GigaDisplayTouch + lvgl).

  Before this builds: convert assets/splash_logo.png with the
  LVGL Image Converter (https://lvgl.io/tools/imageconverter),
  LVGL v9 tab:
    - Name: splash_logo
    - Color format: RGB565A8 - NOT plain RGB565 (no alpha
      channel, renders as a solid opaque block) and not
      ARGB8888 (needlessly bigger for this image - only 1 real
      colour is used). RGB565A8 keeps a real per-pixel alpha
      channel for the logo's transparent background/anti-
      aliased edges while staying smaller than full ARGB8888.
    - Output format: C array
  Download the result and drop it next to this .ino file.

  Also needs the "ArduinoJson" library (Library Manager, v7.x)
  for the tow-config API below.

  Tow-config SD card wiring (confirmed against a real GIGA on
  forum.arduino.cc/t/arduino-giga-r1-and-sd-card/1221185 - the
  plain SD library works as-is with this exact wiring, no custom
  SPIClass needed despite MISO/MOSI/SCK being on the GIGA's
  separate SPI1 header rather than the usual SPI pins):
    MISO -> D89, MOSI -> D90, SCK -> D91, CS -> D10, 3.3V, GND
*/

#include "Arduino_H7_Video.h"
#include "Arduino_GigaDisplayTouch.h"
#include "lvgl.h"
#include <WiFi.h>
#include <SD.h>
#include <ArduinoJson.h>
#include <Arduino_GigaDisplay.h> /* GigaDisplayRGB - the Display Shield's own DL1 LED, I2C-driven (see below) */
#include "secrets.h" /* WIFI_SSID / WIFI_PASSWORD - gitignored, fill in yourself */

Arduino_H7_Video         Display(800, 480, GigaDisplayShield);
Arduino_GigaDisplayTouch TouchDetector;

#define ARDUINO_TEAL     lv_color_hex(0x00878F)
#define LIGHT_GREY       lv_color_hex(0xE4E7E7)
#define LIGHT_GREEN      lv_color_hex(0xA9DED6)
#define WIFI_DOT_GREEN   lv_color_hex(0x2ECC71)
#define WIFI_DOT_RED     lv_color_hex(0xE74C3C)
#define SPLASH_DURATION_MS 5000
#define MAX_WIFI_NETWORKS 20
#define WIFI_STATUS_POLL_MS 1000

#define SD_CS_PIN 10
#define TOW_CONFIG_PATH "/tow_config.json"
#define HTTP_PORT 80

static lv_obj_t *splash_screen;
static lv_obj_t *home_screen;
static lv_obj_t *settings_btn;
static lv_obj_t *settings_panel;
static lv_obj_t *content_area;
static lv_obj_t *keyboard;
static lv_obj_t *wifi_status_dot;

/* Boot flow: splash -> mode_select_screen (Solo-tow/Winchman) ->
   pilot_info_screen (Name/Weight) -> home_screen ("Start", idle state). */
static lv_obj_t *mode_select_screen;
static lv_obj_t *pilot_info_screen;
static lv_obj_t *pilot_name_ta;
static lv_obj_t *pilot_weight_value_label;
static lv_obj_t *pilot_info_keyboard;

/* "Start" (home_screen's idle state) layout - separate objects from
   content_area/settings_panel below, which stay a gear-icon-triggered
   overlay for Network/Tow Settings exactly as before. Placeholders only
   for now - real tension display / tow-state controls are the next
   step once designed. */
static lv_obj_t *start_title;
static lv_obj_t *start_grey_panel;
static lv_obj_t *start_green_panel;
static lv_obj_t *start_pilot_label;
static lv_obj_t *start_calibrate_btn;
static lv_obj_t *start_tow_btn;
static lv_obj_t *calibrate_value_label;
static lv_obj_t *calibrate_set_btn;
static lv_obj_t *calibrate_cancel_btn;
static lv_obj_t *tension_gauge_arc;
static lv_obj_t *tension_gauge_label;
static lv_obj_t *tension_gauge_unit_label;
static lv_obj_t *rope_out_label;

static char  pilot_name[32] = "";
static float pilot_weight_kg = 80.0f;

static char wifi_ssids[MAX_WIFI_NETWORKS][33];
static int  wifi_network_count = 0;
static char selected_ssid[33] = "";

static lv_obj_t   *wifi_password_ta;
static lv_obj_t   *wifi_status_label;
static lv_timer_t *wifi_connect_timer = NULL;

/* Same field names/shape as MQTT_Layout's config/giga_boot_config.json -
   the dashboard is the only place these get edited, this firmware just
   receives the pushed JSON, keeps it in memory and mirrors it to the SD
   card so it survives a power cycle. */
struct TowConfig {
  char  operating_mode[16] = "winchman";
  bool  use_saved_calibration = false;
  int   cal_raw_zero = 0;
  int   cal_raw_100kg = 0;
  int   under_tree_height_reduction_pct = 40;
  int   start_reduction_pct = 60;
  float treeheight_to_full_tow_ramp_s = 6;
  float start_to_treeheight_ramp_s = 6;
  float release_before_taking_in_s = 4;
  float pid_kp = 0;
  float pid_ki = 0;
  float pid_kd = 0;
};

static TowConfig tow_config;
static bool      sd_ready = false;
static WiFiServer http_server(HTTP_PORT);
static bool       http_server_started = false;

// ---------------------------------------------------------------------------
// ESP32 link (GIGA pins D0/D1 -> Arduino object Serial1, NOT Serial0 -
// GIGA's `Serial` is reserved for USB, so the D0/D1 hardware UART the
// datasheet itself labels "Serial 0" is exposed as `Serial1` in code -
// confirmed against Arduino's own docs/forum before wiring this up, not
// guessed). Wired to the ESP32 mainboard's own GIGA-UART pins (GPIO43
// TXD -> here RX, GPIO44 RXD -> here TX), same JSON `cmd`/`telemetry`
// protocol as docs/software.md. First step: just mirror `telemetry`'s
// `state` on the onboard RGB LED, using the exact same colour table as
// esp32_mainboard.ino's updateStatusLed() - proves the link/JSON
// parsing works before building any real UI on top of it.
// ---------------------------------------------------------------------------
struct WinchStateColor {
  const char *state;
  uint8_t     r, g, b;
};

static const WinchStateColor WINCH_STATE_COLORS[] = {
  { "IDLE",              20,  20,  20  },
  { "CALIBRATING",       0,   0,   255 },
  { "READY",             0,   255, 0   },
  { "LAUNCH",            255, 0,   255 },
  { "UNDER_TREE_HEIGHT", 255, 255, 0   },
  { "NORMAL_TOW",        0,   255, 100 },
  { "PAY_OUT",           255, 100, 0   },
  { "RELEASE",           150, 0,   255 },
  { "RECOVERY",          0,   200, 255 },
};
#define WINCH_STATE_COLOR_COUNT (sizeof(WINCH_STATE_COLORS) / sizeof(WINCH_STATE_COLORS[0]))

static char   g_winch_state[24] = "";  // last state seen in a telemetry message, "" = none yet
static float  g_last_tension_kg = 0;   // last tension_kg seen in a telemetry message
static String esp32_line_buffer;

/* The base GIGA R1 board's own LEDR/LEDG/LEDB never lit at all in
   testing (neither polarity, ruled out with an explicit on-hardware
   test) and separately, analogWrite() on those same pins crashed the
   board outright (mbed fault handler, not this sketch's error() loop)
   - dead end either way. The Display Shield has its OWN separate RGB
   LED (DL1), driven over I2C by a dedicated IS31FL3197 driver chip,
   completely unrelated to the base board's pins - reached through the
   official Arduino_GigaDisplay library's GigaDisplayRGB class
   (confirmed against its real source on GitHub, and against a working
   MicroPython I2C implementation of the same protocol). Full 0-255
   per-channel fidelity, real PWM done by the driver chip itself over
   I2C - no crash risk like analogWrite on the base board's pins had,
   so the ESP32's exact RGB triples can be used as-is, no on/off
   approximation needed. */
static GigaDisplayRGB shield_rgb;

static void set_status_led_rgb(uint8_t r, uint8_t g, uint8_t b) {
  shield_rgb.on(r, g, b);
}

static void apply_status_led_for_state(const char *state) {
  if (strcmp(state, "EMERGENCY_STOPPED") == 0) {
    /* Same ~2Hz blink as the ESP32 side - re-evaluated by a periodic
       timer (see setup()), not just when a new telemetry line arrives,
       so it keeps blinking smoothly between messages. */
    bool on = (millis() / 250) % 2;
    set_status_led_rgb(on ? 255 : 0, 0, 0);
    return;
  }
  for (size_t i = 0; i < WINCH_STATE_COLOR_COUNT; i++) {
    if (strcmp(state, WINCH_STATE_COLORS[i].state) == 0) {
      set_status_led_rgb(WINCH_STATE_COLORS[i].r, WINCH_STATE_COLORS[i].g, WINCH_STATE_COLORS[i].b);
      return;
    }
  }
  set_status_led_rgb(0, 0, 0);  // unknown or no telemetry received yet
}

static void led_state_refresh_cb(lv_timer_t *timer) {
  apply_status_led_for_state(g_winch_state);
}

static void handle_esp32_telemetry_line(const String &line) {
  JsonDocument doc;
  if (deserializeJson(doc, line) != DeserializationError::Ok) return;
  const char *type = doc["type"] | "";
  if (strcmp(type, "telemetry") != 0) return;
  const char *state = doc["state"] | "";
  strlcpy(g_winch_state, state, sizeof(g_winch_state));
  apply_status_led_for_state(g_winch_state);

  /* Tension gauge + rope-out distance, top/bottom of the Start screen's
     green panel. %d, not %.0f - see refresh_pilot_weight_label()'s own
     comment on LVGL's lightweight snprintf silently printing a literal
     "f" for any float spec.

     Only touch the LVGL widgets when the displayed integer actually
     changes, rather than unconditionally on every 5Hz telemetry line -
     telemetry arrives constantly for the whole session (not just during
     calibration), and repeated lv_label_set_text_fmt/lv_arc_set_value
     calls reallocate/redraw even when nothing visible would change.
     Cuts a lot of needless churn on a memory-constrained target -
     suspected contributor to a crash seen after repeated on-screen use
     this session, though not confirmed with a real crash dump. */
  float tension_kg = doc["tension_kg"] | 0.0f;
  float rope_out_m = doc["rope_out_m"] | 0.0f;
  g_last_tension_kg = tension_kg;

  static int last_tension_int = INT32_MIN;
  static int last_rope_out_int = INT32_MIN;
  int tension_int = (int)tension_kg;
  int rope_out_int = (int)rope_out_m;
  if (tension_int != last_tension_int) {
    lv_arc_set_value(tension_gauge_arc, tension_int);
    lv_label_set_text_fmt(tension_gauge_label, "%d", tension_int);
    last_tension_int = tension_int;
  }
  if (rope_out_int != last_rope_out_int) {
    lv_label_set_text_fmt(rope_out_label, "%d m", rope_out_int);
    last_rope_out_int = rope_out_int;
  }
}

/* Non-blocking, byte-at-a-time - same one-JSON-object-per-line framing
   as docs/software.md. Buffer capped the same way the ESP32 side caps
   its own line buffer (512B) - a stuck/oversized line gets dropped
   instead of growing forever. */
static void poll_esp32_uart() {
  while (Serial1.available()) {
    char c = (char)Serial1.read();
    if (c == '\n') {
      /* Debug echo to the USB Serial Monitor - lets us see whether
         anything is arriving on Serial1 at all, and what it actually
         looks like, before worrying about whether the JSON parses. */
      Serial.print("ESP32 RX: ");
      Serial.println(esp32_line_buffer);
      handle_esp32_telemetry_line(esp32_line_buffer);
      esp32_line_buffer = "";
    } else if (c != '\r') {
      esp32_line_buffer += c;
      if (esp32_line_buffer.length() > 600) esp32_line_buffer = "";
    }
  }
}

/* Boot-config `cmd` messages to the ESP32 - see docs/software.md's `cmd`
   fields table. Sent as two separate partial messages (operating_mode +
   tow-config tunables right after Solo-tow/Winchman is tapped,
   pilot_name + weight after the pilot-info OK) since the ESP32 applies
   each field independently and only requires operating_mode, pilot_name
   and pilot_weight_kg to have arrived at SOME point - not necessarily
   in the same message - before it unlocks calibrate. */
static uint16_t g_giga_cmd_seq = 0;

static void send_cmd_to_esp32(JsonDocument &doc) {
  doc["type"] = "cmd";
  doc["seq"] = g_giga_cmd_seq++;
  doc["src"] = "giga";
  String out;
  serializeJson(doc, out);
  Serial1.println(out);
}

static void send_boot_tow_config_to_esp32() {
  JsonDocument doc;
  doc["operating_mode"] = tow_config.operating_mode;
  doc["use_saved_calibration"] = tow_config.use_saved_calibration;
  doc["cal_raw_zero"] = tow_config.cal_raw_zero;
  doc["cal_raw_100kg"] = tow_config.cal_raw_100kg;
  doc["under_tree_height_reduction_pct"] = tow_config.under_tree_height_reduction_pct;
  doc["start_reduction_pct"] = tow_config.start_reduction_pct;
  doc["treeheight_to_full_tow_ramp_s"] = tow_config.treeheight_to_full_tow_ramp_s;
  doc["start_to_treeheight_ramp_s"] = tow_config.start_to_treeheight_ramp_s;
  doc["release_before_taking_in_s"] = tow_config.release_before_taking_in_s;
  doc["pid_kp"] = tow_config.pid_kp;
  doc["pid_ki"] = tow_config.pid_ki;
  doc["pid_kd"] = tow_config.pid_kd;
  send_cmd_to_esp32(doc);
}

static void send_pilot_info_to_esp32() {
  JsonDocument doc;
  doc["pilot_name"] = pilot_name;
  doc["pilot_weight_kg"] = pilot_weight_kg;
  send_cmd_to_esp32(doc);
}

void error() {
  while (true) {
    shield_rgb.on(255, 0, 0);
    delay(500);
    shield_rgb.off();
    delay(500);
  }
}

static String tow_config_to_json() {
  JsonDocument doc;
  doc["operating_mode"] = tow_config.operating_mode;
  doc["use_saved_calibration"] = tow_config.use_saved_calibration;
  doc["cal_raw_zero"] = tow_config.cal_raw_zero;
  doc["cal_raw_100kg"] = tow_config.cal_raw_100kg;
  doc["under_tree_height_reduction_pct"] = tow_config.under_tree_height_reduction_pct;
  doc["start_reduction_pct"] = tow_config.start_reduction_pct;
  doc["treeheight_to_full_tow_ramp_s"] = tow_config.treeheight_to_full_tow_ramp_s;
  doc["start_to_treeheight_ramp_s"] = tow_config.start_to_treeheight_ramp_s;
  doc["release_before_taking_in_s"] = tow_config.release_before_taking_in_s;
  doc["pid_kp"] = tow_config.pid_kp;
  doc["pid_ki"] = tow_config.pid_ki;
  doc["pid_kd"] = tow_config.pid_kd;
  String out;
  serializeJson(doc, out);
  return out;
}

/* `doc["x"] | tow_config.x` falls back to the CURRENT value (not a
   hardcoded default) for any field missing from the JSON - so a
   partial PATCH body only touches the fields it actually sends. */
static bool apply_tow_config_json(const String &json) {
  JsonDocument doc;
  if (deserializeJson(doc, json) != DeserializationError::Ok) return false;

  const char *mode = doc["operating_mode"] | tow_config.operating_mode;
  strlcpy(tow_config.operating_mode, mode, sizeof(tow_config.operating_mode));
  tow_config.use_saved_calibration = doc["use_saved_calibration"] | tow_config.use_saved_calibration;
  tow_config.cal_raw_zero = doc["cal_raw_zero"] | tow_config.cal_raw_zero;
  tow_config.cal_raw_100kg = doc["cal_raw_100kg"] | tow_config.cal_raw_100kg;
  tow_config.under_tree_height_reduction_pct = doc["under_tree_height_reduction_pct"] | tow_config.under_tree_height_reduction_pct;
  tow_config.start_reduction_pct = doc["start_reduction_pct"] | tow_config.start_reduction_pct;
  tow_config.treeheight_to_full_tow_ramp_s = doc["treeheight_to_full_tow_ramp_s"] | tow_config.treeheight_to_full_tow_ramp_s;
  tow_config.start_to_treeheight_ramp_s = doc["start_to_treeheight_ramp_s"] | tow_config.start_to_treeheight_ramp_s;
  tow_config.release_before_taking_in_s = doc["release_before_taking_in_s"] | tow_config.release_before_taking_in_s;
  tow_config.pid_kp = doc["pid_kp"] | tow_config.pid_kp;
  tow_config.pid_ki = doc["pid_ki"] | tow_config.pid_ki;
  tow_config.pid_kd = doc["pid_kd"] | tow_config.pid_kd;
  return true;
}

static void save_tow_config_to_sd() {
  if (!sd_ready) return;
  SD.remove(TOW_CONFIG_PATH); /* FILE_WRITE appends, not truncates - remove first for a clean overwrite. */
  File f = SD.open(TOW_CONFIG_PATH, FILE_WRITE);
  if (!f) {
    Serial.println("tow_config: failed to open file for writing");
    return;
  }
  f.print(tow_config_to_json());
  f.close();
  Serial.println("tow_config: saved to SD");
}

static void load_tow_config_from_sd() {
  if (!sd_ready || !SD.exists(TOW_CONFIG_PATH)) return;
  File f = SD.open(TOW_CONFIG_PATH, FILE_READ);
  if (!f) return;
  String content = f.readString();
  f.close();
  if (apply_tow_config_json(content)) {
    Serial.println("tow_config: loaded from SD");
  }
}

static void send_http_response(WiFiClient &client, int code, const char *content_type, const String &body) {
  const char *status_text = (code == 200) ? "OK" : (code == 400) ? "Bad Request" : "Not Found";
  client.print("HTTP/1.1 ");
  client.print(code);
  client.print(" ");
  client.println(status_text);
  client.print("Content-Type: ");
  client.println(content_type);
  client.print("Content-Length: ");
  client.println(body.length());
  client.println("Connection: close");
  client.println();
  client.print(body);
}

static String read_http_line(WiFiClient &client) {
  String line = client.readStringUntil('\n');
  line.trim(); /* also drops the trailing \r */
  return line;
}

/* Minimal single-request HTTP/1.1 handling - just enough for the
   MQTT_Layout dashboard's GET/PATCH /api/config + GET /api/ping
   contract (see project memory: giga_wifi_sync). No keep-alive,
   no chunked bodies - every response closes the connection. */
static void handle_http_client(WiFiClient &client) {
  String request_line = read_http_line(client);

  int content_length = 0;
  while (client.connected()) {
    String line = read_http_line(client);
    if (line.length() == 0) break;
    /* Header names are case-insensitive per HTTP/1.1, and Node's
       fetch() (what the dashboard uses) sends "content-length"
       lowercased - a case-sensitive match here silently missed the
       header, read zero bytes of body, and failed to parse. */
    String lower_line = line;
    lower_line.toLowerCase();
    if (lower_line.startsWith("content-length:")) {
      content_length = line.substring(line.indexOf(':') + 1).toInt();
    }
  }

  String body;
  if (content_length > 0) {
    uint32_t start = millis();
    while ((int)body.length() < content_length && millis() - start < 3000) {
      if (client.available()) body += (char)client.read();
    }
  }

  Serial.print("HTTP: ");
  Serial.println(request_line);

  if (request_line.startsWith("GET /api/ping")) {
    send_http_response(client, 200, "text/plain", "OK");
  } else if (request_line.startsWith("GET /api/config")) {
    send_http_response(client, 200, "application/json", tow_config_to_json());
  } else if (request_line.startsWith("PATCH /api/config")) {
    if (apply_tow_config_json(body)) {
      save_tow_config_to_sd();
      send_http_response(client, 200, "application/json", "{\"ok\":true}");
    } else {
      send_http_response(client, 400, "application/json", "{\"error\":\"invalid json\"}");
    }
  } else if (request_line.startsWith("GET /api/tows")) {
    /* No tow-logging implemented yet (see project memory:
       gps_logging) - route exists and responds correctly so the
       dashboard's "From winch" pull completes cleanly (0 tows
       imported) instead of erroring, ahead of real logging existing. */
    send_http_response(client, 200, "application/json", "[]");
  } else {
    send_http_response(client, 404, "text/plain", "Not found");
  }

  client.stop();
}

static void build_splash_screen() {
  splash_screen = lv_obj_create(NULL);
  lv_obj_set_style_bg_color(splash_screen, ARDUINO_TEAL, LV_PART_MAIN);

  /* RGB565A8 already stores the logo's real colour per pixel -
     no runtime recolor needed, just its own alpha channel for
     transparency. Source PNG is kept small (253x210) on purpose -
     a 507x420 version compiled into a 638,820-element array and
     ground the build to a near-halt. Zoomed 2x here instead of
     shipping the bigger source, same on-screen size either way. */
  LV_IMG_DECLARE(splash_logo);
  lv_obj_t *logo = lv_img_create(splash_screen);
  lv_img_set_src(logo, &splash_logo);
  lv_img_set_zoom(logo, 512);
  lv_obj_center(logo);
}

static void clear_content_area() {
  /* Cancel any in-flight connect poll - otherwise it'd keep firing
     and try to update a status label that's about to be deleted. */
  if (wifi_connect_timer) {
    lv_timer_del(wifi_connect_timer);
    wifi_connect_timer = NULL;
  }
  lv_obj_clean(content_area);
  lv_obj_add_flag(keyboard, LV_OBJ_FLAG_HIDDEN);
}

/* Three mutually-exclusive states for the home screen - never
   grey and green showing together. */
static void show_idle() {
  lv_obj_add_flag(content_area, LV_OBJ_FLAG_HIDDEN);
  lv_obj_add_flag(settings_panel, LV_OBJ_FLAG_HIDDEN);
  lv_obj_clear_flag(settings_btn, LV_OBJ_FLAG_HIDDEN);
  lv_obj_clear_flag(start_title, LV_OBJ_FLAG_HIDDEN);
  lv_obj_clear_flag(start_grey_panel, LV_OBJ_FLAG_HIDDEN);
  lv_obj_clear_flag(start_green_panel, LV_OBJ_FLAG_HIDDEN);
}

static void show_nav_menu() {
  lv_obj_add_flag(content_area, LV_OBJ_FLAG_HIDDEN);
  lv_obj_clear_flag(settings_panel, LV_OBJ_FLAG_HIDDEN);
  lv_obj_add_flag(settings_btn, LV_OBJ_FLAG_HIDDEN);
  lv_obj_add_flag(start_title, LV_OBJ_FLAG_HIDDEN);
  lv_obj_add_flag(start_grey_panel, LV_OBJ_FLAG_HIDDEN);
  lv_obj_add_flag(start_green_panel, LV_OBJ_FLAG_HIDDEN);
}

static void show_content_fullscreen() {
  lv_obj_add_flag(settings_panel, LV_OBJ_FLAG_HIDDEN);
  lv_obj_clear_flag(content_area, LV_OBJ_FLAG_HIDDEN);
  lv_obj_add_flag(start_title, LV_OBJ_FLAG_HIDDEN);
  lv_obj_add_flag(start_grey_panel, LV_OBJ_FLAG_HIDDEN);
  lv_obj_add_flag(start_green_panel, LV_OBJ_FLAG_HIDDEN);
}

static void back_btn_event_cb(lv_event_t *e) {
  clear_content_area();
  show_idle();
}

static lv_obj_t *make_back_btn(lv_obj_t *parent) {
  lv_obj_t *btn = lv_btn_create(parent);
  lv_obj_set_size(btn, 100, 50);
  lv_obj_align(btn, LV_ALIGN_BOTTOM_RIGHT, -20, -20);
  lv_obj_add_event_cb(btn, back_btn_event_cb, LV_EVENT_CLICKED, NULL);
  lv_obj_t *label = lv_label_create(btn);
  lv_label_set_text(label, "Back");
  lv_obj_center(label);
  return btn;
}

static void settings_btn_event_cb(lv_event_t *e) {
  show_nav_menu();
}

static void cancel_btn_event_cb(lv_event_t *e) {
  clear_content_area();
  show_idle();
}

static void textarea_event_cb(lv_event_t *e) {
  lv_obj_t *ta = (lv_obj_t *)lv_event_get_target(e);
  lv_event_code_t code = lv_event_get_code(e);
  if (code == LV_EVENT_FOCUSED) {
    lv_keyboard_set_textarea(keyboard, ta);
    lv_obj_clear_flag(keyboard, LV_OBJ_FLAG_HIDDEN);
  } else if (code == LV_EVENT_DEFOCUSED) {
    lv_obj_add_flag(keyboard, LV_OBJ_FLAG_HIDDEN);
  }
}

static void wifi_connect_poll_cb(lv_timer_t *timer) {
  int status = WiFi.status();
  if (status == WL_CONNECTED) {
    lv_label_set_text(wifi_status_label, "Status: Connected");
    lv_timer_del(timer);
    wifi_connect_timer = NULL;
  } else if (status == WL_CONNECT_FAILED || status == WL_CONNECTION_LOST || status == WL_DISCONNECTED) {
    lv_label_set_text(wifi_status_label, "Status: Connection failed");
    lv_timer_del(timer);
    wifi_connect_timer = NULL;
  }
  /* else still in progress (WL_IDLE_STATUS etc.) - keep polling. */
}

/* Runs forever (not deleted) - drives the top-right status dot on the
   homepage and is also what actually starts the HTTP server, so that
   works whether WiFi came up via the boot-time auto-connect below or
   via the manual Network menu. */
static void wifi_status_poll_cb(lv_timer_t *timer) {
  bool connected = (WiFi.status() == WL_CONNECTED);
  lv_obj_set_style_bg_color(wifi_status_dot, connected ? WIFI_DOT_GREEN : WIFI_DOT_RED, LV_PART_MAIN);

  if (connected && !http_server_started) {
    http_server.begin();
    http_server_started = true;
    Serial.print("HTTP server listening on ");
    Serial.println(WiFi.localIP());
  }
}

static void wifi_connect_btn_event_cb(lv_event_t *e) {
  const char *password = lv_textarea_get_text(wifi_password_ta);
  lv_label_set_text(wifi_status_label, "Status: Connecting...");

  WiFi.begin(selected_ssid, password);

  if (wifi_connect_timer) {
    lv_timer_del(wifi_connect_timer);
  }
  wifi_connect_timer = lv_timer_create(wifi_connect_poll_cb, 500, NULL);
}

static void show_wifi_password_step() {
  lv_obj_clean(content_area);
  lv_obj_add_flag(keyboard, LV_OBJ_FLAG_HIDDEN);

  lv_obj_t *title = lv_label_create(content_area);
  lv_label_set_text_fmt(title, "Connect to: %s", selected_ssid);
  lv_obj_set_style_text_font(title, &lv_font_montserrat_48, LV_PART_MAIN);
  lv_obj_align(title, LV_ALIGN_TOP_LEFT, 20, 20);

  wifi_password_ta = lv_textarea_create(content_area);
  lv_textarea_set_one_line(wifi_password_ta, true);
  lv_textarea_set_password_mode(wifi_password_ta, false); /* show what's typed, not masked */
  lv_textarea_set_placeholder_text(wifi_password_ta, "Password");
  lv_obj_set_size(wifi_password_ta, 400, 70);
  lv_obj_align(wifi_password_ta, LV_ALIGN_TOP_LEFT, 20, 70);
  lv_obj_add_event_cb(wifi_password_ta, textarea_event_cb, LV_EVENT_FOCUSED, NULL);
  lv_obj_add_event_cb(wifi_password_ta, textarea_event_cb, LV_EVENT_DEFOCUSED, NULL);

  lv_obj_t *connect_btn = lv_btn_create(content_area);
  lv_obj_set_size(connect_btn, 160, 60);
  lv_obj_align(connect_btn, LV_ALIGN_TOP_LEFT, 20, 155);
  lv_obj_add_event_cb(connect_btn, wifi_connect_btn_event_cb, LV_EVENT_CLICKED, NULL);
  lv_obj_t *connect_label = lv_label_create(connect_btn);
  lv_label_set_text(connect_label, "Connect");
  lv_obj_center(connect_label);

  wifi_status_label = lv_label_create(content_area);
  lv_label_set_text(wifi_status_label, "Status: Not connected");
  lv_obj_align(wifi_status_label, LV_ALIGN_TOP_LEFT, 20, 230);

  /* Created last so it's always on top and clickable - see the
     z-order note on settings_btn in build_home_screen(). */
  make_back_btn(content_area);
}

static void wifi_list_btn_event_cb(lv_event_t *e) {
  int idx = (int)(intptr_t)lv_event_get_user_data(e);
  strncpy(selected_ssid, wifi_ssids[idx], sizeof(selected_ssid) - 1);
  selected_ssid[sizeof(selected_ssid) - 1] = '\0';
  show_wifi_password_step();
}

static void network_btn_event_cb(lv_event_t *e) {
  clear_content_area();
  show_content_fullscreen();

  /* WiFi.scanNetworks() blocks for a couple of seconds - the
     screen just won't respond to touch for that long, no
     "Scanning..." message in between (a nested lv_timer_handler()
     call here to force one would work but risks re-entrancy). */
  int found = WiFi.scanNetworks();
  wifi_network_count = found < MAX_WIFI_NETWORKS ? found : MAX_WIFI_NETWORKS;

  lv_obj_t *list_title = lv_label_create(content_area);
  lv_label_set_text(list_title, "Select a WiFi network");
  lv_obj_set_style_text_font(list_title, &lv_font_montserrat_48, LV_PART_MAIN);
  lv_obj_align(list_title, LV_ALIGN_TOP_LEFT, 20, 10);

  lv_obj_t *list = lv_list_create(content_area);
  lv_obj_set_size(list, 700, 350);
  lv_obj_align(list, LV_ALIGN_TOP_LEFT, 20, 45);

  if (wifi_network_count == 0) {
    lv_list_add_text(list, "No networks found");
  }
  for (int i = 0; i < wifi_network_count; i++) {
    strncpy(wifi_ssids[i], WiFi.SSID(i), sizeof(wifi_ssids[i]) - 1);
    wifi_ssids[i][sizeof(wifi_ssids[i]) - 1] = '\0';
    lv_obj_t *btn = lv_list_add_btn(list, LV_SYMBOL_WIFI, wifi_ssids[i]);
    lv_obj_add_event_cb(btn, wifi_list_btn_event_cb, LV_EVENT_CLICKED, (void *)(intptr_t)i);
  }

  /* Created last so it's always on top and clickable - see the
     z-order note on settings_btn in build_home_screen(). */
  make_back_btn(content_area);
}

/* Tow Settings, editable directly on the touchscreen (not just pushed
   from the dashboard) - split across 3 pages, one green-panel button
   each, so every field fits comfortably at the same big font as the
   rest of the UI (no shrunk-font dense grid). Numeric fields use
   +/- stepper buttons rather than the on-screen keyboard - faster
   for nudging a value, no typing needed. */
enum TowPage { TOW_PAGE_PROFILE, TOW_PAGE_CALIBRATION, TOW_PAGE_PID };
enum TowFieldType { TOW_FIELD_INT, TOW_FIELD_FLOAT };

struct TowSettingField {
  const char  *name;
  TowFieldType type;
  void        *value_ptr;
  float        step;
  TowPage      page;
};

/* `name` here is display text only (shown on the touchscreen) - it
   has no bearing on the JSON keys used for the HTTP API/SD file,
   those stay the original snake_case names hardcoded in
   tow_config_to_json()/apply_tow_config_json(), so renaming these is
   purely cosmetic and doesn't touch the dashboard contract. Capped
   at 4 fields per page on purpose - release_before_taking_in_s moved
   here from Tow Profile to keep Profile at 4 too. */
static TowSettingField tow_setting_fields[] = {
  // Tow Profile
  { "TreeheightReduction",  TOW_FIELD_INT,   &tow_config.under_tree_height_reduction_pct, 1.0f,  TOW_PAGE_PROFILE },
  { "StartReduction",       TOW_FIELD_INT,   &tow_config.start_reduction_pct,              1.0f,  TOW_PAGE_PROFILE },
  { "TreeheightFullRamp",   TOW_FIELD_FLOAT, &tow_config.treeheight_to_full_tow_ramp_s,    0.5f,  TOW_PAGE_PROFILE },
  { "StartTreeheightRamp",  TOW_FIELD_FLOAT, &tow_config.start_to_treeheight_ramp_s,       0.5f,  TOW_PAGE_PROFILE },
  // Calibration (operating_mode/use_saved_calibration are toggles, built separately below)
  { "cal_raw_zero",         TOW_FIELD_INT,   &tow_config.cal_raw_zero,                     10.0f, TOW_PAGE_CALIBRATION },
  { "cal_raw_100kg",        TOW_FIELD_INT,   &tow_config.cal_raw_100kg,                    10.0f, TOW_PAGE_CALIBRATION },
  // PID
  { "pid_kp",         TOW_FIELD_FLOAT, &tow_config.pid_kp, 0.01f, TOW_PAGE_PID },
  { "pid_ki",         TOW_FIELD_FLOAT, &tow_config.pid_ki, 0.01f, TOW_PAGE_PID },
  { "pid_kd",         TOW_FIELD_FLOAT, &tow_config.pid_kd, 0.01f, TOW_PAGE_PID },
  { "TakingInDelay",  TOW_FIELD_FLOAT, &tow_config.release_before_taking_in_s, 0.5f, TOW_PAGE_PID },
};
#define TOW_SETTING_FIELD_COUNT (sizeof(tow_setting_fields) / sizeof(tow_setting_fields[0]))
#define TOW_ROW_HEIGHT 60
#define TOW_NAME_COL_WIDTH 380

static lv_obj_t *tow_field_value_labels[TOW_SETTING_FIELD_COUNT];
static lv_obj_t *tow_mode_value_label;
static lv_obj_t *tow_cal_value_label;

/* Takes an index rather than a TowSettingField reference - Arduino's
   auto-generated function prototypes get hoisted above every type
   definition in the sketch, so any function signature using a custom
   struct/enum type fails to compile ("does not name a type") no
   matter where that type is actually defined in the file. Plain int
   sidesteps it. */
static String format_tow_field_value(int idx) {
  TowSettingField &f = tow_setting_fields[idx];
  if (f.type == TOW_FIELD_INT) return String(*(int *)f.value_ptr);
  return String(*(float *)f.value_ptr, 2);
}

static void refresh_tow_field_label(int idx) {
  lv_label_set_text(tow_field_value_labels[idx], format_tow_field_value(idx).c_str());
}

static void tow_field_step(int idx, int direction) {
  TowSettingField &f = tow_setting_fields[idx];
  if (f.type == TOW_FIELD_INT) {
    int *v = (int *)f.value_ptr;
    *v += (int)f.step * direction;
  } else {
    float *v = (float *)f.value_ptr;
    *v += f.step * direction;
  }
  refresh_tow_field_label(idx);
}

static void tow_field_minus_cb(lv_event_t *e) {
  tow_field_step((int)(intptr_t)lv_event_get_user_data(e), -1);
}

static void tow_field_plus_cb(lv_event_t *e) {
  tow_field_step((int)(intptr_t)lv_event_get_user_data(e), +1);
}

static void tow_mode_toggle_cb(lv_event_t *e) {
  bool is_winchman = strcmp(tow_config.operating_mode, "winchman") == 0;
  strlcpy(tow_config.operating_mode, is_winchman ? "solo" : "winchman", sizeof(tow_config.operating_mode));
  lv_label_set_text(tow_mode_value_label, tow_config.operating_mode);
}

static void tow_cal_toggle_cb(lv_event_t *e) {
  tow_config.use_saved_calibration = !tow_config.use_saved_calibration;
  lv_label_set_text(tow_cal_value_label, tow_config.use_saved_calibration ? "yes" : "no");
}

/* Save + close in one tap - same spot and same "leave the screen"
   behaviour the back button used to have, just also persisting
   tow_config to SD first. No confirmation message - if the SD write
   silently failed the "(SD not detected)" state would already have
   been obvious before you started editing. */
static void tow_save_btn_event_cb(lv_event_t *e) {
  save_tow_config_to_sd();
  show_idle();
}

/* Name label sits in a fixed-width column immediately left of the
   -/value/+ controls (one row, not stacked) - keeps every row the
   same height regardless of how long the field name is. Long names
   get an ellipsis rather than wrapping or pushing the controls over. */
static void build_tow_stepper_row(lv_obj_t *parent, int y, int field_idx) {
  TowSettingField &f = tow_setting_fields[field_idx];

  lv_obj_t *name_label = lv_label_create(parent);
  lv_label_set_text(name_label, f.name);
  lv_label_set_long_mode(name_label, LV_LABEL_LONG_DOT);
  lv_obj_set_width(name_label, TOW_NAME_COL_WIDTH);
  lv_obj_align(name_label, LV_ALIGN_TOP_LEFT, 0, y + 13);

  lv_obj_t *minus_btn = lv_btn_create(parent);
  lv_obj_set_size(minus_btn, 60, 50);
  lv_obj_align(minus_btn, LV_ALIGN_TOP_LEFT, TOW_NAME_COL_WIDTH + 10, y);
  lv_obj_add_event_cb(minus_btn, tow_field_minus_cb, LV_EVENT_CLICKED, (void *)(intptr_t)field_idx);
  lv_obj_t *minus_label = lv_label_create(minus_btn);
  lv_label_set_text(minus_label, "-");
  lv_obj_center(minus_label);

  lv_obj_t *value_label = lv_label_create(parent);
  lv_obj_align(value_label, LV_ALIGN_TOP_LEFT, TOW_NAME_COL_WIDTH + 80, y + 13);
  tow_field_value_labels[field_idx] = value_label;
  refresh_tow_field_label(field_idx);

  lv_obj_t *plus_btn = lv_btn_create(parent);
  lv_obj_set_size(plus_btn, 60, 50);
  lv_obj_align(plus_btn, LV_ALIGN_TOP_LEFT, TOW_NAME_COL_WIDTH + 150, y);
  lv_obj_add_event_cb(plus_btn, tow_field_plus_cb, LV_EVENT_CLICKED, (void *)(intptr_t)field_idx);
  lv_obj_t *plus_label = lv_label_create(plus_btn);
  lv_label_set_text(plus_label, "+");
  lv_obj_center(plus_label);
}

static void build_tow_toggle_row(lv_obj_t *parent, int y, const char *name, const char *initial_value,
                                  lv_obj_t **value_label_out, lv_event_cb_t cb) {
  lv_obj_t *name_label = lv_label_create(parent);
  lv_label_set_text(name_label, name);
  lv_label_set_long_mode(name_label, LV_LABEL_LONG_DOT);
  lv_obj_set_width(name_label, TOW_NAME_COL_WIDTH);
  lv_obj_align(name_label, LV_ALIGN_TOP_LEFT, 0, y + 13);

  lv_obj_t *btn = lv_btn_create(parent);
  lv_obj_set_size(btn, 220, 50);
  lv_obj_align(btn, LV_ALIGN_TOP_LEFT, TOW_NAME_COL_WIDTH + 10, y);
  lv_obj_add_event_cb(btn, cb, LV_EVENT_CLICKED, NULL);

  lv_obj_t *label = lv_label_create(btn);
  lv_label_set_text(label, initial_value);
  lv_obj_center(label);

  *value_label_out = label;
}

/* Shared by all 3 Tow Settings pages - only the field set (filtered
   by `page`) and title differ. `fields` deliberately stays scrollable
   (unlike the old read-only rows box) since the Tow Profile page's 5
   fields don't all fit in the visible height at this font size -
   swipe to reach the rest rather than shrinking the text. */
/* `page` is declared plain int, not TowPage, for the same reason
   format_tow_field_value() takes an index - see the comment there. */
static void build_tow_settings_page(int page, const char *title) {
  clear_content_area();
  show_content_fullscreen();

  lv_obj_t *title_label = lv_label_create(content_area);
  lv_label_set_text(title_label, title);
  lv_obj_set_style_text_font(title_label, &lv_font_montserrat_48, LV_PART_MAIN);
  lv_obj_align(title_label, LV_ALIGN_TOP_LEFT, 20, 15);

  lv_obj_t *fields = lv_obj_create(content_area);
  lv_obj_set_size(fields, 720, 260);
  lv_obj_align(fields, LV_ALIGN_TOP_LEFT, 20, 55);
  lv_obj_set_style_bg_opa(fields, LV_OPA_TRANSP, LV_PART_MAIN);
  lv_obj_set_style_border_width(fields, 0, LV_PART_MAIN);
  lv_obj_set_style_shadow_width(fields, 0, LV_PART_MAIN);
  lv_obj_set_style_outline_width(fields, 0, LV_PART_MAIN);
  /* Every page is capped at 4 fields now (240px of rows, fits well
     inside this box), so scrolling is never needed - the scrollbar
     was showing as a stray grey line along the bottom/edge. */
  lv_obj_clear_flag(fields, LV_OBJ_FLAG_SCROLLABLE);
  lv_obj_set_scrollbar_mode(fields, LV_SCROLLBAR_MODE_OFF);

  int y = 0;
  if (page == TOW_PAGE_CALIBRATION) {
    build_tow_toggle_row(fields, y, "operating_mode", tow_config.operating_mode, &tow_mode_value_label, tow_mode_toggle_cb);
    y += TOW_ROW_HEIGHT;
    build_tow_toggle_row(fields, y, "use_saved_calibration", tow_config.use_saved_calibration ? "yes" : "no",
                          &tow_cal_value_label, tow_cal_toggle_cb);
    y += TOW_ROW_HEIGHT;
  }
  for (size_t i = 0; i < TOW_SETTING_FIELD_COUNT; i++) {
    if (tow_setting_fields[i].page != page) continue;
    build_tow_stepper_row(fields, y, i);
    y += TOW_ROW_HEIGHT;
  }

  /* Where the back button used to be - Save now does both jobs
     (persist to SD, then leave the screen) instead of needing a
     separate back button alongside it. */
  lv_obj_t *save_btn = lv_btn_create(content_area);
  lv_obj_set_size(save_btn, 100, 50);
  lv_obj_align(save_btn, LV_ALIGN_BOTTOM_RIGHT, -20, -20);
  lv_obj_add_event_cb(save_btn, tow_save_btn_event_cb, LV_EVENT_CLICKED, NULL);
  lv_obj_t *save_label = lv_label_create(save_btn);
  lv_label_set_text(save_label, "Save");
  lv_obj_center(save_label);
}

static void tow_profile_btn_event_cb(lv_event_t *e) { build_tow_settings_page(TOW_PAGE_PROFILE, "Tow Profile"); }
static void tow_calibration_btn_event_cb(lv_event_t *e) { build_tow_settings_page(TOW_PAGE_CALIBRATION, "Calibration"); }
static void tow_pid_btn_event_cb(lv_event_t *e) { build_tow_settings_page(TOW_PAGE_PID, "PID"); }

static lv_obj_t *make_settings_menu_btn(lv_obj_t *parent, const char *text, lv_event_cb_t cb) {
  lv_obj_t *btn = lv_btn_create(parent);
  lv_obj_set_size(btn, 170, 60);
  lv_obj_add_event_cb(btn, cb, LV_EVENT_CLICKED, NULL);

  lv_obj_t *label = lv_label_create(btn);
  lv_label_set_text(label, text);
  lv_obj_center(label);
  return btn;
}

/* Mode select (Solo-tow / Winchman) and pilot info (Name/Weight) - the
   very first screens after splash, before "Start". Solo-tow: pilot info
   is asked once here and persists for every tow after this (see
   docs/software.md "Boot Configuration" - operating_mode "solo" skips
   the ESP32's per-tow pilot reset). Winchman: same screen, but the
   ESP32 forgets pilot_name/pilot_weight_kg again after every
   release/fault in this mode, so re-entry before the next tow is
   already enforced there (refuses "calibrate" until resent) - this UI
   doesn't need its own separate lock for that. */
/* Whole-kg steps only, so %d avoids LVGL's lightweight snprintf
   (LV_SPRINTF_USE_FLOAT off by default) silently printing a literal
   "f" instead of the value for any %f-style spec. */
static void refresh_pilot_weight_label() {
  lv_label_set_text_fmt(pilot_weight_value_label, "%d kg", (int)pilot_weight_kg);
}

static void pilot_weight_minus_cb(lv_event_t *e) {
  pilot_weight_kg -= 1;
  if (pilot_weight_kg < 20) pilot_weight_kg = 20;
  refresh_pilot_weight_label();
}

static void pilot_weight_plus_cb(lv_event_t *e) {
  pilot_weight_kg += 1;
  if (pilot_weight_kg > 150) pilot_weight_kg = 150;
  refresh_pilot_weight_label();
}

static void pilot_info_textarea_event_cb(lv_event_t *e) {
  lv_event_code_t code = lv_event_get_code(e);
  if (code == LV_EVENT_FOCUSED) {
    lv_obj_clear_flag(pilot_info_keyboard, LV_OBJ_FLAG_HIDDEN);
  } else if (code == LV_EVENT_DEFOCUSED) {
    lv_obj_add_flag(pilot_info_keyboard, LV_OBJ_FLAG_HIDDEN);
  }
}

static void show_pilot_info_screen() {
  lv_textarea_set_text(pilot_name_ta, "");
  pilot_weight_kg = 80.0f;
  refresh_pilot_weight_label();
  /* Keyboard shown by default - Name is the first thing to fill in on
     this screen, no need to tap the textarea first to bring it up. */
  lv_obj_clear_flag(pilot_info_keyboard, LV_OBJ_FLAG_HIDDEN);
  lv_scr_load(pilot_info_screen);
}

/* Solo-tow/Winchman choice takes effect (and is saved to SD) right
   away, so it survives a reboot even if the pilot-info step below
   never completes - the tow-config tunables/calibration go to the
   ESP32 in the same message. pilot_name/pilot_weight_kg follow once
   the pilot-info OK button is tapped. */
static void mode_select_solo_btn_event_cb(lv_event_t *e) {
  strlcpy(tow_config.operating_mode, "solo", sizeof(tow_config.operating_mode));
  save_tow_config_to_sd();
  send_boot_tow_config_to_esp32();
  show_pilot_info_screen();
}

static void mode_select_winchman_btn_event_cb(lv_event_t *e) {
  strlcpy(tow_config.operating_mode, "winchman", sizeof(tow_config.operating_mode));
  save_tow_config_to_sd();
  send_boot_tow_config_to_esp32();
  show_pilot_info_screen();
}

static void pilot_info_ok_btn_event_cb(lv_event_t *e) {
  const char *name = lv_textarea_get_text(pilot_name_ta);
  strncpy(pilot_name, name, sizeof(pilot_name) - 1);
  pilot_name[sizeof(pilot_name) - 1] = '\0';
  send_pilot_info_to_esp32();
  lv_label_set_text_fmt(start_pilot_label, "Pilot %s %d kg", pilot_name, (int)pilot_weight_kg);
  lv_scr_load(home_screen);
  show_idle();
}

/* Calibrate flow - two on-screen steps (0kg tare, then 100kg reference
   pull) matching the ESP32's own two-point sequence exactly
   (requestStateTransition() in esp32_mainboard.ino): "calibrate" makes
   it capture the tare reading right then (IDLE->CALIBRATING), and
   "calibration_done" captures the second point and computes the
   calibration factor (CALIBRATING->READY). So each step's Set button
   is what actually saves that point's load-cell reading, by sending
   the matching state_cmd at that exact tap - not when the flow starts. */
enum class CalibrateStep { NONE, ZERO, HUNDRED };
static CalibrateStep g_calibrate_step = CalibrateStep::NONE;

static void show_start_idle_buttons() {
  g_calibrate_step = CalibrateStep::NONE;
  lv_label_set_text(start_title, "Start");
  lv_obj_add_flag(calibrate_value_label, LV_OBJ_FLAG_HIDDEN);
  lv_obj_add_flag(calibrate_set_btn, LV_OBJ_FLAG_HIDDEN);
  lv_obj_add_flag(calibrate_cancel_btn, LV_OBJ_FLAG_HIDDEN);
  lv_obj_clear_flag(start_calibrate_btn, LV_OBJ_FLAG_HIDDEN);
  lv_obj_clear_flag(start_tow_btn, LV_OBJ_FLAG_HIDDEN);
}

static void show_calibrate_zero_step() {
  g_calibrate_step = CalibrateStep::ZERO;
  lv_label_set_text(start_title, "Calibrate");
  lv_obj_add_flag(start_calibrate_btn, LV_OBJ_FLAG_HIDDEN);
  lv_obj_add_flag(start_tow_btn, LV_OBJ_FLAG_HIDDEN);
  lv_label_set_text(calibrate_value_label, "0 kg on the line");
  lv_obj_clear_flag(calibrate_value_label, LV_OBJ_FLAG_HIDDEN);
  lv_obj_clear_flag(calibrate_set_btn, LV_OBJ_FLAG_HIDDEN);
  lv_obj_clear_flag(calibrate_cancel_btn, LV_OBJ_FLAG_HIDDEN);
}

static void show_calibrate_hundred_step() {
  g_calibrate_step = CalibrateStep::HUNDRED;
  lv_label_set_text(calibrate_value_label, "100 kg on the line");
}

static void start_calibrate_btn_event_cb(lv_event_t *e) {
  show_calibrate_zero_step();
}

static void start_tow_btn_event_cb(lv_event_t *e) {
  JsonDocument doc;
  doc["state_cmd"] = "start_tow";
  send_cmd_to_esp32(doc);
}

static void calibrate_set_btn_event_cb(lv_event_t *e) {
  JsonDocument doc;
  if (g_calibrate_step == CalibrateStep::ZERO) {
    doc["state_cmd"] = "calibrate";
    send_cmd_to_esp32(doc);
    show_calibrate_hundred_step();
  } else if (g_calibrate_step == CalibrateStep::HUNDRED) {
    doc["state_cmd"] = "calibration_done";
    send_cmd_to_esp32(doc);

    /* Field recalibration: the winchman nudges the reading with the
       +5kg/-5kg buttons to match an external reference scale's true
       100kg before confirming here - any gap from the nominal 100kg
       target means the previously stored cal_raw_100kg was off by
       that same percentage (e.g. settling on 104 = 4% over nominal
       scales the stored raw count up 4% too). 100.0f is the fixed
       real-world calibration reference weight, not the ESP32 sim's
       own ramp target - correct even if that ramp constant changes. */
    float nudge_pct = (g_last_tension_kg - 100.0f) / 100.0f;
    tow_config.cal_raw_100kg = (int)(tow_config.cal_raw_100kg * (1.0f + nudge_pct) + 0.5f);
    save_tow_config_to_sd();

    show_start_idle_buttons();
  }
}

static void calibrate_cancel_btn_event_cb(lv_event_t *e) {
  /* Only the HUNDRED step means the ESP32 is actually sitting in
     CALIBRATING (the ZERO step's Set is what sends "calibrate" in the
     first place) - bring it back to IDLE rather than leaving it
     stuck there. */
  if (g_calibrate_step == CalibrateStep::HUNDRED) {
    JsonDocument doc;
    doc["state_cmd"] = "idle";
    send_cmd_to_esp32(doc);
  }
  show_start_idle_buttons();
}

static void build_mode_select_screen() {
  mode_select_screen = lv_obj_create(NULL);
  lv_obj_set_style_bg_color(mode_select_screen, lv_color_white(), LV_PART_MAIN);
  lv_obj_set_style_text_font(mode_select_screen, &lv_font_montserrat_24, LV_PART_MAIN);

  lv_obj_t *title = lv_label_create(mode_select_screen);
  lv_label_set_text(title, "Select mode");
  lv_obj_set_style_text_font(title, &lv_font_montserrat_48, LV_PART_MAIN);
  lv_obj_align(title, LV_ALIGN_TOP_MID, 0, 30);

  lv_obj_t *solo_btn = lv_btn_create(mode_select_screen);
  lv_obj_set_size(solo_btn, 320, 150);
  lv_obj_align(solo_btn, LV_ALIGN_LEFT_MID, 40, 20);
  lv_obj_add_event_cb(solo_btn, mode_select_solo_btn_event_cb, LV_EVENT_CLICKED, NULL);
  lv_obj_t *solo_label = lv_label_create(solo_btn);
  lv_label_set_text(solo_label, "Solo-tow");
  lv_obj_center(solo_label);

  lv_obj_t *winchman_btn = lv_btn_create(mode_select_screen);
  lv_obj_set_size(winchman_btn, 320, 150);
  lv_obj_align(winchman_btn, LV_ALIGN_RIGHT_MID, -40, 20);
  lv_obj_add_event_cb(winchman_btn, mode_select_winchman_btn_event_cb, LV_EVENT_CLICKED, NULL);
  lv_obj_t *winchman_label = lv_label_create(winchman_btn);
  lv_label_set_text(winchman_label, "Winchman");
  lv_obj_center(winchman_label);
}

static void build_pilot_info_screen() {
  pilot_info_screen = lv_obj_create(NULL);
  lv_obj_set_style_bg_color(pilot_info_screen, lv_color_white(), LV_PART_MAIN);
  lv_obj_set_style_text_font(pilot_info_screen, &lv_font_montserrat_24, LV_PART_MAIN);

  lv_obj_t *title = lv_label_create(pilot_info_screen);
  lv_label_set_text(title, "Pilot info");
  lv_obj_set_style_text_font(title, &lv_font_montserrat_48, LV_PART_MAIN);
  lv_obj_align(title, LV_ALIGN_TOP_LEFT, 20, 15);

  lv_obj_t *name_label = lv_label_create(pilot_info_screen);
  lv_label_set_text(name_label, "Name");
  lv_obj_align(name_label, LV_ALIGN_TOP_LEFT, 20, 75);

  pilot_name_ta = lv_textarea_create(pilot_info_screen);
  lv_textarea_set_one_line(pilot_name_ta, true);
  lv_textarea_set_placeholder_text(pilot_name_ta, "Pilot name");
  lv_obj_set_size(pilot_name_ta, 400, 70);
  lv_obj_align(pilot_name_ta, LV_ALIGN_TOP_LEFT, 160, 60);
  lv_obj_add_event_cb(pilot_name_ta, pilot_info_textarea_event_cb, LV_EVENT_FOCUSED, NULL);
  lv_obj_add_event_cb(pilot_name_ta, pilot_info_textarea_event_cb, LV_EVENT_DEFOCUSED, NULL);

  lv_obj_t *weight_label = lv_label_create(pilot_info_screen);
  lv_label_set_text(weight_label, "Weight");
  lv_obj_align(weight_label, LV_ALIGN_TOP_LEFT, 20, 165);

  lv_obj_t *minus_btn = lv_btn_create(pilot_info_screen);
  lv_obj_set_size(minus_btn, 60, 50);
  lv_obj_align(minus_btn, LV_ALIGN_TOP_LEFT, 160, 150);
  lv_obj_add_event_cb(minus_btn, pilot_weight_minus_cb, LV_EVENT_CLICKED, NULL);
  lv_obj_t *minus_label = lv_label_create(minus_btn);
  lv_label_set_text(minus_label, "-");
  lv_obj_center(minus_label);

  pilot_weight_value_label = lv_label_create(pilot_info_screen);
  lv_obj_align(pilot_weight_value_label, LV_ALIGN_TOP_LEFT, 230, 163);
  refresh_pilot_weight_label();

  lv_obj_t *plus_btn = lv_btn_create(pilot_info_screen);
  lv_obj_set_size(plus_btn, 60, 50);
  lv_obj_align(plus_btn, LV_ALIGN_TOP_LEFT, 320, 150);
  lv_obj_add_event_cb(plus_btn, pilot_weight_plus_cb, LV_EVENT_CLICKED, NULL);
  lv_obj_t *plus_label = lv_label_create(plus_btn);
  lv_label_set_text(plus_label, "+");
  lv_obj_center(plus_label);

  pilot_info_keyboard = lv_keyboard_create(pilot_info_screen);
  lv_obj_set_size(pilot_info_keyboard, 800, 200);
  lv_obj_align(pilot_info_keyboard, LV_ALIGN_BOTTOM_MID, 0, 0);
  lv_obj_set_style_text_font(pilot_info_keyboard, &lv_font_montserrat_24, LV_PART_ITEMS);
  lv_obj_add_flag(pilot_info_keyboard, LV_OBJ_FLAG_HIDDEN);
  lv_keyboard_set_textarea(pilot_info_keyboard, pilot_name_ta);

  lv_obj_t *ok_btn = lv_btn_create(pilot_info_screen);
  lv_obj_set_size(ok_btn, 100, 50);
  lv_obj_align(ok_btn, LV_ALIGN_BOTTOM_RIGHT, -20, -20);
  lv_obj_add_event_cb(ok_btn, pilot_info_ok_btn_event_cb, LV_EVENT_CLICKED, NULL);
  lv_obj_t *ok_label = lv_label_create(ok_btn);
  lv_label_set_text(ok_label, "OK");
  lv_obj_center(ok_label);
}

static void build_home_screen() {
  /* Placeholder - replace with the real winch/tow UI once it's designed. */
  home_screen = lv_obj_create(NULL);
  lv_obj_set_style_bg_color(home_screen, lv_color_white(), LV_PART_MAIN);
  /* text_font is an inheritable style property - setting it once
     here cascades to every label/button/list item/textarea in
     the tree below, so nothing else needs it set individually. */
  lv_obj_set_style_text_font(home_screen, &lv_font_montserrat_24, LV_PART_MAIN);

  /* Grey content area - holds whatever the current settings nav
     selection puts there (WiFi fields, tow settings, ...). Hidden
     until Network/Tow Settings is tapped - never shown at the
     same time as the green nav panel. Fullscreen (minus the same
     20px white border used elsewhere), since it's never shown
     docked beside the green panel any more. */
  content_area = lv_obj_create(home_screen);
  lv_obj_set_style_bg_color(content_area, LIGHT_GREY, LV_PART_MAIN);
  lv_obj_set_size(content_area, 760, 440);
  lv_obj_align(content_area, LV_ALIGN_CENTER, 0, 0);
  lv_obj_add_flag(content_area, LV_OBJ_FLAG_HIDDEN);

  /* On-screen keyboard for the text fields above - hidden until a
     textarea is focused. Sized explicitly (not left to the
     default) so it can't end up partly hidden behind another
     panel. */
  keyboard = lv_keyboard_create(home_screen);
  lv_obj_set_size(keyboard, 800, 200);
  lv_obj_align(keyboard, LV_ALIGN_BOTTOM_MID, 0, 0);
  lv_obj_set_style_text_font(keyboard, &lv_font_montserrat_24, LV_PART_ITEMS);
  lv_obj_add_flag(keyboard, LV_OBJ_FLAG_HIDDEN);

  /* Settings nav panel - hidden until the gear button is tapped.
     Network/Tow Settings pinned to the top, Cancel to the bottom.
     Same 20px margin from the screen edge and from content_area
     as content_area itself uses. */
  settings_panel = lv_obj_create(home_screen);
  lv_obj_set_size(settings_panel, 200, 440);
  lv_obj_align(settings_panel, LV_ALIGN_RIGHT_MID, -20, 0);
  lv_obj_set_style_bg_color(settings_panel, LIGHT_GREEN, LV_PART_MAIN);
  lv_obj_add_flag(settings_panel, LV_OBJ_FLAG_HIDDEN);

  lv_obj_t *network_btn = make_settings_menu_btn(settings_panel, "Network", network_btn_event_cb);
  lv_obj_align(network_btn, LV_ALIGN_TOP_MID, 0, 20);

  lv_obj_t *tow_profile_btn = make_settings_menu_btn(settings_panel, "Tow Profile", tow_profile_btn_event_cb);
  lv_obj_align(tow_profile_btn, LV_ALIGN_TOP_MID, 0, 90);

  lv_obj_t *calibration_btn = make_settings_menu_btn(settings_panel, "Calibration", tow_calibration_btn_event_cb);
  lv_obj_align(calibration_btn, LV_ALIGN_TOP_MID, 0, 160);

  lv_obj_t *pid_btn = make_settings_menu_btn(settings_panel, "PID", tow_pid_btn_event_cb);
  lv_obj_align(pid_btn, LV_ALIGN_TOP_MID, 0, 230);

  lv_obj_t *cancel_btn = make_settings_menu_btn(settings_panel, "Cancel", cancel_btn_event_cb);
  lv_obj_set_size(cancel_btn, 140, 50);
  lv_obj_align(cancel_btn, LV_ALIGN_BOTTOM_MID, 0, -20);

  /* "Start" idle-state layout - grey (left) + green (right) placeholder
     panels, same colours as content_area/settings_panel above but
     separate objects, always docked together whenever content_area/
     settings_panel are both hidden (show_idle()). No tow-operation
     controls in them yet - just establishing the layout. */
  start_title = lv_label_create(home_screen);
  lv_label_set_text(start_title, "Start");
  lv_obj_set_style_text_font(start_title, &lv_font_montserrat_48, LV_PART_MAIN);
  lv_obj_align(start_title, LV_ALIGN_TOP_MID, 0, 15);

  start_grey_panel = lv_obj_create(home_screen);
  lv_obj_set_style_bg_color(start_grey_panel, LIGHT_GREY, LV_PART_MAIN);
  lv_obj_set_size(start_grey_panel, 540, 380);
  lv_obj_align(start_grey_panel, LV_ALIGN_TOP_LEFT, 20, 70);

  /* Pilot info recap, top-left of the grey panel - set once the
     pilot-info OK button is tapped (see pilot_info_ok_btn_event_cb). */
  start_pilot_label = lv_label_create(start_grey_panel);
  lv_obj_align(start_pilot_label, LV_ALIGN_TOP_LEFT, 15, 15);

  /* Calibrate/Start, bottom of the grey panel - side by side, same
     15px margin the pilot label uses, ~110px gap between them (540
     panel width - 2*15 margin - 2*200 button width = 110). Hidden for
     the duration of the calibrate flow (show_calibrate_zero_step()),
     restored by show_start_idle_buttons(). */
  start_calibrate_btn = lv_btn_create(start_grey_panel);
  lv_obj_set_size(start_calibrate_btn, 200, 60);
  lv_obj_align(start_calibrate_btn, LV_ALIGN_BOTTOM_LEFT, 15, -15);
  lv_obj_add_event_cb(start_calibrate_btn, start_calibrate_btn_event_cb, LV_EVENT_CLICKED, NULL);
  lv_obj_t *calibrate_label = lv_label_create(start_calibrate_btn);
  lv_label_set_text(calibrate_label, "Calibrate");
  lv_obj_center(calibrate_label);

  start_tow_btn = lv_btn_create(start_grey_panel);
  lv_obj_set_size(start_tow_btn, 200, 60);
  lv_obj_align(start_tow_btn, LV_ALIGN_BOTTOM_RIGHT, -15, -15);
  lv_obj_add_event_cb(start_tow_btn, start_tow_btn_event_cb, LV_EVENT_CLICKED, NULL);
  lv_obj_t *start_tow_label = lv_label_create(start_tow_btn);
  lv_label_set_text(start_tow_label, "Start");
  lv_obj_center(start_tow_label);

  /* Calibrate flow widgets - same grey panel, hidden until
     show_calibrate_zero_step() reveals them (see start_calibrate_btn's
     callback) and hidden again by show_start_idle_buttons(). Uses a real
     &lv_font_montserrat_48 rather than a transform_zoom on montserrat_24 -
     zoomed/scaled label text was a suspected crash cause (LVGL re-renders
     a scaled glyph bitmap on every text change, repeatedly across this
     screen's "0 kg"/"100 kg" transitions) - see project memory. Requires
     LV_FONT_MONTSERRAT_48 enabled in this board core's lv_conf.h (same
     buried, core-update-fragile file already edited once before for
     montserrat_24). */
  calibrate_value_label = lv_label_create(start_grey_panel);
  lv_obj_set_style_text_align(calibrate_value_label, LV_TEXT_ALIGN_CENTER, LV_PART_MAIN);
  lv_obj_set_style_text_font(calibrate_value_label, &lv_font_montserrat_48, LV_PART_MAIN);
  /* Truly centered horizontally in the grey panel (x=0) - same position
     for both "0 kg on the line" and "100 kg on the line" since it's one
     label with its text swapped between steps. */
  lv_obj_align(calibrate_value_label, LV_ALIGN_CENTER, 0, -20);
  lv_obj_add_flag(calibrate_value_label, LV_OBJ_FLAG_HIDDEN);

  calibrate_set_btn = lv_btn_create(start_grey_panel);
  lv_obj_set_size(calibrate_set_btn, 200, 60);
  lv_obj_align(calibrate_set_btn, LV_ALIGN_BOTTOM_LEFT, 15, -15);
  lv_obj_add_event_cb(calibrate_set_btn, calibrate_set_btn_event_cb, LV_EVENT_CLICKED, NULL);
  lv_obj_t *calibrate_set_label = lv_label_create(calibrate_set_btn);
  lv_label_set_text(calibrate_set_label, "Set");
  lv_obj_center(calibrate_set_label);
  lv_obj_add_flag(calibrate_set_btn, LV_OBJ_FLAG_HIDDEN);

  calibrate_cancel_btn = lv_btn_create(start_grey_panel);
  lv_obj_set_size(calibrate_cancel_btn, 200, 60);
  lv_obj_align(calibrate_cancel_btn, LV_ALIGN_BOTTOM_RIGHT, -15, -15);
  lv_obj_add_event_cb(calibrate_cancel_btn, calibrate_cancel_btn_event_cb, LV_EVENT_CLICKED, NULL);
  lv_obj_t *calibrate_cancel_label = lv_label_create(calibrate_cancel_btn);
  lv_label_set_text(calibrate_cancel_label, "Cancel");
  lv_obj_center(calibrate_cancel_label);
  lv_obj_add_flag(calibrate_cancel_btn, LV_OBJ_FLAG_HIDDEN);

  start_green_panel = lv_obj_create(home_screen);
  lv_obj_set_style_bg_color(start_green_panel, LIGHT_GREEN, LV_PART_MAIN);
  lv_obj_set_size(start_green_panel, 200, 380);
  lv_obj_align(start_green_panel, LV_ALIGN_TOP_RIGHT, -20, 70);

  /* Tension gauge, top of the green panel - lv_arc rather than the
     lv_meter/lv_scale "real gauge" widgets used in Arduino's own LVGL
     examples, since this machine has no Arduino IDE/LVGL source to
     confirm which of those exists in the exact bundled LVGL version
     (v9 removed lv_meter). lv_arc is stable across LVGL versions and
     gives the same "ring showing a live value" gauge look. Read-only -
     clickable/knob interaction removed since this only ever displays
     telemetry, never accepts input. Range 0-150kg, comfortably above
     the ~100kg tow-force target this project designs around. */
  tension_gauge_arc = lv_arc_create(start_green_panel);
  lv_obj_set_size(tension_gauge_arc, 160, 160);
  lv_obj_align(tension_gauge_arc, LV_ALIGN_TOP_MID, 0, 15);
  lv_arc_set_range(tension_gauge_arc, 0, 150);
  lv_arc_set_value(tension_gauge_arc, 0);
  lv_obj_remove_style(tension_gauge_arc, NULL, LV_PART_KNOB);
  lv_obj_clear_flag(tension_gauge_arc, LV_OBJ_FLAG_CLICKABLE);

  /* Value only (unit is its own label below) - real &lv_font_montserrat_48
     rather than a transform_zoom on montserrat_24 (zoomed/scaled text was
     a suspected crash cause - see calibrate_value_label's own comment).
     True bold still isn't available without a separately-converted bold
     font asset, which this project doesn't have yet. */
  tension_gauge_label = lv_label_create(tension_gauge_arc);
  lv_label_set_text(tension_gauge_label, "0");
  lv_obj_set_style_text_font(tension_gauge_label, &lv_font_montserrat_48, LV_PART_MAIN);
  lv_obj_align(tension_gauge_label, LV_ALIGN_CENTER, 0, -8);

  tension_gauge_unit_label = lv_label_create(tension_gauge_arc);
  lv_label_set_text(tension_gauge_unit_label, "kg");
  lv_obj_align(tension_gauge_unit_label, LV_ALIGN_BOTTOM_MID, -5, -17);

  /* Line paid-out distance, bottom of the green panel - telemetry's
     rope_out_m (ESP32-side, currently a fixed test placeholder until
     the real hall-sensor pulse counting exists - see project memory:
     giga_display_firmware). Real &lv_font_montserrat_48, not a
     transform_zoom - same crash-avoidance reasoning as the other two
     labels above. */
  rope_out_label = lv_label_create(start_green_panel);
  lv_label_set_text(rope_out_label, "0 m");
  lv_obj_set_style_text_font(rope_out_label, &lv_font_montserrat_48, LV_PART_MAIN);
  lv_obj_align(rope_out_label, LV_ALIGN_BOTTOM_MID, -5, -5);

  /* Gear button created last so it's always on top, regardless of
     what content_area/settings_panel are doing underneath it -
     previously it could end up mostly covered, leaving only a few
     clickable pixels. */
  settings_btn = lv_btn_create(home_screen);
  lv_obj_set_size(settings_btn, 60, 60);
  lv_obj_align(settings_btn, LV_ALIGN_TOP_LEFT, 10, 5);
  lv_obj_add_event_cb(settings_btn, settings_btn_event_cb, LV_EVENT_CLICKED, NULL);
  /* Transparent, borderless - just an invisible tap target behind the
     grey gear icon below, not a visible blue button. */
  lv_obj_set_style_bg_opa(settings_btn, LV_OPA_TRANSP, LV_PART_MAIN);
  lv_obj_set_style_border_width(settings_btn, 0, LV_PART_MAIN);
  lv_obj_set_style_shadow_width(settings_btn, 0, LV_PART_MAIN);
  lv_obj_set_style_outline_width(settings_btn, 0, LV_PART_MAIN);

  lv_obj_t *gear_label = lv_label_create(settings_btn);
  lv_label_set_text(gear_label, LV_SYMBOL_SETTINGS);
  lv_obj_set_style_text_color(gear_label, lv_color_hex(0x808080), LV_PART_MAIN);
  lv_obj_set_style_transform_zoom(gear_label, 320, LV_PART_MAIN); /* ~1.25x, "a little bigger" */
  lv_obj_center(gear_label);

  /* WiFi status dot, top-right corner. Lives directly on home_screen
     (not content_area/settings_panel) in the one 20x20 corner both of
     those leave free in every state, so it's always visible and never
     overlapped or click-blocking. Colour is driven by wifi_status_poll_cb. */
  wifi_status_dot = lv_obj_create(home_screen);
  lv_obj_set_size(wifi_status_dot, 14, 14);
  lv_obj_set_style_radius(wifi_status_dot, LV_RADIUS_CIRCLE, LV_PART_MAIN);
  lv_obj_set_style_border_width(wifi_status_dot, 0, LV_PART_MAIN);
  lv_obj_set_style_bg_color(wifi_status_dot, WIFI_DOT_RED, LV_PART_MAIN);
  lv_obj_clear_flag(wifi_status_dot, LV_OBJ_FLAG_CLICKABLE);
  lv_obj_clear_flag(wifi_status_dot, LV_OBJ_FLAG_SCROLLABLE);
  lv_obj_align(wifi_status_dot, LV_ALIGN_TOP_RIGHT, -6, 6);
}

static void splash_timeout_cb(lv_timer_t *timer) {
  lv_scr_load(mode_select_screen);
  lv_timer_del(timer);
}

void setup() {
  Serial.begin(115200);

  /* Called before Display.begin() below (not after) so that error()'s
     blink is actually visible even if display init itself fails. */
  shield_rgb.begin();
  set_status_led_rgb(0, 0, 0);  // off until the first telemetry line arrives

  Serial1.begin(115200);  // ESP32 mainboard link - GIGA D0/D1, see the comment above WINCH_STATE_COLORS

  if (strlen(WIFI_SSID) > 0) {
    Serial.println("Auto-connecting to WiFi...");
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  } else {
    Serial.println("No WiFi credentials in secrets.h - skipping auto-connect");
  }

  /* Explicit slow clock (400kHz) rather than the library's default -
     breadboard/jumper wiring to the SD reader is far more likely to
     work reliably at this speed while debugging; bump it back up
     once the wiring itself is confirmed solid. */
  sd_ready = SD.begin(400000, SD_CS_PIN);
  Serial.println(sd_ready ? "SD card OK" : "SD card FAILED (check wiring, card inserted?)");
  if (sd_ready) load_tow_config_from_sd();

  if (Display.begin()) {
    error();
  }
  TouchDetector.begin();

  build_splash_screen();
  build_mode_select_screen();
  build_pilot_info_screen();
  build_home_screen();

  lv_scr_load(splash_screen);
  lv_timer_create(splash_timeout_cb, SPLASH_DURATION_MS, NULL);
  lv_timer_create(wifi_status_poll_cb, WIFI_STATUS_POLL_MS, NULL);
  lv_timer_create(led_state_refresh_cb, 250, NULL);
}

void loop() {
  lv_timer_handler();
  poll_esp32_uart();

  if (http_server_started) {
    WiFiClient client = http_server.available();
    if (client) {
      handle_http_client(client);
    }
  }
}
