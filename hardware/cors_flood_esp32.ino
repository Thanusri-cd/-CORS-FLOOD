/*
 CORS-FLOOD ESP32 sensor transmitter (Arduino IDE)

 Example hardware:
   JSN-SR04T ultrasonic sensor: TRIG GPIO 5, ECHO GPIO 18
   Rain sensor module digital output (DO): GPIO 27
   Optional YF-S201 flow pulse output: GPIO 26

 Required Arduino libraries:
   - ArduinoJson (Library Manager: ArduinoJson by Benoit Blanchon)

 SAFETY / CALIBRATION:
   - Do not connect a 5V ECHO signal directly to ESP32. Use a voltage divider
     or level shifter to reduce ECHO to 3.3V.
   - Confirm the exact module pinout/voltage before wiring.
   - INSTALL_HEIGHT_CM is the distance from ultrasonic sensor face to channel
     bottom when empty. Water depth = install height - measured distance.
   - Latitude/longitude below are placeholders. Replace with actual fixed site
     coordinates or add a GNSS receiver and read its live coordinates.
   - Rain digital output detects wet/dry; it does not measure rainfall mm/hour.
*/

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

const char* WIFI_SSID = "YOUR_WIFI_NAME";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Replace with your computer's LAN IP address.
// Example: http://192.168.1.10:5000/api/sensors/data
const char* BACKEND_URL = "http://192.168.1.10:5000/api/sensors/data";

const char* DEVICE_ID = "S001";
const char* LOCATION_NAME = "Bapatla";

// Example site coordinates only. Replace with actual installation coordinates.
const float SITE_LATITUDE = 15.9045;
const float SITE_LONGITUDE = 80.4675;

// Change this to the measured mounting height above the channel bottom.
const float INSTALL_HEIGHT_CM = 100.0;

// Demonstration thresholds only; calibrate and validate before real alerts.
const float WARNING_DEPTH_CM = 25.0;
const float HIGH_DEPTH_CM = 45.0;

const int TRIG_PIN = 5;
const int ECHO_PIN = 18;
const int RAIN_DO_PIN = 27;
const int FLOW_PIN = 26;

const bool USE_FLOW_SENSOR = false;
const float FLOW_PULSES_PER_LITER = 450.0; // Verify/calibrate for your exact flow sensor.

volatile unsigned long flowPulses = 0;
unsigned long previousFlowMillis = 0;
float flowRateLpm = 0.0;

void IRAM_ATTR onFlowPulse() {
  flowPulses++;
}

float readDistanceCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(3);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  unsigned long duration = pulseIn(ECHO_PIN, HIGH, 30000UL);
  if (duration == 0) return -1.0;
  return duration * 0.0343f / 2.0f;
}

float readWaterDepthCm() {
  float distance = readDistanceCm();
  if (distance < 0 || distance > INSTALL_HEIGHT_CM) return -1.0;
  float depth = INSTALL_HEIGHT_CM - distance;
  if (depth < 0) depth = 0;
  return depth;
}

void updateFlowRate() {
  if (!USE_FLOW_SENSOR) return;
  unsigned long now = millis();
  unsigned long elapsed = now - previousFlowMillis;
  if (elapsed < 1000) return;

  noInterrupts();
  unsigned long pulses = flowPulses;
  flowPulses = 0;
  interrupts();

  // L/min = pulses per interval / pulses-per-liter / interval minutes.
  flowRateLpm = (pulses / FLOW_PULSES_PER_LITER) * (60000.0f / elapsed);
  previousFlowMillis = now;
}

void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to Wi-Fi");

  unsigned long started = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started < 20000) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("Wi-Fi connected. ESP32 IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("Wi-Fi connection failed; will retry.");
  }
}

void postReading(float waterDepthCm, bool rainDetected, float flowLpm) {
  connectWiFi();
  if (WiFi.status() != WL_CONNECTED) return;

  StaticJsonDocument<512> doc;
  doc["device_id"] = DEVICE_ID;
  doc["road_id"] = DEVICE_ID;
  doc["location"] = LOCATION_NAME;
  doc["latitude"] = SITE_LATITUDE;
  doc["longitude"] = SITE_LONGITUDE;
  doc["water_level_cm"] = waterDepthCm >= 0 ? serialized(String(waterDepthCm, 1)) : serialized("null");
  doc["rain_detected"] = rainDetected;

  // This sensor type is a digital rain switch, not a calibrated rain gauge.
  doc["rainfall_mm_hr"] = nullptr;
  if (USE_FLOW_SENSOR) {
    doc["flow_rate_lpm"] = flowLpm;
  } else {
    doc["flow_rate_lpm"] = nullptr;
  }
  doc["timestamp_ms"] = millis();

  String risk = "LOW";
  if (waterDepthCm >= HIGH_DEPTH_CM) risk = "HIGH";
  else if (waterDepthCm >= WARNING_DEPTH_CM || rainDetected) risk = "WARNING";
  doc["device_reported_risk"] = risk;

  String body;
  serializeJson(doc, body);

  HTTPClient http;
  http.setTimeout(5000);
  http.begin(BACKEND_URL);
  http.addHeader("Content-Type", "application/json");

  int status = http.POST(body);
  Serial.printf("POST /api/sensors/data -> HTTP %d\n", status);
  Serial.println(body);
  if (status > 0) Serial.println(http.getString());
  else Serial.printf("HTTP error: %s\n", http.errorToString(status).c_str());
  http.end();
}

void setup() {
  Serial.begin(115200);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(RAIN_DO_PIN, INPUT);

  if (USE_FLOW_SENSOR) {
    pinMode(FLOW_PIN, INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(FLOW_PIN), onFlowPulse, RISING);
  }

  previousFlowMillis = millis();
  connectWiFi();
}

void loop() {
  float waterDepth = readWaterDepthCm();

  // Many rain modules are active-low. Reverse this if your module behaves differently.
  bool rainDetected = digitalRead(RAIN_DO_PIN) == LOW;

  updateFlowRate();

  Serial.printf("Water depth: %.1f cm | Rain: %s | Flow: %.2f L/min\n",
                waterDepth, rainDetected ? "WET" : "DRY", flowRateLpm);

  postReading(waterDepth, rainDetected, flowRateLpm);
  delay(5000);
}
