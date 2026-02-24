
import urllib.request
import urllib.parse
import json
import http.cookiejar

BASE_URL = "http://localhost:5000"

# Setup cookie jar for session management
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

def login(email, password):
    print(f"--- 🔑 Logging in as {email} ---")
    data = urllib.parse.urlencode({"email": email, "password": password}).encode()
    try:
        req = urllib.request.Request(f"{BASE_URL}/login", data=data, method='POST')
        with opener.open(req) as response:
            if "Dashboard" in response.read().decode():
                print("✅ Login Successful")
                return True
            else:
                print("❌ Login Failed (Check credentials)")
                return False
    except Exception as e:
        print(f"❌ Login Error: {e}")
        return False

def test_sos_dispatch():
    print("\n--- 🚨 Testing Emergency SOS Dispatch ---")
    
    # 1. Create SOS Request (Public endpoint)
    payload = {
        "name": "Authenticated Verification Patient",
        "phone": "123-456-7890",
        "address": "Antigravity HQ",
        "latitude": 12.9345,
        "longitude": 77.6101
    }
    
    req = urllib.request.Request(f"{BASE_URL}/api/emergency/create", 
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

    # 2. Login as Admin to check monitor
    if login("admin@careaxis.com", "admin123"):
        print("\n--- 🖥️ Verifying Admin Monitor ---")
        try:
            with opener.open(f"{BASE_URL}/api/admin/emergencies") as response:
                res_data = json.loads(response.read().decode())
                emergencies = res_data['data']
                latest = next((r for r in emergencies if r['id'] == req_id), None)
                if latest:
                    print(f"✅ Admin sees SOS #{req_id} as {latest['status']} and assigned to {latest['assigned_driver']}")
                else:
                    print(f"❌ SOS #{req_id} not found in Admin monitor")
                    
            with opener.open(f"{BASE_URL}/api/admin/ambulances") as response:
                res_data = json.loads(response.read().decode())
                ambulances = res_data['data']
                assigned_amb = next((a for a in ambulances if a['driver_name'] == amb_info['driver']), None)
                if assigned_amb and assigned_amb['status'] == 'Busy':
                    print(f"✅ Ambulance {assigned_amb['vehicle_number']} is correctly marked as BUSY")
                else:
                    print(f"❌ Ambulance status mismatch: {assigned_amb['status'] if assigned_amb else 'Not found'}")
        except Exception as e:
            print(f"❌ Admin Verification Failed: {e}")

    # 3. Login as Driver to verify alert
    driver_email = "sumeet@careaxis.com" # Dispatched above (nearest to 12.9345, 77.6101 is AMB-002)
    if login(driver_email, "driver123"):
        print(f"\n--- 📢 Verifying Driver Alert for {driver_email} ---")
        try:
            with opener.open(f"{BASE_URL}/api/driver/emergency-status") as response:
                res_data = json.loads(response.read().decode())
                if res_data['status'] == 'success' and res_data['data']:
                    alert = res_data['data']
                    print(f"✅ Driver received alert for SOS #{alert['id']} (Patient: {alert['patient_name']})")
                    
                    # 4. Accept the Mission
                    print(f"--- 🏁 Accepting Mission ---")
                    req_accept = urllib.request.Request(f"{BASE_URL}/api/driver/accept/{alert['id']}", method='POST')
                    with opener.open(req_accept) as res_acc:
                        acc_data = json.loads(res_acc.read().decode())
                        print(f"✅ Mission Accepted: {acc_data['message']}")
                        
                    # 5. Complete the Mission (Free up ambulance)
                    print(f"--- ✅ Completing Mission (Resets status to Available) ---")
                    req_comp = urllib.request.Request(f"{BASE_URL}/api/driver/complete/{alert['id']}", method='POST')
                    with opener.open(req_comp) as res_comp:
                        comp_data = json.loads(res_comp.read().decode())
                        print(f"✅ Mission Completed: {comp_data['message']}")
                        
                    # 6. Verify status reset in Admin monitor
                    login("admin@careaxis.com", "admin123")
                    with opener.open(f"{BASE_URL}/api/admin/ambulances") as response:
                        res_data = json.loads(response.read().decode())
                        ambulances = res_data['data']
                        freed_amb = next((a for a in ambulances if a['driver_name'] == amb_info['driver']), None)
                        if freed_amb and freed_amb['status'] == 'Available':
                            print(f"✅ Ambulance {freed_amb['vehicle_number']} is back to AVAILABLE status")
                        else:
                            print(f"❌ Status reset failed: {freed_amb['status'] if freed_amb else 'Not found'}")
                            
                else:
                    print("❌ No alert found for the assigned driver")
        except Exception as e:
            print(f"❌ Driver Verification Failed: {e}")

if __name__ == "__main__":
    test_sos_dispatch()
