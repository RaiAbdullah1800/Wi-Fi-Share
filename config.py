import os
import json

PORT = 5000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.join(BASE_DIR, "shared_storage")
PUBLIC_DIR = os.path.join(BASE_DIR, "public")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

# Ensure required directories exist
os.makedirs(STORAGE_DIR, exist_ok=True)
os.makedirs(PUBLIC_DIR, exist_ok=True)

# Default Config
config = {
    "admin_password": "admin123"
}

def load_config():
    global config
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config.update(json.load(f))
        except Exception as e:
            print(f"Error loading config.json: {e}")
    else:
        save_config()

def save_config():
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Error saving config.json: {e}")

# Load initial configuration on module import
load_config()
