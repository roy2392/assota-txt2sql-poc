# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install uv for faster Python package management
RUN pip install uv

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container
COPY . .

# Run the database setup script
RUN python db_setup.py

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define environment variables
ENV GEMINI_API_KEY=""
ENV OPENAI_API_KEY=""
ENV LANGCHAIN_TRACING_V2=""
ENV LANGCHAIN_API_KEY=""
ENV LANGCHAIN_PROJECT="assota-txt2sql-poc"

# Clickhouse MCP environment variables
ENV CLICKHOUSE_HOST="ra8f4bs5ok.eu-central-1.aws.clickhouse.cloud"
ENV CLICKHOUSE_PORT="8443"
ENV CLICKHOUSE_USER="default"
ENV CLICKHOUSE_PASSWORD="89Y9.vJt~7wcg"
ENV CLICKHOUSE_SECURE="true"
ENV CLICKHOUSE_VERIFY="true"
ENV CLICKHOUSE_CONNECT_TIMEOUT="30"
ENV CLICKHOUSE_SEND_RECEIVE_TIMEOUT="30"

# Run app.py when the container launches
CMD ["python", "app.py"]