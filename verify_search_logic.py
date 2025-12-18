import unicodedata
import os
import json

def slugify(text: str) -> str:
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    return text.lower().replace(" ", "-")

def test_location_logic(prompt: str):
    print(f"\n--- Testing Prompt: '{prompt}' ---")
    clean_prompt = prompt.lower()
    prompt_slug = slugify(prompt)
    region_id = None
    region_type = None

    known_locations = {
        "ceska republika": (-99, 'region'), "cr": (-99, 'region'), "cz": (-99, 'region'),
        "brno": (72, 'district'),
        "jihocesky": (1, 'region'), "budejovice": (1, 'region'),
        "plzensky": (2, 'region'), "plzen": (2, 'region'),
        "karlovarsky": (3, 'region'), "vary": (3, 'region'),
        "ustecky": (4, 'region'), "usti": (4, 'region'),
        "liberecky": (5, 'region'), "liberec": (5, 'region'),
        "kralovehradecky": (6, 'region'), "hradec": (6, 'region'),
        "pardubicky": (7, 'region'), "pardubice": (7, 'region'),
        "olomoucky": (8, 'region'), "olomouc": (8, 'region'),
        "zlinsky": (9, 'region'), "zlin": (9, 'region'),
        "praha": (10, 'region'),
        "praha-vychod": (-99, 'district'),
        "praha-zapad": (-99, 'district'),
        "stredocesky": (11, 'region'),
        "moravskoslezsky": (12, 'region'), "ostrava": (12, 'region'),
        "vysocina": (13, 'region'), "jihlava": (13, 'region'),
        "jihomoravsky": (14, 'region'),
    }

    # 1. Check for Specific Prague Districts
    import re
    p_match = re.search(r'praha\s*(\d+)', clean_prompt)
    if p_match:
        dist_num = int(p_match.group(1))
        if 1 <= dist_num <= 10:
             region_id = 5000 + dist_num
             print(f"  -> Matched Specific Prague District: {region_id}")

    # 2. Check General Location Map
    if not region_id:
        sorted_locs = sorted(known_locations.items(), key=lambda x: len(x[0]), reverse=True)
        for city, val in sorted_locs:
            if city in prompt_slug:
                if isinstance(val, tuple):
                    r_id, r_type = val
                else:
                    r_id, r_type = val, 'region'
                
                if r_id == -99:
                    region_id = None
                    region_type = None
                    print(f"  -> Matched Universal/Blocked: {city}")
                else:
                    region_id = r_id
                    region_type = r_type
                    print(f"  -> Matched Known Location: {city} -> {region_id} ({region_type})")
                break
    
    print(f"  => Validated Region: {region_id} ({region_type})")

if __name__ == "__main__":
    test_location_logic("Praha")
    test_location_logic("Byt v Praze")
    test_location_logic("Prodej bytu Praha 5")
    test_location_logic("Brno venkov")
