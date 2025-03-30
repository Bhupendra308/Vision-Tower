import paho.mqtt.client as mqtt
import pygame
import os

# ✅ Disable Pygame's video system (fix for headless environments)
os.environ["SDL_VIDEODRIVER"] = "dummy"

# ✅ MQTT Setup
MQTT_BROKER = "test.mosquitto.org"
MQTT_TOPIC = "crowd/alert"

pygame.mixer.init()
pygame.mixer.music.load("alarm.mp3")

def on_message(client, userdata, msg):
    """Play sound when alert received"""
    print(f"📩 Received Alert: {msg.payload.decode()}")
    pygame.mixer.music.play()

mqtt_client = mqtt.Client()
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, 1883, 60)
mqtt_client.subscribe(MQTT_TOPIC)

print("📡 Waiting for Crowd Alerts...")

mqtt_client.loop_forever()  # Keep Listening
