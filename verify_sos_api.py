
import urllib.request
import json
import time

BASE_URL = "http://localhost:5000/api"

def test_sos_dispatch():
    print("--- 🚨 Testing Emergency SOS Dispatch ---")
    
    # 1. Create SOS Request (Simulated Patient)
    payload = {
        "name": "Verification Test Patient",
        "phone": "999-888-7777",
        "address": "Antigravity Test Lab, Sector 7",
        "latitude": 12.9716,
        "longitude": 77.5946
    }
    
    req = urllib.request.Request(f"{BASE_URL}/emergency/create", 
                                 data=json.dumps(payload).encode('utf-8'),
                                 headers={'Content-Type': 'application/json'},
                                 method='POST')
    
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode())
            print(f"✅ SOS Request Created: {res_data['message']}")
            req_id = res_data['data']['request_id']
            amb_info = res_data['data']['ambulance']
            print(f"🚑 Dispatched Ambulance: {amb_info['number']} (Driver: {amb_info['driver']})")
    except Exception as e:
        print(f"❌ SOS Request Failed: {e}")
        return

    # 2. Verify Admin Monitor (Simulated Admin)
    print("\n--- 🖥️ Verifying Admin Monitor ---")
    try:
        with urllib.request.urlopen(f"{BASE_URL}/admin/emergencies") as response:
            res_data = json.loads(response.read().decode())
            emergencies = res_data['data']
            latest = next((r for r in emergencies if r['id'] == req_id), None)
            if latest:
                print(f"✅ Admin sees SOS #{req_id} as {latest['status']} and assigned to {latest['assigned_driver']}")
            else:
                print(f"❌ SOS #{req_id} not found in Admin monitor")
    except Exception as e:
        print(f"❌ Admin Monitor Check Failed: {e}")

    # 3. Verify Ambulance Lock (Simulated Fleet Status)
    print("\n--- 🚐 Verifying Ambulance Status Lock ---")
    try:
        with urllib.request.urlopen(f"{BASE_URL}/admin/ambulances") as response:
            res_data = json.loads(response.read().decode())
            ambulances = res_data['data']
            assigned_amb = next((a for a in ambulances if a['driver_name'] == amb_info['driver']), None)
            if assigned_amb and assigned_amb['status'] == 'Busy':
                print(f"✅ Ambulance {assigned_amb['vehicle_number']} is correctly marked as BUSY")
            else:
                print(f"❌ Ambulance status mismatch: {assigned_amb['status'] if assigned_amb else 'Not found'}")
    except Exception as e:
        print(f"❌ Fleet Status Check Failed: {e}")

if __name__ == "__main__":
    test_sos_dispatch()
