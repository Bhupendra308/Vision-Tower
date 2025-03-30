import cv2
import numpy as np
import time
import threading
import asyncio
from playsound import playsound
import settings
import websockets
import json

def run_security_monitoring():
    # Load video from the live stream in dashboard.html or the recorded video being played
    VIDEO_SOURCE = settings.CONFIG["VIDEO_SOURCE"]  # This should be set to the source of the video being played in the dashboard

    # Load the video
    cap = cv2.VideoCapture(VIDEO_SOURCE)

    if not cap.isOpened():
        print("Error: Could not open video.")
        exit()

    # Set the video resolution to Full HD (1920x1080)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)  # Width
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)  # Height

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_delay = int(1000 / fps)

    # Read initial frames
    ret, frame1 = cap.read()
    ret, frame2 = cap.read()

    if not ret:
        print("Error: Could not read frames. Exiting...")
        cap.release()
        exit()

    last_alert_time = 0
    alert_cooldown = 5  # Cooldown time to avoid continuous alerts
    alert_playing = False  
    motion_history = []  # To track movement over time

    async def send_alert(event):
        """Send alert to WebSocket server."""
        async with websockets.connect("ws://localhost:8765") as websocket:
            await websocket.send(json.dumps({"event": event}))

    def play_alert():
        global alert_playing
        alert_playing = True
        playsound("static/alerts/alert_sound.mp3")  # Adjust path to the alert sound file
        alert_playing = False

    while cap.isOpened():
        # Convert to grayscale
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        # Apply Gaussian blur
        gray1 = cv2.GaussianBlur(gray1, (5, 5), 0)
        gray2 = cv2.GaussianBlur(gray2, (5, 5), 0)

        # Compute absolute difference
        frame_diff = cv2.absdiff(gray1, gray2)

        # Thresholding to highlight movement
        _, thresh = cv2.threshold(frame_diff, 25, 255, cv2.THRESH_BINARY)

        # Morphological operations to reduce noise
        kernel = np.ones((5, 5), np.uint8)
        thresh = cv2.dilate(thresh, kernel, iterations=2)

        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        suspicious_activity_detected = False
        large_movements = []

        for contour in contours:
            if cv2.contourArea(contour) > 5000:  # Adjusted threshold to detect movement
                x, y, w, h = cv2.boundingRect(contour)
                center = (x + w // 2, y + h // 2)
                large_movements.append(center)

                # Track movement over time
                motion_history.append(center)
                if len(motion_history) > 10:  
                    motion_history.pop(0)  # Keep only recent movements

                # Detect sudden movement (attack-like behavior)
                if len(motion_history) >= 5:
                    speed = np.linalg.norm(np.array(motion_history[-1]) - np.array(motion_history[0]))
                    if speed > 50:  # Sudden fast movement detected
                        suspicious_activity_detected = True
                        cv2.putText(frame1, "ALERT: Attack Detected!", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

                # Highlight the detected movement area
                cv2.rectangle(frame1, (x, y), (x + w, y + h), (0, 0, 255), 2)

        # Play alert sound with cooldown
        current_time = time.time()
        if suspicious_activity_detected and (current_time - last_alert_time > alert_cooldown) and not alert_playing:
            last_alert_time = current_time
            threading.Thread(target=play_alert, daemon=True).start()

        # Resize frame to fit the display size (for frontend display)
        frame_resized = cv2.resize(frame1, (1920, 1080))  # Adjust resolution if needed

        # Send frame update and alert to frontend via WebSocket
        asyncio.run(send_alert(f"Frame Update - Suspicious Activity: {suspicious_activity_detected}"))

        # Read the next frame
        frame1 = frame2
        ret, frame2 = cap.read()

        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Reset video capture if it ends
            ret, frame1 = cap.read()
            ret, frame2 = cap.read()

    # Release video capture when done
    cap.release()
