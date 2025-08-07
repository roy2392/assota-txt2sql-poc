import pandas as pd
import sqlite3
import random

def setup_database():
    # Read the CSV file into a pandas DataFrame
    df = pd.read_csv('data/appointments_cleaned_for_bigquery.csv')

    # Data Cleaning and Preprocessing
    df.columns = df.columns.str.strip()
    df = df.drop_duplicates()

    # Convert date column to datetime objects
    df['appointment_date_time_c'] = pd.to_datetime(df['appointment_date_time_c'], errors='coerce')

    # Create a connection to the SQLite database
    conn = sqlite3.connect('app_database.db')
    cursor = conn.cursor()

    # Drop tables if they exist
    cursor.execute("DROP TABLE IF EXISTS appointments")
    cursor.execute("DROP TABLE IF EXISTS accounts")

    # Create the appointments table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS appointments (
        row_id TEXT PRIMARY KEY,
        user_id TEXT,
        appointment_type TEXT,
        appointment_date_time TEXT,
        appointment_status TEXT,
        cancel_reason_code TEXT,
        record_type TEXT,
        site_name TEXT,
        site_address TEXT,
        site_instructions TEXT
    )
    ''')

    # Create the accounts table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS accounts (
        user_id TEXT PRIMARY KEY,
        user_name TEXT,
        age INTEGER
    )
    ''')

    # Insert data into the appointments table
    for _, row in df.iterrows():
        cursor.execute('''
        INSERT OR REPLACE INTO appointments (row_id, user_id, appointment_type, appointment_date_time, appointment_status, cancel_reason_code, record_type, site_name, site_address, site_instructions)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (row['row_id'], row['user_id'], row['appoitment_type'], str(row['appointment_date_time_c']), row['appointment_status'], row['cancel_reason_code'], row['record_type'], row['site_name'], row['site_address'], row['site_instructions']))

    # Insert unique user_ids and random names into the accounts table
    hebrew_names = ["יוסי", "דוד", "משה", "אברהם", "יצחק", "יעקב", "שלמה", "אהרון", "שמואל", "אליהו"]
    unique_user_ids = df['user_id'].unique()
    for user_id in unique_user_ids:
        cursor.execute('''
        INSERT OR REPLACE INTO accounts (user_id, user_name, age)
        VALUES (?, ?, ?)
        ''', (user_id, random.choice(hebrew_names), random.randint(10, 90)))

    # Commit the changes and close the connection
    conn.commit()
    conn.close()

if __name__ == '__main__':
    setup_database()