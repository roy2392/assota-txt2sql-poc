# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container
COPY . .

# Run the database setup script
RUN python db_setup.py

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Define environment variable
ENV GEMINI_API_KEY=""

# Run app.py when the container launches
CMD ["python", "app.py"]