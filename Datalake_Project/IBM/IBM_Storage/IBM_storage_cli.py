import json
import warnings
from IBM_storage_class import APIClient
import urllib3

# Suppress InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.simplefilter("ignore", category=UserWarning)

# Instantiate the APIClient
client = APIClient()

try:
    # Authenticate the client
    client.authenticate()
    print("Authentication successful.")

    # Make requests to the endpoints and save responses
    response_lsvdisk = client.post_to_lsvdisk()
    with open("lsvdisk_response.json", "w") as file:
        json.dump(response_lsvdisk, file, indent=4)
    print("Response from /lsvdisk saved to 'lsvdisk_response.json'.")


    response_merge_vdisk_mappings= client.merge_vdisk_mappings()
    with open("merge_vdisk_mappings_response.json", "w") as file:
        json.dump(response_merge_vdisk_mappings, file, indent=4)
    print("Response saved to 'merge_vdisk_mappings_response.json'.")

    response_lsmdiskgrp = client.post_to_lsmdiskgrp()
    with open("lsmdiskgrp_response.json", "w") as file:
        json.dump(response_lsmdiskgrp, file, indent=4)
    print("Response from /lsmdiskgrp saved to 'lsmdiskgrp_response.json'.")

    response_lsmdiskgrp_by_id = client.post_to_lsmdiskgrp_by_id()
    with open("lsmdisk_by_id_responses.json", "w") as file:
        json.dump(response_lsmdiskgrp_by_id, file, indent=4)
    print("Responses from /lsmdisk/{id} saved to 'lsmdiskgrp_by_id_responses.json'.")

    response_lshost = client.post_to_lshost()
    with open("lshost_response.json", "w") as file:
        json.dump(response_lshost, file, indent=4)
    print("Response from /lshost saved to 'lshost_response.json'.")

    response_lshost_by_id = client.post_to_lshost_by_id()
    with open("lshost_by_id_responses.json", "w") as file:
        json.dump(response_lshost_by_id, file, indent=4)
    print("Responses from /lshost/{id} saved to 'lshost_by_id_responses.json'.")


    response_lsnodestats = client.post_to_lsnodestats()
    with open("lsnodestats_response.json", "w") as file:
        json.dump(response_lsnodestats, file, indent=4)
    print("Response from /lsnodestats saved to 'lsnodestats_response.json'.")


    response_lsenclosurestats = client.post_to_lsenclosurestats()
    with open("lsenclosurestats_response.json", "w") as file:
        json.dump(response_lsenclosurestats, file, indent=4)
    print("Response from /lsenclosurestats saved to 'lsenclosurestats_response.json'.")

    response_lssystem = client.post_to_lssystem()
    with open("lssystem_response.json", "w") as file:
        json.dump(response_lssystem, file, indent=4)
    print("Response from /lssystem saved to 'lssystem_response.json'.")

    response_lsportfc = client.post_to_lsportfc()
    with open("lsportfc_response.json", "w") as file:
        json.dump(response_lsportfc, file, indent=4)
    print("Response from /lsportfc saved to 'lslsportfc_response.json'.")

    response_lshostvdiskmap = client.post_to_lshostvdiskmap()
    with open("lshostvdiskmap_response.json", "w") as file:
        json.dump(response_lshostvdiskmap, file, indent=4)
    print("Response from /lshostvdiskmap saved to 'lshostvdiskmap_response.json'.")

    response_lssystemstats = client.post_to_lssystemstats()
    with open("lssystemstats_response.json", "w") as file:
        json.dump(response_lssystemstats, file, indent=4)
    print("Response from /lssystemstats saved to 'lssystemstats_response.json'.")


    response_lsmdisk = client.post_to_lsmdisk()
    with open("lsmdisk_response.json", "w") as file:
        json.dump(response_lsmdisk, file, indent=4)
    print("Response from /lsmdisk_response saved to 'lsmdisk_response.json'.")


except Exception as e:
    print("An error occurred:", str(e))
