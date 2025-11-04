import os
import json

CONFIG_FILE = os.getenv("BOT_CONFIG_PATH", "config.json")

SUPPORTED_LANGS = []
CONFIG = None

class Config:
    def __init__(self, data):
        self.default_rate_limit = data.get("default_rate_limit", 5)
        self.reaction_timeout = data.get("reaction_timeout", 300)

def load_config():
    global CONFIG, SUPPORTED_LANGS
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        CONFIG = Config(data)
        SUPPORTED_LANGS = data.get("supported_langs", [])
        print("✅ Config loaded.")
    except Exception as e:
        print(f"⚠️ Failed to load config: {e}")
        CONFIG = Config({})
        SUPPORTED_LANGS = ["en"]

load_config()