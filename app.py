from flask import Flask, render_template, request, redirect, flash, session, jsonify
from ultralytics import YOLO
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import mysql.connector
import os
import re
import cv2
import uuid
import base64
import requests
import polyline
import math
from datetime import datetime

# API Keys
TOMTOM_API_KEY = "N5r2oscYpyTlryw8xkuTwzH3adcrhSdd"
WEATHER_API_KEY = "b19689dd41586dc21f652b06f0dc1dbb"

app = Flask(__name__)
app.secret_key = "3344"

# Load YOLO Model
model = YOLO("best (4).pt")


# MySQL Connection
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="potholedb"
    )


# Folders
UPLOAD_FOLDER = "static/uploads"
RESULT_FOLDER = "static/results"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)


# Home Page
@app.route('/')
def index():
    return render_template("index.html")


# About Page
@app.route('/about')
def about():
    return render_template("about.html")


# Methodology Page
@app.route('/methodology')
def methodology():
    return render_template("methodology.html")


# Register
@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        uname = request.form['uname']
        email = request.form['email']
        password = request.form['password']

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash("Invalid Email")
            return redirect('/register')

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE email=%s",
            (email,)
        )

        user = cursor.fetchone()

        if user:
            flash("Email Already Registered")
            cursor.close()
            conn.close()
            return redirect('/register')

        cursor.execute(
            "INSERT INTO users(uname,email,password) VALUES(%s,%s,%s)",
            (uname, email, hashed_password)
        )

        conn.commit()
        cursor.close()
        conn.close()
        flash("Registration Successful")
        return redirect('/login')

    return render_template("register.html")


# Login
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM users WHERE email=%s", (email,) )
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['u_id']
            session['username'] = user['uname']
            return redirect('/')

        else:

            flash("Invalid Email or Password")
            return redirect('/login')

    return render_template("login.html")


# Logout
@app.route('/logout')
def logout():
    session.clear()
    return render_template("index.html")

# Prediction
@app.route('/predict', methods=['GET'])
def predict():
    
    if 'user_id' not in session:
        return redirect('/login')

    return render_template("prediction.html")


# Real-time frame detection
cap = None

@app.route("/detect_frame", methods=["POST"])
def detect_frame():
    global cap
    
    if cap is None:
        # Scan indices to detect the active camera source (e.g. DroidCam/Webcam)
        for idx in [1, 0, 2, 3]:
            temp_cap = cv2.VideoCapture(idx)
            if temp_cap.isOpened():
                ret, frame = temp_cap.read()
                if ret and frame is not None:
                    cap = temp_cap
                    break
                else:
                    temp_cap.release()
            else:
                temp_cap.release()
        if cap is None:
            cap = cv2.VideoCapture(0)
            
    ret, frame = cap.read()
    if not ret or frame is None:
        return jsonify({"error": "Camera frame not found"}), 400
        
    # YOLO Detection
    results = model(frame)
    result = results[0]
    
    # Draw bounding boxes
    img = result.plot()
    
    pothole_count = len(result.boxes)
    
    if pothole_count == 0:
        risk = "Low"
        traffic = "Low Traffic"
        road_condition = "Safe"
        traffic_message = "No potholes detected. Low traffic risk is expected."
       
    elif pothole_count <= 3:
       risk = "Medium"
       traffic = "Moderate Traffic"
       road_condition = "Caution"
       traffic_message = "Some potholes detected. Moderate traffic risk is expected."
    else:
        risk = "High"
        traffic = "Heavy Traffic"
        road_condition = "High Risk"
        traffic_message = "Multiple potholes detected. High traffic congestion may occur."
        
    # Encode frame to base64
    success, buffer = cv2.imencode(".jpg", img)
    if not success:
        return jsonify({"error": "Encoding failed"}), 500
        
    encoded = base64.b64encode(buffer).decode("utf-8")
    
    return jsonify({
        "image": encoded,
        "alert": pothole_count > 0,
        "potholes": pothole_count,
        "risk": risk,
        "traffic": traffic,
        "road_condition": road_condition,
        "traffic_message": traffic_message
    })

@app.route("/stop_camera", methods=["POST"])
def stop_camera():
    global cap
    if cap is not None:
        cap.release()
        cap = None
    return jsonify({"status": "stopped"})


# --- Traffic Page Routes & Helpers ---
def geocode(place):
    url = f"https://nominatim.openstreetmap.org/search?q={place}&format=json"
    res = requests.get(url, headers={"User-Agent": "traffic-app"}).json()

    if not res:
        raise Exception("Location not found: " + place)

    return float(res[0]["lat"]), float(res[0]["lon"])



def get_weather(lat, lon):
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}"
    data = requests.get(url).json()

    if "weather" not in data:
        raise Exception("Weather API failed")

    return data["weather"][0]["main"]

def extract_duration(route):
    if "summary" in route:
        return route["summary"]["duration"]

    if "properties" in route:
        return route["properties"]["summary"]["duration"]

    raise Exception("Unknown route format")

def get_routes(start, end):
    """
    TomTom real-time traffic routing.
    Returns normalized routes sorted by duration.
    """

    base_url = "https://api.tomtom.com/routing/1/calculateRoute"

    coord_str = f"{start[0]},{start[1]}:{end[0]},{end[1]}"

    params = {
        "key": TOMTOM_API_KEY,
        "traffic": "true",          # REAL-TIME TRAFFIC
        "maxAlternatives": 2,       # request alternate routes
        "routeType": "fastest",
        "travelMode": "car"
    }

    url = f"{base_url}/{coord_str}/json"

    response = requests.get(url, params=params)

    if response.status_code != 200:
        raise Exception(f"TomTom HTTP Error {response.status_code}: {response.text}")

    data = response.json()

    if "routes" not in data or not data["routes"]:
        raise Exception("No routes returned from TomTom")

    normalized_routes = []

    for r in data["routes"]:
        summary = r["summary"]
        points = r["legs"][0]["points"]

        # convert to polyline format compatible with your system
        coords = [(p["latitude"], p["longitude"]) for p in points]

        # Extract live traffic-specific data
        travel_time = summary.get("travelTimeInSeconds", 0)
        traffic_delay = summary.get("trafficDelayInSeconds", 0)
        # TomTom might not always provide noTrafficTravelTimeInSeconds, so we calculate it as fallback
        base_time = summary.get("noTrafficTravelTimeInSeconds", max(0, travel_time - traffic_delay))

        normalized_routes.append({
            "summary": {
                "duration": travel_time,
                "traffic_delay": traffic_delay,
                "base_duration": base_time
            },
            "geometry_coords": coords
        })

    # sort fastest first
    normalized_routes.sort(key=lambda r: r["summary"]["duration"])

    return normalized_routes


def classify_traffic(duration, delay, base_duration, weather):
    score = 0

    # 1. Traffic Delay Intensity (Live Traffic Impact)
    if base_duration > 0:
        delay_ratio = delay / base_duration
        
        if delay_ratio > 0.40:    # 40% slower than usual
            score += 5
        elif delay_ratio > 0.25:  # 25% slower
            score += 3
        elif delay_ratio > 0.10:  # 10% slower
            score += 2
        elif delay_ratio > 0.05:  # 5% slower
            score += 1

    # 2. Weather Impact (Safety & Visibility)
    weather_lower = weather.lower()
    if any(cond in weather_lower for cond in ["rain", "storm", "snow", "thunderstorm", "drizzle", "hail"]):
        score += 2
    elif any(cond in weather_lower for cond in ["mist", "fog", "haze", "smoke", "dust"]):
        score += 1

    # 3. Peak Hours (Historical Pressure)
    hour = datetime.now().hour
    if (8 <= hour <= 10) or (17 <= hour <= 20):
        score += 2
    elif (7 <= hour < 8) or (16 <= hour < 17) or (20 <= hour <= 21):
        score += 1

    # Final bucket classification
    if score >= 6:
        return "High"
    elif score >= 3:
        return "Moderate"
    else:
        return "Low"


def extract_coords(route):
    # TomTom normalized format
    if "geometry_coords" in route:
        return route["geometry_coords"]

    # fallback for older formats
    if isinstance(route.get("geometry"), str):
        return polyline.decode(route["geometry"])

    raise Exception("Unknown geometry format")

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c


@app.route('/traffic')
def traffic():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template("traffic.html")


@app.route("/get_traffic", methods=["POST"])
def get_traffic():
    try:
        data = request.get_json()

        source = data.get("source")
        destination = data.get("destination")

        if not source or not destination:
            return jsonify({"error": "Source or destination missing"})

        # Geocode
        slat, slon = geocode(source)
        dlat, dlon = geocode(destination)

        # Weather
        weather = get_weather(slat, slon)

        # Routes
        routes = get_routes((slat, slon), (dlat, dlon))

        if not routes or len(routes) == 0:
            return jsonify({"error": "No routes found"})

        main_route = routes[0]
        alt_route = routes[1] if len(routes) > 1 else None

        # Extract details for classification
        summary = main_route["summary"]
        duration = summary["duration"]
        delay = summary["traffic_delay"]
        base_dur = summary["base_duration"]

        status = classify_traffic(duration, delay, base_dur, weather)

        main_coords = extract_coords(main_route)
        alt_coords = extract_coords(alt_route) if (alt_route and status != "Low") else []



        response_data = {
            "status": status,
            "weather": weather,
            "main_route": main_coords,
            "alt_route": alt_coords
        }

        print("SUCCESS RESPONSE:", response_data)

        return jsonify(response_data)

    except Exception as e:
        print("TRAFFIC API ERROR:", e)
        return jsonify({"error": str(e)})


if __name__ == "__main__":

    app.run(debug=True, port=5000)