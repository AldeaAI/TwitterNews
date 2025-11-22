import json
from datetime import datetime, timedelta
from typing import List, Dict
import os

HISTORY_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "post_history.json")

def load_history() -> List[Dict]:
    """
    Loads post history and purges entries older than 7 days.
    """
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            history = json.load(f)
    except FileNotFoundError:
        return []

    one_week_ago = datetime.now() - timedelta(days=7)
    fresh = [item for item in history if datetime.fromisoformat(item["date"]) > one_week_ago]

    if len(fresh) != len(history):
        with open(HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(fresh, f, indent=4)

    return fresh

def save_history(url: str, history: List[Dict]) -> None:
    """
    Append a new entry to history and persist.
    """
    new_entry = {"url": url, "date": datetime.now().isoformat()}
    history.append(new_entry)
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4)
