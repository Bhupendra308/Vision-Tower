from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json
import os
import threading
import paho.mqtt.client as mqtt
import pygame
from flask_socketio import SocketIO, emit
# from detection.accident import run_accident_detection
from detection.crowd_control import detect_crowd
# from detection.security_monitoring import run_security_monitoring
# from detection.weapon_detection import run_weapon_detection
import cv2
import glob

app = Flask(__name__)
app.secret_key = "your_secret_key"
socketio = SocketIO(app)

# Load settings
CONFIG_PATH = "config/config.json"

def load_config():
    with open(CONFIG_PATH, "r") as config_file:
        return json.load(config_file)

def save_config(config):
    with open(CONFIG_PATH, "w") as config_file:
        json.dump(config, config_file, indent=4)

# MQTT Setup
MQTT_BROKER = "test.mosquitto.org"
MQTT_TOPIC = "crowd/alert"

pygame.mixer.init()
pygame.mixer.music.load("static/audio/alarm.mp3")

def on_message(client, userdata, msg):
    """Play sound and send alert via WebSocket when MQTT alert received"""
    alert_message = msg.payload.decode()
    print(f"📩 Received Alert: {alert_message}")
    pygame.mixer.music.play()
    socketio.emit("mqtt_alert", {"message": alert_message})

mqtt_client = mqtt.Client()
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, 1883, 60)
mqtt_client.subscribe(MQTT_TOPIC)
mqtt_thread = threading.Thread(target=mqtt_client.loop_forever, daemon=True)
mqtt_thread.start()

def get_first_video():
    """Find the first available video in static/videos/"""
    videos = glob.glob("static/videos/*.*")  # Get all files in the folder
    if videos:
        return videos[0]  
    return None  

# Routes
@app.route("/")
def index():
    return redirect(url_for("login"))

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))

    config = load_config()

    # OR condition: Live camera (IP) or Stored Video
    video_source = config["ip_address"] if config["detection_mode"] == "live" else get_first_video()
    
    error_message = None  # Default: No error
    if not video_source:
        error_message = "⚠ No valid video source found. Please check your settings."
        video_source = ""  # Prevent errors in HTML

    return render_template("dashboard.html", video_source=video_source, mode=config["detection_mode"], error_message=error_message)


@app.route("/settings", methods=["GET", "POST"])
def settings():
    if "user" not in session:
        return redirect(url_for("login"))

    config = load_config()
    if request.method == "POST":
        config["ip_address"] = request.form["ip_address"]
        config["detection_mode"] = request.form["detection_mode"]
        save_config(config)
        return redirect(url_for("dashboard"))

    return render_template("settings.html", config=config)

@app.route("/save_settings", methods=["POST"])
def save_settings():
    config = load_config()

    # Get values from the form
    detection_mode = request.form.get("detection_mode", "live")  # Default to live
    camera_ip = request.form.get("camera_ip", config.get("CAMERA_IP", ""))
    camera_quality = request.form.get("camera_quality")
    storage_limit = request.form.get("storage_limit")
    theme = request.form.get("theme")

    # Update config with new settings
    config["detection_mode"] = detection_mode
    config["camera_quality"] = camera_quality
    config["storage_limit"] = storage_limit
    config["theme"] = theme

    if detection_mode == "live":
        config["CAMERA_IP"] = camera_ip
    else:
        config["CAMERA_IP"] = ""  # Clear the IP if recorded mode is selected

    save_config(config)
    return redirect(url_for("settings"))

@app.route("/get_settings", methods=["GET"])
def get_settings():
    try:
        with open(CONFIG_PATH, "r") as config_file:
            config_data = json.load(config_file)
            return jsonify(config_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/get_alert", methods=["GET"])
def get_alert():
    return jsonify({
        "alert": True,
        "message": "Security alert detected!",  # Example alert message
        "audio": "/static/audio/alert.mp3"  # Correct path to audio file
    })


@app.route("/logs")
def logs():
    if "user" not in session:
        return redirect(url_for("login"))
    with open("logs/detection_logs.txt", "r") as f:
        logs = f.readlines()
    return render_template("logs.html", logs=logs)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username == "admin" and password == "admin123":
            session["user"] = username
            return redirect(url_for("dashboard"))
        return "Invalid credentials"
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

@app.route("/start-camera")
def start_camera():
    """ Start the Crowd Detection using live camera feed """
    
    # CAMERA_URL = "http://172.16.40.1:8080/video"
    CAMERA_URL = "http://192.168.87.96:8080/video"
    MODEL_PATH = "yolov8n.pt"
    
    # 🔥 Fix: Use absolute path for the alert sound
    ALERT_SOUND = os.path.abspath("static/audio/alarm.mp3")  
    CROWD_THRESHOLD = 3

    # Check if crowd_control.py exists
    if not os.path.exists("detection/crowd_control.py"):
        return jsonify({"error": "detection/crowd_control.py file not found"}), 500

    # Start the detection in a new thread
    thread = threading.Thread(target=detect_crowd, args=(CAMERA_URL, MODEL_PATH, ALERT_SOUND, CROWD_THRESHOLD))
    thread.start()

    return jsonify({"message": "Live Camera Started"})


if __name__ == "__main__":
    socketio.run(app, debug=True)
