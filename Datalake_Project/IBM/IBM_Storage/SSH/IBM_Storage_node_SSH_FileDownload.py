import json
import os
import subprocess
import re
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

def copy_files(config):
    host = config.get("host")
    username = config.get("username")
    password = config.get("password")
    remote_path = config.get("remote_path")
    local_path = config.get("local_path", ".")

    list_command = (
        f"sshpass -p '{password}' ssh -o StrictHostKeyChecking=no "
        f"{username}@{host} \"lsdumps -prefix {remote_path}\""
    )
    raw_output = os.popen(list_command).read().strip().splitlines()
    
    file_list = [line.split(None, 1)[1] for line in raw_output if len(line.split(None, 1)) == 2]
    

    latest_files = find_latest_files(file_list)

    for file in latest_files:
        remote_file = os.path.join(remote_path, file)
        local_file = os.path.join(local_path, file)

        scp_command = (
            f"sshpass -p '{password}' scp -o StrictHostKeyChecking=no "
            f"{username}@{host}:{remote_file} {local_path}"
        )

        os.system(scp_command)

        # Read and print the content of the downloaded XML file
        with open(local_file, "r", encoding="utf-8") as f:
            print(f.read())
            delete_file(local_file)

def delete_file(file_path):
    try:
        os.remove(file_path)

    except Exception as e:
        print(f"Error deleting file {file_path}: {e}")

if __name__ == "__main__":
    config = load_config()
    copy_files(config)
