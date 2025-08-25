import os
import re
import sys
import xml.etree.ElementTree as ET


# Get folder name from command-line argument
if len(sys.argv) != 2:
    print("Usage: python3 myscript.py <folder_name>")
    sys.exit(1)

xml_directory = os.path.abspath(sys.argv[1])  # Get the absolute path of the provided folder

if not os.path.isdir(xml_directory):
    print(f"Error: '{xml_directory}' is not a valid directory.")
    sys.exit(1)

#region Definitons
##############################################################
# Regex pattern for Nd only
pattern_Nd = re.compile(r'^(Nd)_stats_([^_]+)_(\d{6})_(\d{6})$')
pattern_Nv = re.compile(r'^(Nv)_stats_([^_]+)_(\d{6})_(\d{6})$')
pattern_Nm = re.compile(r'^(Nm)_stats_([^_]+)_(\d{6})_(\d{6})$')
pattern_Nn = re.compile(r'^(Nn)_stats_([^_]+)_(\d{6})_(\d{6})$')

# Fields to subtract for Nd
Nd_fields = ["ro", "wo", "rb", "wb", "re", "we", "rq", "wq" ,"ure", "uwe", "urq", "uwq", "pre", "pwe", "pro", "pwo", "rxl", "wxl"]
Nv_fields = ["ro", "wo", "rb", "wb", "re", "we", "rq", "wq" ,"ure", "uwe", "urq", "uwq", "pre", "pwe", "pro", "pwo", "rxl", "wxl", "rl", "wl", "rlw", "wlw"]
Nm_fields = ["ro", "wo", "rb", "wb", "re", "we", "rq", "wq" ,"ure", "uwe", "urq", "uwq", "pre", "pwe", "pro", "pwo", "ure", "uwe", "urq", "uwq"]
Nn_fields = ["ro", "wo", "rb", "wb", "re", "we", "rq", "wq" ,"ure", "uwe", "urq", "uwq", "pre", "pwe", "pro", "pwo", "rxl", "wxl"]
# XML Structure Definitions

###########################################################
#endregion
 ###########################################################################################f"nd_identifier_attr_{var_suffix}"  
def find_pairs(directory, typ):
    """Find old & new Nd files, parse them, compute deltas, and write a new XML file."""
    file_groups = {}

    # Collect Nd files
    for fname in os.listdir(directory):
        if (typ == "Nd"): 
            pattern_name=re.compile(r'^(Nd)_stats_([^_]+)_(\d{6})_(\d{6})$')
        elif (typ == "Nm"): 
             pattern_name=re.compile(r'^(Nm)_stats_([^_]+)_(\d{6})_(\d{6})$')
        elif (typ == "Nv"): 
            pattern_name=re.compile(r'^(Nv)_stats_([^_]+)_(\d{6})_(\d{6})$')
        elif (typ == "Nn"): 
            pattern_name=re.compile(r'^(Nn)_stats_([^_]+)_(\d{6})_(\d{6})$')
        
        match = pattern_name.match(fname)
        if match:
            prefix, node, yymmdd, hhmmss = match.groups()
            key = f"{prefix}_stats_{node}"
            file_groups.setdefault(key, []).append((fname, yymmdd, hhmmss))

    # Process each group if it has at least 2 files
    for key, fileinfo in file_groups.items():
        if len(fileinfo) < 2:
            print(f"[INFO] Skipping {key}, only {len(fileinfo)} file(s). Need >=2.")
            continue

        # Sort by date/time
        fileinfo.sort(key=lambda x: (x[1], x[2]))
        old_file, new_file = fileinfo[-2][0], fileinfo[-1][0]
        old_path = os.path.join(directory, old_file)
        new_path = os.path.join(directory, new_file)

        # print(f"\n===== {key} =====")
        # print(f"  Old => {old_file}")
        # print(f"  New => {new_file}")

        # Parse old & new XML
        old_tree, old_root, old_data = parsefunction(old_path, typ)
        new_tree, new_root, new_data = parsefunction(new_path, typ)

        # Compute deltas
        deltas = compute_deltas(old_data, new_data)

        # Write the delta XML
        delta_output_file = os.path.join("/Datalake_Project/IBM/IBM_Storage/SSH/iostats/deltaValues/", f"{key}_delta.xml")
        write_delta_xml(new_tree, new_root, deltas, delta_output_file, typ)

        # print(f"[INFO] Delta XML saved: {delta_output_file}")

def parsefunction(file_path, typ):
    """Parse an Nd XML file, remove namespaces, and extract numeric attributes."""
    # print(f"[DEBUG] parse_{typ}.xml => {file_path}")
    tree = ET.parse(file_path)
    root = tree.getroot()

    # Remove namespaces
    remove_namespace(root)

    data = {}
    if (typ == "Nd"): 
        rootname = ".//mdsk"
    elif (typ == "Nm"): 
        rootname = ".//mdsk"
    elif (typ == "Nv"): 
        rootname = ".//vdsk"
    elif (typ == "Nn"): 
        rootname = ".//node"
    
    

    # Find each <mdsk> parent
    for parent in root.findall(rootname):
        if (typ == "Nd"): 
            identifier_attr = "idx"
        elif (typ == "Nm"): 
            identifier_attr = "id"
        elif (typ == "Nv"): 
            identifier_attr = "id"
        elif (typ == "Nn"): 
            identifier_attr = "id"
        idx_value = parent.get(identifier_attr)
        if idx_value:
            if idx_value not in data:
                data[idx_value] = {}

            # Store numeric attributes
            for attr_name, val_str in parent.attrib.items():
                if (typ == "Nd"): 
                    fields = ["ro", "wo", "rb", "wb", "re", "we", "rq", "wq" ,"ure", "uwe", "urq", "uwq", "pre", "pwe", "pro", "pwo", "rxl", "wxl"]
                elif (typ == "Nm"): 
                    fields = ["ro", "wo", "rb", "wb", "re", "we", "rq", "wq" ,"ure", "uwe", "urq", "uwq", "pre", "pwe", "pro", "pwo", "rxl", "wxl"]
                elif (typ == "Nv"): 
                    fields = ["ro", "wo", "rb", "wb", "re", "we", "rq", "wq" ,"ure", "uwe", "urq", "uwq", "pre", "pwe", "pro", "pwo", "rxl", "wxl", "rl", "wl", "rlw", "wlw"] 
                elif (typ == "Nn"): 
                    fields =  ["ro", "wo", "rb", "wb", "re", "we", "rq", "wq" ,"ure", "uwe", "urq", "uwq", "pre", "pwe", "pro", "pwo", "rxl", "wxl"]
                
                if attr_name in fields:
                    try:
                        val_int = int(val_str)
                        data[idx_value][attr_name] = val_int
                    except ValueError:
                        pass

    print(f"[DEBUG] Final Extracted Data:\n{data}")
    return tree, root, data

def write_delta_xml(tree, root, deltas, output_file, typ):
    """Write a new XML file with delta values."""
    print("\n[DEBUG] write_delta_xml")
    if (typ == "Nd"): 
        rootname = ".//mdsk"
    elif (typ == "Nm"): 
        rootname = ".//mdsk"
    elif (typ == "Nv"): 
        rootname = ".//vdsk"
    elif (typ == "Nn"): 
        rootname = ".//node"
    
    

    # Find each <mdsk> parent
    for parent in root.findall(rootname):
        if (typ == "Nd"): 
            identifier_attr = "idx"
        elif (typ == "Nm"): 
            identifier_attr = "id"
        elif (typ == "Nv"): 
            identifier_attr = "id"
        elif (typ == "Nn"): 
            identifier_attr = "id"
        idx_value = parent.get(identifier_attr)
        if idx_value and idx_value in deltas:
            for attr_name, delta_value in deltas[idx_value].items():
                parent.set(attr_name, str(delta_value))  # Overwrite attribute with delta

    # Save the modified tree
    tree.write(output_file, encoding="utf-8", xml_declaration=True)

def delete_processed_files(directory):
    """Deletes all files in the given directory after processing."""
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        try:
            if os.path.isfile(file_path):  # Only delete files, not directories
                os.remove(file_path)
                print(f"Deleted file: {file_path}")
        except Exception as e:
            print(f"Error deleting {file_path}: {e}")



#region ### Non Unique Functions ###
def remove_namespace(elem):
    """Remove namespaces from XML elements in-place."""
    if elem.tag.startswith("{"):
        elem.tag = elem.tag.split("}", 1)[1]
    for child in elem:
        remove_namespace(child)


def compute_deltas(old_data, new_data):
    """Compute delta values (new - old)."""
    print("\n[DEBUG] compute_deltas => (new - old)")
    deltas = {}

    for idx_value, new_attrs in new_data.items():
        deltas[idx_value] = {}
        for attr_name, new_val in new_attrs.items():
            old_val = old_data.get(idx_value, {}).get(attr_name, 0)
            delta_val = new_val - old_val
            deltas[idx_value][attr_name] = delta_val
            print(f"  idx={idx_value}, attr={attr_name}, old={old_val}, new={new_val}, diff={delta_val}")

    return deltas

#endregion 


def main():
    for prefix in ["Nv", "Nm", "Nn", "Nd"]:
        find_pairs(xml_directory, prefix)
        print("\n[INFO] Delta computation and XML writing completed.")

    # After processing, delete all files in the provided directory
    delete_processed_files(xml_directory)

if __name__ == "__main__":
    main()
