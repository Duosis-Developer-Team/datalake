import requests

from datetime import datetime

import urllib.parse

import urllib3

import json

json_file_path = "/Datalake_Project/configuration_file.json"

with open(json_file_path, "r") as file:

    config = json.load(file)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
 
def sql_str(value):

    if value is None:

        return "NULL"

    if not isinstance(value, str):

        value = str(value)

    escaped = value.replace("'", "''")

    return f"'{escaped}'"
 
def sql_null_or_value(value):

    if value is None:

        return "NULL"

    return str(value)
 
def fetch_disk_pools(api_url, bearer_token):

    headers = {"Authorization": f"Bearer {bearer_token}"}

    response = requests.get(api_url, headers=headers, verify=False)

    response.raise_for_status()

    return response.json()
 
def generate_disk_pools_insert_queries(data, table_name="netbackup_disk_pools"):

    queries = []
 
    for item in data.get("data", []):

        attributes = item.get("attributes", {})

        disk_volumes = attributes.get("diskVolumes", [{}])[0]  # Assume single disk volume
 
        query = (

            f"INSERT INTO {table_name} ("

            f"name, sType, storageCategory, diskVolumes_name, diskVolumes_id, diskVolumes_diskMediaId, diskVolumes_state,"

            f"diskVolumes_rawSizeBytes, diskVolumes_freeSizeBytes, diskVolumes_isReplicationSource,"

            f"diskVolumes_isReplicationTarget, diskVolumes_wormIndelibleMinimumInterval, diskVolumes_wormIndelibleMaximumInterval,"

            f"highWaterMark, lowWaterMark, max_limitIoStreams, diskPoolState, rawSizeBytes, usableSizeBytes, availableSpaceBytes,"

            f"usedCapacityBytes, wormCapable, readOnly, mediaServersCount"

            f") VALUES ("

            f"{sql_str(attributes.get('name'))}, {sql_str(attributes.get('sType'))}, {sql_str(attributes.get('storageCategory'))},"

            f"{sql_str(disk_volumes.get('name'))}, {sql_str(disk_volumes.get('id'))}, {sql_str(disk_volumes.get('diskMediaId'))},"

            f"{sql_str(disk_volumes.get('state'))}, {sql_null_or_value(disk_volumes.get('rawSizeBytes'))},"

            f"{sql_null_or_value(disk_volumes.get('freeSizeBytes'))}, {sql_null_or_value(disk_volumes.get('isReplicationSource'))},"

            f"{sql_null_or_value(disk_volumes.get('isReplicationTarget'))}, {sql_null_or_value(disk_volumes.get('wormIndelibleMinimumInterval'))},"

            f"{sql_null_or_value(disk_volumes.get('wormIndelibleMaximumInterval'))}, {sql_null_or_value(attributes.get('highWaterMark'))},"

            f"{sql_null_or_value(attributes.get('lowWaterMark'))}, {sql_null_or_value(attributes.get('maximumIoStreams', {}).get('limitIoStreams'))},"

            f"{sql_str(attributes.get('diskPoolState'))}, {sql_null_or_value(attributes.get('rawSizeBytes'))},"

            f"{sql_null_or_value(attributes.get('usableSizeBytes'))}, {sql_null_or_value(attributes.get('availableSpaceBytes'))},"

            f"{sql_null_or_value(attributes.get('usedCapacityBytes'))}, {sql_null_or_value(attributes.get('wormCapable'))},"

            f"{sql_null_or_value(attributes.get('readOnly'))}, {sql_null_or_value(attributes.get('mediaServersCount'))}"

            f");"

        )

        queries.append(query)
 
    return queries
 
if __name__ == "__main__":

    netbackup_config = config["Netbackup"]

    api_url = netbackup_config["api_url_diskpool"]

    bearer_token = netbackup_config["bearer_token"]
 
    try:

        disk_pools_data = fetch_disk_pools(api_url, bearer_token)

        queries = generate_disk_pools_insert_queries(disk_pools_data, table_name="netbackup_disk_pools")

        for q in queries:

            print(q)

    except Exception as e:

        print(f"Error: {e}")