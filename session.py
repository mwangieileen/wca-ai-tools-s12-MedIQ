# session.py
# Handles Conversation Memory + Saved Session for MedIQ
# PDF rules:
# - Conversation Memory: Full list of messages sent with each API call, supports at least 4 turns
# - Saved Session: Save full conversation + summary to .json or .md with date in file name, in samples/ folder

import os
import json
from datetime import datetime

SAMPLES_DIR = "samples"
MEMORY_FILE = "memory.txt"

class Session:
    """Keeps FULL conversation for ONE session. Never cuts turns."""

    def __init__(self, language="English"):
        self.language = language
        self.messages = []  # list of {"role": "you" / "MedIQ", "text": "..."}
        self.started_at = datetime.now()

    def add(self, role, text):
        """Add ONE message - called for EVERY turn, you + MedIQ."""
        if not text or not str(text).strip():
            return
        self.messages.append({
            "role": role,
            "text": str(text).strip()
        })

    def get_history_for_api(self):
        """
        Return FULL list for EVERY API call.
        Used by main.py -> ask_gemini_with_full_history()
        This is what makes 4+ turns work.
        Example:
        you: Jina langu ni Brian
        MedIQ: Sasa Brian...
        you: Nina headache
        MedIQ: ...
        """
        history = []
        for m in self.messages:
            history.append(f"{m['role']}: {m['text']}")
        return "\n".join(history)

    def get_turn_count(self):
        """How many messages in this session."""
        return len(self.messages)

    def to_markdown(self, summary=""):
        """Build .md file: full conversation + summary."""
        date_str = self.started_at.strftime("%d %B %Y %H:%M")
        lines = []
        lines.append("# MedIQ - Hope Clinic - Saved Session")
        lines.append(f"Date: {date_str}")
        lines.append(f"Language: {self.language}")
        lines.append(f"Total turns: {len(self.messages)}")
        lines.append("")
        lines.append("## Conversation")
        lines.append("")
        for m in self.messages:
            lines.append(f"{m['role']}: {m['text']}")
            lines.append("")
        lines.append("## Summary")
        lines.append("")
        lines.append(summary if summary.strip() else "No summary generated.")
        lines.append("")
        return "\n".join(lines)

    def to_dict(self, summary=""):
        return {
            "tool": "MedIQ",
            "clinic": "Hope Clinic",
            "date": self.started_at.strftime("%Y-%m-%d %H:%M:%S"),
            "language": self.language,
            "total_turns": len(self.messages),
            "conversation": self.messages,
            "summary": summary
        }

    def save(self, summary=""):
        """
        Save to samples/ with DATE in filename.
        Creates BOTH .md (for examiner to read) + .json (for marking).
        Example: samples/session_2026-11-23_11-30.md
        """
        os.makedirs(SAMPLES_DIR, exist_ok=True)
        filename_base = self.started_at.strftime("session_%Y-%m-%d_%H-%M-%S")
        # 1. .md file
        md_path = os.path.join(SAMPLES_DIR, filename_base + ".md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(self.to_markdown(summary))

        # 2. .json file
        json_path = os.path.join(SAMPLES_DIR, filename_base + ".json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(summary), f, indent=4, ensure_ascii=False)

        return md_path, json_path

def list_saved_sessions():
    """List all saved sessions in samples/ for Menu option 2 - Past session."""
    if not os.path.exists(SAMPLES_DIR):
        return []
    files = [f for f in os.listdir(SAMPLES_DIR) if f.startswith("session_") and f.endswith(".md")]
    files.sort(reverse=True)  # newest first
    return files

def load_saved_session(filename):
    """Open and display one past session file."""
    path = os.path.join(SAMPLES_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None

def save_to_memory_file(messages):
    """
    Keep memory.txt for NEXT chat context.
    Last 40 lines only = last 20 turns.
    This is NOT the Saved Session - Saved Session is in samples/.
    messages = list of {"role": ..., "text": ...} from Session.messages
    """
    text = ""
    for m in messages:
        # Convert Session format to memory.txt format
        if m["role"] == "you":
            text += f"\npatient: {m['text']}\n"
        else:
            text += f"\nMedIQ: {m['text']}\n"
    text = "\n".join(text.splitlines()[-40:])
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        f.write(text)
    return text