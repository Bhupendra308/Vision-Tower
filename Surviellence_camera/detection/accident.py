import cv2
import numpy as np
import time
import settings
import paho.mqtt.client as mqtt
import asyncio
import json
from flask_socketio import SocketIO, emit

# ✅ Load configurations
CAMERA_IP = settings.CONFIG["CAMERA_IP"]
MQTT_BROKER = settings.CONFIG["MQTT_BROKER"]
MQTT_TOPIC = settings.CONFIG["MQTT_TOPIC"]

# ✅ Initialize MQTT
mqtt_client = mqtt.Client()
mqtt_client.connect(MQTT_BROKER, 1883, 60)

async def send_alert(event, socketio):
    """Send event to frontend via WebSocket"""
    socketio.emit("accident_alert", {"message": event})

async def run_accident_detection(cap, socketio):
    # Read the first two frames
    ret, frame1 = cap.read()
    ret, frame2 = cap.read()

    if not ret:
        socketio.emit("accident_alert", {"message": "Error: Unable to read video stream."})
        return

    last_alert_time = 0
    alert_cooldown = 10  # Prevent frequent alerts
    motion_history = []

    while cap.isOpened():
        ret, frame2 = cap.read()
        if not ret:
            socketio.emit("accident_alert", {"message": "Video stream ended or error occurred."})
            break

        # Convert frames to grayscale
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        # Compute frame difference
        frame_diff = cv2.absdiff(gray1, gray2)
        _, thresh = cv2.threshold(frame_diff, 25, 255, cv2.THRESH_BINARY)
        thresh = cv2.dilate(thresh, np.ones((5, 5), np.uint8), iterations=2)

        # Find contours in the thresholded image
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        accident_detected = False

        for contour in contours:
            if cv2.contourArea(contour) > 8000:  # Ignore small movements
                x, y, w, h = cv2.boundingRect(contour)
                # Draw bounding box around detected motion
                cv2.rectangle(frame2, (x, y), (x + w, y + h), (0, 255, 0), 2)
                motion_history.append((x, y))

                if len(motion_history) > 10:
                    motion_history.pop(0)

                if len(motion_history) >= 5:
                    speed = np.linalg.norm(np.array(motion_history[-1]) - np.array(motion_history[0]))
                    if speed > 30:  # Speed threshold for accident detection
                        accident_detected = True

        # If accident detected, send alert and publish to MQTT
        if accident_detected and time.time() - last_alert_time > alert_cooldown:
            last_alert_time = time.time()
            mqtt_client.publish(MQTT_TOPIC, "Accident Detected!")
            await send_alert("Accident Detected", socketio)

        # Send the processed frame to the frontend for real-time display
        _, jpeg_frame = cv2.imencode('.jpg', frame2)
        frame_data = jpeg_frame.tobytes()
        socketio.emit('video_feed', {'frame': frame_data})

        # Update frame1 for the next iteration
        frame1 = frame2
