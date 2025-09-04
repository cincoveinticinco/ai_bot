import json
from rapidfuzz import process, fuzz

def lambda_handler(event, context):
    filter_values = event.get("filter_values", {})
    data_sets = event.get("data_sets", {})
    filter_data_sets = {}
    print(f"Filter values: {filter_values}")
   
    for key, value in filter_values.items():
        print(f"Processing filter for key: {key}, value: {value}")
        key = "set_location" if key == "loc" or key == "set" else key
        if key in data_sets:
            filter_data_sets[key] = []
            print(f"Found key: {key} in data_sets and has value: {len(data_sets[key])} items")
            for item in value:
                print(f"**" * 50)
                print(f"Item: {item}")
                print(f"**" * 50)
                if isinstance(item, str):
                    print(f"lets continue with item: {item}")
                    for obj in data_sets[key]:
                        if isinstance(obj, dict) and "name" in obj:
                            match = process.extractOne(item.upper(), [obj["name"].upper()], scorer=fuzz.token_set_ratio)
                            if match and match[1] > 50:
                                print(f"Matching {item} with {obj['name']}: {match}")
                                filter_data_sets[key].append(obj)
        else:
            print(f"Key: {key} not found in data_sets")
            continue
    print(f"Filtered data sets: {filter_data_sets}")
    return {
        "statusCode": 200,
        "body": json.dumps("Hola mundo")
    }

if __name__ == "__main__":
    # Prueba local
    with open("events/event_filter_data.json", encoding="utf-8") as f:
        event = json.load(f)
    response = lambda_handler(event, None)
    print(json.dumps(response, indent=2, ensure_ascii=False))