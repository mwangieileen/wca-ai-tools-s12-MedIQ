import os
import json
import re
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
from google import genai
from google.genai import types
from system_propmt import build_prompt, SUMMARY_PROMPT

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    print("WARNING: GEMINI_API_KEY not found in .env")
    client = None
else:
    client = genai.Client(api_key=API_KEY)

def load_knowledge():
    try:
        with open("knowledge.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "No knowledge base found."

KNOWLEDGE = load_knowledge()
MEMORY_FILE = "memory.json"
BOOKING_FILE = "booking.json"

def clean_json(text):
    text = text.strip()
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()

def ask_gemini(prompt_text, required_fields):
    try:
        if not client:
            print("ERROR: No API key. Check your .env file.")
            return None
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt_text,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=2000,
                response_mime_type="application/json"
            )
        )
        raw = clean_json(response.text)
        try:
            data = json.loads(raw)
        except:
            data = {"reply": raw, "language": "English", "main_reason": raw, "session_date": ""}
        if "reply" not in data and "main_reason" not in data:
            data["reply"] = raw
        if "reply" not in data and "main_reason" in required_fields:
            data["main_reason"] = raw
        for field in required_fields:
            if field not in data or data[field] == "" or data[field] is None:
                if field == "reply":
                    data[field] = raw
                elif field == "language":
                    data[field] = "English"
                else:
                    data[field] = "Not provided"
        return data
    except Exception as e:
        print(f"\nREAL ERROR: {e}")
        print("\n----------------------------------------")
        print("No internet connection.")
        print("Please connect to internet to continue.")
        print("----------------------------------------")
        return None

def save_booking(name, phone, date, time, reason):
    try:
        with open(BOOKING_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    b = json.loads(line)
                    if b.get("patient_name") == name and b.get("date") == date and b.get("time") == time and b.get("reason") == reason:
                        print(f"\n[BOOKING ALREADY SAVED - skipping duplicate]")
                        return b
                except:
                    continue
    except FileNotFoundError:
        pass
    booking = {
        "patient_name": name,
        "phone": phone,
        "date": date,
        "time": time,
        "reason": reason,
        "booked_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    with open(BOOKING_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(booking) + "\n")
    print(f"\n[BOOKING SAVED] {name} - {date} at {time} - {reason}")
    return booking

def new_session():
    print("\n--- New Session ---")
    print("Type 'exit' to end session and get summary (after at least 4 turns).")
    print("Type 'menu' to go back to menu.\n")
    name = input("MedIQ: What is your name? (or press Enter to skip): ").strip()
    language = input("MedIQ: Which language? English / Swahili / Sheng: ").strip() or "English"
    history = []
    booked_this_session = False
    turn_count = 0
    if name:
        history.append(f"Patient name: {name}")
    history.append(f"Language: {language}")
    while True:
        user_msg = input("\nYou: ").strip()
        if user_msg.lower() == "exit":
            if turn_count < 4:
                print(f"\n[MedIQ needs at least 4 turns. You have done {turn_count}/4 turns.]")
                print(f"Please chat {4 - turn_count} more turn(s) before exiting.")
                continue
            break
        if user_msg.lower() == "menu":
            return
        if not user_msg:
            continue
        history.append(f"Patient: {user_msg}")
        conversation = "\n".join(history)
        prompt_text = build_prompt(KNOWLEDGE, conversation, language, history, user_msg)
        result = ask_gemini(prompt_text, ["reply", "language"])
        if result:
            reply = result["reply"]
            print(f"\nMedIQ: {reply}")
            history.append(f"MedIQ: {reply}")
            turn_count += 1
            print(f"[Turn {turn_count}/4]")
            booking_date = result.get("booking_date", "")
            booking_time = result.get("booking_time", "")
            booking_phone = result.get("booking_phone", "")
            if not booked_this_session and booking_date and booking_time and booking_date != "Not provided" and booking_phone and booking_phone != "Not provided":
                b_name = result.get("booking_name", name) or name or "Unknown"
                if b_name == "Not provided":
                    b_name = name or "Unknown"
                b_reason = result.get("booking_reason", user_msg)
                if b_reason == "Not provided":
                    b_reason = user_msg
                save_booking(b_name, booking_phone, booking_date, booking_time, b_reason)
                booked_this_session = True
        else:
            print("Try again after connecting to internet.")
    print("\n--- Generating Summary ---")
    full_convo = "\n".join(history)
    summary_prompt_text = SUMMARY_PROMPT + f"\n\nCONVERSATION:\n{full_convo}"
    summary = ask_gemini(summary_prompt_text, ["main_reason", "session_date"])
    if summary:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        summary["session_date"] = timestamp
        if not summary.get("patient_name") or summary.get("patient_name") == "Not provided":
            summary["patient_name"] = name or "Unknown"
        with open(MEMORY_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(summary) + "\n")
            f.flush()
        print("\n--- Session Summary Saved ---")
        print(f"Saved to: {os.path.abspath(MEMORY_FILE)}")
        print(f"Patient saved: {summary.get('patient_name')} - {summary.get('main_reason')}")
        print(json.dumps(summary, indent=2))
    else:
        print("Could not generate summary. Check internet and try again.")

def open_past_session():
    print("\n--- Past Sessions ---")
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            lines = [l for l in f.readlines() if l.strip()]
        if not lines:
            print("No past sessions yet.")
            return
        for i, line in enumerate(lines, 1):
            try:
                s = json.loads(line)
                print(f"{i}. {s.get('session_date','')} - {s.get('patient_name','Unknown')} - {s.get('main_reason','')}")
            except:
                continue
        pick = input("\nEnter session number to see full details (or press Enter to go back): ").strip()
        if not pick:
            return
        try:
            s = json.loads(lines[int(pick)-1])
            print("\n--- FULL SESSION DETAILS ---")
            print(json.dumps(s, indent=2))
        except:
            print("Invalid number.")
    except FileNotFoundError:
        print("No past sessions yet.")

def open_bookings():
    print("\n--- Bookings ---")
    try:
        with open(BOOKING_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if not lines:
            print("No bookings yet.")
            return
        for i, line in enumerate(lines, 1):
            try:
                b = json.loads(line)
                print(f"{i}. {b.get('date','')} at {b.get('time','')} - {b.get('patient_name','Unknown')} - {b.get('phone','')} - {b.get('reason','')}")
            except:
                continue
    except FileNotFoundError:
        print("No bookings yet.")

def main():
    print("MedIQ AI - Hope Health Clinic FAQ Assistant")
    while True:
        print("\n--- MENU ---")
        print("1. Start New Session")
        print("2. Open Past Session")
        print("3. View Bookings")
        print("4. Exit")
        choice = input("Choose (1/2/3/4): ").strip()
        if choice == "1":
            new_session()
        elif choice == "2":
            open_past_session()
        elif choice == "3":
            open_bookings()
        elif choice == "4":
            print("Goodbye! Stay healthy.")
            break
        else:
            print("Please choose 1, 2, 3 or 4.")

if __name__ == "__main__":
    main()