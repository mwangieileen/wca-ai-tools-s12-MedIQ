# wca-ai-tools-s12-MedIQ

# About the Project

MedIQ is a Clinic FAQ Assistant developed using Python and OpenAI's API.

The assistant helps patients access information about a clinic, including:

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
- Uses OpenAI to generate conversational responses.

## Requirements

Before running MedIQ, you need:

- Python installed on your computer.
- An OpenAI API key.
- Git installed on your computer.

## Installation and Setup

### 1. Clone the repository

Open your terminal and run:

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
```

Navigate into the downloaded project folder:

```bash
cd wca-ai-tools-s12-MedIQ
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate the virtual environment.

**Windows:**

```bash
venv\Scripts\activate
```

**macOS/Linux:**

```bash
source venv/bin/activate
```

### 3. Install the required packages

```bash
pip install -r requirements.txt
```

### 4. Configure your OpenAI API key

MedIQ uses OpenAI's API to generate responses.

1. Visit [OpenAI Platform](https://platform.openai.com/).
2. Sign in and create an API key.
3. In the main project folder, create a file named `.env`.
4. Add your API key in the following format:

```env
OPENAI_API_KEY='your_api_key_here'
```

Replace '`your_api_key_here`' with your actual API key.

**Note:** Kindly keep your API key private. Never share it or upload your `.env` file to GitHub.

### 5. Run MedIQ

In your terminal, run:

```bash
python main.py
```

Follow the instructions displayed to start interacting with MedIQ.

## Technologies Used

- Python
- OpenAI API (GPT-4.1-mini)
- JSON
- python-dotenv

## Developers

- Evonah Ombiro
- Eileen Mwangi
- Shadrack Opiyo

## Disclaimer

MedIQ is an informational clinic assistance tool. It does not diagnose medical conditions or replace professional medical advice. Patients experiencing emergencies are expected to seek immediate medical attention.
