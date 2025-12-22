import requests
import json

def verify_access():
    url = "http://127.0.0.1:8000/search"
    
    # 1. Test Whole CZ Search (formerly restricted)
    # sending 'byt v chomutove' to test fuzzy match
    payload = {"prompt": "byt v chomutove"} 
    
    print("Testing Search for 'byt v chomutove'...")
    try:
        resp = requests.post(url, data=payload)
        
        if resp.status_code == 200:
            if "Je vyžadován Upgrade" in resp.text:
                print("FAIL: Still seeing Upgrade Wall")
            elif "Nebyly nalezeny žádné výsledky" in resp.text:
                 # This might happen if harvester finds 0 items, but it proves we passed the wall.
                 print("SUCCESS: Passed Wall (No results found, but access granted)")
            elif "results-container" in resp.text or "card" in resp.text:
                 print("SUCCESS: Passed Wall and got Results")
            else:
                 print("SUCCESS: Endpoint returned 200 (Content check ambiguous)")
                 # print(resp.text[:500])
        else:
            print(f"FAIL: Status {resp.status_code}")
            
    except Exception as e:
        print(f"Error connecting: {e}")
        print("Is server running?")

if __name__ == "__main__":
    verify_access()
