import os
import json
import toml
from typing import Dict, List

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.toml")

def get_api_key() -> str:
    """
    Reads the Perplexity API key from environment variables or config.toml.
    """
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if api_key:
        return api_key

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = toml.load(f)
        api_key = cfg.get("PERPLEXITY_API_KEY")
        if api_key and api_key != "YOUR_API_KEY_HERE":
            return api_key
    except FileNotFoundError:
        pass

    raise ValueError(
        "API key not found. Please set PERPLEXITY_API_KEY env or add it to config.toml."
    )

def get_twitter_credentials() -> Dict[str, str]:
    """
    Load/export Twitter credentials. Priority: env vars then config.toml.
    Exports any found credentials into os.environ for downstream code (CI-friendly).
    """
    keys = [
        "TWITTER_API_KEY",
        "TWITTER_API_SECRET",
        "TWITTER_ACCESS_TOKEN",
        "TWITTER_ACCESS_TOKEN_SECRET",
    ]
    creds = {}

    for k in keys:
        v = os.environ.get(k)
        if v:
            creds[k] = v

    if len(creds) != len(keys):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = toml.load(f) or {}
        except FileNotFoundError:
            cfg = {}

        for k in keys:
            if k not in creds and k in cfg:
                creds[k] = cfg[k]

    for k, v in creds.items():
        os.environ.setdefault(k, v)

    return creds

def load_sources(path: str = None) -> List[str]:
    """
    Load list of news domains from sources.json (project root by default).
    """
    if path is None:
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sources.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
