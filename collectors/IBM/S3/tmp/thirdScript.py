import json
import os

# File paths for input and output
input_file = '/ZabbixCustomMonitoring/IBM/s3icos/processed_output.json'
output_file = '/ZabbixCustomMonitoring/IBM/s3icos/edited.json'

# Function to remove specific keys
def remove_keys(d, keys):
    if isinstance(d, dict):
        for key in keys:
            d.pop(key, None)  # Remove the key if it exists
        for value in d.values():
            remove_keys(value, keys)  # Recursively process nested structures
    elif isinstance(d, list):
        for item in d:
            remove_keys(item, keys)  # Process each item in the list

# Function to extract only the lparsUtil block
def extract_lpars_util(data):
    lpars_data = []
    for entry in data:
        try:
            util_samples = entry["systemUtil"]["utilSamples"]
            for sample in util_samples:
                if "lparsUtil" in sample:
                    lpars_data.extend(sample["lparsUtil"])
        except KeyError as e:
            print(f"KeyError: {e}. Skipping entry: {entry}")
            continue
    return lpars_data

# Function to rename keys with name prefix
def rename_keys_with_name(lpars_util_data):
    for entry in lpars_util_data:
        name = entry.get('name', '')

        def recursive_rename(d, parent_key=''):
            if isinstance(d, dict):
                new_dict = {}
                for key, value in d.items():
                    new_key = f"{name}-{parent_key}{key}" if parent_key else f"{name}-{key}"
                    new_dict[new_key] = recursive_rename(value, f"{parent_key}{key}-")
                return new_dict
            elif isinstance(d, list):
                return [recursive_rename(item, parent_key) for item in d]
            else:
                return d

        renamed_entry = recursive_rename(entry)
        lpars_util_data[lpars_util_data.index(entry)] = renamed_entry

    return lpars_util_data

# Function to rename keys with unique indexes
def rename_inner_keys(data):
    # Helper function to rename keys in a list of dictionaries
    def process_inner_key(group, key_prefix):
        for i, item in enumerate(group):
            suffix = f"-{i+1}"  # Create a unique suffix
            for key in list(item.keys()):  # List of current keys to rename
                new_key = f"{key}{suffix}"  # Append suffix to the key
                item[new_key] = item.pop(key)  # Rename the key
        return group

    # Iterate through the data to locate and rename inner keys
    for entry in data:
        for key, value in entry.items():
            if isinstance(value, dict):  # Check if the value is a dictionary
                for inner_key, inner_value in value.items():
                    if isinstance(inner_value, list) and all(isinstance(v, dict) for v in inner_value):
                        value[inner_key] = process_inner_key(inner_value, inner_key)

    return data

# Main script logic
with open(input_file, 'r') as f:
    data = json.load(f)

if isinstance(data, list) and len(data) > 0:
    data.pop(0)

keys_to_remove = ["startTimeStamp", "endTimeStamp", "timeStamp"]
remove_keys(data, keys_to_remove)



lpars_util_data = rename_keys_with_name(data)
renamed_lpars_util = rename_inner_keys(lpars_util_data)

with open(output_file, 'w') as f:
    json.dump(renamed_lpars_util, f, indent=4)


# Step 7: Delete the original input file
try:
    os.remove(input_file)
    print(f"{input_file} has been deleted.")
except FileNotFoundError:
    print(f"{input_file} does not exist.")
except Exception as e:
    print(f"Error while deleting {input_file}: {e}")

os.system('/usr/bin/python3 /ZabbixCustomMonitoring/IBM/s3icos/fourthScript.py')