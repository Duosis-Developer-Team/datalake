import os
import re
import shutil
import subprocess

# Get the current working directory where the files are stored
current_directory = "/Datalake_Project/IBM/IBM_Storage/SSH/iostats/"

# Regular expression to extract the unique identifier and timestamp from filenames
pattern = re.compile(r'_stats_([^_]+)_(\d{6})_(\d{6})$')

def organize_files(directory):
    """
    Organizes files by extracting unique values from their filenames,
    finds the two highest combined date-time timestamps, and moves only those files into respective folders.
    Returns the list of created folders.
    """
    file_map = {}  # Maps unique values to their files
    timestamp_set = set()  # Stores combined timestamps (YYMMDD + HHMMSS)
    created_folders = set()  # Store created folders

    # Scan files in the directory
    for filename in os.listdir(directory):
        match = pattern.search(filename)
        if match:
            unique_value = match.group(1)  # Extract the unique identifier
            date_part = match.group(2)     # Extract the date (YYMMDD)
            time_part = match.group(3)     # Extract the time (HHMMSS)

            combined_timestamp = f"{date_part}{time_part}"
            timestamp_set.add(combined_timestamp)

            # Store the file under the corresponding unique value
            if unique_value not in file_map:
                file_map[unique_value] = []
            file_map[unique_value].append((filename, combined_timestamp))

    # Find the two latest combined timestamps
    top_timestamps = sorted(timestamp_set, reverse=True)[:2]

    print(f"Top 2 combined timestamps selected: {top_timestamps}")

    # Create folders and move only the files with the top timestamps
    for unique_value, files in file_map.items():
        folder_path = os.path.join(directory, unique_value)

        # Create the directory if it doesn't exist
        os.makedirs(folder_path, exist_ok=True)
        created_folders.add(unique_value)  # Track created folders

        # Move files only if they have one of the top 2 timestamps
        for filename, combined_timestamp in files:
            if combined_timestamp in top_timestamps:
                src_path = os.path.join(directory, filename)
                dest_path = os.path.join(folder_path, filename)
                shutil.move(src_path, dest_path)
                print(f"Moved {filename} → {folder_path}")

    return created_folders

if __name__ == "__main__":
    created_folders = organize_files(current_directory)
    print("File organization completed.")

    # Run subprocess for each created folder
    for folder_name in created_folders:
        folder_path = os.path.join(current_directory, folder_name)
        result = subprocess.run(["python3", "/Datalake_Project/IBM/IBM_Storage/SSH/iostats/noncumul.py", folder_path],
                                capture_output=True, text=True)

        # Debugging Output
        # print(f"Subprocess for {folder_name}:")
        # print("STDOUT:", result.stdout)
        # print("STDERR:", result.stderr)
