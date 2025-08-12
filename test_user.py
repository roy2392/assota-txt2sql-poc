#!/usr/bin/env python3

import requests
import json

def test_chatbot():
    base_url = "http://localhost:5000"
    
    print("Starting test session...")
    
    # Start chat session
    response = requests.post(f"{base_url}/start")
    if response.status_code == 200:
        data = response.json()
        session_id = data['session_id']
        print(f"Session ID: {session_id}")
        if 'responses' in data:
            for i, msg in enumerate(data['responses']):
                print(f"Bot initial message {i+1}: {msg}")
        elif 'response' in data:
            print(f"Bot initial message: {data['response']}")
    else:
        print(f"Failed to start session: {response.status_code}")
        return
    
    # Send user ID
    print("\nSending user ID...")
    response = requests.post(f"{base_url}/chat", 
                           json={"session_id": session_id, "message": "0017E00001JQT0pQAH"})
    if response.status_code == 200:
        data = response.json()
        print(f"Bot greeting response: {data.get('response', 'No response')}")
    else:
        print(f"Failed to send user ID: {response.status_code}")
        return
    
    # Test a regular message
    print("\nSending regular message...")
    response = requests.post(f"{base_url}/chat", 
                           json={"session_id": session_id, "message": "מתי התור הבא שלי?"})
    if response.status_code == 200:
        data = response.json()
        if 'responses' in data:
            for i, msg in enumerate(data['responses']):
                print(f"Bot response {i+1}: {msg}")
        else:
            print(f"Bot response: {data.get('response', 'No response')}")
    else:
        print(f"Failed to send message: {response.status_code}")
        return
    
    # Test another message
    print("\nSending another message...")
    response = requests.post(f"{base_url}/chat", 
                           json={"session_id": session_id, "message": "איך להגיע?"})
    if response.status_code == 200:
        data = response.json()
        if 'responses' in data:
            for i, msg in enumerate(data['responses']):
                print(f"Bot response {i+1}: {msg}")
        else:
            print(f"Bot response: {data.get('response', 'No response')}")
    else:
        print(f"Failed to send message: {response.status_code}")

if __name__ == "__main__":
    test_chatbot()