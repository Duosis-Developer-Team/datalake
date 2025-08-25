import json
import os

# File path for the input and output JSON files
input_file = '/ZabbixCustomMonitoring/IBM/s3icos/edited.json'
output_file = '/ZabbixCustomMonitoring/IBM/s3icos/edited_flat.json'

def flatten_json_no_headers(nested_json):
    flat_dict = {}
    if isinstance(nested_json, dict):
        for key, value in nested_json.items():
            if isinstance(value, (dict, list)):
                flat_dict.update(flatten_json_no_headers(value))
            else:
                flat_dict[key] = value
    elif isinstance(nested_json, list):
        for item in nested_json:
            flat_dict.update(flatten_json_no_headers(item))
    return flat_dict

# Load JSON data from a file
with open(input_file, 'r') as f:
    data = json.load(f)

# Flatten the data without headers
flattened_data = flatten_json_no_headers(data)

# Save the flattened data to a file
with open(output_file, 'w') as f:
    json.dump(flattened_data, f, indent=4)
#os.system('/usr/bin/php /ZabbixCustomMonitoring/IBM/custom/GetLpar.php')
print(f"Flattened JSON data without headers has been saved to {output_file}")