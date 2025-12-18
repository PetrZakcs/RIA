import requests
import json
import time

BASE_URL = "http://localhost:8000"

def verify_auth():
    print("--- Verifying Auth Endpoints ---")
    
    # 1. Register User (Randomize to allow re-runs)
    email = f"test_{int(time.time())}@example.com"
    payload = {
        "email": email,
        "password": "strongpassword123",
        "full_name": "Test User",
        "subscription_tier": "BASIC"
    }
    
    print(f"1. Registering: {email}")
    try:
        r = requests.post(f"{BASE_URL}/auth/register", json=payload)
        if r.status_code == 200:
            print("  ✅ Register Success")
            user_data = r.json()
            print(f"  User ID: {user_data.get('id')}")
        else:
            print(f"  ❌ Register Failed: {r.status_code} {r.text}")
            return
    except:
        print("  ❌ Connection Failed (Server running?)")
        return

    # 2. Login
    print("2. Logging In")
    login_payload = {
        "email": email,
        "password": "strongpassword123"
    }
    try:
        # Note: My endpoint expects JSON body (dict), which is standard for my implementation
        # Standard OAuth2 uses form-data, but I implemented JSON in auth.py
        r = requests.post(f"{BASE_URL}/auth/login", json=login_payload)
        
        if r.status_code == 200:
            data = r.json()
            token = data.get("access_token")
            if token:
                print(f"  ✅ Login Success. Token: {token[:15]}...")
            else:
                print("  ❌ Login Success but No Token??")
        else:
            print(f"  ❌ Login Failed: {r.status_code} {r.text}")
    except Exception as e:
        print(f"  ❌ Error: {e}")

    # 3. Check Homepage for Auth JS
    print("3. Checking Homepage Content")
    r = requests.get(f"{BASE_URL}/")
    if "localStorage.getItem('access_token')" in r.text:
         print("  ✅ Homepage contains Auth JS")
    else:
         print("  ❌ Homepage missing Auth JS")

if __name__ == "__main__":
    verify_auth()
