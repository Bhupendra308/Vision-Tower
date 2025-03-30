import cv2
import time
import pygame
import threading
import settings
import websockets
import json
import asyncio

# Load Pretrained Cascade for Weapon Detection (Ensure it is weapon-specific cascade)
gun_cascade = cv2.CascadeClassifier('detection/cascade.xml')

# Initialize Pygame for Sound
pygame.mixer.init()
alert_sound = "static/audio/alert.mp3"  # Adjust path to the alert sound file

prev_time = 0
alert_cooldown = 2  # Minimum time gap between sounds (in seconds)
frame_time = 1 / 30  # Target FPS (30 FPS)
fps_multiplier = 1.5  # Increase FPS multiplier to speed up video
frame_skip = 2  # Skip every 2nd frame to speed up processing (can be adjusted)
frame_counter = 0

async def send_alert(event):
    """Send alert to WebSocket server."""
    async with websockets.connect("ws://localhost:8765") as websocket:
        await websocket.send(json.dumps({"event": event}))

def play_alert():
    """ Function to play alert sound without overlapping """
    if not pygame.mixer.get_busy():  # Play only if no other sound is playing
        pygame.mixer.music.load(alert_sound)
        pygame.mixer.music.play()

def run_weapon_detection():
    # Load video from live stream or recorded video
    VIDEO_SOURCE = settings.CONFIG["VIDEO_SOURCE"]  # Use live video source or recorded file
    cap = cv2.VideoCapture(VIDEO_SOURCE)

    if not cap.isOpened():
        print("Error: Could not open video.")
        exit()

    # Set the video resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_delay = int(1000 / fps)

    last_alert_time = 0
    alert_playing = False

    # Initialize start_time for FPS control
    start_time = time.time()

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("Error: Could not read frame.")
            break

        # Convert frame to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Detect weapons using the trained cascade classifier
        guns = gun_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))

        weapon_detected = False
        for (x, y, w, h) in guns:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
            weapon_detected = True

        # Play alert sound with cooldown to prevent overlapping
        curr_time = time.time()
        if weapon_detected and (curr_time - last_alert_time) > alert_cooldown and not alert_playing:
            last_alert_time = curr_time
            threading.Thread(target=play_alert, daemon=True).start()

        # Resize the frame for the frontend display
        frame_resized = cv2.resize(frame, (1920, 1080))

        # Send frame update and alert to frontend via WebSocket
        asyncio.run(send_alert(f"Weapon Detection Update - Weapon Detected: {weapon_detected}"))

        # Display the frame (this can be skipped to avoid opening new windows)
        # If you do need to display, you can do it in a custom UI
        # cv2.imshow("Weapon Detection", frame_resized)

        # Manage FPS control
        elapsed_time = time.time() - start_time
        sleep_time = max(0, frame_time / fps_multiplier - elapsed_time)
        time.sleep(sleep_time)

        frame_counter += 1

    # Release video capture when done
    cap.release()
