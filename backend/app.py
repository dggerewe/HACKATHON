from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import random
import time
from model import predict_wait_time

app = Flask(__name__)
CORS(app)

# TELEGRAM CONFIG 
TELEGRAM_BOT_TOKEN = "8441639678:AAGf_q3WXZluGdk-g6Fno_jfVlfGHyAFTRo"
TELEGRAM_CHAT_ID = 6382096984

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    response = requests.post(url, json=payload)
    print("📨 Telegram status:", response.status_code)
    print("📨 Telegram response:", response.text)

#  REGISTERED DRIVERS 
REGISTERED_DRIVERS = {
    "6382096984": "AMB-001",
    "9876543210": "AMB-002"
}

OTP_STORE = {}

# OTP LOGIN 
@app.route("/request-otp", methods=["POST"])
def request_otp():
    mobile = request.json.get("mobile")

    if mobile not in REGISTERED_DRIVERS:
        return jsonify({"error": "Unauthorized driver"}), 403

    otp = str(random.randint(100000, 999999))
    OTP_STORE[mobile] = {
        "otp": otp,
        "expires": time.time() + 120
    }

    send_telegram_alert(
        f"🚑 Ambulance Login OTP\n\nMobile: {mobile}\nOTP: {otp}\nValid for 2 minutes"
    )

    print("🔐 OTP GENERATED:", otp)
    return jsonify({"message": "OTP sent"})

@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    mobile = request.json.get("mobile")
    otp = request.json.get("otp")

    record = OTP_STORE.get(mobile)
    if not record:
        return jsonify({"error": "OTP not requested"}), 400

    if time.time() > record["expires"]:
        return jsonify({"error": "OTP expired"}), 400

    if otp != record["otp"]:
        return jsonify({"error": "Invalid OTP"}), 401

    return jsonify({
        "success": True,
        "driver_mobile": mobile
    })

#  GEOCODING 
@app.route("/geocode")
def geocode():
    query = request.args.get("q")
    if not query:
        return jsonify([])

    r = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": query, "format": "json", "limit": 5},
        headers={"User-Agent": "emergency-app"}
    )

    return jsonify([
        {"label": p["display_name"], "coords": [float(p["lon"]), float(p["lat"])]}
        for p in r.json()
    ])

#  ROUTING + ML + ROADS 
@app.route("/routes", methods=["POST"])
def routes():
    start = request.json["start"]
    end = request.json["end"]

    url = (
        f"https://router.project-osrm.org/route/v1/driving/"
        f"{start[0]},{start[1]};{end[0]},{end[1]}"
        "?alternatives=true&steps=true&geometries=geojson"
    )

    osrm = requests.get(url).json()
    output = []

    for route in osrm.get("routes", [])[:3]:
        roads = []
        for leg in route["legs"]:
            for step in leg["steps"]:
                if step["name"] and step["name"] not in roads:
                    roads.append(step["name"])

        traffic = random.choice(["LOW", "MEDIUM", "HIGH"])
        wait = predict_wait_time(traffic.lower(), random.choice(["yes", "no"]))

        output.append({
            "coords": [(c[1], c[0]) for c in route["geometry"]["coordinates"]],
            "distance": round(route["distance"] / 1000, 2),
            "duration": round(route["duration"] / 60, 2),
            "traffic": traffic,
            "predicted_wait": wait,
            "roads": roads[:6]
        })

    return jsonify({"routes": output})

#  CONTROL ROOM 
@app.route("/notify-control-room", methods=["POST"])
def notify_control_room():
    data = request.json
    mobile = data["driver_mobile"]

    ambulance_id = REGISTERED_DRIVERS.get(mobile, "UNKNOWN")

    roads = "\n".join([f"• {r}" for r in data["roads"]])

    message = (
        "🚨 EMERGENCY ROUTE ACTIVATED 🚑\n\n"
        f"Ambulance ID: {ambulance_id}\n"
        f"ETA: {data['duration']} min\n"
        f"Distance: {data['distance']} km\n\n"
        "🚦 CLEAR THESE ROADS:\n"
        f"{roads}\n\n"
        "Green Corridor Requested"
    )

    send_telegram_alert(message)
    print(message)

    return jsonify({"message": "Control room notified"})

if __name__ == "__main__":
    app.run(debug=True)
