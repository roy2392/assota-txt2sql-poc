# Assuta Text-to-SQL Chatbot

This project is a simple web-based chatbot that allows users to ask questions in Hebrew about their appointments. The chatbot uses Google's Gemini API to understand natural language queries and retrieve information from a SQLite database.

## Features

-   **Natural Language Understanding:** Uses the Gemini API to interpret user questions.
-   **Database Integration:** Connects to a SQLite database to fetch appointment data.
-   **Web-Based UI:** Provides a simple and clean chat interface using Flask and Bootstrap.
-   **Hebrew Language Support:** The chatbot is configured to respond in Hebrew using a system prompt.
-   **Dockerized:** Includes a Dockerfile for easy containerization and deployment.

## Screenshot

![Assuta Chatbot UI](data/screenshot.png)

## Project Structure

```
.
├── .env                    # Environment variables (contains GEMINI_API_KEY)
├── .gitignore              # Git ignore file
├── Dockerfile              # Dockerfile for building the container image
├── app.py                  # Flask web application
├── data/
│   └── db.csv              # CSV data for appointments
├── db_setup.py             # Script to create and populate the SQLite database
├── requirements.txt        # Python dependencies
├── system_prompt.txt       # System prompt for the Gemini model
└── templates/
    └── index.html          # HTML template for the chat UI
```

## Setup and Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
# Assota Text-to-SQL PoC

This is a proof-of-concept for a text-to-SQL chatbot using Google's Gemini API.

## Architecture

The application is a Flask-based web server that provides a chat interface for interacting with a Gemini-powered chatbot. The chatbot is designed to answer questions about appointments by querying a local SQLite database.

### Data Flow

1.  **Database Setup:** When the application starts, it checks for the existence of a local SQLite database (`app_database.db`). If the database doesn't exist, it's created and populated with data from a CSV file (`data/appointments_cleaned_for_bigquery.csv`).

2.  **User Interaction:** The user interacts with the chatbot through a simple web interface. When a user starts a new chat, they are prompted to enter their user ID.

3.  **LLM Interaction:** Once the user ID is provided, the application fetches the user's appointment data from the database and sends it to the Gemini API as part of a system prompt. This prompt instructs the Gemini model to act as a helpful assistant and to use the provided data to answer the user's questions.

4.  **Response Generation:** The Gemini model processes the user's questions and the provided data to generate a natural language response. This response is then displayed to the user in the chat interface.

## Running the Application

### With Docker

1.  **Build the Docker image:**
    ```bash
    docker build -t assota-chatbot .
    ```

2.  **Run the Docker container:**
    ```bash
    docker run -p 5000:5000 -e GEMINI_API_KEY="YOUR_API_KEY" assota-chatbot
    ```
    Replace `"YOUR_API_KEY"` with your actual Gemini API key.

3.  Open your browser and navigate to `http://localhost:5000`.

### Locally

1.  **Install the required packages:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Set up the database:**
    ```bash
    python db_setup.py
    ```

3.  **Run the application:**
    ```bash
    python app.py
    ```

4.  Open your browser and navigate to `http://localhost:5000`.

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

## Running with Docker

You can also run the application using Docker.

### 1. Build the Docker Image

```bash
docker build -t assota-chatbot .
```

### 2. Run the Docker Container

Make sure to pass your Gemini API key as an environment variable.

```bash
docker run -p 5000:5000 -e GEMINI_API_KEY="YOUR_API_KEY" assota-chatbot
```

The application will be accessible at `http://127.0.0.1:5000`.