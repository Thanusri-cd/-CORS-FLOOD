from datetime import datetime
import random

SENSORS = [
    {
        "sensor_id": "S001", "road_id": "R001", "location": "Bapatla",
        "latitude": 15.9045, "longitude": 80.4675
    },
    {
        "sensor_id": "S002", "road_id": "R002", "location": "Chirala",
        "latitude": 15.8120, "longitude": 80.3520
    },
    {
        "sensor_id": "S003", "road_id": "R003", "location": "Guntur",
        "latitude": 16.3067, "longitude": 80.4365
    },
    {
        "sensor_id": "S004", "road_id": "R004", "location": "Repalle",
        "latitude": 16.0180, "longitude": 80.8290
    }
]

SCENARIOS = {
    "normal": {"water": (5, 18), "rain": (0, 15), "flow": (0, 20)},
    "warning": {"water": (25, 40), "rain": (20, 40), "flow": (20, 50)},
    "flood": {"water": (45, 80), "rain": (60, 100), "flow": (80, 100)}
}


def generate_all_readings(scenario="normal"):
    if scenario not in SCENARIOS:
        scenario = "normal"

    settings = SCENARIOS[scenario]
    readings = []

    for sensor in SENSORS:
        rain = random.uniform(*settings["rain"])
        readings.append({
            **sensor,
            "device_id": sensor["sensor_id"],
            "water_level_cm": round(random.uniform(*settings["water"]), 1),
            "rainfall_mm_hr": round(rain, 1),
            "flow_level": round(random.uniform(*settings["flow"]), 1),
            "rain_detected": rain >= 20,
            "scenario": scenario,
            "simulated": True,
            "timestamp": datetime.now().isoformat()
        })

    return readings
