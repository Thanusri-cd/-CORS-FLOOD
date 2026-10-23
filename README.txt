CORS-FLOOD WHOLE PROJECT
========================

Folder structure
----------------
CORS-FLOOD/
  frontend/index.html             Dashboard, map and safe-route prototype
  backend/app.py                  Flask API server
  backend/risk_engine.py          Road risk classification and alerts
  backend/sensor_simulator.py     Demo readings for Bapatla, Chirala, Guntur, Repalle
  backend/requirements.txt        Python dependencies
  hardware/cors_flood_esp32.ino   ESP32 sensor sender starter sketch
  README.txt                      This guide

RUN THE FRONTEND AND BACKEND (SIMULATION MODE)
----------------------------------------------
Requirements: Python installed and internet access for map tiles/routing.

1. Extract the ZIP file.
2. Open the extracted CORS-FLOOD folder in VS Code.
3. Open a VS Code terminal and run:

   cd backend
   python -m pip install -r requirements.txt
   python app.py

   Keep this terminal open.

4. Open a SECOND terminal in VS Code, from the project root, and run:

   cd frontend
   python -m http.server 5500

5. Open the dashboard in a browser:

   http://127.0.0.1:5500/

6. Test backend status:
   http://127.0.0.1:5000/api/health
   http://127.0.0.1:5000/api/roads

TEST THE SIMULATION SCENARIO
----------------------------
To switch to the flood simulation, run this in a third terminal:

python -c "import urllib.request,json; r=urllib.request.Request('http://127.0.0.1:5000/api/simulation/scenario',data=json.dumps({'scenario':'flood'}).encode(),headers={'Content-Type':'application/json'},method='POST'); print(urllib.request.urlopen(r).read().decode())"

To switch back to normal:

python -c "import urllib.request,json; r=urllib.request.Request('http://127.0.0.1:5000/api/simulation/scenario',data=json.dumps({'scenario':'normal'}).encode(),headers={'Content-Type':'application/json'},method='POST'); print(urllib.request.urlopen(r).read().decode())"

ESP32 HARDWARE
--------------
The hardware folder contains a starter sketch. Arduino IDE is needed only when
uploading the sketch to a physical ESP32. Before uploading, edit the Wi-Fi SSID,
password, backend URL, fixed site coordinates and installation height in the
sketch. The backend URL must use the laptop's LAN IPv4 address (not 127.0.0.1)
when the ESP32 sends data over Wi-Fi. Laptop and ESP32 need network connectivity.
Install the ArduinoJson library in Arduino IDE.

The sketch assumes specific pins and sensor types; check the comments in the
sketch and verify your own wiring. Never connect a 5V ultrasonic ECHO output
directly to an ESP32 GPIO; use a suitable voltage divider/level shifter.

IMPORTANT LIMITATIONS
---------------------
- Simulated readings are demonstration values, not live observations.
- Risk thresholds are examples and are not official road-safety standards.
- The route finder uses public geocoding/routing services and a proximity-based
  prototype heuristic; it cannot guarantee a route is safe or passable.
- The ESP32 sketch uses fixed site coordinates, not live GNSS/CORS positioning.
- A basic digital rain sensor detects wet/dry; it does not measure rainfall
  intensity. A suitable calibrated sensor is required for mm/hour measurements.
- Live readings are held in memory and expire after 60 seconds. Restarting the
  backend clears them.
- The backend binds to 0.0.0.0 for local network access. Use only on a trusted
  network and configure firewall access carefully.
