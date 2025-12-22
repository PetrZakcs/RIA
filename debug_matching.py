import json
import difflib
import os

def test_matching():
    # Load Dict
    with open("src/common/cz_municipalities.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    munis = data.get("municipalities", [])
    names = [m['hezkyNazev'] for m in munis]
    print(f"Loaded {len(names)} municipalities.")
    
    # Test Case
    user_input = "byt v chomutově"
    clean_prompt = user_input.lower()
    
    stop_words_loc = set(["byt", "dum", "v", "na", "u", "prodej", "pronajem", "okres", "kraj", "do", "cena"])
    user_words = [w for w in clean_prompt.split() if w not in stop_words_loc and len(w)>2]
    
    print(f"User Words: {user_words}")
    
    for w in user_words:
        print(f"Testing word: {w}")
        # 1. Exact Caseless
        # 2. Difflib
        matches = difflib.get_close_matches(w.capitalize(), names, n=3, cutoff=0.6) # Lower cutoff to see what happens
        print(f"Matches for '{w}': {matches}")
        
        # Test "Chomutov" specifically
        if "Chomutov" in names:
            print("Chomutov is in the list.")
        else:
            print("Chomutov is NOT in the list (Check accents?)")

if __name__ == "__main__":
    test_matching()
