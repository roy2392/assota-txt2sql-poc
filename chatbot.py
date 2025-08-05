
import sqlite3
import google.generativeai as genai
import os
import sys

def get_user_data(user_id):
    conn = sqlite3.connect('app_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM appointments WHERE user_id=?", (user_id,))
    user_data = cursor.fetchall()
    conn.close()
    return user_data

def main():
    # Configure the Gemini API key
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')

    if len(sys.argv) < 3:
        print("Usage: python chatbot.py <user_id> <question>")
        return

    user_id = sys.argv[1]
    user_question = sys.argv[2]
    user_data = get_user_data(user_id)

    if not user_data:
        print("User not found.")
        return

    prompt = f"Context: The user with user_id {user_id} has the following appointments: {user_data}. Question: {user_question}. Answer:"
    response = model.generate_content(prompt)
    print(response.text)

if __name__ == '__main__':
    main()
