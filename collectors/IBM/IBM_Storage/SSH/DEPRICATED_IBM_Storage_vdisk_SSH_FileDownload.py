import json
import os
import re




def load_config(file_path="/Datalake_Project/configuration_file.json"):
    try:
        with open(file_path, "r") as file:
            config_data = json.load(file)
            # Get the "IBM-Storage" block
            ibm_storage_config = config_data["IBM-Virtualize"]
            return ibm_storage_config
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file '{file_path}' not found.")

def find_latest_files(file_list):
    latest = {}


    # Updated regex pattern to match filenames correctly
    pattern = re.compile(r'^(N[dmnv])_stats_[A-Za-z0-9]+-(.+)_(\d{6})_(\d{6})$')



    for filename in file_list:

        #print("DEBUG:", repr(filename), [ord(c) for c in filename])
        filename = filename.strip()

        match = pattern.match(filename)
        if not match:
            #print(f"Skipping (no match): {filename}")  # Debugging output
            continue  # If the pattern does not match, move to the next file

        prefix, suffix, date_str, time_str = match.groups()
        combined_dt = int(date_str + time_str)
        key = (prefix, suffix)

        if key not in latest or combined_dt > latest[key][1]:
            latest[key] = (filename, combined_dt)
       # break
    return [latest[k][0] for k in latest]


def copy_files(config):
    host = config.get("host")
    username = config.get("username")
    password = config.get("password")
    remote_path = config.get("remote_path", "/dumps/iostats")  # Default path
    local_path = config.get("local_path", ".")

    # Use svcinfo lsiostatsdumps to list available dumps
    list_command = (
        f"sshpass -p '{password}' ssh -o StrictHostKeyChecking=no "
        f"{username}@{host} \"svcinfo lsiostatsdumps -nohdr -delim :\""
    )

    raw_output = os.popen(list_command).read().strip().splitlines()

    # Extract filenames from the command output
    file_list = [line.split(":")[1] for line in raw_output if ":" in line]

    if not file_list:
        print("No iostat dumps found.")
        return

    # Get the latest files
    latest_files = find_latest_files(file_list)

    for file in latest_files:
        remote_file = os.path.join(remote_path, file)
        local_file = os.path.join(local_path, file)

        scp_command = (
            f"sshpass -p '{password}' scp -o StrictHostKeyChecking=no "
            f"{username}@{host}:{remote_file} {local_path}"
        )

        os.system(scp_command)

        # Read and print the content of the downloaded file
        with open(local_file, "r", encoding="utf-8") as f:
            print(f.read())
#             delete_file(local_file)

def delete_file(file_path):
    try:
        os.remove(file_path)
    except Exception as e:
        print(f"Error deleting file {file_path}: {e}")

if __name__ == "__main__":
    config = load_config()
    copy_files(config)
