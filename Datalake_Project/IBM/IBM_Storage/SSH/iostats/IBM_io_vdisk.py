import json
import os
import re
import subprocess
from collections import defaultdict
import subprocess

def load_config(file_path="/Datalake_Project/configuration_file.json"):
    """Loads IBM Storwize SSH connection details from JSON config file."""
    try:
        with open(file_path, "r") as file:
            config_data = json.load(file)
            return config_data["IBM-Virtualize"]  # Get IBM-Virtualize section
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file '{file_path}' not found.")

def run_ssh_command(command):
    """Executes an SSH command and returns the output as a list of lines."""
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate()

    if process.returncode != 0:
        print(f"Error executing SSH command: {stderr}")
        return []

    return stdout.strip().splitlines()

def extract_timestamp(file_list):
    """
    Extracts unique timestamps (hhmmss) from filenames and returns the highest two timestamps.
    """
    timestamp_pattern = re.compile(r'_(\d{6})$')  # Captures hhmmss from filenames
    timestamps = set()

    for filename in file_list:
        match = timestamp_pattern.search(filename)
        if match:
            timestamps.add(match.group(1))

    # Convert to sorted list (descending order)
    top_timestamps = sorted(timestamps, reverse=True)[:2]
    
    return top_timestamps

def copy_files(config):
    """Lists and downloads files with the highest two timestamps from remote SSH folder."""
    host = config.get("host")
    username = config.get("username")
    password = config.get("password")
    remote_path = config.get("remote_path", "/dumps/iostats")  # Default path
    local_path = config.get("local_path", ".")

    # 1. List all files using 'lsdumps -prefix'
    list_command = (
        f"sshpass -p '{password}' ssh -o StrictHostKeyChecking=no "
        f"{username}@{host} \"lsdumps -prefix {remote_path}\""
    )
    raw_output = run_ssh_command(list_command)

    # Extract filenames from SSH output
    file_list = [line.split(None, 1)[1].strip() for line in raw_output if len(line.split(None, 1)) == 2]

    if not file_list:
        print("No files found in remote directory.")
        return

    print(f"Found {len(file_list)} files. Extracting latest timestamps...")

    # 2. Find the top 2 highest timestamps
    top_timestamps = extract_timestamp(file_list)

    if not top_timestamps:
        print("No valid timestamps found in filenames.")
        return

    print(f"Selected timestamps for download: {top_timestamps}")

    # 3. Filter filenames matching these timestamps
    selected_files = [file for file in file_list if any(file.endswith(f"_{ts}") for ts in top_timestamps)]

    if not selected_files:
        print("No files match the selected timestamps.")
        return

    print(f"Downloading {len(selected_files)} files with the selected timestamps...")

    # 4. Download selected files
    for file in selected_files:
        remote_file = os.path.join(remote_path, file)
        local_file = os.path.join(local_path, file)

        scp_command = (
            f"sshpass -p '{password}' scp -o StrictHostKeyChecking=no "
            f"{username}@{host}:{remote_file} {local_file}"
        )

        print(f"Downloading {file}...")
        os.system(scp_command)  # Execute SCP command for each selected file

    print(f"Download complete: {len(selected_files)} files saved to {local_path}")

if __name__ == "__main__":
    config = load_config()
    copy_files(config)
#    result = subprocess.run(["python3", "/Datalake_Project/IBM/IBM_Storage/SSH/iostats/data_analyzepython.py"], capture_output=True, text=True)
