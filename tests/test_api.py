import requests
import json
import time

BASE_URL = "http://localhost:5000/api"

def test_flow():
    print("Step 1: Submitting positive feedback...")
    payload = {
        "patient_id": "P-1001",
        "feedback_text": "The doctor was amazing and the surgery went well. Highly recommend!"
    }
    res = requests.post(f"{BASE_URL}/feedback", json=payload)
    print(res.json())

    print("\nStep 2: Submitting negative feedback (Critical)...")
    payload = {
        "patient_id": "P-1002",
        "feedback_text": "I am considering a lawsuit. The wrong medication was given and the nurse was extremely rude."
    }
    res = requests.post(f"{BASE_URL}/feedback", json=payload)
    print(res.json())

    print("\nStep 3: Checking recovery tasks...")
    res = requests.get(f"{BASE_URL}/tasks")
    print(res.json())

    print("\nStep 4: Checking SLA breaches...")
    res = requests.post(f"{BASE_URL}/sla/check")
    print(res.json())

if __name__ == "__main__":
    # Note: Backend must be running for this to work
    try:
        test_flow()
    except Exception as e:
        print(f"Error: {e}. Make sure the backend server is running on port 5000.")
