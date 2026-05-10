# src/history.py

import os
from src.constants import HISTORY_FILE

def ensure_history_file():
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "w", encoding="utf-8"):
            pass

def load_history():
    ensure_history_file()
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    return []

def save_to_history(city):
    history = load_history()
    if city in history:
        history.remove(city)
    history.insert(0, city)
    history = history[:30]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        for item in history:
            f.write(item + "\n")
