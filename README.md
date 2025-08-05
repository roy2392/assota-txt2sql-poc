
# Assuta Text-to-SQL Chatbot

This project is a simple web-based chatbot that allows users to ask questions in Hebrew about their appointments. The chatbot uses Google's Gemini Pro model to understand natural language queries and retrieve information from a SQLite database.

## Features

-   **Natural Language Understanding:** Uses the Gemini Pro API to interpret user questions.
-   **Database Integration:** Connects to a SQLite database to fetch appointment data.
-   **Web-Based UI:** Provides a simple and clean chat interface using Flask and Bootstrap.
-   **Hebrew Language Support:** The chatbot is configured to respond in Hebrew.

## Project Structure

```
.
├── app.py                  # Flask web application
├── chatbot.py              # Original command-line chatbot script
├── data
│   └── db.csv              # CSV data for appointments
├── db_setup.py             # Script to create and populate the SQLite database
├── requirements.txt        # Python dependencies
├── static/
├── system_prompt.txt       # System prompt for the Gemini model
├── templates
│   └── index.html          # HTML template for the chat UI
└── venv/                     # Virtual environment directory
```

## Setup and Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd assota_txt2sql_poc
```

### 2. Create and Activate a Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up the Database

Run the `db_setup.py` script to create the `app_database.db` file from the CSV data.

```bash
python3 db_setup.py
```

### 5. Configure the API Key

Create a `.env` file in the root directory and add your Gemini API key:

```
GEMINI_API_KEY="YOUR_API_KEY"
```

## Running the Application

To start the Flask web server, run:

```bash
python3 app.py
```

Open your web browser and navigate to `http://127.0.0.1:5000` to start chatting.

## Command-Line Chatbot (Optional)

The original command-line version of the chatbot is also available. To use it, run:

```bash
python3 chatbot.py <user_id> "<your_question>"
```

For example:

```bash
python3 chatbot.py "0014J00000JAuIGQA1" "What are my upcoming appointments?"
```
