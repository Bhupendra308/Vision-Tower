import cv2
import time
import pygame
import threading
import torch
import numpy as np
from ultralytics import YOLO

def detect_crowd(camera_url, model_path='yolov8n.pt', alert_sound_path='alarm.mp3', crowd_threshold=5):
    """ Detects crowd using YOLOv8 and plays an alert if the crowd exceeds the threshold. """

    # Load YOLOv8 Model
    model = YOLO(model_path).to('cpu')  # Using CPU for inference

    # Initialize Pygame for Sound Alerts
    pygame.mixer.init()
    alert_sound = pygame.mixer.Sound(alert_sound_path)

    # Alert control variables
    alert_active = False
    stop_threads = False  # Flag to stop threads

    def play_alert():
        """Plays alert sound."""
        nonlocal alert_active
        if not alert_active:
            alert_active = True
            alert_sound.play(-1)  # 🔥 Play continuously until stopped

    def stop_alert():
        """Stops alert sound."""
        nonlocal alert_active
        if alert_active:
            alert_sound.stop()
            alert_active = False

    # Open IP Camera Stream
    camera = cv2.VideoCapture(camera_url, cv2.CAP_FFMPEG)
    if not camera.isOpened():
        print("Error: Could not open video stream.")
        return

    frame = None  # Initialize frame

    def capture_frame():
        """Capture frame from IP camera in a separate thread for better performance."""
        nonlocal frame, stop_threads
        while not stop_threads:
            ret, new_frame = camera.read()
            if ret:
                frame = new_frame

    # Start background thread for capturing frames
    capture_thread = threading.Thread(target=capture_frame, daemon=True)
    capture_thread.start()

    while True:
        if frame is None:
            continue  # 🔴 FIX: Wait until frame is available

        # Convert frame to NumPy array
        frame_np = np.array(frame)

        # Run YOLOv8 Inference
        with torch.no_grad():
            results = model.track(frame_np, conf=0.5, persist=True)

        # Count persons detected
        person_count = sum(1 for obj in results[0].boxes.cls if int(obj) == 0)  # Class 0 = 'person'

        # Draw bounding boxes
        for i, box in enumerate(results[0].boxes.xyxy):
            if int(results[0].boxes.cls[i]) == 0:
                x1, y1, x2, y2 = map(int, box)
                cv2.rectangle(frame_np, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # Display person count
        cv2.putText(frame_np, f"People Count: {person_count}", (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)

        # Trigger Alert if crowd exceeds threshold
        if person_count >= crowd_threshold:
            threading.Thread(target=play_alert, daemon=True).start()
        else:
            stop_alert()

        # Show Video
        cv2.imshow("Crowd Control - YOLOv8", frame_np)

        # Exit if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            stop_threads = True  # Stop thread
            break

    # 🔴 **Release Resources Properly**
    camera.release()
    cv2.destroyAllWindows()
    pygame.mixer.quit()
    capture_thread.join()  # Ensure thread stops before exiting

