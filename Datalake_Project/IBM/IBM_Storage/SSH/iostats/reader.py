
import os

# Set the target directory to "deltaValues"
directory = "/Datalake_Project/IBM/IBM_Storage/SSH/iostats/deltaValues"

def print_and_delete_files(directory):
    """
    Iterates through all files in the given directory, prints their content, and then deletes them.
    """
    # Get a list of all files in the directory
    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]

    if not files:
        print("No files found in the directory.")
        return

    # Iterate over each file
    for file in files:
        file_path = os.path.join(directory, file)

        try:
            # Print file content

            with open(file_path, "r", encoding="utf-8") as f:
                print(f.read())

            # Delete the file
            os.remove(file_path)
    #        print(f"[INFO] Deleted: {file}")

        except Exception as e:
            print(f"[ERROR] Could not process {file}: {e}")

if __name__ == "__main__":
    print_and_delete_files(directory)
   # print("\n[INFO] File processing completed.")
