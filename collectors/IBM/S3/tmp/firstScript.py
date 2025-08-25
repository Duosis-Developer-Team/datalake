import requests
import os
from requests.auth import HTTPBasicAuth
import json
# Define the URL and parameters
url = 'https://10.34.6.14/manager/api/json/1.0/listVaults.adm'


# Define the authentication credentials
username = 'Zabbixtest'
password = 'Zabbixtest123!'


def delete_files():
    files_to_delete = [
        "/ZabbixCustomMonitoring/IBM/s3icos/response_data.json",
        "/ZabbixCustomMonitoring/IBM/s3icos/prettified_output.json",
        "/ZabbixCustomMonitoring/IBM/s3icos/edited_flat.json",
        "/ZabbixCustomMonitoring/IBM/s3icos/edited.json"
    ]
    for file in files_to_delete:
        try:
            if os.path.exists(file):
                os.remove(file)  # Delete the file
                print(f"File {file} has been deleted.")
            else:
                print(f"File {file} does not exist.")
        except Exception as e:
            print(f"Error deleting file {file}: {e}")
# Send the GET request with basic authentication
if __name__ == "__main__":
    delete_files()
response = requests.get(url, auth=HTTPBasicAuth(username, password), verify=False)

# Check if the request was successful
if response.status_code == 200:
    with open('response_data.json', 'w') as file:
        json.dump(response.json(), file, indent=4)
else:
    # Print the error if the request failed
    print(f"Error: {response.status_code}, {response.text}")
os.system('/usr/bin/python3 /Datalake_Project/IBM/S3/tmp/secondScript.py')
