import requests
import time

BASE_URL = "http://localhost:8000"

def verify_gating():
    print("--- Verifying Feature Gating ---")
    
    # 1. Register BASIC User
    email_basic = f"basic_{int(time.time())}@example.com"
    print(f"1. Registering BASIC User: {email_basic}")
    r = requests.post(f"{BASE_URL}/auth/register", json={
        "email": email_basic, "password": "pass", "full_name": "Basic User", "subscription_tier": "BASIC"
    })
    if r.status_code != 200:
        print(f"  ❌ Register Failed: {r.text}")
        return

    # 2. Login BASIC
    print("2. Logging in BASIC")
    r = requests.post(f"{BASE_URL}/auth/login", json={"email": email_basic, "password": "pass"})
    token_basic = r.json()["access_token"]
    cookies_basic = {"access_token": token_basic}

    # 3. Test Blocked Search (Whole CZ)
    print("3. Testing BLOCKED Search (Generic 'Byt na prodej') for BASIC")
    # Prompt implies universal search (no specific location found in app.py logic)
    r = requests.post(f"{BASE_URL}/search", data={"prompt": "Byt na prodej"}, cookies=cookies_basic)
    
    if "Upgrade Required" in r.text:
        print("  ✅ Access CORRECTLY Blocked (Upgrade page found)")
    else:
        print("  ❌ Access INCORRECTLY Allowed or Error")
        # print(r.text[:200])

    # 4. Test Allowed Search (Specific Location)
    print("4. Testing ALLOWED Search ('Byt v Praze') for BASIC")
    r = requests.post(f"{BASE_URL}/search", data={"prompt": "Byt v Praze"}, cookies=cookies_basic)
    if "Upgrade Required" not in r.text and r.status_code == 200:
        print("  ✅ Access CORRECTLY Allowed")
    else:
        print(f"  ❌ Access Blocked or Failed: {r.status_code}")

    # 5. Register BUSINESS User
    email_biz = f"biz_{int(time.time())}@example.com"
    print(f"5. Registering BUSINESS User: {email_biz}")
    requests.post(f"{BASE_URL}/auth/register", json={
        "email": email_biz, "password": "pass", "full_name": "Biz User", "subscription_tier": "BUSINESS"
    })
    
    # 6. Login BUSINESS
    r = requests.post(f"{BASE_URL}/auth/login", json={"email": email_biz, "password": "pass"})
    token_biz = r.json()["access_token"]
    cookies_biz = {"access_token": token_biz}
    
    # 7. Test Allowed Universal Search
    print("7. Testing ALLOWED Universal Search for BUSINESS")
    r = requests.post(f"{BASE_URL}/search", data={"prompt": "Byt na prodej"}, cookies=cookies_biz)
    if "Upgrade Required" not in r.text and r.status_code == 200:
        print("  ✅ Access CORRECTLY Allowed for Business")
    else:
        print("  ❌ Access Blocked for Business")

if __name__ == "__main__":
    verify_gating()
