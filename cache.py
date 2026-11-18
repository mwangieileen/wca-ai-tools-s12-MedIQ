
import json
import os
import time

# Define the name of the file that stores cached responses
CACHE_FILE = "cache.json"

# Set how long a cached answer should remain valid (30 days)
CACHE_EXPIRY = 30 * 24 * 60 * 60


def load_cache():
    # Check whether the cache file already exists
    if not os.path.exists(CACHE_FILE):
        # If it does not exist, return an empty dictionary
        return {}

    try:
        # Open the cache file in read mode
        with open(CACHE_FILE, "r", encoding="utf-8") as file:

            # Read the JSON data and convert it into a Python dictionary
            cache = json.load(file)

            # Return the loaded cache data
            return cache

    except (json.JSONDecodeError, OSError):
        # If the file is empty, corrupted or cannot be opened,
        # return an empty dictionary instead of crashing
        return {}


def save_cache(cache):
    # Open the cache file in write mode
    with open(CACHE_FILE, "w", encoding="utf-8") as file:

        # Convert the Python dictionary into JSON
        # indent=4 makes the file easier to read
        json.dump(cache, file, indent=4)


def get_cached(question):
    # Load all previously saved cached responses
    cache = load_cache()

    # Convert the question to lowercase and remove extra spaces
    # This helps match questions regardless of capitalization
    question_key = question.lower().strip()

    # Check whether this question exists in the cache
    if question_key not in cache:
        # Return None when no cached answer is available
        return None

    # Retrieve the saved answer and its timestamp
    cached_item = cache[question_key]

    # Get the time when the answer was originally cached
    saved_time = cached_item.get("timestamp", 0)

    # Calculate how much time has passed since the answer was cached
    current_time = time.time()
    elapsed_time = current_time - saved_time

    # Check whether the cached answer has exceeded its expiry period
    if elapsed_time > CACHE_EXPIRY:

        # Delete the expired answer from the cache
        del cache[question_key]

        # Save the cache after removing the expired answer
        save_cache(cache)

        # Return None so the chatbot can get a fresh answer
        return None

    # Return the cached answer if it is still valid
    return cached_item.get("answer")


def set_cache(question, answer):
    # Load the existing cache before adding a new answer
    cache = load_cache()

    # Standardize the question by converting it to lowercase
    # and removing unnecessary spaces
    question_key = question.lower().strip()

    # Store the answer and the time it was saved
    cache[question_key] = {
        "answer": answer,
        "timestamp": time.time()
    }

    # Save the updated cache to the JSON file
    save_cache(cache)


def is_cacheable(question):
    # Convert the question to lowercase for easier comparison
    q = question.lower().strip()

    # List keywords related to medical questions
    # These questions should always receive fresh handling
    medical_keywords = [
        "pain", "ache", "fever", "homa", "cough",
        "bleeding", "damu", "pregnant", "mjamzito",
        "medicine", "dawa", "symptom", "diagnosis",
        "treatment", "sick", "ill", "diarrhoea",
        "diarrhea", "vomiting", "kutapika",
        "kuharisha", "injury", "wound", "snake",
        "nyoka", "bite", "emergency", "dharura",
        "breathing", "seizure", "kifafa",
        "blood", "swelling", "headache", "malaria",
        "typhoid", "diabetes", "child", "baby"
    ]

    # List keywords related to bookings
    # Booking requests must not be stored as general FAQ responses
    booking_keywords = [
        "book", "booking", "appointment",
        "cancel", "reschedule", "my booking",
        "ku-book", "ku-cancel", "booking yangu"
    ]

    # Check whether the question contains any medical keywords
    if any(word in q for word in medical_keywords):
        return False

    # Check whether the question contains any booking keywords
    if any(word in q for word in booking_keywords):
        return False

    # List stable clinic FAQ topics that are safe to cache
    allowed_topics = [
        "opening hours",
        "what time do you open",
        "what time do you close",
        "location",
        "address",
        "where are you",
        "where is the clinic",
        "services",
        "what services do you offer",
        "consultation price",
        "consultation cost",
        "dental checkup price",
        "dental cleaning price",
        "malaria test price",
        "blood sugar test price",
        "typhoid test price",
        "urine test price",
        "mpesa till",
        "accept sha",
        "payment methods",
        "how much is consultation",
        "how much does consultation cost",
        "do you accept cash"
    ]

    # Return True if the question matches a stable FAQ topic
    # Otherwise, return False
    return any(topic in q for topic in allowed_topics)
