# session.py
# MedIQ - Conversation Memory and Session Management
#
# This file handles:
# - Storing the full conversation during a session.
# - Preparing conversation history for OpenAI API calls.
# - Saving conversations and summaries in Markdown and JSON formats.
# - Retrieving previously saved sessions.
# - Maintaining recent conversation memory for future sessions.

# Used to create folders, access files and manage file paths.
import os

# Used to save structured session data in JSON format.
import json

# Used to record session dates, times and timestamps.
from datetime import datetime


# Folder where complete conversations and summaries are saved.
SAMPLES_DIR = "samples"

# File used to store recent conversation history.
MEMORY_FILE = "memory.txt"


# SESSION CLASS

# A Session object represents one conversation between
# the patient and MedIQ.
class Session:
    """Keeps the full conversation for one session without cutting messages."""

    # Initialise a new session with the selected language,
    # an empty message list and the current date and time.
    def __init__(self, language="English"):
        self.language = language

        # Stores both patient messages and MedIQ responses.
        # Each message contains a role and its text.
        self.messages = []

        # Records when the session started.
        self.started_at = datetime.now()


    # MESSAGE STORAGE

    def add(self, role, text):
        """Add one patient or MedIQ message to the conversation."""

        # Ignore empty messages to keep the conversation clean.
        if not text or not str(text).strip():
            return

        # Store the message together with its sender.
        # The role identifies whether the message came
        # from the patient or MedIQ.
        self.messages.append({
            "role": role,
            "text": str(text).strip()
        })


    # CONVERSATION HISTORY FOR OPENAI

    def get_history_for_api(self):
        """
        Convert the full conversation into a text format.

        Used by main.py through ask_openai_with_full_history().

        Sending the complete conversation allows MedIQ to
        remember earlier messages and respond with context.

        Example:
        you: Jina langu ni Brian
        MedIQ: Sasa Brian...
        you: Nina headache
        MedIQ: ...
        """

        # Create an empty list for formatted messages.
        history = []

        # Retrieve every message in the current session
        # and format it using the sender's role and message text.
        for m in self.messages:
            history.append(f"{m['role']}: {m['text']}")

        # Combine all messages into one text string,
        # with each message appearing on a separate line.
        return "\n".join(history)


    # Return the total number of individual messages,
    # including both patient messages and MedIQ responses.
    def get_turn_count(self):
        """Return the number of messages in the session."""
        return len(self.messages)


    # MARKDOWN SESSION FORMAT

    def to_markdown(self, summary=""):
        """Prepare the full conversation and summary in Markdown format."""

        # Convert the session timestamp into a readable date and time.
        date_str = self.started_at.strftime("%d %B %Y %H:%M")

        # Create a list to hold the contents of the Markdown file.
        lines = []

        # Add the session heading and general session information.
        lines.append("# MedIQ - Hope Clinic - Saved Session")
        lines.append(f"Date: {date_str}")
        lines.append(f"Language: {self.language}")
        lines.append(f"Total turns: {len(self.messages)}")
        lines.append("")

        # Create a section for the complete conversation.
        lines.append("## Conversation")
        lines.append("")

        # Add every patient message and MedIQ response
        # in the order in which they occurred.
        for m in self.messages:
            lines.append(f"{m['role']}: {m['text']}")
            lines.append("")

        # Create a separate section for the session summary.
        lines.append("## Summary")
        lines.append("")

        # Include the generated summary if available.
        # Otherwise, display a default message.
        lines.append(summary if summary.strip() else "No summary generated.")
        lines.append("")

        # Combine all the lines into a single Markdown document.
        return "\n".join(lines)


    # STRUCTURED SESSION DATA

    def to_dict(self, summary=""):
        """Convert the session into a dictionary for JSON storage."""

        # Organise session information into named fields.
        # This makes the saved data easier for other programs
        # to read, process or analyse.
        return {
            "tool": "MedIQ",
            "clinic": "Hope Clinic",
            "date": self.started_at.strftime("%Y-%m-%d %H:%M:%S"),
            "language": self.language,
            "total_turns": len(self.messages),
            "conversation": self.messages,
            "summary": summary
        }


    # SAVE COMPLETED SESSION

    def save(self, summary=""):
        """
        Save the complete conversation and summary in samples/.

        Two files are created:
        - Markdown (.md): Easy for people to read.
        - JSON (.json): Structured data for programmatic use.

        The session start date and time are included in the filename.

        Example:
        samples/session_2026-11-23_11-30-00.md
        """

        # Create the samples folder if it does not already exist.
        # exist_ok=True prevents an error if the folder exists.
        os.makedirs(SAMPLES_DIR, exist_ok=True)

        # Generate a filename using the session start date and time.
        filename_base = self.started_at.strftime("session_%Y-%m-%d_%H-%M-%S")

        # 1. Save the Markdown file.

        # Build the full file path.
        md_path = os.path.join(SAMPLES_DIR, filename_base + ".md")

        # Write the complete conversation and summary
        # in a human-readable format.
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(self.to_markdown(summary))

        # 2. Save the JSON file.

        # Build the full JSON file path.
        json_path = os.path.join(SAMPLES_DIR, filename_base + ".json")

        # Save the structured session dictionary as JSON.
        # indent=4 improves readability.
        # ensure_ascii=False preserves special language characters.
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(summary), f, indent=4, ensure_ascii=False)

        # Return both file paths to main.py so the application
        # can identify where the session was saved.
        return md_path, json_path

# RETRIEVE SAVED SESSIONS

def list_saved_sessions():
    """List saved sessions for Menu Option 2 - Past session."""

    # Return an empty list if the samples folder does not exist.
    if not os.path.exists(SAMPLES_DIR):
        return []

    # Find Markdown files whose names begin with "session_".
    # Only Markdown files are listed to avoid displaying
    # both versions of the same saved session.
    files = [f for f in os.listdir(SAMPLES_DIR) if f.startswith("session_") and f.endswith(".md")]

    # Sort sessions by filename, with the newest appearing first.
    files.sort(reverse=True)

    return files

# OPEN A PREVIOUS SESSION
def load_saved_session(filename):
    """Read the contents of a selected past session."""

    # Construct the path to the selected session file.
    path = os.path.join(SAMPLES_DIR, filename)

    try:
        # Open the file and return its complete contents.
        # main.py is responsible for displaying the contents.
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    # Return None if the file cannot be opened.
    # This allows main.py to handle the error.
    except OSError:
        return None

# PERSISTENT CONVERSATION MEMORY

def save_to_memory_file(messages):
    """
    Save recent conversation history in memory.txt.

    This file provides previous conversation context
    when another chat session begins.

    Only the last 40 lines are retained to limit the
    amount of memory stored.

    This is different from the complete saved sessions,
    which are stored separately in the samples folder.
    """

    # Create an empty string for the formatted conversation.
    text = ""

    # Convert the session messages into the memory.txt format.
    for m in messages:

        # Identify messages sent by the patient.
        if m["role"] == "you":
            text += f"\npatient: {m['text']}\n"

        # Format MedIQ responses.
        else:
            text += f"\nMedIQ: {m['text']}\n"

    # Retain only the last 40 lines of conversation history.
    # This prevents the memory file from growing indefinitely.
    text = "\n".join(text.splitlines()[-40:])

    # Write the recent conversation history to memory.txt.
    # Opening the file in write mode replaces its previous contents.
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        f.write(text)

    # Return the saved memory text.
    return text