import os
import json

filepath = r"c:\108\AI-accounting-0.03\backend\sprint3_validation\reports\MISTRAL_FULL_EXTRACTION.json"

if os.path.exists(filepath):
    print("MISTRAL_FULL_EXTRACTION.json exists!")
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"Root is list of length {len(data)}")
    
    # Search for EIS/25-26/1014 in the list
    found_item = None
    for idx, obj in enumerate(data):
        obj_str = json.dumps(obj)
        if "EIS/25-26/1014" in obj_str:
            print(f"Found match at index {idx}!")
            found_item = obj
            break
            
    if found_item:
        print("Keys of the match:", list(found_item.keys()) if isinstance(found_item, dict) else "Not a dict")
        print("Matching object snippet:")
        print(json.dumps(found_item, indent=2)[:3000])
    else:
        print("EIS/25-26/1014 not found. Searching for HSN 8210 in the list:")
        for idx, obj in enumerate(data):
            obj_str = json.dumps(obj)
            if "8210" in obj_str:
                print(f"Found HSN 8210 match at index {idx}!")
                print(json.dumps(obj, indent=2)[:1500])
                break
else:
    print("MISTRAL_FULL_EXTRACTION.json does not exist at", filepath)
