import json
import os
import time

CACHE_FILE = "cache.json"
CACHE = {}

def load_cache():
    global CACHE
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                CACHE = json.load(f)
        except:
            CACHE = {}
    return CACHE

def save_cache():
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(CACHE, f, indent=2)

def get(key):
    load_cache()
    key = key.lower().strip()
    if key in CACHE:
        item = CACHE[key]
        # Check if expired
        if time.time() - item["time"] < item["ttl"]:
            print(f"[CACHE HIT] {key}")
            return item["value"]
        else:
            del CACHE[key]
            save_cache()
    return None

def set(key, value, ttl=3600):
    load_cache()
    key = key.lower().strip()
    CACHE[key] = {
        "value": value,
        "time": time.time(),
        "ttl": ttl
    }
    save_cache()
    print(f"[CACHE SAVED] {key}")
    return value

def clear():
    global CACHE
    CACHE = {}
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
    print("Cache cleared")

def stats():
    load_cache()
    return {"total_saved": len(CACHE), "keys": list(CACHE.keys())}

# Load on start
load_cache()