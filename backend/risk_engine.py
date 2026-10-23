from datetime import datetime


def classify_road(reading):
    water = reading.get("water_level_cm", reading.get("water_level"))
    rain = reading.get("rainfall_mm_hr", reading.get("rainfall"))
    flow = reading.get("flow_level", reading.get("flow_rate_lpm"))
    rain_detected = reading.get("rain_detected", False)

    def as_number(value):
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    water = as_number(water)
    rain = as_number(rain)
    flow = as_number(flow)

    has_measurement = (
        water is not None or rain is not None or flow is not None
        or rain_detected is True
    )

    if not has_measurement:
        risk, color = "UNKNOWN", "gray"
    elif (
        (water is not None and water >= 45)
        or (rain is not None and rain >= 60)
        or (flow is not None and flow >= 80)
    ):
        risk, color = "HIGH", "red"
    elif (
        (water is not None and water >= 25)
        or (rain is not None and rain >= 20)
        or (flow is not None and flow >= 45)
        or rain_detected is True
    ):
        risk, color = "WARNING", "orange"
    else:
        risk, color = "LOW", "green"

    result = dict(reading)
    result["water_level_cm"] = water
    result["rainfall_mm_hr"] = rain
    result["flow_level"] = flow
    result["risk"] = risk
    result["color"] = color
    return result


def create_alerts(roads):
    alerts = []
    for road in roads:
        risk = road.get("risk", "UNKNOWN")
        if risk not in ("WARNING", "HIGH"):
            continue

        source = "Simulated" if road.get("simulated", False) else "Sensor-reported"
        alerts.append({
            "road_id": road.get("road_id"),
            "sensor_id": road.get("sensor_id"),
            "location": road.get("location"),
            "severity": risk,
            "message": (
                f"{source} {risk.lower()} road waterlogging risk near "
                f"{road.get('location', 'unknown location')}."
            ),
            "simulated": road.get("simulated", False),
            "timestamp": road.get("timestamp", datetime.now().isoformat())
        })
    return alerts
