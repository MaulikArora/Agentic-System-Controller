import json
from pathlib import Path


CONFIG_PATH = Path(__file__).resolve().parent / "config.json"


def load_config():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Missing config file: {CONFIG_PATH}")

    with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
        return json.load(config_file)


def get_spotify_config():
    config = load_config()
    spotify_config = config.get("spotify", {})

    client_id = spotify_config.get("client_id")
    client_secret = spotify_config.get("client_secret")
    redirect_uri = spotify_config.get("redirect_uri", "http://127.0.0.1:8888/callback")

    if not client_id or not client_secret:
        raise ValueError("Spotify client_id and client_secret must be set in config.json")

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
    }


def get_wakeword_config():
    config = load_config()
    wakeword_config = config.get("wakeword", {})
    phrases = wakeword_config.get("phrases", ["koro"])
    normalized_phrases = []

    for phrase in phrases:
        if isinstance(phrase, str):
            normalized_phrases.append({
                "text": phrase,
                "threshold": wakeword_config.get("threshold", 0.4),
            })
        else:
            normalized_phrases.append({
                "text": phrase.get("text", ""),
                "threshold": phrase.get("threshold", wakeword_config.get("threshold", 0.4)),
            })

    return {
        "name": wakeword_config.get("name", "koro"),
        "engine": wakeword_config.get("engine", "openwakeword"),
        "threshold": wakeword_config.get("threshold", 0.4),
        "cooldown_seconds": wakeword_config.get("cooldown_seconds", 3),
        "consecutive_matches": wakeword_config.get("consecutive_matches", 1),
        "negative_margin": wakeword_config.get("negative_margin", 0.08),
        "phrases": normalized_phrases,
    }


def get_assistant_name():
    config = load_config()
    assistant_config = config.get("assistant", {})
    wakeword_config = config.get("wakeword", {})

    return assistant_config.get("name", wakeword_config.get("name", "koro"))


def get_llm_config():
    config = load_config()
    llm_config = config.get("llm", {})

    return {
        "intent_model": llm_config.get("intent_model", llm_config.get("model", "qwen2:0.5b")),
        "intent_temperature": llm_config.get("intent_temperature", 0),
        "intent_max_tokens": llm_config.get("intent_max_tokens", 60),
        "response_model": llm_config.get("response_model", llm_config.get("model", "qwen2:0.5b")),
        "response_temperature": llm_config.get("response_temperature", 0.55),
        "response_max_tokens": llm_config.get("response_max_tokens", 140),
        "keep_alive": llm_config.get("keep_alive", "10m"),
    }
