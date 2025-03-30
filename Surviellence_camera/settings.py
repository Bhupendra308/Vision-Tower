import json

CONFIG_PATH = "config/config.json"

def load_config():
    """Loads the configuration from JSON file"""
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def save_config(data):
    """Saves new configuration to JSON file"""
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=4)

# ✅ Load configuration once at startup
CONFIG = load_config()
