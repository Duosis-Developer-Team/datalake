import json
import os

def prettify_json(json_data, output_file):
    try:
        # If json_data is a string, parse it into a Python object
        if isinstance(json_data, str):
            json_data = json.loads(json_data)
        
        # Write the prettified JSON to the output file with indentation
        with open(output_file, 'w') as file:
            json.dump(json_data, file, indent=4)
        
        # Optionally, print success message
        # print(f"Prettified JSON has been saved to {output_file}")
    
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        print(f"Error at line {e.lineno}, column {e.colno}: {e.msg}")


def check_json_format(input_file):
    try:
        with open(input_file, 'r') as file:
            json.load(file)
        #print("JSON is valid!")
    except json.JSONDecodeError as e:
        print(f"JSONDecodeError: {e}")
        print(f"Problematic line: {e.lineno}, column: {e.colno}")
    
def get_vaults_from_file(file_path):
    """Extracts and returns the value of 'vaults' as JSON."""
    # Open and read the JSON file
    with open(file_path, 'r') as file:
        json_data = json.load(file)  # Parse the JSON data from the file

    # Access the 'vaults' key under 'responseData' and return its value
    vaults = json_data.get('responseData', {}).get('vaults', [])

    # Return the vaults as JSON (serialized string)
    return json.dumps(vaults, indent=4)

def process_dict(data):
    """Recursively process all nested dictionaries and lists, keeping only the first element in lists with exactly three elements."""
    if isinstance(data, dict):
        # Iterate over all key-value pairs in the dictionary
        for key, value in data.items():
            if isinstance(value, list):
                # If it's a list of three elements, replace it with the first element
                if len(value) == 3:
                    data[key] = value[0]
                else:
                    # If the list contains other dictionaries, process each element
                    for i in range(len(value)):
                        if isinstance(value[i], (dict, list)):
                            data[key][i] = process_dict(value[i])
            elif isinstance(value, dict):
                # Recursively process nested dictionaries
                data[key] = process_dict(value)
    elif isinstance(data, list):
        # If the data itself is a list, process each element
        for i in range(len(data)):
            if isinstance(data[i], (dict, list)):
                data[i] = process_dict(data[i])
    return data


def process_json(input_file, output_file):
    # Read the JSON data from the input file
    with open(input_file, 'r') as file:
        json_data = json.load(file)
    
    # Process the JSON data (modify lists with three values)
    processed_data = process_dict(json_data)
    
    # Write the modified JSON to the output file
    with open(output_file, 'w') as file:
        json.dump(processed_data, file, indent=4)
    
    #print(f"Processed JSON has been saved to {output_file}")


if __name__ == "__main__":
    f_input_file = "/ZabbixCustomMonitoring/IBM/s3icos/response_data.json"  # Specify your input file name
    prettified_output_file = "/ZabbixCustomMonitoring/IBM/s3icos/prettified_output.json"  # Prettified output file
    processed_output_file = "/ZabbixCustomMonitoring/IBM/s3icos/processed_output.json"  # Processed output file
    
    # Step 1: Extract vaults from the input JSON file
    vaults = get_vaults_from_file(f_input_file)
    
    # Step 2: Prettify the JSON (using the full JSON, not just the vaults)
    prettify_json(vaults, prettified_output_file)

    # Step 3: Check if the prettified JSON is valid
    check_json_format(prettified_output_file)
    
    # Step 4: Process the JSON to remove the last 2 values in lists of length 3
    process_json(prettified_output_file, processed_output_file)
    
    # Step 5: Validate the final processed JSON
    check_json_format(processed_output_file)

    # Step 6: Run an external Python script if needed
    os.system('/usr/bin/python3 /ZabbixCustomMonitoring/IBM/s3icos/thirdScript.py')


