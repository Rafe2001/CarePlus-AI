# 🏥 CarePlus AI Clinic Assistant
<img width="1920" height="1020" alt="image" src="https://github.com/user-attachments/assets/d394c00d-6d7f-4345-b000-0571814f65d0" />

An intelligent, multi-agent clinic booking system powered by **LangGraph** and **Groq**. 

CarePlus AI seamlessly manages the full appointment lifecycle autonomously. It acts as a digital front desk, allowing patients to select specialists, book time slots, and manage their schedules, while gracefully handling emergency scenarios.

## ✨ Features

- **Agentic Appointment Booking:** Guides users through selecting a medical speciality, choosing a doctor, picking an available date/time, and confirming the booking.
- **Smart Rescheduling & Cancellations:** Patients can manage their existing appointments using just their phone number. The bot autonomously interacts with the database to look up the booking and executes the cancellation or time-slot update.
- **Automated Email & Calendar Invites:** Upon booking confirmation, the system instantly generates an `.ics` calendar file and emails it to both the patient and the doctor.
- **Returning Patient Recognition:** Remembers returning patients by their phone number, welcoming them by name and skipping repetitive data collection.
- **Emergency Sub-Agent:** Automatically detects life-threatening situations and uses web-search tools to instantly find and route the patient to the nearest hospital based on their city or zip code.
- **Modern UI:** Built with Streamlit, featuring dynamic typing indicators, quick-reply buttons, and a clean chat interface.

## 🛠️ Technology Stack

- **AI Orchestration:** LangGraph (State management, conditional edges, multi-agent routing)
- **LLM Engine:** Groq API (`llama-3.3-70b-versatile` for ultra-fast inference)
- **Frontend:** Streamlit
- **Database:** SQLite (Relational mapping for Doctors, Patients, and Bookings)
- **Integrations:** `smtplib` (Automated Emails), `ics` (Calendar Invites), `ddgs` (DuckDuckGo Web Search)

## 🚀 Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/Rafe2001/CarePlus-AI.git
cd CarePlus-AI
```

### 2. Install Dependencies
Ensure you have Python installed, then run:
```bash
pip install -r requirements.txt
```

### 3. Set up Environment Variables
Create a `.env` file in the root directory and add your API credentials. 
*(Note: If `SMTP_PASSWORD` is omitted, the bot will run in "Mock Mode" and print emails to the terminal instead of sending them).*
```env
GROQ_API_KEY="your_groq_api_key_here"
SMTP_EMAIL="your_clinic_email@gmail.com"
SMTP_PASSWORD="your_16_char_google_app_password"
```

### 4. Run the Application
```bash
streamlit run ui/streamlit.py
```

## 🏗️ Architecture

The system utilizes a **Supervisor/Sub-Agent** architecture driven by LangGraph:
- **Greeting & Routing Node:** Evaluates user intent to determine the correct workflow.
- **Booking Agent:** A state-machine that collects necessary details sequentially (Speciality -> Doctor -> Date -> Time).
- **Reschedule Agent:** An autonomous tool-calling loop that executes Python functions to modify SQLite records.
- **Emergency Agent:** A highly-prioritized node that breaks out of standard flows to provide immediate, web-searched hospital data.

## 🤝 Contributing
Contributions are welcome! Feel free to open an issue or submit a pull request.
