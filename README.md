# CarePlus AI Clinic Assistant

CarePlus is a multi-agent clinic booking app built with Streamlit, LangGraph, and Groq. It guides patients through booking appointments, managing existing appointments, and handling emergency-related requests.

## Features

- Appointment booking with speciality, doctor, date, time, and patient detail collection
- Rescheduling and cancellation flow using a phone number lookup
- Emergency routing that can search for nearby hospitals
- Confirmation emails and calendar invite generation
- Streamlit chat UI with quick replies, typing indicators, and light/dark mode
- Terminal logging for database activity and app startup

## Tech Stack

- Frontend: Streamlit
- Orchestration: LangGraph
- LLM API: Groq
- Database: PostgreSQL on Render
- Email and calendar: `smtplib`, `ics`
- Emergency search: DuckDuckGo-based search tool

## Project Structure

```text
data/              Database connection and CRUD helpers
agent/             Booking, reschedule, and emergency agents
tools/             Shared service helpers
ui/                Streamlit app and launcher
.streamlit/        Streamlit config
```

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Create a `.env` file in the project root:

```env
GROQ_API_KEY="your_groq_api_key_here"
DATABASE_URL="postgresql://user:password@host:5432/database_name"
SMTP_EMAIL="your_clinic_email@gmail.com"
SMTP_PASSWORD="your_google_app_password"
```

3. Run the app:

```bash
streamlit run ui/streamlit.py
```

## Notes

- The app now uses PostgreSQL from `DATABASE_URL` instead of SQLite.
- On startup, the app initializes the schema and seeds the doctor list if needed.
- If SMTP credentials are missing, email sending falls back to mock mode and logs to the terminal.
- The terminal prints database connection and query logs, which is helpful while testing booking and rescheduling.

## UI

The current UI is a chat-first clinic intake layout with:

- a compact sidebar
- a simple clinic logo mark
- light and dark mode support
- quick reply buttons for the booking flow

## Run From Source

If you are developing locally, the launcher remains:

```bash
streamlit run ui/streamlit.py
```

## Contributing

Pull requests and issues are welcome.
