from datetime import datetime, timezone
from threading import Lock

from flask import Flask, jsonify, request
from flask_cors import CORS

from sensor_simulator import generate_all_readings
from risk_engine import classify_road, create_alerts

app = Flask(__name__)
CORS(app)

current_scenario = "normal"
live_readings = {}
data_lock = Lock()
LIVE_TIMEOUT_SECONDS = 60


def utc_now():
    return datetime.now(timezone.utc)


def get_fresh_live_readings():
    now = utc_now()
    fresh = {}

    with data_lock:
        for device_id, item in live_readings.items():
            age = (now - item["_received_at"]).total_seconds()
            if age <= LIVE_TIMEOUT_SECONDS:
                fresh[device_id] = {
                    key: value for key, value in item.items()
                    if key != "_received_at"
                }

    return list(fresh.values())


def get_current_readings():
    live = get_fresh_live_readings()
    if live:
        return live, "LIVE"
    return generate_all_readings(current_scenario), "SIMULATION"


def get_roads():
    readings, mode = get_current_readings()
    return [classify_road(reading) for reading in readings], mode


@app.route("/api/health", methods=["GET"])
def health():
    live = get_fresh_live_readings()
    return jsonify({
        "status": "ok",
        "mode": "LIVE" if live else "SIMULATION",
        "live_devices": len(live),
        "scenario": current_scenario,
        "timestamp": utc_now().isoformat()
    })


@app.route("/api/sensors", methods=["GET"])
def sensors():
    readings, mode = get_current_readings()
    return jsonify({
        "mode": mode,
        "scenario": current_scenario,
        "simulated": mode == "SIMULATION",
        "sensors": readings
    })


@app.route("/api/roads", methods=["GET"])
def roads():
    road_data, mode = get_roads()
    return jsonify({
        "mode": mode,
        "scenario": current_scenario,
        "roads": road_data
    })


@app.route("/api/road-risk", methods=["GET"])
def road_risk():
    road_data, mode = get_roads()
    return jsonify({"mode": mode, "roads": road_data})


@app.route("/api/alerts", methods=["GET"])
def alerts():
    road_data, mode = get_roads()
    return jsonify({"mode": mode, "alerts": create_alerts(road_data)})


@app.route("/api/sensors/data", methods=["POST"])
def receive_sensor_data():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Send a valid JSON object."}), 400

    device_id = data.get("device_id") or data.get("sensor_id")
    if not device_id:
        return jsonify({"error": "device_id or sensor_id is required."}), 400

    try:
        latitude = float(data["latitude"])
        longitude = float(data["longitude"])
        if not -90 <= latitude <= 90:
            raise ValueError
        if not -180 <= longitude <= 180:
            raise ValueError
    except (KeyError, TypeError, ValueError):
        return jsonify({
            "error": "Valid latitude and longitude are required."
        }), 400

    water = data.get("water_level_cm", data.get("water_level"))
    rain = data.get("rainfall_mm_hr", data.get("rainfall"))
    flow = data.get("flow_level", data.get("flow_rate_lpm"))
    rain_detected = data.get("rain_detected", False)

    if not isinstance(rain_detected, bool):
        return jsonify({"error": "rain_detected must be true or false."}), 400

    def optional_number(value, field_name):
        if value is None:
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"{field_name} must be a number or null.")
        if number < 0:
            raise ValueError(f"{field_name} cannot be negative.")
        return number

    try:
        water = optional_number(water, "water_level_cm")
        rain = optional_number(rain, "rainfall_mm_hr")
        flow = optional_number(flow, "flow_level")
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    if water is None and rain is None and flow is None and "rain_detected" not in data:
        return jsonify({
            "error": "At least one sensor measurement is required."
        }), 400

    reading = {
        "device_id": str(device_id),
        "sensor_id": str(data.get("sensor_id", device_id)),
        "road_id": data.get("road_id", str(device_id)),
        "location": data.get("location", "Live sensor location"),
        "latitude": latitude,
        "longitude": longitude,
        "water_level_cm": water,
        "rainfall_mm_hr": rain,
        "flow_level": flow,
        "rain_detected": rain_detected,
        "timestamp": data.get("timestamp", utc_now().isoformat()),
        "simulated": False
    }

    classified = classify_road(reading)
    with data_lock:
        live_readings[str(device_id)] = {
            **reading,
            "_received_at": utc_now()
        }

    return jsonify({
        "status": "received",
        "mode": "LIVE",
        "sensor_id": str(device_id),
        "risk": classified["risk"],
        "message": "Sensor reading received successfully."
    }), 201


@app.route("/api/simulation/scenario", methods=["POST"])
def change_scenario():
    global current_scenario
    data = request.get_json(silent=True) or {}
    scenario = data.get("scenario")

    if scenario not in ("normal", "warning", "flood"):
        return jsonify({
            "error": "Scenario must be normal, warning, or flood."
        }), 400

    current_scenario = scenario
    return jsonify({
        "status": "success",
        "scenario": current_scenario,
        "message": "Simulation scenario changed."
    })


@app.route("/api/simulation/refresh", methods=["POST"])
def refresh_simulation():
    return jsonify({
        "status": "success",
        "scenario": current_scenario,
        "sensors": generate_all_readings(current_scenario)
    })


if __name__ == "__main__":
    print("CORS-FLOOD backend starting...")
    print("Health: http://127.0.0.1:5000/api/health")
    app.run(host="0.0.0.0", port=5000, debug=False)
