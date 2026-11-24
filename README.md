# wca-ai-tools-s12-MedIQ

## About the Project

MedIQ is a Clinic FAQ Assistant developed using Python and Google's Gemini API.

The assistant answers patients' questions about a small clinic, including:

- Clinic opening hours
- Available services
- Consultation and service prices
- Appointment booking

During a session, MedIQ remembers what the patient has already asked to avoid repeating information. It also DOES NOT provide medical diagnoses.

## Features

- Answers clinic-related questions.
- Supports English, Swahili and Sheng.
- Remembers conversation history during a session.
- Assists patients with appointment booking.
- Identifies potential medical emergencies and provides appropriate guidance.
- Saves conversation sessions and summaries.

## Requirements

Before running MedIQ, you need:

- Python installed on your computer.
- A Google Gemini API key.
- Git installed on your computer.

## Installation and Setup

### 1. Clone the repository

Open your terminal and run:
  
    git clone YOUR_GITHUB_REPOSITORY_URL

Navigate into the downloaded project folder:

    cd wca-ai-tools-s12-MedIQ

### 2. Create a virtual environment

    python -m venv venv

Activate the virtual environment.

    **Windows:**

        venv\Scripts\activate


    **macOS/Linux:**

        source venv/bin/activate


### 3. Install the required packages

pip install -r requirements.txt

### 4. Configure your Gemini API key

MedIQ uses Google's Gemini API to generate responses.

1. Visit [Google AI Studio](https://aistudio.google.com/).
2. Sign in and create your own API key.
3. In the main project folder, create a file named `.env`.
4. Add your API key in the following format:

GEMINI_API_KEY='your_api_key_here'

Replace `your_api_key_here` with your actual API key.

**Note:** Keep your API key private. Do not share even to GitHub.

### 5. Run MedIQ

In your terminal, run:

python main.py


Follow the instructions displayed to start interacting with MedIQ.

## Technologies Used

- Python
- Google Gemini API
- JSON
- python-dotenv

## Developers

**Name:**   Evone
            Eileen

## Disclaimer

MedIQ is an informational clinic assistance tool. It does not diagnose medical conditions or replace professional medical advice. Patients experiencing emergencies should seek immediate medical attention.