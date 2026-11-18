# ==========================================
# MEDIQ - HOPE CLINIC CHATBOT
# ==========================================
# MedIQ is the virtual medical assistant.
# Hope Clinic is the healthcare provider.
#
# Features:
# - Gemini-powered clinic FAQs
# - English, Swahili and Sheng responses
# - FAQ caching (through cache.py)
# - Basic conversation memory (memory.txt)
# - Guided appointment-request flow
# - Booking requests saved separately in bookings.json
# - Basic emergency keyword interruption
#
# IMPORTANT:
# This version records appointment REQUESTS locally.
# It does not connect to the clinic's live appointment calendar.
# A saved request is therefore PENDING clinic confirmation.

# Import required libraries
from google import genai
from google.genai import types
from dotenv import load_dotenv

import os
import re
import json
import uuid
from datetime import datetime, date, time

# Import caching functions from cache.py
from cache import get_cached, set_cache, is_cacheable


# ==========================================
# 1. FILE SETTINGS
# ==========================================

KNOWLEDGE_FILE = "knowledge.txt"
MEMORY_FILE = "memory.txt"
BOOKINGS_FILE = "bookings.json"

# Name shown to patients
ASSISTANT_NAME = "MedIQ"
CLINIC_NAME = "Hope Clinic"
CLINIC_PHONE = "0712 345 678"


# ==========================================
# 2. LOAD API KEY AND CONNECT TO GEMINI
# ==========================================

# Load environment variables from .env
load_dotenv()

# Get the Gemini API key.
# Your .env file should contain: api_key=YOUR_KEY
api_key = os.getenv("api_key")

if not api_key:
    raise ValueError("api_key not found. Check your .env file.")

# Connect to Gemini and retry temporary server errors.
client = genai.Client(
    api_key=api_key,
    http_options=types.HttpOptions(
        retry_options=types.HttpRetryOptions(
            attempts=5,
            initial_delay=1.0,
            max_delay=30.0
        )
    )
)

# ==========================================
# 3. LOAD THE CLINIC KNOWLEDGE BASE
# ==========================================

try:
    with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as file:
        knowledge = file.read()
except OSError:
    knowledge = "No knowledge base available."


# ==========================================
# 4. LOAD CONVERSATION MEMORY
# ==========================================

try:
    with open(MEMORY_FILE, "r", encoding="utf-8") as file:
        old_memory = file.read()
except OSError:
    old_memory = ""

    # Create the memory file if it does not exist
    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
        file.write("")

if not old_memory.strip():
    old_memory = "No previous conversation."


def save_memory(question, answer):
    """
    Save general FAQ conversation context.

    Do not call this function for booking steps because names,
    phone numbers and appointment details are personal information.
    Those details belong only in bookings.json.
    """
    global old_memory

    new_entry = (
        f"\npatient: {question}\n"
        f"{ASSISTANT_NAME}: {answer}\n"
    )

    old_memory += new_entry

    # Keep the memory file small
    old_memory = "\n".join(old_memory.splitlines()[-40:])

    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
        file.write(old_memory)


# ==========================================
# 5. CREATE THE GEMINI CHAT SESSION
# ==========================================

chat = client.chats.create(
    # Use the model that was available to your API key
    model="gemini-3.5-flash-lite",

    config=types.GenerateContentConfig(
        # Gemini must return JSON so Python can read its answer
        response_mime_type="application/json",

        # Keep answers focused and reasonably short
        temperature=0.2,
        max_output_tokens=300,

        # Instructions that guide MedIQ's behaviour
        system_instruction=f"""
You are {ASSISTANT_NAME}, the virtual medical assistant for
{CLINIC_NAME} in Westlands, Nairobi.

IDENTITY:
- Your name is MedIQ.
- You represent Hope Clinic.
- Introduce yourself as MedIQ, the virtual medical assistant
  for Hope Clinic when an introduction is appropriate.
- You are an AI assistant, not a doctor or human receptionist.

YOUR ROLE:
Help patients with clinic information, services, prices,
opening hours, doctors and appointment enquiries.

MEDICAL SAFETY:
- Never diagnose a disease or prescribe medication.
- Only a qualified clinician can diagnose a patient.
- Follow the clinic knowledge base for triage guidance.
- For emergency symptoms, advise immediate medical attention.
- Do not tell a patient to wait for a chat response in an emergency.

LANGUAGE:
- Communicate in English, Swahili or Sheng.
- Respond in the language used by the patient.
- Use simple, friendly and respectful language.

KNOWLEDGE BASE:
{knowledge}

PREVIOUS GENERAL CONVERSATION CONTEXT:
{old_memory}

IMPORTANT RULES:

1. Answer only what the patient has asked.
2. Keep responses short, clear and conversational.
3. Do not define medical terms or specialist roles unless the patient asks for an explanation.
4. Do not use filler phrases such as "Anyway, back to the clinic".
5. Do not give unnecessary clinic advertisements.
6. Do not repeat the clinic location or services unless relevant.
7. Never invent clinic prices, opening hours, services or doctor schedules.
8. Do not claim the clinic is open today unless verified.
9. Do not diagnose or prescribe medication.
10. For medical concerns, follow the triage guidance in the knowledge base.
11. Do not invent appointment confirmations or booking IDs.
12. Do not automatically ask every patient whether they want to book.
13. Discuss booking only when the patient shows interest.
14. If information is unavailable, politely direct the patient to call {CLINIC_PHONE}.
15. If a question is unrelated to medicine or Hope Clinic, do not answer it or provide additional information. Respond with:

"I can only assist with enquiries related to Hope Clinic. Our services include general consultations, dental care, laboratory tests, family planning, vaccinations and wound dressing. How may I help you with our clinic services today?"

Only list services recorded in the knowledge base.
16. Never reveal internal cache, memory, code or technical messages.
17. Only respond to medical-related questions and enquiries about Hope Clinic.

SPECIALIST REQUESTS:

18. If a patient requests a specialist who is not listed in the knowledge base, briefly explain that the clinic does not have that specialist listed.

19. Offer a general consultation as an alternative by asking:
"Would you like to book an appointment with a general doctor instead?"

20. Do not define specialist roles or list unrelated clinic services, prices or fees when responding to specialist requests.

21. Do not end a specialist-related response with a phone number or an instruction to call the clinic. Wait for the patient's response before proceeding with booking.
GREETING:
If the patient only greets you, respond briefly:
"Hello! Welcome to Hope Clinic. I'm MedIQ, your virtual medical
assistant. How may I help you today?"
Do not list all clinic services unless asked.

BOOKING:
Python handles the step-by-step booking-request process.
Do not collect patient names or phone numbers in a general FAQ response.
Do not claim a booking is confirmed unless a real clinic system confirms it.

OUTPUT FORMAT:
Return ONLY valid JSON in this structure:

{{
    "answer": "Your response to the patient",
    "faq_number": 1,
    "topic": "hours/location/services/prices/bookings/symptoms/others",
    "triage": "EMERGENCY/COME TODAY/CAN WAIT",
    "language": "english/swahili/sheng",
    "is_emergency": false
}}
"""
    )
)


# ==========================================
# 6. GREETING DETECTION
# ==========================================

def is_greeting(question):
    """Check for a message that is only a greeting."""
    greetings = [
        "hello", "hi", "hey",
        "good morning", "good afternoon", "good evening",
        "habari", "niaje", "sasa", "mambo",
        "hujambo", "salama", "hello mediq"
    ]

    return question.lower().strip().strip("!.?") in greetings


# ==========================================
# 7. EMERGENCY DETECTION
# ==========================================

def is_emergency(question):
    """
    Basic keyword screening based on the clinic knowledge base.

    This is not a complete medical triage system. Patients with
    severe or rapidly worsening symptoms should seek urgent care
    even if a phrase is not recognised here.
    """
    emergency_words = [
        "difficulty breathing",
        "cannot breathe",
        "can't breathe",
        "cant breathe",
        "shortness of breath",
        "chest pain",
        "maumivu ya kifua",
        "coughing blood",
        "vomiting blood",
        "heavy bleeding",
        "bleeding heavily",
        "pregnant and bleeding",
        "pregnancy bleeding",
        "mjamzito na damu",
        "snake bite",
        "snake bitten",
        "nyoka ameniuma",
        "fainting",
        "unconscious",
        "unresponsive",
        "seizure",
        "kifafa",
        "deep cut",
        "animal bite",
        "severe allergic reaction",
        "swollen face",
        "face is swelling",
        "blue lips",
        "head injury",
        "baby not breastfeeding",
        "baby not feeding",
        "baby is not moving"
    ]

    q = question.lower()
    return any(word in q for word in emergency_words)


# ==========================================
# 8. CLINIC QUESTION DETECTION
# ==========================================

def is_clinic_question(question):
    """Identify questions that are related to Hope Clinic."""
    clinic_words = [
        "hours", "open", "fungua", "funga", "close",
        "services", "huduma", "price", "pesa", "bei",
        "book", "booking", "appointment",
        "daktari", "doctor", "clinic", "hope clinic",
        "hope health", "wapi", "location", "address",
        "phone", "simu", "mpesa", "insurance", "sha",
        "chanjo", "kipimo", "meno", "dentist",
        "consultation", "lab test", "home visit",
        "mediq"
    ]

    q = question.lower()
    return any(word in q for word in clinic_words)


# ==========================================
# 9. BOOKING HELPER FUNCTIONS
# ==========================================

def normalise_phone(phone):
    """Remove spaces and common punctuation from a phone number."""
    return re.sub(r"[\s\-()]", "", phone)


def valid_kenyan_phone(phone):
    """Basic validation for common Kenyan mobile phone formats."""
    cleaned = normalise_phone(phone)
    return bool(
        re.fullmatch(r"0[17]\d{8}", cleaned)
        or re.fullmatch(r"\+254[17]\d{8}", cleaned)
        or re.fullmatch(r"254[17]\d{8}", cleaned)
    )


def load_bookings():
    """Load existing booking requests, or return an empty list."""
    try:
        with open(BOOKINGS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        return data if isinstance(data, list) else []

    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_booking(booking):
    """
    Save one booking request to bookings.json.

    This is local project storage, not a live clinic booking system.
    """
    bookings = load_bookings()
    bookings.append(booking)

    with open(BOOKINGS_FILE, "w", encoding="utf-8") as file:
        json.dump(bookings, file, indent=4, ensure_ascii=False)


def create_booking_id():
    """Create a unique booking request ID."""
    return "HHC-" + uuid.uuid4().hex[:8].upper()


def classify_service(message):
    """
    Identify the service category from the patient's response.
    Return None if the service is not clear.
    """
    q = message.lower()

    dental_words = [
        "dental", "dentist", "tooth", "teeth", "meno",
        "jino", "gum", "toothache"
    ]
    lab_words = [
        "lab", "test", "blood test", "malaria", "sugar",
        "typhoid", "urine", "kipimo"
    ]
    general_words = [
        "general", "consultation", "doctor", "daktari",
        "checkup", "check-up", "fever", "cough",
        "stomach", "headache", "sick", "unwell"
    ]
    other_words = [
        "vaccination", "vaccine", "chanjo",
        "family planning", "wound dressing",
        "home visit"
    ]

    if any(word in q for word in dental_words):
        return "Dental care"

    if any(word in q for word in lab_words):
        return "Lab test"

    if any(word in q for word in general_words):
        return "General consultation"

    if any(word in q for word in other_words):
        return "Other clinic service"

    return None


def is_booking_request(message):
    """Detect an explicit request to make an appointment."""
    q = message.lower()

    booking_phrases = [
        "i want to book",
        "i would like to book",
        "i'd like to book",
        "book an appointment",
        "make an appointment",
        "schedule an appointment",
        "can i book",
        "i need an appointment",
        "nataka ku-book",
        "nataka appointment",
        "ningependa kuweka appointment",
        "book for me"
    ]

    return any(phrase in q for phrase in booking_phrases)


def parse_appointment_date(message):
    """
    Parse an exact date supplied by the patient.
    Accepted examples: 2026-11-20, 20/11/2026, 20-11-2026.
    """
    value = message.strip()

    formats = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]

    for date_format in formats:
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            pass

    return None


def parse_appointment_time(message):
    """
    Accept different ways of entering time:
    11am, 11 AM, 11:00am, 11.00am, 14:00, etc.
    """

    value = message.strip().upper().replace(".", ":")

     # Add a space before AM or PM if the patient omitted it.
    # Example: 11:00AM becomes 11:00 AM.
    value = re.sub(r"(\d)(AM|PM)$", r"\1 \2", value)

    formats = [
        "%I:%M %p",
        "%I %p",
        "%H:%M"
    ]

    for time_format in formats:
        try:
            return datetime.strptime(value, time_format).time()
        except ValueError:
            continue

    return None


def clinic_hours_for(day):
    """
    Return the clinic's regular opening hours from the supplied
    Hope Clinic knowledge base.
    Monday-Friday: 8 AM-6 PM
    Saturday: 9 AM-2 PM
    Sunday: closed
    """
    weekday = day.weekday()

    if weekday <= 4:
        return time(8, 0), time(18, 0)

    if weekday == 5:
        return time(9, 0), time(14, 0)

    return None, None


def validate_appointment_schedule(service, doctor, appointment_date,
                                  appointment_time):
    """
    Check regular opening hours and the doctor schedules listed
    in the clinic knowledge base.

    This does NOT check whether a slot is already occupied.
    """
    opening, closing = clinic_hours_for(appointment_date)

    if opening is None:
        return False, "The clinic is closed on Sundays. Please choose another day."

    if not (opening <= appointment_time <= closing):
        return False, (
            "That time is outside the clinic's regular opening hours. "
            "Please choose another time during opening hours."
        )

    weekday = appointment_date.weekday()

    if service == "General consultation":
        if weekday > 4:
            return False, (
                "The listed general consultation doctors are available "
                "Monday to Friday. Please choose a weekday."
            )

        if doctor == "Dr Nancy":
            if not (time(9, 0) <= appointment_time <= time(13, 0)):
                return False, (
                    "Dr Nancy's listed consultation hours are "
                    "Monday to Friday, 9 AM to 1 PM."
                )

        elif doctor == "Dr Otieno":
            if not (time(14, 0) <= appointment_time <= time(18, 0)):
                return False, (
                    "Dr Otieno's listed consultation hours are "
                    "Monday to Friday, 2 PM to 6 PM."
                )

    if service == "Dental care":
        # Monday=0, Wednesday=2, Friday=4
        if weekday not in [0, 2, 4]:
            return False, (
                "The listed dental doctor, Dr Wanjiru, is available "
                "on Monday, Wednesday and Friday. Please choose one "
                "of those days."
            )

        if appointment_date <= date.today():
            return False, "Dental appointments should be arranged at least one day in advance."

    if appointment_date < date.today():
        return False, "That date has already passed. Please choose a future date."

    if appointment_date == date.today() and appointment_time <= datetime.now().time():
        return False, "That time has already passed. Please choose a later time."

    return True, ""


# ==========================================
# 10. BOOKING CONVERSATION STATE
# ==========================================

# booking_state tells Python which detail to ask for next.
# The booking process is handled by Python, not left to Gemini.
booking_state = None
booking_data = {}

# This becomes True when MedIQ has just asked whether the patient
# wants to book. It allows a short reply such as "yes" to start booking.
booking_offer_pending = False


def start_booking():
    """Start a fresh booking request."""
    global booking_state, booking_data, booking_offer_pending

    booking_state = "ASK_SERVICE"
    booking_data = {}
    booking_offer_pending = False

    return (
        "Of course! What service would you like to book?\n"
        "For example: general consultation, dental care, "
        "lab tests or another clinic service."
    )


def handle_booking_message(message):
    """
    Process one message according to the current booking state.
    Returns the response that MedIQ should show to the patient.
    """
    global booking_state, booking_data, booking_offer_pending

    q = message.strip()

    # Patient can cancel the booking at any stage
    if q.lower() in ["cancel", "cancel booking", "stop", "acha", "wacha"]:
        booking_state = None
        booking_data = {}
        return "No problem. I've stopped the booking request. How else may I help you?"

    # --------------------------------------
    # STEP 1: ASK FOR THE SERVICE
    # --------------------------------------
    if booking_state == "ASK_SERVICE":

        service = classify_service(q)

        if not service:
            return (
                "Which service do you need?\n"
                "You can say general consultation, dental care, "
                "lab tests or another clinic service."
            )

        booking_data["service"] = service

        # General consultation: patient may choose between doctors
        if service == "General consultation":
            booking_state = "ASK_DOCTOR"
            return (
                "Do you have a preferred doctor?\n"
                "Dr Nancy (Monday-Friday, 9 AM-1 PM), "
                "Dr Otieno (Monday-Friday, 2 PM-6 PM), "
                "or no preference?"
            )

        # Dental care has one listed dentist
        if service == "Dental care":
            booking_data["doctor"] = "Dr Wanjiru"
            booking_state = "ASK_DATE"
            return (
                "Dental appointments are with Dr Wanjiru "
                "on Mondays, Wednesdays and Fridays, and should "
                "be arranged at least one day in advance.\n"
                "What date would you prefer? Please use DD/MM/YYYY."
            )

        # Lab tests do not need a doctor selection in this flow
        if service == "Lab test":
            booking_data["doctor"] = "Not applicable"
            booking_state = "ASK_DATE"
            return (
                "Which lab test would you like? "
                "For example, malaria, blood sugar, typhoid or urine test."
            )

        # Other services may have their own arrangements
        booking_data["doctor"] = "To be confirmed by clinic"
        booking_state = "ASK_DATE"
        return (
            "What date would you prefer? Please use DD/MM/YYYY. "
            "The clinic will confirm the arrangements for this service."
        )

    # --------------------------------------
    # STEP 2: ASK FOR THE DOCTOR
    # --------------------------------------
    if booking_state == "ASK_DOCTOR":
        q_lower = q.lower()

        if "nancy" in q_lower:
            doctor = "Dr Nancy"
        elif "otieno" in q_lower:
            doctor = "Dr Otieno"
        elif any(word in q_lower for word in ["no preference", "any", "either", "whoever"]):
            doctor = "No preference"
        else:
            return (
                "Please choose Dr Nancy, Dr Otieno, or say "
                "'no preference'."
            )

        booking_data["doctor"] = doctor
        booking_state = "ASK_DATE"

        return "Which date would you prefer? Please use DD/MM/YYYY."

    # --------------------------------------
    # STEP 3: ASK FOR DATE
    # --------------------------------------
    if booking_state == "ASK_DATE":

        # For lab tests, first capture which test they need
        if booking_data.get("service") == "Lab test" and "test" not in booking_data:
            booking_data["test"] = q
            return "Which date would you prefer? Please use DD/MM/YYYY."

        appointment_date = parse_appointment_date(q)

        if not appointment_date:
            return (
                "Please enter the date in DD/MM/YYYY format, "
                "for example 20/11/2026."
            )

        if appointment_date < date.today():
            return "That date has already passed. Please choose a future date."

        if appointment_date.weekday() == 6:
            return "The clinic is closed on Sundays. Please choose another date."

        booking_data["date"] = appointment_date.isoformat()
        booking_state = "ASK_TIME"

        return "What time would you prefer? For example, 10:00 AM."

    # --------------------------------------
    # STEP 4: ASK FOR TIME
    # --------------------------------------
    if booking_state == "ASK_TIME":

        appointment_time = parse_appointment_time(q)

        if not appointment_time:
            return (
                "Please enter a time such as 10:00 AM, 2:00 PM "
                "or 14:00."
            )

        appointment_date = date.fromisoformat(booking_data["date"])
        service = booking_data["service"]
        doctor = booking_data.get("doctor", "")

        # If the patient has no doctor preference, select the
        # doctor whose listed hours match the chosen time.
        if service == "General consultation" and doctor == "No preference":
            if time(9, 0) <= appointment_time <= time(13, 0):
                doctor = "Dr Nancy"
            elif time(14, 0) <= appointment_time <= time(18, 0):
                doctor = "Dr Otieno"
            else:
                return (
                    "The general consultation doctors' listed hours are "
                    "9 AM-1 PM for Dr Nancy and 2 PM-6 PM for Dr Otieno. "
                    "Please choose a time within those hours."
                )

            booking_data["doctor"] = doctor

        valid, reason = validate_appointment_schedule(
            service,
            doctor,
            appointment_date,
            appointment_time
        )

        if not valid:
            return reason + " Please enter another time."

        booking_data["time"] = appointment_time.strftime("%I:%M %p")
        booking_state = "ASK_NAME"

        return "Thank you. May I have the patient's full name?"

    # --------------------------------------
    # STEP 5: ASK FOR PATIENT NAME
    # --------------------------------------
    if booking_state == "ASK_NAME":

        if len(q.split()) < 2 or len(q) < 5:
            return "Please enter the patient's full name."

        booking_data["name"] = q
        booking_state = "ASK_PHONE"

        return "Thank you. What phone number can the clinic use to contact you?"

    # --------------------------------------
    # STEP 6: ASK FOR PHONE NUMBER
    # --------------------------------------
    if booking_state == "ASK_PHONE":

        if not valid_kenyan_phone(q):
            return (
                "That phone number doesn't look valid. "
                "Please enter a Kenyan mobile number, for example 0712345678."
            )

        booking_data["phone"] = normalise_phone(q)

        # Prepare the summary for the patient's review
        summary = (
            "Please review your appointment request:\n\n"
            f"Name: {booking_data['name']}\n"
            f"Phone: {booking_data['phone']}\n"
            f"Service: {booking_data['service']}\n"
            f"Doctor: {booking_data.get('doctor', 'To be confirmed')}\n"
            f"Date: {booking_data['date']}\n"
            f"Time: {booking_data['time']}\n"
        )

        if "test" in booking_data:
            summary += f"Lab test: {booking_data['test']}\n"

        summary += (
            "\nWould you like me to submit this request? "
            "Please reply YES or NO."
        )

        booking_state = "CONFIRM"
        return summary

    # --------------------------------------
    # STEP 7: CONFIRM OR REJECT REQUEST
    # --------------------------------------
    if booking_state == "CONFIRM":

        answer = q.lower().strip()

        if answer in ["yes", "y", "ndio", "ndio kabisa", "sawa"]:
            booking_id = create_booking_id()

            booking_record = {
                "booking_id": booking_id,
                "name": booking_data["name"],
                "phone": booking_data["phone"],
                "service": booking_data["service"],
                "doctor": booking_data.get("doctor", "To be confirmed"),
                "date": booking_data["date"],
                "time": booking_data["time"],
                "lab_test": booking_data.get("test"),
                "status": "PENDING_CLINIC_CONFIRMATION",
                "date_saved": datetime.now().isoformat(timespec="seconds")
            }

            save_booking(booking_record)

            # Clear the current booking state after saving
            booking_state = None
            booking_data = {}

            return (
                f"Thank you. Your appointment request has been recorded.\n"
                f"Request ID: {booking_id}\n\n"
                "Your appointment is NOT confirmed yet. The clinic needs "
                "to verify availability and contact you. You can also call "
                f"{CLINIC_PHONE} for follow-up."
            )

        if answer in ["no", "n", "hapana", "cancel"]:
            booking_state = None
            booking_data = {}
            return (
                "No problem. I have not submitted the request. "
                "How else may I help you?"
            )

        return "Please reply YES to submit the request or NO to cancel it."

    return "How may I help you today?"


# ==========================================
# 11. START MEDIQ
# ==========================================

print("\nMedIQ - Hope Clinic")
print("Your Virtual Medical Assistant")
print("Type 'exit' to end the conversation.\n")

print(
    "MedIQ: Hello! Welcome to Hope Clinic. "
    "I'm MedIQ, your virtual medical assistant. "
    "How may I help you today?"
)
print("-" * 50)


# ==========================================
# 12. MAIN CHATBOT LOOP
# ==========================================

while True:

    # Receive a message from the patient
    question = input("you: ").strip()

    # Stop the chatbot when the patient types exit
    if question.lower() == "exit":
        print("MedIQ: Take care! / Kuwa na afya njema!")
        break

    # Ignore empty messages
    if not question:
        continue

    # --------------------------------------
    # A. CHECK FOR EMERGENCIES FIRST
    # --------------------------------------
    # Emergency concerns interrupt any booking flow.
    if is_emergency(question):

        booking_state = None
        booking_data = {}
        booking_offer_pending = False

        answer = (
            "This may be a medical emergency. Please seek immediate "
            "medical attention at the nearest emergency department. "
            "Do not wait for a chat response. You may also call "
            f"{CLINIC_NAME} on {CLINIC_PHONE} for guidance."
        )

        print(f"MedIQ: {answer}")

        # Do not save emergency messages or answers in the FAQ cache.
        # Do not save possible patient health details in general memory.
        print("-" * 50)
        continue

    # --------------------------------------
    # B. HANDLE AN ACTIVE BOOKING
    # --------------------------------------
    # While booking_state is active, send the message to the
    # Python booking flow instead of Gemini or the FAQ cache.
    if booking_state is not None:

        answer = handle_booking_message(question)
        print(f"MedIQ: {answer}")

        # Booking information is not written to memory.txt or cache.json.
        print("-" * 50)
        continue

    # --------------------------------------
    # C. START A BOOKING
    # --------------------------------------
    if is_booking_request(question):

        answer = start_booking()
        print(f"MedIQ: {answer}")
        print("-" * 50)
        continue

    # If MedIQ's previous reply asked whether the patient wanted
    # to book, a simple "yes" starts the booking process.
    yes_replies = ["yes", "yeah", "yep", "ndio", "sawa", "okay", "ok"]

    if booking_offer_pending and question.lower().strip("!.?") in yes_replies:
        answer = start_booking()
        print(f"MedIQ: {answer}")
        print("-" * 50)
        continue

    # A clear "no" answers the pending booking offer without
    # starting a booking.
    if booking_offer_pending and question.lower().strip("!.?") in [
        "no", "no thanks", "hapana"
    ]:
        booking_offer_pending = False
        answer = "No problem. How else may I help you?"
        print(f"MedIQ: {answer}")
        print("-" * 50)
        continue

    # --------------------------------------
    # D. HANDLE GREETINGS
    # --------------------------------------
    if is_greeting(question):

        answer = (
            "Hello! Welcome to Hope Clinic. I'm MedIQ, "
            "your virtual medical assistant. How may I help you today?"
        )

        print(f"MedIQ: {answer}")
        booking_offer_pending = False
        print("-" * 50)
        continue

    # Any message other than a direct YES/NO answer means the
    # previous booking offer is no longer awaiting a reply.
    booking_offer_pending = False

    # --------------------------------------
    # E. CHECK THE FAQ CACHE
    # --------------------------------------
    # Only stable, non-personal FAQ answers should be cacheable.
    # Booking questions must be excluded in cache.py as well.
    if is_cacheable(question):

        cached = get_cached(question)

        if cached:
            print(f"MedIQ: {cached}")

            # A cached FAQ may contain a booking invitation.
            booking_offer_pending = bool(
                re.search(r"\b(would you like to book|do you want to book|"
                          r"would you like an appointment)\b",
                          cached.lower())
            )

            save_memory(question, cached)
            print("-" * 50)
            continue

    # --------------------------------------
    # F. SEND THE QUESTION TO GEMINI
    # --------------------------------------
    try:

        was_clinic = is_clinic_question(question)

        if was_clinic:
            prompt = question
        else:
            prompt = f"""
The patient has asked an unrelated question:

{question}

Answer briefly and politely, then gently redirect the conversation
to Hope Clinic. Follow the required JSON output format.
"""

        # Send the question to Gemini
        response = chat.send_message(prompt).text

        # Remove code fences if Gemini adds them
        clean = response.replace("```json", "").replace("```", "").strip()

        # Convert the JSON response into a Python dictionary
        data = json.loads(clean)

        # Get the patient-facing answer
        answer = data.get(
            "answer",
            "Sorry, I could not understand that. Please try again."
        )

        # If Gemini returns an emergency flag, advise urgent care.
        if data.get("is_emergency") is True or data.get("triage") == "EMERGENCY":
            answer = (
                "This may be a medical emergency. Please seek immediate "
                "medical attention at the nearest emergency department. "
                "Do not wait for a chat response. You may also call "
                f"{CLINIC_NAME} on {CLINIC_PHONE} for guidance."
            )

        print(f"MedIQ: {answer}")

        # Detect whether Gemini has asked if the patient wants to book.
        # This makes a short reply such as "yes" meaningful next turn.
        booking_offer_pending = bool(
            re.search(
                r"\b(would you like to book|do you want to book|"
                r"would you like an appointment|shall i book)\b",
                answer.lower()
            )
        )

        # Save safe FAQ context only.
        # Avoid saving symptom/health conversations in general memory.
        if data.get("triage") not in ["EMERGENCY", "COME TODAY"]:
            if is_cacheable(question):
                set_cache(question, answer)

            save_memory(question, answer)

    # --------------------------------------
    # G. HANDLE ERRORS
    # --------------------------------------
    except Exception as error:

        print(
            "MedIQ: Sorry, I'm having a problem responding right now. "
            f"Please try again or call {CLINIC_PHONE}."
        )

        # Technical details are for the developer, not the patient.
        print("Developer error:", error)

        booking_offer_pending = False

    print("-" * 50)
