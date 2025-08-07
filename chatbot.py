
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
    try:
        with open('system_prompt.txt', 'r', encoding='utf-8') as f:
            system_prompt = f.read()
    except FileNotFoundError:
        print("Error: system_prompt.txt not found.")
        return

    model = genai.GenerativeModel(
        'gemini-1.5-flash',
        system_instruction=system_prompt
    )

    prompt = f"The user with user_id {user_id} has the following appointments: {user_data}. Question: {user_question}. Answer:"
    response = model.generate_content(prompt)
    print(response.text)

if __name__ == '__main__':
    main()
