#
import json
import requests
import time
class APIClient:
    def __init__(self, config_file="/Datalake_Project/configuration_file.json"):
        self.config_file = config_file
        self.token = None
        self._load_config()
        self.endpoints = {
            "lsvdisk": "/rest/v1/lsvdisk",
            "lsmdiskgrp": "/rest/v1/lsmdiskgrp",
            "lshost": "/rest/v1/lshost",
            "lsnodestats": "/rest/v1/lsnodestats",
            "lsenclosurestats": "/rest/v1/lsenclosurestats",
            "lssystem": "/rest/v1/lssystem",
            "lsportfc": "/rest/v1/lsportfc", ###eklendi
            "lsportfcid": "/rest/v1/lsdumps",  ###ekl<endi
            "lshostvdiskmap": "/rest/v1/lshostvdiskmap", ###eklendi
            ###################################
             ## eklenecek
            "lssystemstats": "/rest/v1/lssystemstats", ##elendi
            # "lsdrive": "/rest/v1/lsdrive", ##elendi
            # "lshostcluster": "/rest/v1/lshostcluster", ##elendi
            # "lshostclustervolumemap": "/rest/v1/lshostclustervolumemap", ###elendi
            # "lshostclustermember": "/rest/v1/lshostclustermember",
            "lsmdisk": "/rest/v1/lsmdisk" ##elendi
            # "lsfreeextents": "/rest/v1/lsfreeextents/0", ##sorulabilir
            
            # "lsvdiskfcmappings": "/rest/v1/lsvdiskfcmappings/823", ### boş elendi
            # "lsvolumegroup": "/rest/v1/lsvolumegroup" ## elendi
        }
###########################
    def post_to_lsportfc(self):
        return self.post_with_token("lsportfc")
    def post_to_lsmdisk(self):
        return self.post_with_token("lsmdisk")
    def post_to_lssystemstats(self):
        return self.post_with_token("lssystemstats")
    def post_to_lsdrive(self):
        return self.post_with_token("lsdrive")
    def post_to_lshostclustervolumemap(self):
        return self.post_with_token("lshostclustervolumemap")
    def post_to_lsmdiskmember(self):
        return self.post_with_token("lsmdiskmember")
    def post_to_lsfreeextents(self):
        return self.post_with_token("lsfreeextents")
    def post_to_lshostvdiskmap(self):
        return self.post_with_token("lshostvdiskmap")
    def post_to_lsdependentvdisks(self, vdisk_id):
        return self.post_with_token("lsdependentvdisks", additional_path=vdisk_id)

    def post_to_lsvdiskfcmappings(self):
        return self.post_with_token("lsvdiskfcmappings")
    def post_to_lsvolumegroup(self):
        return self.post_with_token("lsvolumegroup")
    def post_to_lsdumps(self, prefix=None):
        params = {}
        if prefix:
            params["prefix"] = prefix
        return self.post_with_token("lsdumps", params=params)

    
########################
    def _load_config(self):
        try:
            with open(self.config_file, "r") as file:
                config_data = json.load(file)
                # Select the "IBM-Virtualize" config block
                self.config = config_data["IBM-Virtualize"]
        except FileNotFoundError:
            raise Exception(f"Config file '{self.config_file}' not found.")

    def authenticate(self):
        url = self.config["link"] + "/rest/auth"
        headers = {
            'X-Auth-Username': self.config["name"],
            'X-Auth-Password': self.config["password"]
        }
        response = requests.post(url, headers=headers, verify=False)
        if response.status_code == 200:
            self.token = response.json().get("token")
            print(self.token)
        else:
            raise Exception(f"Authentication failed: {response.status_code} - {response.text}")

    def post_with_token(self, endpoint_key, additional_path=None):
        if not self.token:
            raise Exception("Token not available. Authenticate first.")

        if endpoint_key not in self.endpoints:
            raise ValueError(f"Invalid endpoint key: {endpoint_key}")

        url = self.config["link"] + self.endpoints[endpoint_key]
        if additional_path:
            url += f"/{additional_path}"

        headers = {
            'X-Auth-Token': self.token,
            'accept': 'application/json',
            'Content-Type': 'application/json'
        }
        response = requests.post(url, headers=headers, json=None, verify=False)  # Empty payload, bypass SSL
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Request failed: {response.status_code} - {response.text}")

    def post_to_lsvdisk(self):
        return self.post_with_token("lsvdisk")

    def post_to_lsmdiskgrp(self):
        return self.post_with_token("lsmdiskgrp")

    def post_to_lsmdiskgrp_by_id(self):
        response = self.post_to_lsmdiskgrp()
        if isinstance(response, list):
            results = {}
            for item in response:
                if "id" in item:
                    results[item["id"]] = self.post_with_token("lsmdiskgrp", additional_path=item["id"])
                    time.sleep(0.2)
                else:
                    raise Exception("No 'id' field found in one of the lsmdiskgrp items.")
            return results
        else:
            raise Exception("The lsmdiskgrp response is not a list.")

    def post_to_lshost(self):
        return self.post_with_token("lshost")

    def post_to_lsnodestats(self):
        return self.post_with_token("lsnodestats")

    def post_to_lsenclosurestats(self):
        return self.post_with_token("lsenclosurestats")
    
    def post_to_lssystem(self):
        return self.post_with_token("lssystem")
    
    def merge_vdisk_mappings(self):
        # Fetch data from both endpoints
        vdisk_fc_mappings = self.post_to_lshostvdiskmap()  # Has {"name": <host_name>, "vdisk_name": <volume_name>}
        vdisk_mappings = self.post_to_lsvdisk()            # Has {"name": <volume_name>, "mdisk_grp_name": <mdisk_group>}

        # Build a dict to quickly lookup mdisk_grp_name from the vdisk name
        # vdisk_mappings is a list of entries:
        #   {
        #       "name": <volume_name>,
        #       "mdisk_grp_name": <mdisk_group>
        #       ...
        #   }
        vdisk_dict = {entry["name"]: entry["mdisk_grp_name"] for entry in vdisk_mappings}

        # Merge data based on vdisk_name
        result = []
        for entry in vdisk_fc_mappings:
            # From lshostvdiskmap, "name" is host_name, "vdisk_name" is the volume name
            vdisk_name = entry["vdisk_name"]
            host_name = entry["name"]  # host name

            # Only add to result if we have a matching vdisk entry in vdisk_dict
            if vdisk_name in vdisk_dict:
                result.append({
                    "vdisk_name": vdisk_name,
                    "host_name": host_name,
                    "mdiskgrp_name": vdisk_dict[vdisk_name]
                })

        return result



    def post_to_lshost_by_id(self):
        response = self.post_to_lshost()
        if isinstance(response, list):
            results = {}
            for item in response:
                if "id" in item:
                    results[item["id"]] = self.post_with_token("lshost", additional_path=item["id"])
                    time.sleep(0.2)  # Wait 1 second between requests
                else:
                    raise Exception("No 'id' field found in one of the lshost items.")
            return results
        else:
            raise Exception("The lshost response is not a list.")
        
    def post_to_lsvdisk_by_id(self):
        response = self.post_to_lsvdisk()
        if isinstance(response, list):
            results = {}
            for item in response:
                if "id" in item:
                    results[item["id"]] = self.post_with_token("lsvdisk", additional_path=item["id"])
                    time.sleep(0.2)
                else:
                    raise Exception("No 'id' field found in one of the lsvdisk items.")
            return results
        else:
            raise Exception("The lsvdisk response is not a list.")

