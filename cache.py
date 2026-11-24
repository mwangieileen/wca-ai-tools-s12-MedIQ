import json
import os
import re

CACHE_FILE = "cache.json"

def _load():
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def _save(data):
    with open(CACHE_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

def _normalise(question):
    return re.sub(r"\s+", " ", question.lower().strip())

def get_cached(question):
    data = _load()
    return data.get(_normalise(question))

def set_cache(question, answer):
    data = _load()
    data[_normalise(question)] = answer
    _save(data)

def is_cacheable(question):
    q = question.lower().strip()

    not_cacheable = [
        "book", "booking", "appointment",
        "my name", "name is", "i'm ", "i am ",
        "phone", "071", "072", "073", "074",
        "075", "076", "077", "078", "079", "254",
        "i have", "i feel", "my child", "mtoto",
        "cough", "fever", "headache", "pain", "symptom",
        "sick", "unwell", "bleeding", "chest",
        "nancy", "otieno", "wanjiru",
        "am", "pm", "yes", "no", "ndio", "hapana",
        "thank you", "thanks"
    ]

    if any(word in q for word in not_cacheable):
        return False

    if len(q.split()) < 2:
        return False

    return True
    if any(word in q for word in not_cacheable):
        return False
    if len(q.split()) < 2:
        return False
    return True