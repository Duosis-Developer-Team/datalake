#!/usr/bin/env python3
import os

def parse_iostat_file(filepath):
    """
    Given the path to a single iostat dump file,
    parse each line as 'key:value', converting numeric values to float if possible.
    Returns a dictionary of parsed data.
    """
    stats = {}

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if ":" not in line:
                continue  # skip lines that don't look like "key:value"

            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip()

            # Convert numeric fields to float, keep as string otherwise
            try:
                val = float(val)
            except ValueError:
                pass

            stats[key] = val

    return stats

def main():
    """
    1. Set the directory containing downloaded iostat dumps.
    2. Loop over each file in that directory.
    3. Parse the file with parse_iostat_file().
    4. Print or process the resulting dictionary.
    """
    iostats_dir = "/Datalake_Project/IBM/IBM_Storage/SSH/iostats"  # <-- Set your local folder containing downloaded iostat dumps

    # Ensure the directory exists
    if not os.path.isdir(iostats_dir):
        print(f"Directory '{iostats_dir}' does not exist.")
        return

    # List files in the iostats_dir
    files = os.listdir(iostats_dir)
    if not files:
        print(f"No files found in '{iostats_dir}'.")
        return

    print(f"Found {len(files)} file(s) in '{iostats_dir}':\n")

    for filename in files:
        full_path = os.path.join(iostats_dir, filename)

        # Check it's indeed a file (not a subfolder)
        if not os.path.isfile(full_path):
            continue

        # Optional: Filter only "Nn_stats_xxx"-style filenames
        # if not filename.startswith(("Nn_stats_", "Nm_stats_", "Nv_stats_", "Nd_stats_")):
        #    continue

        # Parse the iostat dump
        stats = parse_iostat_file(full_path)

        # Print the results
        print(f"\n=== Parsed {filename} ===")
        for key, val in stats.items():
            print(f"{key}: {val}")

        # TODO:
        # - Store these in a data structure
        # - Compute deltas vs. previous measurements
        # - Write to JSON or text file, etc.

if __name__ == "__main__":
    main()
