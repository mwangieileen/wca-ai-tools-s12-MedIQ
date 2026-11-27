# main.py
# MedIQ - Hope Clinic - Virtual Medical Assistant
# Menu: 1. New session, 2. Past session, 3. View bookings, 4. Exit
# Language: English / Swahili / Sheng
# Conversation Memory: FULL list of messages sent with EVERY API call - supports at least 4 turns
# Saved Session: full conversation + summary saved to sessions/session_DATE.md + .json

# Import the OpenAI client used for chat responses and session summaries.
from openai import OpenAI
# Load environment variables from the .env file.
from dotenv import load_dotenv
# Access environment variables and handle file-related operations.
import os
# Use regular expressions for phone validation and text matching.
import re
# Read and write booking records in JSON format.
import json
# Generate unique appointment reference IDs.
import uuid
# Test connectivity to the OpenAI server.
import socket
# Work with appointment dates, times and timestamps.
from datetime import datetime, date, time
# Import functions for checking, retrieving and saving cached answers.
from cache import get_cached, set_cache, is_cacheable
# Import the instructions used for chat responses and summaries.
from system_propmt import build_system_prompt, SUMMARY_PROMPT
# Import session history, storage and retrieval functions.
from session import Session, list_saved_sessions, load_saved_session, save_to_memory_file

# Define the local files used for clinic information, memory and bookings.
KNOWLEDGE_FILE = "knowledge.txt"
MEMORY_FILE = "memory.txt"
BOOKINGS_FILE = "bookings.json"

# Set the assistant identity and clinic contact details.
ASSISTANT_NAME = "MedIQ"
CLINIC_NAME = "Hope Clinic"
CLINIC_PHONE = "0712 345 678"

# Load configuration before reading the API key.
load_dotenv()

# Read the secret API key from the environment rather than hardcoding it.
api_key = os.getenv("OPENAI_API_KEY")

# Stop startup if the required API key is missing.
if not api_key:
    raise ValueError("OPENAI_API_KEY not found. Check your .env file.")

# Create the client used for OpenAI requests.
client = OpenAI(api_key=api_key)

# Read the clinic knowledge base; use a fallback if it cannot be opened.
try:
    with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as file:
        knowledge = file.read()
except OSError:
    knowledge = "No knowledge base available."

# Load previous conversation memory, or create an empty file if needed.
try:
    with open(MEMORY_FILE, "r", encoding="utf-8") as file:
        old_memory = file.read()
except OSError:
    old_memory = ""
    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
        file.write("")

# Remove an old placeholder from the memory file.
if old_memory.strip() == "No previous conversation.":
    old_memory = ""
    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
        file.write("")
# Preserve actual conversation lines if they follow the placeholder.
if old_memory.strip().startswith("No previous conversation."):
    lines = old_memory.splitlines()
    if len(lines) > 1:
        old_memory = "\n".join(lines[1:]).strip()
        with open(MEMORY_FILE, "w", encoding="utf-8") as file:
            file.write(old_memory)
# Supply a readable default when there is no previous conversation.
if not old_memory.strip():
    old_memory = "No previous conversation."

# Use English as the initial language until the user selects another.
selected_language = "English"

# Store menu labels, greetings and connectivity messages for each language.
TEXT = {
    "English": {
        "welcome": "MedIQ - Hope Clinic\nYour Virtual Medical Assistant",
        "choose": "\nPlease choose an option:",
        "new": "1. New session",
        "past": "2. Past session",
        "bookings": "3. View bookings",
        "exit": "4. Exit",
        "enter": "Enter choice (1-4): ",
        "greeting": "Hello! Welcome to Hope Clinic. I'm MedIQ, your virtual medical assistant. How may I help you today?",
        "back": "Type 'exit' to go back to menu.",
        "ended": "Session ended. Returning to menu.",
        "bye": "Thank you for contacting Hope Clinic.Have a great day!",
        "invalid": "Please enter 1, 2, 3 or 4.",
        "no_internet": "No internet connection. Please connect to internet to continue.",
        "retry": "Press Enter to try again, or type 'exit' to go back to menu: ",
        "internet_back": "Internet connected. You can now continue."
    },
    "Swahili": {
        "welcome": "MedIQ - Hope Clinic\nMsaidizi Wako wa Kiwirtuali",
        "choose": "\nTafadhali chagua:",
        "new": "1. Kikao kipya",
        "past": "2. Kikao kilichopita",
        "bookings": "3. Angalia bookings",
        "exit": "4. Toka",
        "enter": "Weka chaguo (1-4): ",
        "greeting": "Habari! Karibu Hope Clinic. Mimi ni MedIQ, msaidizi wako. Ninaweza kukusaidiaje leo?",
        "back": "Andika 'exit' kurudi kwa menu.",
        "ended": "Kikao kimeisha. Narudi kwa menu.",
        "bye": "Kuwa na afya njema!",
        "invalid": "Tafadhali weka 1, 2, 3 au 4.",
        "no_internet": "Hakuna mtandao. Tafadhali ungana na mtandao ili kuendelea. MedIQ haiwezi kufanya kazi bila mtandao.",
        "retry": "Bonyeza Enter kujaribu tena, au andika 'exit' kurudi kwa menu: ",
        "internet_back": "Mtandao umerudi. Sasa unaweza kuendelea."
    },
    "Sheng": {
        "welcome": "MedIQ - Hope Clinic\nMsaidizi Wako",
        "choose": "\nChagua beste:",
        "new": "1. Session mpya",
        "past": "2. Session ilipita",
        "bookings": "3. Angalia bookings",
        "exit": "4. Toka",
        "enter": "Weka chaguo (1-4): ",
        "greeting": "Sasa beste! Karibu Hope Clinic. Mimi ni MedIQ. Nikusaidie aje leo?",
        "back": "Andika 'exit' kurudi kwa menu.",
        "ended": "Session imeisha. Narudi kwa menu.",
        "bye": "Stay fiti beste!",
        "invalid": "Weka 1, 2, 3 ama 4.",
        "no_internet": "Hakuna net beste. Connect kwa net ndio tuendelee. MedIQ haiwezi kufanya kazi bila net.",
        "retry": "Bonyeza Enter kujaribu tena, ama andika 'exit' kurudi kwa menu: ",
        "internet_back": "Net imerudi. Sasa unaweza kuendelea."
    }
}

# Store translated booking questions, validation messages and confirmation templates.
BOOKING_TEXT = {
    "English": {
        "ask_service": "Of course! What service would you like to book?\nFor example: general consultation, dental care, lab tests or another clinic service.",
        "ask_doctor": "Do you have a preferred doctor?\nDr Nancy (Monday-Friday, 9 AM-1 PM), Dr Otieno (Monday-Friday, 2 PM-6 PM), or no preference?",
        "ask_date": "What date would you prefer? Please use DD/MM/YYYY.",
        "ask_date_child": "Child health appointments are with Dr Nancy Monday to Friday, 9 AM to 1 PM.\nWhat date would you prefer? Please use DD/MM/YYYY.",
        "ask_date_dental": "Dental appointments are with Dr Wanjiru on Mondays, Wednesdays and Fridays, and should be arranged at least one day in advance.\nWhat date would you prefer? Please use DD/MM/YYYY.",
        "ask_date_lab": "Which lab test would you like? For example, malaria, blood sugar, typhoid or urine test.",
        "ask_date_general": "Sure! Let's arrange your appointment. What date would you prefer? Please use DD/MM/YYYY.",
        "ask_time": "What time would you prefer? For example, 10:00 AM.",
        "ask_name": "Thank you. May I have the patient's full name?",
        "ask_phone": "Thank you. What phone number can the clinic use to contact you?",
        "invalid_phone": "That phone number doesn't look valid. Please enter a Kenyan mobile number, for example 0712345678.",
        "invalid_date": "Please enter the date in DD/MM/YYYY format, for example 20/11/2026.",
        "invalid_time": "Please enter a time such as 10:00 AM, 2:00 PM or 14:00.",
        "invalid_doctor": "Please choose Dr Nancy, Dr Otieno, or say 'no preference'.",
        "invalid_service": "Which service do you need?\nYou can say general consultation, dental care, lab tests or another clinic service.",
        "invalid_name": "Please enter the patient's full name.",
        "confirm": "Please review your appointment request:\n\nName: {name}\nPhone: {phone}\nService: {service}\nDoctor: {doctor}\nDate: {date}\nTime: {time}\n\nWould you like me to submit this request? Please reply YES or NO.",
        "confirm_lab": "Please review your appointment request:\n\nName: {name}\nPhone: {phone}\nService: {service}\nDoctor: {doctor}\nDate: {date}\nTime: {time}\nLab test: {test}\n\nWould you like me to submit this request? Please reply YES or NO.",
        "confirmed": "Your appointment request has been successfully submitted. The clinic will contact you to confirm your appointment.\n\nAppointment ID: {id}\nName: {name}\nService: {service}\nHealthcare provider: {doctor}\nDate: {date}\nTime: {time}\n\nOnce confirmed, please arrive at least 15 minutes before your appointment.\nWe look forward to seeing you at Hope Clinic!",
        "cancelled": "No problem. I have not submitted the request. How else may I help you?",
        "stop": "No problem. I've stopped the booking request. How else may I help you?",
        "confirm_yes_no": "Please reply YES to submit the request or NO to cancel it.",
        "closed_sunday": "The clinic is closed on Sundays. Please choose another date.",
        "date_past": "That date has already passed. Please choose a future date.",
        "time_past": "That time has already passed. Please choose a later time.",
        "outside_hours": "That time is outside the clinic's regular opening hours. Please choose another time during opening hours.",
        "dental_advance": "Dental appointments should be arranged at least one day in advance.",
        "ask_date_other": "What date would you prefer? Please use DD/MM/YYYY. The clinic will confirm the arrangements for this service."
    },
    "Swahili": {
        "ask_service": "Sawa! Huduma gani ungependa ku-book?\nKwa mfano: general consultation, dental care, vipimo vya maabara au huduma nyingine ya kliniki.",
        "ask_doctor": "Una daktari unayempendelea?\nDr Nancy (Jumatatu-Ijumaa, 9 AM-1 PM), Dr Otieno (Jumatatu-Ijumaa, 2 PM-6 PM), au huna upendeleo?",
        "ask_date": "Tarehe gani ungependa? Tafadhali tumia DD/MM/YYYY.",
        "ask_date_child": "Miadi ya afya ya mtoto ni na Dr Nancy Jumatatu hadi Ijumaa, 9 AM hadi 1 PM.\nTarehe gani ungependa? Tafadhali tumia DD/MM/YYYY.",
        "ask_date_dental": "Miadi ya meno ni na Dr Wanjiru Jumatatu, Jumatano na Ijumaa, na inapaswa kupangwa angalau siku moja kabla.\nTarehe gani ungependa? Tafadhali tumia DD/MM/YYYY.",
        "ask_date_lab": "Kipimo gani cha maabara ungependa? Kwa mfano, malaria, sukari, typhoid au mkojo.",
        "ask_date_general": "Sawa! Tupange miadi yako. Tarehe gani ungependa? Tafadhali tumia DD/MM/YYYY.",
        "ask_time": "Saa ngapi ungependa? Kwa mfano, 10:00 AM.",
        "ask_name": "Asante. Naomba jina kamili la mgonjwa?",
        "ask_phone": "Asante. Namba gani ya simu kliniki inaweza kutumia kukuwasiliana nawe?",
        "invalid_phone": "Namba hiyo ya simu haionekani sahihi. Tafadhali weka namba ya simu ya Kenya, kwa mfano 0712345678.",
        "invalid_date": "Tafadhali weka tarehe kwa DD/MM/YYYY, kwa mfano 20/11/2026.",
        "invalid_time": "Tafadhali weka saa kama 10:00 AM, 2:00 PM au 14:00.",
        "invalid_doctor": "Tafadhali chagua Dr Nancy, Dr Otieno, au sema 'huna upendeleo'.",
        "invalid_service": "Huduma gani unahitaji?\nUnaweza kusema general consultation, dental care, vipimo vya maabara au huduma nyingine ya kliniki.",
        "invalid_name": "Tafadhali weka jina kamili la mgonjwa.",
        "confirm": "Tafadhali hakiki ombi lako la miadi:\n\nJina: {name}\nSimu: {phone}\nHuduma: {service}\nDaktari: {doctor}\nTarehe: {date}\nSaa: {time}\n\nUngependa nitume ombi hili? Tafadhali jibu YES au NO.",
        "confirm_lab": "Tafadhali hakiki ombi lako la miadi:\n\nJina: {name}\nSimu: {phone}\nHuduma: {service}\nDaktari: {doctor}\nTarehe: {date}\nSaa: {time}\nKipimo: {test}\n\nUngependa nitume ombi hili? Tafadhali jibu YES au NO.",
        "confirmed": "Ombi lako la miadi limetumwa. Kliniki itawasiliana nawe kuthibitisha miadi yako.\n\nKitambulisho cha Miadi: {id}\nJina: {name}\nHuduma: {service}\nMtoa huduma: {doctor}\nTarehe: {date}\nSaa: {time}\n\nBaada ya kuthibitishwa, tafadhali fika angalau dakika 15 kabla ya miadi yako.\nTunatarajia kukuona Hope Clinic!",
        "cancelled": "Sawa. Sikutuma ombi. Ninaweza kukusaidiaje tena?",
        "stop": "Sawa. Nimesimamisha ombi la ku-book. Ninaweza kukusaidiaje tena?",
        "confirm_yes_no": "Tafadhali jibu YES kutuma ombi au NO kulighairi.",
        "closed_sunday": "Kliniki imefungwa Jumapili. Tafadhali chagua siku nyingine.",
        "date_past": "Tarehe hiyo imepita. Tafadhali chagua tarehe ya baadaye.",
        "time_past": "Saa hiyo imepita. Tafadhali chagua saa ya baadaye.",
        "outside_hours": "Saa hiyo iko nje ya saa za kazi za kliniki. Tafadhali chagua saa nyingine ndani ya saa za kazi.",
        "dental_advance": "Miadi ya meno inapaswa kupangwa angalau siku moja kabla.",
        "ask_date_other": "Tarehe gani ungependa? Tafadhali tumia DD/MM/YYYY. Kliniki itathibitisha mipango ya huduma hii."
    },
    "Sheng": {
        "ask_service": "Sawa beste! Service gani unataka ku-book?\nKwa mfano: general consultation, dental care, lab test ama service ingine ya clinic.",
        "ask_doctor": "Una doc unataka?\nDr Nancy (Mon-Fri, 9 AM-1 PM), Dr Otieno (Mon-Fri, 2 PM-6 PM), ama huna preference?",
        "ask_date": "Date gani unataka? Tumia DD/MM/YYYY.",
        "ask_date_child": "Miadi ya mtoto ni na Dr Nancy Mon hadi Fri, 9 AM hadi 1 PM.\nDate gani unataka? Tumia DD/MM/YYYY.",
        "ask_date_dental": "Miadi ya meno ni na Dr Wanjiru Mon, Wed na Fri, na inafaa ku-book angalau siku moja kabla.\nDate gani unataka? Tumia DD/MM/YYYY.",
        "ask_date_lab": "Lab test gani unataka? Kwa mfano, malaria, sukari, typhoid ama urine.",
        "ask_date_general": "Sawa! Tupange miadi yako. Date gani unataka? Tumia DD/MM/YYYY.",
        "ask_time": "Saa ngapi unataka? Kwa mfano, 10:00 AM.",
        "ask_name": "Poa. Naomba jina kamili ya mgonjwa?",
        "ask_phone": "Poa. Namba gani ya simu clinic inaweza kutumia kuku-reach?",
        "invalid_phone": "Hiyo namba haiko sawa beste. Weka namba ya Kenya, kwa mfano 0712345678.",
        "invalid_date": "Weka date kwa DD/MM/YYYY, kwa mfano 20/11/2026.",
        "invalid_time": "Weka saa kama 10:00 AM, 2:00 PM ama 14:00.",
        "invalid_doctor": "Chagua Dr Nancy, Dr Otieno, ama sema 'huna preference'.",
        "invalid_service": "Service gani unahitaji?\nUnaweza sema general consultation, dental care, lab test ama service ingine ya clinic.",
        "invalid_name": "Weka jina kamili ya mgonjwa.",
        "confirm": "Check ombi yako ya miadi:\n\nJina: {name}\nSimu: {phone}\nService: {service}\nDoc: {doctor}\nDate: {date}\nSaa: {time}\n\nUnataka nitume hii? Jibu YES ama NO.",
        "confirm_lab": "Check ombi yako ya miadi:\n\nJina: {name}\nSimu: {phone}\nService: {service}\nDoc: {doctor}\nDate: {date}\nSaa: {time}\nLab test: {test}\n\nUnataka nitume hii? Jibu YES ama NO.",
        "confirmed": "Ombi yako ya miadi imetumwa! Clinic itaku-contact ku-confirm miadi yako.\n\nAppointment ID: {id}\nJina: {name}\nService: {service}\nDoc: {doctor}\nDate: {date}\nSaa: {time}\n\nIkisha-confirmiwa, fika angalau dakika 15 kabla ya miadi yako.\nTunangoja kukuona Hope Clinic!",
        "cancelled": "Poa. Sikutuma ombi. Nikusaidie aje tena?",
        "stop": "Poa. Nime-stop ku-book. Nikusaidie aje tena?",
        "confirm_yes_no": "Jibu YES kutuma ombi ama NO ku-cancel.",
        "closed_sunday": "Clinic imefungwa Sunday. Chagua siku ingine.",
        "date_past": "Hiyo date imepita. Chagua date ya mbele.",
        "time_past": "Hiyo saa imepita. Chagua saa ya mbele.",
        "outside_hours": "Hiyo saa iko nje ya masaa ya clinic. Chagua saa ingine ndani ya masaa.",
        "dental_advance": "Miadi ya meno inafaa ku-book angalau siku moja kabla.",
        "ask_date_other": "Date gani unataka? Tumia DD/MM/YYYY. Clinic ita-confirm mipango ya hii service."
    }
}

# Store emergency guidance and other short responses in each supported language.
MISC_TEXT = {
    "English": {
        "emergency": "This may be a medical emergency. Please seek immediate medical attention at the nearest emergency department. Do not wait for a chat response. You may also call Hope Clinic on 0712 345 678 for guidance.",
        "no_problem": "No problem. How else may I help you?",
        "how_help": "How may I help you today?"
    },
    "Swahili": {
        "emergency": "Hii inaweza kuwa dharura. Tafadhali tafuta msaada wa dharura mara moja katika hospitali iliyo karibu. Usisubiri jibu la chat. Unaweza pia kupiga Hope Clinic 0712 345 678 kwa mwongozo.",
        "no_problem": "Sawa. Ninaweza kukusaidiaje tena?",
        "how_help": "Ninaweza kukusaidiaje leo?"
    },
    "Sheng": {
        "emergency": "Hii inaweza kuwa emergency beste. Enda hosi iliyo karibu sasa hivi. Usingoje jibu la chat. Unaweza pia kupiga Hope Clinic 0712 345 678.",
        "no_problem": "Poa. Nikusaidie aje tena?",
        "how_help": "Nikusaidie aje leo?"
    }
}

# Check whether a connection to the OpenAI server can be established.
def check_internet():
    try:
        socket.create_connection(("api.openai.com", 443), timeout=5)
        return True
    except OSError:
        return False

# Ask the user to reconnect or return to the menu while connectivity is unavailable.
def wait_for_internet():
    t = TEXT[selected_language]
    while not check_internet():
        print(f"\nMedIQ: {t['no_internet']}")
        choice = input(t["retry"]).strip().lower()
        if choice == "exit":
            return False
    print(f"MedIQ: {t['internet_back']}")
    return True

# Display language options and update the shared language setting.
def choose_language():
    global selected_language
    print("\nChoose language / Chagua lugha / Chagua lugha:")
    print("1. English")
    print("2. Swahili")
    print("3. Sheng")
    choice = input("Enter choice (1-3): ").strip()
    if choice == "2":
        selected_language = "Swahili"
    elif choice == "3":
        selected_language = "Sheng"
    else:
        selected_language = "English"
    print(f"Language set to: {selected_language}")
    return selected_language

# --- NEW: Send FULL history with EVERY API call - at least 4 turns ---
def ask_openai_with_full_history(session_obj):
    """
    PDF rule: Full list of messages sent with each API call.
    We build one prompt with:
    - system instruction (persona + knowledge + language)
    - FULL conversation so far from session.py (Turn 1...Turn N)
    - instruction to reply in JSON
    Returns parsed dict.
    """

    # Build the system instructions using clinic information, memory and selected language.
    system_text = build_system_prompt(
        ASSISTANT_NAME,
        CLINIC_NAME,
        CLINIC_PHONE,
        knowledge,
        old_memory,
        selected_language
    )

    full_history = session_obj.get_history_for_api()  # ALL turns, not just last one

    # Combine instructions and the complete current conversation into one prompt.
    full_prompt = (
        system_text
        + "\n\n--- FULL CONVERSATION SO FAR (use this to remember earlier turns) ---\n"
        + full_history
        + "\n--- END OF CONVERSATION ---\n"
        + "\nReply to the LAST patient message above. Reply ONLY in JSON: "
        "{\"answer\": \"...\", \"triage\": \"...\", \"is_emergency\": false}"
    )

    # Request a JSON-formatted answer from the model using a low temperature.
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=full_prompt,
        text={
            "format": {
                "type": "json_object"
            }
        },
        temperature=0.2
    )

    # Reject an empty API response before attempting to parse it.
    if not response.output_text:
        raise ValueError("OpenAI returned an empty response.")

    # Convert the JSON response text into a Python object for the chat handler.
    return json.loads(response.output_text)

# Append a question and answer to local memory, retaining the last 40 lines.
def save_memory(question, answer):
    global old_memory
    if old_memory.strip() == "No previous conversation.":
        old_memory = ""
    new_entry = f"\npatient: {question}\n{ASSISTANT_NAME}: {answer}\n"
    old_memory += new_entry
    old_memory = "\n".join(old_memory.splitlines()[-40:])
    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
        file.write(old_memory)

# Recognise simple greetings so they can be answered without an API call.
def is_greeting(question):
    greetings = ["hello", "hi", "hey", "good morning", "good afternoon", "good evening", "habari", "niaje", "sasa", "mambo", "hujambo", "salama", "hello mediq"]
    return question.lower().strip().strip("!.?") in greetings

# Screen for predefined emergency phrases; this is not a clinical diagnosis.
def is_emergency(question):
    emergency_words = ["difficulty breathing", "cannot breathe", "can't breathe", "cant breathe", "shortness of breath", "chest pain", "maumivu ya kifua", "coughing blood", "vomiting blood", "heavy bleeding", "bleeding heavily", "pregnant and bleeding", "pregnancy bleeding", "mjamzito na damu", "snake bite", "snake bitten", "nyoka ameniuma", "fainting", "unconscious", "unresponsive", "seizure", "kifafa", "deep cut", "animal bite", "severe allergic reaction", "swollen face", "face is swelling", "blue lips", "head injury", "baby not breastfeeding", "baby not feeding", "baby is not moving"]
    q = question.lower()
    return any(word in q for word in emergency_words)

# Identify likely connectivity errors from the supplied error text.
def is_offline_error(error_text):
    return any(word in error_text for word in ["connection", "network", "timeout", "getaddrinfo", "gaierror", "name resolution", "11001", "11002", "dns", "unreachable", "failed to resolve", "no internet"])

# Remove spaces, hyphens and parentheses from phone numbers.
def normalise_phone(phone):
    return re.sub(r"[\s\-()]", "", phone)

# Check whether the cleaned number matches supported Kenyan mobile formats.
def valid_kenyan_phone(phone):
    cleaned = normalise_phone(phone)
    return bool(re.fullmatch(r"0[17]\d{8}", cleaned) or re.fullmatch(r"\+254[17]\d{8}", cleaned) or re.fullmatch(r"254[17]\d{8}", cleaned))

# Read saved bookings; return an empty list if the file is missing or invalid.
def load_bookings():
    try:
        with open(BOOKINGS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []

# Append a booking record and write the updated list to disk.
def save_booking(booking):
    bookings = load_bookings()
    bookings.append(booking)
    with open(BOOKINGS_FILE, "w", encoding="utf-8") as file:
        json.dump(bookings, file, indent=4, ensure_ascii=False)

# Generate an appointment reference using part of a random UUID.
def create_booking_id():
    return "HHC-" + uuid.uuid4().hex[:8].upper()

# Classify a message into a clinic service using keyword matches.
def classify_service(message):
    q = message.lower()
    dental_words = ["dental", "dentist", "tooth", "teeth", "meno", "jino", "gum", "toothache"]
    lab_words = ["lab", "test", "blood test", "malaria", "sugar", "typhoid", "urine", "kipimo"]
    child_health_words = ["child health", "child", "mtoto", "watoto", "baby health", "kids health", "child checkup", "child clinic", "mtoto mgonjwa", "baby"]
    general_words = ["general", "consultation", "doctor", "daktari", "checkup", "check-up", "fever", "cough", "coughing", "stomach", "headache", "sick", "unwell", "running nose", "runny nose", "flu", "cold", "sneezing", "sore throat", "remedy", "symptom", "symptoms"]
    vaccination_words = ["vaccination", "vaccine", "vaccines", "kids vaccination", "child vaccination", "children vaccination", "chanjo"]
    other_words = ["family planning", "wound dressing", "home visit"]
    # Return the first matching service; the order of these checks matters.
    if any(word in q for word in dental_words):
        return "Dental care"
    if any(word in q for word in lab_words):
        return "Lab test"
    # Check vaccination before broader child health and consultation keywords.
    if any(word in q for word in vaccination_words):
        return "Child vaccination"
    if any(word in q for word in child_health_words):
        return "Child health"
    if any(word in q for word in general_words):
        return "General consultation"
    if any(word in q for word in other_words):
        return "Other clinic service"
    return None

# Identify booking requests using predefined phrases.
def is_booking_request(message):
    q = message.lower()
    booking_phrases = ["i want to book", "i would like to book", "i'd like to book", "book an appointment", "make an appointment", "schedule an appointment", "can i book", "i need an appointment", "nataka ku-book", "nataka appointment", "ningependa kuweka appointment", "book for me", "book", "booking"]
    return any(phrase in q for phrase in booking_phrases)

# Try supported date formats and return None if none match.
def parse_appointment_date(message):
    value = message.strip()
    for date_format in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]:
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            pass
    return None

# Normalise time input and try supported 12-hour and 24-hour formats.
def parse_appointment_time(message):
    value = message.strip().upper().replace(".", ":")
    value = re.sub(r"(\d)(AM|PM)$", r"\1 \2", value)
    for time_format in ["%I:%M %p", "%I %p", "%H:%M"]:
        try:
            return datetime.strptime(value, time_format).time()
        except ValueError:
            continue
    return None

# Return configured clinic opening and closing times for a given weekday.
def clinic_hours_for(day):
    weekday = day.weekday()
    if weekday <= 4:
        return time(8, 0), time(18, 0)
    if weekday == 5:
        return time(9, 0), time(14, 0)
    return None, None

# Validate a requested appointment against configured hours and service rules.
def validate_appointment_schedule(service, doctor, appointment_date, appointment_time):
    bt = BOOKING_TEXT[selected_language]
    opening, closing = clinic_hours_for(appointment_date)
    if opening is None:
        return False, bt["closed_sunday"]
    if not (opening <= appointment_time <= closing):
        return False, bt["outside_hours"]
    weekday = appointment_date.weekday()
    # Apply weekday and doctor-specific hours for general consultations.
    if service == "General consultation":
        if weekday > 4:
            return False, bt["outside_hours"]
        if doctor == "Dr Nancy":
            if not (time(9, 0) <= appointment_time <= time(13, 0)):
                return False, bt["outside_hours"]
        elif doctor == "Dr Otieno":
            if not (time(14, 0) <= appointment_time <= time(18, 0)):
                return False, bt["outside_hours"]
    # Apply Dr Nancy's configured schedule to child health and vaccination.
    if service in ["Child health", "Child vaccination"]:
        if weekday > 4:
            return False, bt["outside_hours"]
        if not (time(9, 0) <= appointment_time <= time(13, 0)):
            return False, bt["outside_hours"]
    # Restrict dental appointments to specified weekdays and advance booking.
    if service == "Dental care":
        if weekday not in [0, 2, 4]:
            return False, bt["outside_hours"]
        if appointment_date <= date.today():
            return False, bt["dental_advance"]
    # Reject dates or same-day times that have already passed.
    if appointment_date < date.today():
        return False, bt["date_past"]
    if appointment_date == date.today() and appointment_time <= datetime.now().time():
        return False, bt["time_past"]
    return True, ""

# Track the current booking step, collected details and recent booking offers.
booking_state = None
booking_data = {}
booking_offer_pending = False
booking_offer_service = None
last_service_hint = None

# Initialise a booking and select the first question based on the requested service.
def start_booking(service=None):
    global booking_state, booking_data, booking_offer_pending, booking_offer_service
    bt = BOOKING_TEXT[selected_language]
    # Clear previous booking details and pending offers before starting.
    booking_data = {}
    booking_offer_pending = False
    booking_offer_service = None
    # Ask for the service if one has not been supplied.
    if not service:
        booking_state = "ASK_SERVICE"
        return bt["ask_service"]
    booking_data["service"] = service
    # Choose the next booking step and assign a provider where applicable.
    if service == "General consultation":
        booking_state = "ASK_DOCTOR"
        return bt["ask_doctor"]
    if service == "Child health":
        booking_data["doctor"] = "Dr Nancy"
        booking_state = "ASK_DATE"
        return bt["ask_date_child"]
    if service == "Dental care":
        booking_data["doctor"] = "Dr Wanjiru"
        booking_state = "ASK_DATE"
        return bt["ask_date_dental"]
    if service == "Lab test":
        booking_data["doctor"] = "Not applicable"
        booking_state = "ASK_DATE"
        return bt["ask_date_lab"]
    if service == "Child vaccination":
        booking_data["doctor"] = "Dr Nancy"
    else:
        booking_data["doctor"] = "To be confirmed by clinic"
    booking_state = "ASK_DATE"
    return bt["ask_date_general"]

# Process each patient reply according to the current booking step.
def handle_booking_message(message):
    global booking_state, booking_data, booking_offer_pending
    bt = BOOKING_TEXT[selected_language]
    misc = MISC_TEXT[selected_language]
    q = message.strip()
    # Allow the patient to cancel an active booking and clear its details.
    if q.lower() in ["cancel", "cancel booking", "stop", "acha", "wacha"]:
        booking_state = None
        booking_data = {}
        return bt["stop"]
    # Identify the requested service and decide which information to collect next.
    if booking_state == "ASK_SERVICE":
        service = classify_service(q)
        if not service:
            return bt["invalid_service"]
        booking_data["service"] = service
        if service == "General consultation":
            booking_state = "ASK_DOCTOR"
            return bt["ask_doctor"]
        if service == "Child health":
            booking_data["doctor"] = "Dr Nancy"
            booking_state = "ASK_DATE"
            return bt["ask_date_child"]
        if service == "Dental care":
            booking_data["doctor"] = "Dr Wanjiru"
            booking_state = "ASK_DATE"
            return bt["ask_date_dental"]
        if service == "Lab test":
            booking_data["doctor"] = "Not applicable"
            booking_state = "ASK_DATE"
            return bt["ask_date_lab"]
        if service == "Child vaccination":
            booking_data["doctor"] = "Dr Nancy"
        else:
            booking_data["doctor"] = "To be confirmed by clinic"
        booking_state = "ASK_DATE"
        return bt["ask_date_other"]
    # Validate the preferred doctor or accept no preference.
    if booking_state == "ASK_DOCTOR":
        q_lower = q.lower()
        if "nancy" in q_lower:
            doctor = "Dr Nancy"
        elif "otieno" in q_lower:
            doctor = "Dr Otieno"
        elif any(word in q_lower for word in ["no preference", "any", "either", "whoever", "huna upendeleo", "huna preference"]):
            doctor = "No preference"
        else:
            return bt["invalid_doctor"]
        booking_data["doctor"] = doctor
        booking_state = "ASK_DATE"
        return bt["ask_date"]
    # Collect the lab test name first if needed, then validate the appointment date.
    if booking_state == "ASK_DATE":
        if booking_data.get("service") == "Lab test" and "test" not in booking_data:
            booking_data["test"] = q
            return bt["ask_date"]

        appointment_date = parse_appointment_date(q)

        if not appointment_date:
            return bt["invalid_date"]

        if appointment_date < date.today():
            return bt["date_past"]

        # Reject days when the assigned service or doctor is unavailable.
        # Saturday remains available for lab tests and other clinic services.
        service = booking_data.get("service")
        weekday = appointment_date.weekday()
        if weekday == 5 and service in ["General consultation", "Child health", "Child vaccination", "Dental care"]:
            return bt["outside_hours"]
        if service == "Dental care" and weekday not in [0, 2, 4, 6]:
            return bt["outside_hours"]

        if appointment_date.weekday() == 6:
            return bt["closed_sunday"]

        # Store the date in ISO format and proceed to the time question.
        booking_data["date"] = appointment_date.isoformat()
        booking_state = "ASK_TIME"
        return bt["ask_time"]
    # Parse the requested time and check it against the appointment schedule.
    if booking_state == "ASK_TIME":
        appointment_time = parse_appointment_time(q)
        if not appointment_time:
            return bt["invalid_time"]
        appointment_date = date.fromisoformat(booking_data["date"])
        service = booking_data["service"]
        doctor = booking_data.get("doctor", "")
        # Assign a doctor by time when the patient has no preference.
        if service == "General consultation" and doctor == "No preference":
            if time(9, 0) <= appointment_time <= time(13, 0):
                doctor = "Dr Nancy"
            elif time(14, 0) <= appointment_time <= time(18, 0):
                doctor = "Dr Otieno"
            else:
                return bt["outside_hours"]
            booking_data["doctor"] = doctor
        # Validate the selected service, provider, date and time before continuing.
        valid, reason = validate_appointment_schedule(service, doctor, appointment_date, appointment_time)
        if not valid:
            return reason
        booking_data["time"] = appointment_time.strftime("%I:%M %p")
        booking_state = "ASK_NAME"
        return bt["ask_name"]
    # Require a name with at least two words and five characters.
    if booking_state == "ASK_NAME":
        if len(q.split()) < 2 or len(q) < 5:
            return bt["invalid_name"]
        booking_data["name"] = q
        booking_state = "ASK_PHONE"
        return bt["ask_phone"]
    # Validate and store the phone number before displaying the booking review.
    if booking_state == "ASK_PHONE":
        if not valid_kenyan_phone(q):
            return bt["invalid_phone"]
        booking_data["phone"] = normalise_phone(q)
        # Choose the review template depending on whether a lab test was requested.
        if "test" in booking_data:
            summary = bt["confirm_lab"].format(name=booking_data['name'], phone=booking_data['phone'], service=booking_data['service'], doctor=booking_data.get('doctor', 'To be confirmed'), date=booking_data['date'], time=booking_data['time'], test=booking_data['test'])
        else:
            summary = bt["confirm"].format(name=booking_data['name'], phone=booking_data['phone'], service=booking_data['service'], doctor=booking_data.get('doctor', 'To be confirmed'), date=booking_data['date'], time=booking_data['time'])
        booking_state = "CONFIRM"
        return summary
    # Process the patient confirmation or cancellation.
    if booking_state == "CONFIRM":
        answer = q.lower().strip()
        if answer in ["yes", "y", "ndio", "ndio kabisa", "sawa"]:
            # Generate an ID and build the record with pending clinic confirmation status.
            booking_id = create_booking_id()
            booking_record = {"booking_id": booking_id, "name": booking_data["name"], "phone": booking_data["phone"], "service": booking_data["service"], "doctor": booking_data.get("doctor", "To be confirmed"), "date": booking_data["date"], "time": booking_data["time"], "lab_test": booking_data.get("test"), "status": "PENDING_CLINIC_CONFIRMATION", "date_saved": datetime.now().isoformat(timespec="seconds")}
            # Save the request locally; the existing response template describes it as confirmed.
            save_booking(booking_record)
            appointment_date_display = date.fromisoformat(booking_data["date"]).strftime("%d %B %Y")
            doctor = booking_data.get("doctor", "Healthcare provider")
            confirmation_message = bt["confirmed"].format(id=booking_id, name=booking_data['name'], service=booking_data['service'], doctor=doctor, date=appointment_date_display, time=booking_data['time'])
            # Clear booking state after saving the request.
            booking_state = None
            booking_data = {}
            return confirmation_message
        # Discard the request if the patient declines confirmation.
        if answer in ["no", "n", "hapana", "cancel"]:
            booking_state = None
            booking_data = {}
            return bt["cancelled"]
        return bt["confirm_yes_no"]
    return misc["how_help"]

# Display saved sessions, falling back to the memory file if none exist.
def show_past_session():
    print("\n--- Past Session ---")
    files = list_saved_sessions()
    if not files:
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as file:
                content = file.read().strip()
            if content == "No previous conversation.":
                content = ""
            if not content:
                print("No past session found.")
            else:
                print(content)
        except OSError:
            print("No past session found.")
        print("-" * 50)
        return
    # List available session files and allow the user to choose one.
    print("Saved sessions:")
    for i, f in enumerate(files, 1):
        print(f"{i}. {f}")
    print(f"{len(files)+1}. Back to menu")
    choice = input("Choose session to open (number): ").strip()
    try:
        num = int(choice)
        if num == len(files) + 1:
            return
        if 1 <= num <= len(files):
            content = load_saved_session(files[num - 1])
            print("\n" + content if content else "Could not open session file.")
        else:
            print("Invalid choice.")
    except (ValueError, IndexError):
        print("Invalid choice.")
    print("-" * 50)


# Search saved bookings by the full name entered by the user.
def view_bookings():
    print("\n--- Find Your Booking ---")

    patient_name = input(
        "Please enter the full name used when making the booking: "
    ).strip()

    if not patient_name:
        print("Please enter your full name.")
        return

    # Request a second matching detail before displaying booking records.
    patient_phone = input("Please enter the phone number used when booking: ").strip()
    if not valid_kenyan_phone(patient_phone):
        print("Please enter a valid Kenyan mobile number.")
        return

    # Compare local and international forms of the same Kenyan number.
    phone_key = normalise_phone(patient_phone)[-9:]
    bookings = load_bookings()

    # Match both name and phone; this is not secure identity authentication.
    patient_bookings = [
        booking for booking in bookings
        if booking.get("name", "").strip().casefold() == patient_name.casefold()
        and valid_kenyan_phone(booking.get("phone") or "")
        and normalise_phone(booking["phone"])[-9:] == phone_key
    ]

    if not patient_bookings:
        print("No bookings found matching the name and phone number provided.")
        return

    print(f"\nBookings found for {patient_name}:")

    # Display each matching booking and calculate its displayed status.
    for booking in patient_bookings:
        print("-" * 50)
        print(f"Appointment ID: {booking.get('booking_id', '')}")
        print(f"Name: {booking.get('name', '')}")
        print(f"Service: {booking.get('service', '')}")
        print(f"Doctor: {booking.get('doctor', '')}")
        print(f"Date: {booking.get('date', '')}")
        print(f"Time: {booking.get('time', '')}")
        appointment_date = date.fromisoformat(booking["date"])
        today = date.today()

        # Only confirmed records should be displayed as confirmed appointments.
        if booking.get("status") == "PENDING_CLINIC_CONFIRMATION":
            status = "Pending clinic confirmation"
        elif booking.get("status") != "CONFIRMED":
            status = booking.get("status") or "Unknown status"
        elif appointment_date > today:
            status = "Awaiting appointment"
        elif appointment_date == today:
            status = "Waiting to be seen"
        else:
            status = "Appointment date passed"

        print(f"Status: {status}")
    print("-" * 50)


# Generate a summary from the current session, or fall back to old memory.
def generate_summary(session_obj=None):
    try:
        if session_obj is not None and session_obj.messages:
            history_text = session_obj.get_history_for_api()
        else:
            history_text = old_memory

        # Send the summary instructions and conversation history to OpenAI.
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=SUMMARY_PROMPT + "\n" + history_text
        )

        summary_text = response.output_text.strip()
        return summary_text

    # Return a fallback message if summary generation fails.
    except Exception:
        return "No summary generated - API call failed."

# Run the interactive patient conversation and coordinate the other features.
def run_chat():
    global booking_state, booking_data, booking_offer_pending, booking_offer_service, last_service_hint
    t = TEXT[selected_language]
    misc = MISC_TEXT[selected_language]
    # Create a session object to collect the conversation in the selected language.
    session = Session(selected_language)
    # Check connectivity before starting the conversation.
    if not check_internet():
        if not wait_for_internet():
            print(f"MedIQ: {t['ended']}")
            return
    print(f"\nMedIQ: {misc['how_help']}")
    # Record the opening assistant message in the session history.
    session.add("MedIQ", misc["how_help"])
    print("-" * 50)
    # Keep accepting patient messages until the session ends.
    while True:
        question = input("you: ").strip()

        # Reject empty input and ask the patient to type a message.
        if not question:
            print("MedIQ: Please type something so I can assist you.")
            print("-" * 50)
            continue

        # End the session when the patient types exit and generate its summary.
        if question.lower() == "exit":
            summary_text = generate_summary(session)

            # Save the full session and summary in Markdown and JSON files.
            try:
                md_path, json_path = session.save(summary_text)
                print(f"Session saved successfully:")
                print(f"Markdown: {md_path}")
                print(f"JSON: {json_path}")
            except Exception as error:
                print(f"Session saving failed: {error}")

            # Save conversation messages to the memory file separately.
            try:
                save_to_memory_file(session.messages)
            except Exception as error:
                print(f"Memory saving failed: {error}")

            # Display session summary to the patient
            print("\nMedIQ: Here is a summary of your session:")
            print(summary_text)

            print(f"\nMedIQ: {t['ended']}")
            break
        
        # Check connectivity again before processing the next message.
        if not check_internet():
            if not wait_for_internet():
                print(f"MedIQ: {t['ended']}")
                break
            continue
        # Record the patient message before routing it to the appropriate handler.
        session.add("you", question)
        # Prioritise recognised emergency phrases over booking, cache and AI processing.
        if is_emergency(question):
            booking_state = None
            booking_data = {}
            booking_offer_pending = False
            print(f"MedIQ: {misc['emergency']}")
            session.add("MedIQ", misc["emergency"])
            print("-" * 50)
            continue
        # Continue an active booking without sending the reply to the AI.
        if booking_state is not None:
            answer = handle_booking_message(question)
            print(f"MedIQ: {answer}")
            session.add("MedIQ", answer)
            print("-" * 50)
            continue
        # Remember a recognised service to help interpret a later booking request.
        if classify_service(question) is not None:
            last_service_hint = classify_service(question)
        # Start a booking using the requested or most recently recognised service.
        if is_booking_request(question):
            service = classify_service(question) or last_service_hint
            if not service:
                service = "General consultation"
            answer = start_booking(service)
            print(f"MedIQ: {answer}")
            session.add("MedIQ", answer)
            print("-" * 50)
            continue
        # Recognise acceptance of a previous booking offer.
        yes_replies = ["yes", "yeah", "yep", "ndio", "sawa", "okay", "ok"]
        if booking_offer_pending and question.lower().strip("!.?") in yes_replies:
            answer = start_booking(booking_offer_service)
            print(f"MedIQ: {answer}")
            session.add("MedIQ", answer)
            print("-" * 50)
            continue
        # Clear the pending offer if the patient declines.
        if booking_offer_pending and question.lower().strip("!.?") in ["no", "no thanks", "hapana"]:
            booking_offer_pending = False
            booking_offer_service = None
            print(f"MedIQ: {misc['no_problem']}")
            session.add("MedIQ", misc["no_problem"])
            print("-" * 50)
            continue
        # Respond to greetings locally without an API request.
        if is_greeting(question):
            answer = t["greeting"]
            print(f"MedIQ: {answer}")
            session.add("MedIQ", answer)
            booking_offer_pending = False
            booking_offer_service = None
            print("-" * 50)
            continue
        # Clear previous offers before processing a new general question.
        booking_offer_pending = False
        booking_offer_service = None
        # Check whether the question is eligible for caching and look for a saved answer.
        if is_cacheable(question):
            cached = get_cached(question)
            if cached:
                # Support cached answers stored either as text or as a dictionary.
                cached_answer = cached.get("answer", "") if isinstance(cached, dict) else cached

                if cached_answer:
                    print(f"MedIQ: {cached_answer}")
                    session.add("MedIQ", cached_answer)
                    # Detect booking offers in cached replies so a later yes can start a booking.
                    booking_offer_pending = bool(re.search(r"\b(would you like to book|do you want to book|would you like an appointment)\b", cached_answer.lower()))
                    booking_offer_service = classify_service(question)

                    if booking_offer_pending and booking_offer_service is None:
                        booking_offer_service = "General consultation"

                    # Save the cached exchange to memory and skip the API request.
                    save_memory(question, cached_answer)
                    print("-" * 50)
                    continue
        # Request a fresh AI response when no earlier handler has answered.
        try:
            data = ask_openai_with_full_history(session)
            # Extract the answer, supporting the older reply field as a fallback.
            answer = data.get("answer", data.get("reply", "Sorry, I could not understand that. Please try again."))
            # Replace the AI answer with emergency guidance if emergency flags are returned.
            if data.get("is_emergency") is True or data.get("triage") == "EMERGENCY":
                answer = misc["emergency"]
            print(f"MedIQ: {answer}")
            session.add("MedIQ", answer)
            # Detect a booking offer in the AI answer and remember its service.
            booking_offer_pending = bool(re.search(r"\b(would you like to book|do you want to book|would you like an appointment|shall i book)\b", answer.lower()))
            booking_offer_service = classify_service(question)
            if booking_offer_pending and booking_offer_service is None:
                booking_offer_service = "General consultation"
            # Exclude emergency and COME TODAY responses from this cache and memory write.
            if data.get("is_emergency") is not True and data.get("triage") not in ["EMERGENCY", "COME TODAY"]:
                if is_cacheable(question):
                    set_cache(question, answer)
                save_memory(question, answer)
        # Handle API and connectivity failures without exposing raw errors to the patient.
        except Exception as error:
            error_text = str(error).lower()
            # Show a temporary failure message when the service is unavailable.
            if "503" in error_text or "unavailable" in error_text:
                msg = "Sorry, I'm having a problem responding right now. Please try again in a minute."
                print(f"MedIQ: {msg}")
                session.add("MedIQ", msg)
            # Handle network-related errors by offering reconnection.
            elif is_offline_error(error_text):
                print(f"MedIQ: {t['no_internet']}")
                if not wait_for_internet():
                    print(f"MedIQ: {t['ended']}")
                    break
                booking_offer_pending = False
                booking_offer_service = None
            # Use a general fallback for other errors and clear pending booking offers.
            else:
                msg = "Sorry, I'm having a problem responding right now. Please try again or call 0712 345 678."
                print(f"MedIQ: {msg}")
                session.add("MedIQ", msg)
                booking_offer_pending = False
                booking_offer_service = None
        print("-" * 50)

# Start the application, select a language and manage the main menu.
def main():
    global old_memory, booking_state, booking_data

    # Display welcome before language selection
    print("\nMedIQ - Hope Clinic")
    print("Your Virtual Medical Assistant")
    print("\nMedIQ: Hello! Welcome to Hope Clinic. I'm MedIQ, your virtual medical assistant.")
    print("-" * 50)

    # Set the language before displaying translated menu options.
    choose_language()
    t = TEXT[selected_language]

    # Repeat the main menu until the user chooses to exit.
    while True:
        print(t["choose"])
        print(t["new"])
        print(t["past"])
        print(t["bookings"])
        print(t["exit"])
        choice = input(t["enter"]).strip().lower()
        # Start a new session and reset the active booking details.
        if choice in ["1", "new session", "new", "1."]:
            booking_state = None
            booking_data = {}
            run_chat()
            # Reload memory from disk after the chat session ends.
            try:
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    old_memory = f.read().strip() or "No previous conversation."
            except OSError:
                pass
        # Open the past-session viewer.
        elif choice in ["2", "past session", "past", "2."]:
            show_past_session()
        # Open the booking lookup.
        elif choice in ["3", "view bookings", "bookings", "3."]:
            view_bookings()
        # Display the farewell message and exit the menu loop.
        elif choice in ["4", "exit", "quit", "4."]:
            print(f"MedIQ: {t['bye']}")
            break
        else:
            print(t["invalid"])

# Run the application only when this file is executed directly.
if __name__ == "__main__":
    main()