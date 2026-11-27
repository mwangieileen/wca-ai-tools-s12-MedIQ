# cache.py
# MedIQ - Response Caching
# Stores and retrieves previously answered questions.
# This helps reduce response time, API calls and API usage costs.

import json  # Used to read and write JSON files
import re    # Used to clean and standardise questions


# File where cached questions and answers are stored
CACHE_FILE = "cache.json"


# Load previously saved questions and answers
def _load():
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        # Ensure the loaded data is a dictionary
        return data if isinstance(data, dict) else {}

    # Return an empty dictionary if the file is missing
    # or contains invalid JSON
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


# Save questions and answers to the cache file
def _save(data):
    with open(CACHE_FILE, "w", encoding="utf-8") as file:

        # indent=4 makes the JSON file easier to read
        # ensure_ascii=False preserves special characters
        json.dump(data, file, indent=4, ensure_ascii=False)


# Standardise questions before searching or saving them
# Converts text to lowercase and removes unnecessary spaces
# Example: "  Clinic HOURS  " becomes "clinic hours"
def _normalise(question):
    return re.sub(r"\s+", " ", question.lower().strip())


# Check whether a question already has a cached answer
def get_cached(question):
    data = _load()

    # Return the saved answer if it exists
    # Otherwise, return None
    return data.get(_normalise(question))


# Store a new question and its answer in the cache
def set_cache(question, answer):
    data = _load()

    # Use the standardised question as the dictionary key
    data[_normalise(question)] = answer

    # Save the updated cache to cache.json
    _save(data)


# Determine whether a question is suitable for caching
# Personal, medical and booking-related questions should
# receive fresh responses instead of reused answers
def is_cacheable(question):
    q = question.lower().strip()

    # Keywords used to exclude certain questions from caching
    not_cacheable = [

        # Appointment and booking-related questions
        "book", "booking", "appointment",

        # Personal information
        "my name", "name is", "i'm ", "i am ",

        # Phone numbers and contact information
        "phone", "071", "072", "073", "074",
        "075", "076", "077", "078", "079", "254",

        # Personal health concerns
        "i have", "i feel", "my child", "mtoto",

        # Symptoms and potentially urgent medical concerns
        "cough", "fever", "headache", "pain", "symptom",
        "sick", "unwell", "bleeding", "chest",

        # Doctor-related questions
        "nancy", "otieno", "wanjiru",

        # Appointment times and conversation-specific replies
        "am", "pm", "yes", "no", "ndio", "hapana",

        # Courtesy messages
        "thank you", "thanks"
    ]

    # Reject questions containing any excluded keyword
    if any(word in q for word in not_cacheable):
        return False

    # Reject single-word questions or replies because
    # they may depend on previous conversation messages
    if len(q.split()) < 2:
        return False

    # Allow caching if the question passes all checks
    return True