
import requests
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_flow():
    print("🚀 Starting Application Verification...")
    
    # 1. Home Page & Analytics Check
    try:
        res = requests.get(BASE_URL)
        if res.status_code == 200:
            print("✅ Home Page is UP.")
            if "/_vercel/insights/script.js" in res.text:
                print("✅ Vercel Analytics detected.")
            else:
                print("❌ Vercel Analytics MISSING.")
                
            if "/_vercel/speed-insights/script.js" in res.text:
                print("✅ Speed Insights detected.")
            else:
                print("❌ Speed Insights MISSING.")
        else:
            print(f"❌ Home Page Failed: {res.status_code}")
            return
    except Exception as e:
        print(f"❌ Server not running? {e}")
        return

    # 2. Registration
    email = "test_user_cz@example.com"
    password = "password123"
    payload = {
        "email": email,
        "password": password,
        "full_name": "Test Uzivatel",
        "subscription_tier": "BASIC"
    }
    
    print(f"\n🔹 Registering user: {email}...")
    # Cleanup previous run if exists (this is a simple script, might fail if user exists, handling that)
    # Actually register endpoint returns error if exists, which verifies logic too.
    
    res = requests.post(f"{BASE_URL}/auth/register", json=payload)
    if res.status_code == 200 or res.status_code == 201:
        print("✅ Registration Successful.")
    elif res.status_code == 400 and "exists" in res.text:
        print("⚠️ User already exists (Expected on re-run).")
    else:
        print(f"❌ Registration Failed: {res.text}")

    # 3. Login
    print("\n🔹 Logging in...")
    res = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
    if res.status_code == 200:
        token = res.json().get("access_token")
        if token:
            print("✅ Login Successful. Token received.")
        else:
            print("❌ Login Failed: No token.")
            return
    else:
        print(f"❌ Login Failed: {res.text}")
        return

    # 4. Protected Search (Czech Declension)
    print("\n🔹 Testing Search: 'Byt v Praze'...")
    cookies = {"access_token": token}
    # Using the form endpoint simulating HTMX/Browser submission
    res = requests.post(f"{BASE_URL}/search", data={"prompt": "Byt v Praze do 15M"}, cookies=cookies)
    
    if res.status_code == 200:
        if "Nalezeno" in res.text:
            print("✅ Search Successful (Czech UI detected).")
            # Extract count check
            import re
            match = re.search(r"Nalezeno (\d+)", res.text)
            if match:
                count = int(match.group(1))
                print(f"   -> Found {count} properties.")
                if count > 0:
                     print("   -> Results populated correctly.")
                else:
                     print("   ⚠️ No results found (might be valid if API returned 0).")
        else:
            print("❌ Search Page Loaded but 'Nalezeno' text missing (Localization issue?).")
    else:
        print(f"❌ Search Failed: {res.status_code}")

    print("\n🎉 Verification Complete.")

if __name__ == "__main__":
    test_flow()
