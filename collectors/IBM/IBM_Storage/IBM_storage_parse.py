import json
import sys
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import os


def delete_file(file_path):
    try:
        os.remove(file_path)

    except Exception as e:
        print(f"Error deleting file {file_path}: {e}")

def handle_empty_value(value):
    """
    Returns 'NULL' if the value is an empty string or None;
    otherwise returns the value unchanged.
    """
    if value == "" or value is None:
        return "NULL"
    return value


def generate_insert_commands_for_lsmdiskgrp_by_id(json_file):
    """
    This function handles 'lsmdisk_by_id_responses.json' data
    by flattening the 'tiers' array for each record.
    """
    try:
        with open(json_file, "r") as f:
            data = json.load(f)

        utc_plus_3 = timezone(timedelta(hours=3))
        current_time = datetime.now(utc_plus_3)

        processed_records = 0
        for record_key, record in data.items():
            try:
                record_timestamp = current_time.isoformat()

                # Flatten the tier data
                if 'tiers' in record:
                    for tier in record['tiers']:
                        # Create flattened fields for tiers
                        flattened_record = {
                            'id': record['id'],
                            'name': record['name'],
                            'status': handle_empty_value(record['status']),
                            'mdisk_count': handle_empty_value(record['mdisk_count']),
                            'vdisk_count': handle_empty_value(record['vdisk_count']),
                            'capacity': handle_empty_value(record['capacity']),
                            'extent_size': handle_empty_value(record['extent_size']),
                            'free_capacity': handle_empty_value(record['free_capacity']),
                            'virtual_capacity': handle_empty_value(record['virtual_capacity']),
                            'used_capacity': handle_empty_value(record['used_capacity']),
                            'real_capacity': handle_empty_value(record['real_capacity']),
                            'overallocation': handle_empty_value(record['overallocation']),
                            'warning': handle_empty_value(record['warning']),
                            'easy_tier': handle_empty_value(record['easy_tier']),
                            'easy_tier_status': handle_empty_value(record['easy_tier_status']),
                            'tiers_tier': handle_empty_value(tier['tier']),
                            'tiers_tier_mdisk_count': handle_empty_value(tier['tier_mdisk_count']),
                            'tiers_tier_capacity': handle_empty_value(tier['tier_capacity']),
                            'tiers_tier_free_capacity': handle_empty_value(tier['tier_free_capacity']),
                            'compression_active': handle_empty_value(record['compression_active']),
                            'compression_virtual_capacity': handle_empty_value(record['compression_virtual_capacity']),
                            'compression_compressed_capacity': handle_empty_value(record['compression_compressed_capacity']),
                            'compression_uncompressed_capacity': handle_empty_value(record['compression_uncompressed_capacity']),
                            'site_id': handle_empty_value(record['site_id']),
                            'site_name': handle_empty_value(record['site_name']),
                            'parent_mdisk_grp_id': handle_empty_value(record['parent_mdisk_grp_id']),
                            'parent_mdisk_grp_name': handle_empty_value(record['parent_mdisk_grp_name']),
                            'child_mdisk_grp_count': handle_empty_value(record['child_mdisk_grp_count']),
                            'child_mdisk_grp_capacity': handle_empty_value(record['child_mdisk_grp_capacity']),
                            'type': handle_empty_value(record['type']),
                            'encrypt': handle_empty_value(record['encrypt']),
                            'owner_type': handle_empty_value(record['owner_type']),
                            'owner_id': handle_empty_value(record['owner_id']),
                            'owner_name': handle_empty_value(record['owner_name']),
                            'data_reduction': handle_empty_value(record['data_reduction']),
                            'used_capacity_before_reduction': handle_empty_value(record['used_capacity_before_reduction']),
                            'used_capacity_after_reduction': handle_empty_value(record['used_capacity_after_reduction']),
                            'overhead_capacity': handle_empty_value(record['overhead_capacity']),
                            'deduplication_capacity_saving': handle_empty_value(record['deduplication_capacity_saving']),
                            'reclaimable_capacity': handle_empty_value(record['reclaimable_capacity']),
                            'physical_capacity': handle_empty_value(record['physical_capacity']),
                            'physical_free_capacity': handle_empty_value(record['physical_free_capacity']),
                            'shared_resources': handle_empty_value(record['shared_resources']),
                            'vdisk_protection_enabled': handle_empty_value(record['vdisk_protection_enabled']),
                            'vdisk_protection_status': handle_empty_value(record['vdisk_protection_status']),
                            'easy_tier_fcm_over_allocation_max': handle_empty_value(record['easy_tier_fcm_over_allocation_max']),
                            'auto_expand': handle_empty_value(record['auto_expand']),
                            'auto_expand_max_capacity': handle_empty_value(record['auto_expand_max_capacity']),
                            'safeguarded': handle_empty_value(record['safeguarded']),
                            'provisioning_policy_id': handle_empty_value(record['provisioning_policy_id']),
                            'provisioning_policy_name': handle_empty_value(record['provisioning_policy_name']),
                            'timestamp': record_timestamp
                        }

                        # Create the SQL INSERT statement
                        sql_command = (
                            "INSERT INTO ibm_storage_mdisk_by_id ("
                            "id, name, status, mdisk_count, vdisk_count, capacity, extent_size, free_capacity, "
                            "virtual_capacity, used_capacity, real_capacity, overallocation, warning, easy_tier, "
                            "easy_tier_status, tiers_tier, tiers_tier_mdisk_count, tiers_tier_capacity, "
                            "tiers_tier_free_capacity, compression_active, compression_virtual_capacity, "
                            "compression_compressed_capacity, compression_uncompressed_capacity, site_id, site_name, "
                            "parent_mdisk_grp_id, parent_mdisk_grp_name, child_mdisk_grp_count, child_mdisk_grp_capacity, "
                            "type, encrypt, owner_type, owner_id, owner_name, data_reduction, used_capacity_before_reduction, "
                            "used_capacity_after_reduction, overhead_capacity, deduplication_capacity_saving, "
                            "reclaimable_capacity, physical_capacity, physical_free_capacity, shared_resources, "
                            "vdisk_protection_enabled, vdisk_protection_status, easy_tier_fcm_over_allocation_max, "
                            "auto_expand, auto_expand_max_capacity, safeguarded, provisioning_policy_id, "
                            "provisioning_policy_name, timestamp"
                            ") VALUES ("
                            f"'{flattened_record['id']}', '{flattened_record['name']}', "
                            f"'{flattened_record['status']}', {flattened_record['mdisk_count']}, "
                            f"{flattened_record['vdisk_count']}, '{flattened_record['capacity']}', "
                            f"{flattened_record['extent_size']}, '{flattened_record['free_capacity']}', "
                            f"'{flattened_record['virtual_capacity']}', '{flattened_record['used_capacity']}', "
                            f"'{flattened_record['real_capacity']}', {flattened_record['overallocation']}, "
                            f"{flattened_record['warning']}, '{flattened_record['easy_tier']}', "
                            f"'{flattened_record['easy_tier_status']}', '{flattened_record['tiers_tier']}', "
                            f"{flattened_record['tiers_tier_mdisk_count']}, '{flattened_record['tiers_tier_capacity']}', "
                            f"'{flattened_record['tiers_tier_free_capacity']}', "
                            f"'{flattened_record['compression_active']}', "
                            f"'{flattened_record['compression_virtual_capacity']}', "
                            f"'{flattened_record['compression_compressed_capacity']}', "
                            f"'{flattened_record['compression_uncompressed_capacity']}', "
                            f"{flattened_record['site_id']}, '{flattened_record['site_name']}', "
                            f"'{flattened_record['parent_mdisk_grp_id']}', "
                            f"'{flattened_record['parent_mdisk_grp_name']}', "
                            f"{flattened_record['child_mdisk_grp_count']}, "
                            f"'{flattened_record['child_mdisk_grp_capacity']}', "
                            f"'{flattened_record['type']}', '{flattened_record['encrypt']}', "
                            f"'{flattened_record['owner_type']}', '{flattened_record['owner_id']}', "
                            f"'{flattened_record['owner_name']}', '{flattened_record['data_reduction']}', "
                            f"'{flattened_record['used_capacity_before_reduction']}', "
                            f"'{flattened_record['used_capacity_after_reduction']}', "
                            f"'{flattened_record['overhead_capacity']}', "
                            f"'{flattened_record['deduplication_capacity_saving']}', "
                            f"'{flattened_record['reclaimable_capacity']}', "
                            f"'{flattened_record['physical_capacity']}', "
                            f"'{flattened_record['physical_free_capacity']}', "
                            f"'{flattened_record['shared_resources']}', "
                            f"'{flattened_record['vdisk_protection_enabled']}', "
                            f"'{flattened_record['vdisk_protection_status']}', "
                            f"'{flattened_record['easy_tier_fcm_over_allocation_max']}', "
                            f"'{flattened_record['auto_expand']}', "
                            f"'{flattened_record['auto_expand_max_capacity']}', "
                            f"'{flattened_record['safeguarded']}', "
                            f"'{flattened_record['provisioning_policy_id']}', "
                            f"'{flattened_record['provisioning_policy_name']}', "
                            f"'{flattened_record['timestamp']}');"
                        )

                        print(sql_command.strip())
                        processed_records += 1
            except Exception as e:
                print(f"Error processing record {record_key}: {e}")

        delete_file(json_file)

    except Exception as e:
        print(f"An error occurred: {e}")



def generate_insert_commands_for_lssystem_stats(json_file):
    """
    Reads a JSON file containing a list of stat records and generates an SQL INSERT statement.
    For each record, only 'stat_name' and 'stat_current' are used (as a name:value pair).
    """
    try:
        with open(json_file, "r") as f:
            data = json.load(f)
        
        # Build a dictionary with keys as stat_name and values as stat_current
        stats = {}
        for record in data:
            # Only use stat_name and stat_current; ignore peak and peak_time
            stat_name = record.get("stat_name")
            stat_current = record.get("stat_current")
            if stat_name:
                stats[stat_name] = handle_empty_value(stat_current)
        
        # Define the expected columns (in a fixed order)
        columns = [
            "compression_cpu_pc", "cpu_pc", "fc_mb", "fc_io", 
            "sas_mb", "sas_io", "iscsi_mb", "iscsi_io", 
            "write_cache_pc", "total_cache_pc", "vdisk_mb", 
            "vdisk_io", "vdisk_ms", "mdisk_mb", "mdisk_io", 
            "mdisk_ms", "drive_mb", "drive_io", "drive_ms", 
            "vdisk_r_mb", "vdisk_r_io", "vdisk_r_ms", 
            "vdisk_w_mb", "vdisk_w_io", "vdisk_w_ms", 
            "mdisk_r_mb", "mdisk_r_io", "mdisk_r_ms", 
            "mdisk_w_mb", "mdisk_w_io", "mdisk_w_ms", 
            "drive_r_mb", "drive_r_io", "drive_r_ms", 
            "drive_w_mb", "drive_w_io", "drive_w_ms", 
            "power_w", "temp_c", "temp_f", 
            "iplink_mb", "iplink_io", "iplink_comp_mb", 
            "cloud_up_mb", "cloud_up_ms", "cloud_down_mb", 
            "cloud_down_ms", "iser_mb", "iser_io"
        ]
        
        # Get the current timestamp in UTC+3
        utc_plus_3 = timezone(timedelta(hours=3))
        record_timestamp = datetime.now(utc_plus_3).isoformat()
        
        # Build the list of values in the same order; if a column is missing, use NULL.
        values = []
        for col in columns:
            # We assume the stat_current values are numeric strings (or "NULL")
            value = stats.get(col, "NULL")
            values.append(value)
        
        # Append the timestamp column/value (timestamp is treated as text and quoted)
        columns.append("timestamp")
        values.append(f"'{record_timestamp}'")
        
        # Build the final SQL command
        sql_command = (
            "INSERT INTO ibm_storage_system_stats (" + ", ".join(columns) + ") VALUES ("
            + ", ".join(str(v) for v in values) + ");"
        )
        
        print(sql_command)
        delete_file(json_file)    
    except Exception as e:
        print(f"An error occurred: {e}")


def generate_insert_commands_for_lshost_by_id(json_file):
    """
    This function handles 'lshost_by_id_responses.json' data
    by flattening the 'nodes' array for each record.
    """
    try:
        with open(json_file, "r") as f:
            data = json.load(f)

        utc_plus_3 = timezone(timedelta(hours=3))
        current_time = datetime.now(utc_plus_3)

        processed_records = 0
        for record_key, record in data.items():
            try:
                record_timestamp = current_time.isoformat()

                # Flatten the node data
                if 'nodes' in record:
                    for node in record['nodes']:
                        # Create flattened fields for nodes
                        flattened_record = {
                            'id': record['id'],
                            'name': record['name'],
                            'port_count': handle_empty_value(record['port_count']),
                            'type': handle_empty_value(record['type']),
                            'iogrp_count': handle_empty_value(record['iogrp_count']),
                            'status': handle_empty_value(record['status']),
                            'site_id': handle_empty_value(record['site_id']),
                            'site_name': handle_empty_value(record['site_name']),
                            'host_cluster_id': handle_empty_value(record['host_cluster_id']),
                            'host_cluster_name': handle_empty_value(record['host_cluster_name']),
                            'protocol': handle_empty_value(record['protocol']),
                            'status_policy': handle_empty_value(record['status_policy']),
                            'status_site': handle_empty_value(record['status_site']),
                            'nodes_WWPN': handle_empty_value(node['WWPN']),
                            'nodes_node_logged_in_count': handle_empty_value(node['node_logged_in_count']),
                            'nodes_state': handle_empty_value(node['state']),
                            'owner_id': handle_empty_value(record['owner_id']),
                            'owner_name': handle_empty_value(record['owner_name']),
                            'portset_id': handle_empty_value(record['portset_id']),
                            'portset_name': handle_empty_value(record['portset_name']),
                            'timestamp': record_timestamp
                        }

                        # Create the SQL INSERT statement
                        sql_command = (
                            "INSERT INTO ibm_storage_host_by_id ("
                            "id, name, port_count, type, iogrp_count, status, site_id, site_name, "
                            "host_cluster_id, host_cluster_name, protocol, status_policy, status_site, "
                            "nodes_WWPN, nodes_node_logged_in_count, nodes_state, owner_id, owner_name, "
                            "portset_id, portset_name, timestamp"
                            ") VALUES ("
                            f"'{flattened_record['id']}', "
                            f"'{flattened_record['name']}', "
                            f"{flattened_record['port_count']}, "
                            f"'{flattened_record['type']}', "
                            f"{flattened_record['iogrp_count']}, "
                            f"'{flattened_record['status']}', "
                            f"{flattened_record['site_id']}, "
                            f"'{flattened_record['site_name']}', "
                            f"{flattened_record['host_cluster_id']}, "
                            f"'{flattened_record['host_cluster_name']}', "
                            f"'{flattened_record['protocol']}', "
                            f"'{flattened_record['status_policy']}', "
                            f"'{flattened_record['status_site']}', "
                            f"'{flattened_record['nodes_WWPN']}', "
                            f"{flattened_record['nodes_node_logged_in_count']}, "
                            f"'{flattened_record['nodes_state']}', "
                            f"{flattened_record['owner_id']}, "
                            f"'{flattened_record['owner_name']}', "
                            f"{flattened_record['portset_id']}, "
                            f"'{flattened_record['portset_name']}', "
                            f"'{flattened_record['timestamp']}');"
                        )

                        print(sql_command.strip())
                        processed_records += 1
                
            except Exception as e:
                print(f"Error processing record {record_key}: {e}")
        delete_file(json_file)

    except Exception as e:
        print(f"An error occurred: {e}")


def generate_filtered_insert_commands(json_file):
    """
    Handles 'lshost_response.json' data without flattening 'nodes'
    (i.e., one record => one INSERT).
    """
    try:
        with open(json_file, "r") as f:
            data = json.load(f)

        utc_plus_3 = timezone(timedelta(hours=3))
        current_time = datetime.now(utc_plus_3)

        processed_records = 0
        for record in data:
            try:
                record_timestamp = current_time.isoformat()

                # Create a simple SQL INSERT statement
                sql_command = (
                    "INSERT INTO ibm_storage_host ("
                    "id, name, timestamp, port_count, iogrp_count, status, site_id, site_name, "
                    "host_cluster_id, host_cluster_name, protocol, owner_id, owner_name, "
                    "portset_id, portset_name"
                    ") VALUES ("
                    f"'{handle_empty_value(record['id'])}', "
                    f"'{handle_empty_value(record['name'])}', "
                    f"'{record_timestamp}', "
                    f"{handle_empty_value(record['port_count'])}, "
                    f"{handle_empty_value(record['iogrp_count'])}, "
                    f"'{handle_empty_value(record['status'])}', "
                    f"{handle_empty_value(record['site_id'])}, "
                    f"'{handle_empty_value(record['site_name'])}', "
                    f"{handle_empty_value(record['host_cluster_id'])}, "
                    f"'{handle_empty_value(record['host_cluster_name'])}', "
                    f"'{handle_empty_value(record['protocol'])}', "
                    f"{handle_empty_value(record['owner_id'])}, "
                    f"'{handle_empty_value(record['owner_name'])}', "
                    f"{handle_empty_value(record['portset_id'])}, "
                    f"'{handle_empty_value(record['portset_name'])}');"
                )

                print(sql_command.strip())
                processed_records += 1
            except Exception as e:
                print(f"Error processing record {record}: {e}")
        delete_file(json_file)
    except Exception as e:
        print(f"An error occurred: {e}")


def generate_insert_commands_for_lsmdiskgrp(json_file):
    """
    Handles 'lsmdiskgrp_response.json' data (no tier flattening).
    """
    try:
        with open(json_file, "r") as f:
            data = json.load(f)

        utc_plus_3 = timezone(timedelta(hours=3))
        current_time = datetime.now(utc_plus_3)

        processed_records = 0
        for record in data:
            try:
                record_timestamp = current_time.isoformat()

                # Create the SQL INSERT statement
                sql_command = (
                    "INSERT INTO ibm_storage_mdiskgrp ("
                    "id, name, status, mdisk_count, vdisk_count, capacity, extent_size, free_capacity, "
                    "virtual_capacity, used_capacity, real_capacity, overallocation, warning, easy_tier, "
                    "easy_tier_status, compression_active, compression_virtual_capacity, compression_compressed_capacity, "
                    "compression_uncompressed_capacity, parent_mdisk_grp_id, parent_mdisk_grp_name, "
                    "child_mdisk_grp_count, child_mdisk_grp_capacity, type, encrypt, owner_type, owner_id, "
                    "owner_name, site_id, site_name, data_reduction, used_capacity_before_reduction, "
                    "used_capacity_after_reduction, overhead_capacity, deduplication_capacity_saving, reclaimable_capacity, "
                    "easy_tier_fcm_over_allocation_max, provisioning_policy_id, provisioning_policy_name, timestamp"
                    ") VALUES ("
                    f"'{handle_empty_value(record['id'])}', "
                    f"'{handle_empty_value(record['name'])}', "
                    f"'{handle_empty_value(record['status'])}', "
                    f"{handle_empty_value(record['mdisk_count'])}, "
                    f"{handle_empty_value(record['vdisk_count'])}, "
                    f"'{handle_empty_value(record['capacity'])}', "
                    f"{handle_empty_value(record['extent_size'])}, "
                    f"'{handle_empty_value(record['free_capacity'])}', "
                    f"'{handle_empty_value(record['virtual_capacity'])}', "
                    f"'{handle_empty_value(record['used_capacity'])}', "
                    f"'{handle_empty_value(record['real_capacity'])}', "
                    f"{handle_empty_value(record['overallocation'])}, "
                    f"{handle_empty_value(record['warning'])}, "
                    f"'{handle_empty_value(record['easy_tier'])}', "
                    f"'{handle_empty_value(record['easy_tier_status'])}', "
                    f"'{handle_empty_value(record['compression_active'])}', "
                    f"'{handle_empty_value(record['compression_virtual_capacity'])}', "
                    f"'{handle_empty_value(record['compression_compressed_capacity'])}', "
                    f"'{handle_empty_value(record['compression_uncompressed_capacity'])}', "
                    f"'{handle_empty_value(record['parent_mdisk_grp_id'])}', "
                    f"'{handle_empty_value(record['parent_mdisk_grp_name'])}', "
                    f"{handle_empty_value(record['child_mdisk_grp_count'])}, "
                    f"'{handle_empty_value(record['child_mdisk_grp_capacity'])}', "
                    f"'{handle_empty_value(record['type'])}', "
                    f"'{handle_empty_value(record['encrypt'])}', "
                    f"'{handle_empty_value(record['owner_type'])}', "
                    f"'{handle_empty_value(record['owner_id'])}', "
                    f"'{handle_empty_value(record['owner_name'])}', "
                    f"{handle_empty_value(record['site_id'])}, "
                    f"'{handle_empty_value(record['site_name'])}', "
                    f"'{handle_empty_value(record['data_reduction'])}', "
                    f"'{handle_empty_value(record['used_capacity_before_reduction'])}', "
                    f"'{handle_empty_value(record['used_capacity_after_reduction'])}', "
                    f"'{handle_empty_value(record['overhead_capacity'])}', "
                    f"'{handle_empty_value(record['deduplication_capacity_saving'])}', "
                    f"'{handle_empty_value(record['reclaimable_capacity'])}', "
                    f"'{handle_empty_value(record['easy_tier_fcm_over_allocation_max'])}', "
                    f"'{handle_empty_value(record['provisioning_policy_id'])}', "
                    f"'{handle_empty_value(record['provisioning_policy_name'])}', "
                    f"'{record_timestamp}');"
                )

                print(sql_command.strip())
                processed_records += 1
            except Exception as e:
                print(f"Error processing record {record}: {e}")

        delete_file(json_file)
    except Exception as e:
        print(f"An error occurred: {e}")


def generate_insert_commands_for_lsvdisk(json_file):
    """
    Handles 'lsvdisk_response.json' data.
    """
    try:
        with open(json_file, "r") as f:
            data = json.load(f)

        utc_plus_3 = timezone(timedelta(hours=3))
        current_time = datetime.now(utc_plus_3)

        processed_records = 0
        for record in data:
            try:
                record_timestamp = current_time.isoformat()

                # Create the SQL INSERT statement
                sql_command = (
                    "INSERT INTO ibm_storage_vdisk ("
                    "id, name, IO_group_id, IO_group_name, status, mdisk_grp_id, mdisk_grp_name, "
                    "capacity, type, FC_id, FC_name, RC_id, RC_name, vdisk_UID, fc_map_count, "
                    "copy_count, fast_write_state, se_copy_count, RC_change, compressed_copy_count, "
                    "parent_mdisk_grp_id, parent_mdisk_grp_name, owner_id, owner_name, formatting, "
                    "encrypt, volume_id, volume_name, function, protocol, timestamp"
                    ") VALUES ("
                    f"'{handle_empty_value(record['id'])}', "
                    f"'{handle_empty_value(record['name'])}', "
                    f"'{handle_empty_value(record['IO_group_id'])}', "
                    f"'{handle_empty_value(record['IO_group_name'])}', "
                    f"'{handle_empty_value(record['status'])}', "
                    f"'{handle_empty_value(record['mdisk_grp_id'])}', "
                    f"'{handle_empty_value(record['mdisk_grp_name'])}', "
                    f"'{handle_empty_value(record['capacity'])}', "
                    f"'{handle_empty_value(record['type'])}', "
                    f"'{handle_empty_value(record['FC_id'])}', "
                    f"'{handle_empty_value(record['FC_name'])}', "
                    f"'{handle_empty_value(record['RC_id'])}', "
                    f"'{handle_empty_value(record['RC_name'])}', "
                    f"'{handle_empty_value(record['vdisk_UID'])}', "
                    f"'{handle_empty_value(record['fc_map_count'])}', "
                    f"'{handle_empty_value(record['copy_count'])}', "
                    f"'{handle_empty_value(record['fast_write_state'])}', "
                    f"'{handle_empty_value(record['se_copy_count'])}', "
                    f"'{handle_empty_value(record['RC_change'])}', "
                    f"'{handle_empty_value(record['compressed_copy_count'])}', "
                    f"'{handle_empty_value(record['parent_mdisk_grp_id'])}', "
                    f"'{handle_empty_value(record['parent_mdisk_grp_name'])}', "
                    f"'{handle_empty_value(record['owner_id'])}', "
                    f"'{handle_empty_value(record['owner_name'])}', "
                    f"'{handle_empty_value(record['formatting'])}', "
                    f"'{handle_empty_value(record['encrypt'])}', "
                    f"'{handle_empty_value(record['volume_id'])}', "
                    f"'{handle_empty_value(record['volume_name'])}', "
                    f"'{handle_empty_value(record['function'])}', "
                    f"'{handle_empty_value(record['protocol'])}', "
                    f"'{record_timestamp}');"
                )

                print(sql_command.strip())
                processed_records += 1
            except Exception as e:
                print(f"Error processing record {record}: {e}")
        delete_file(json_file)
    except Exception as e:
        print(f"An error occurred: {e}")


def generate_insert_commands_for_lssystem(json_file):
    """
    This function reads a single JSON object from 'json_file', then:
      1) Flattens its 'tiers' array so each tier becomes a separate INSERT.
      2) Prints each INSERT statement to stdout.
    """
    try:
        with open(json_file, "r") as f:
            data = json.load(f)

        # Get the current time in UTC+3
        utc_plus_3 = timezone(timedelta(hours=3))
        current_time = datetime.now(utc_plus_3)

        processed_records = 0

        # If the JSON object contains a 'tiers' array, iterate over it
        if 'tiers' in data:
            for tier in data['tiers']:
                record_timestamp = current_time.isoformat()

                # Build a single flattened record that includes
                # the top-level keys + the fields from each tier
                flattened_record = {
                    # Top-level fields from data
                    'id':             handle_empty_value(data.get('id')),
                    'name':           handle_empty_value(data.get('name')),
                    'location':       handle_empty_value(data.get('location')),
                    'partnership':    handle_empty_value(data.get('partnership')),
                    'total_mdisk_capacity':          handle_empty_value(data.get('total_mdisk_capacity')),
                    'space_in_mdisk_grps':           handle_empty_value(data.get('space_in_mdisk_grps')),
                    'space_allocated_to_vdisks':      handle_empty_value(data.get('space_allocated_to_vdisks')),
                    'total_free_space':              handle_empty_value(data.get('total_free_space')),
                    'total_vdiskcopy_capacity':       handle_empty_value(data.get('total_vdiskcopy_capacity')),
                    'total_used_capacity':            handle_empty_value(data.get('total_used_capacity')),
                    'total_overallocation':           handle_empty_value(data.get('total_overallocation')),
                    'total_vdisk_capacity':           handle_empty_value(data.get('total_vdisk_capacity')),
                    'total_allocated_extent_capacity': handle_empty_value(data.get('total_allocated_extent_capacity')),
                    'statistics_status':     handle_empty_value(data.get('statistics_status')),
                    'statistics_frequency':  handle_empty_value(data.get('statistics_frequency')),
                    'cluster_locale':        handle_empty_value(data.get('cluster_locale')),
                    'time_zone':             handle_empty_value(data.get('time_zone')),
                    'code_level':            handle_empty_value(data.get('code_level')),
                    'console_IP':            handle_empty_value(data.get('console_IP')),
                    'id_alias':              handle_empty_value(data.get('id_alias')),
                    'gm_link_tolerance':     handle_empty_value(data.get('gm_link_tolerance')),
                    'gm_inter_cluster_delay_simulation': handle_empty_value(data.get('gm_inter_cluster_delay_simulation')),
                    'gm_intra_cluster_delay_simulation': handle_empty_value(data.get('gm_intra_cluster_delay_simulation')),
                    'gm_max_host_delay':     handle_empty_value(data.get('gm_max_host_delay')),
                    'email_reply':           handle_empty_value(data.get('email_reply')),
                    'email_contact':         handle_empty_value(data.get('email_contact')),
                    'email_contact_primary': handle_empty_value(data.get('email_contact_primary')),
                    'email_contact_alternate': handle_empty_value(data.get('email_contact_alternate')),
                    'email_contact_location':  handle_empty_value(data.get('email_contact_location')),
                    'email_contact2':          handle_empty_value(data.get('email_contact2')),
                    'email_contact2_primary':  handle_empty_value(data.get('email_contact2_primary')),
                    'email_contact2_alternate': handle_empty_value(data.get('email_contact2_alternate')),
                    'email_state':             handle_empty_value(data.get('email_state')),
                    'inventory_mail_interval': handle_empty_value(data.get('inventory_mail_interval')),
                    'cluster_ntp_IP_address':  handle_empty_value(data.get('cluster_ntp_IP_address')),
                    'cluster_isns_IP_address': handle_empty_value(data.get('cluster_isns_IP_address')),
                    'iscsi_auth_method':       handle_empty_value(data.get('iscsi_auth_method')),
                    'iscsi_chap_secret':       handle_empty_value(data.get('iscsi_chap_secret')),
                    'auth_service_configured': handle_empty_value(data.get('auth_service_configured')),
                    'auth_service_enabled':    handle_empty_value(data.get('auth_service_enabled')),
                    'auth_service_url':        handle_empty_value(data.get('auth_service_url')),
                    'auth_service_user_name':  handle_empty_value(data.get('auth_service_user_name')),
                    'auth_service_pwd_set':    handle_empty_value(data.get('auth_service_pwd_set')),
                    'auth_service_cert_set':   handle_empty_value(data.get('auth_service_cert_set')),
                    'auth_service_type':       handle_empty_value(data.get('auth_service_type')),
                    'relationship_bandwidth_limit': handle_empty_value(data.get('relationship_bandwidth_limit')),
                    
                    # Tiers fields (flattened from each tier element)
                    'tiers_tier':               handle_empty_value(tier.get('tier')),
                    'tiers_tier_capacity':      handle_empty_value(tier.get('tier_capacity')),
                    'tiers_tier_free_capacity': handle_empty_value(tier.get('tier_free_capacity')),

                    'easy_tier_acceleration':   handle_empty_value(data.get('easy_tier_acceleration')),
                    'has_nas_key':              handle_empty_value(data.get('has_nas_key')),
                    'layer':                    handle_empty_value(data.get('layer')),
                    'rc_buffer_size':           handle_empty_value(data.get('rc_buffer_size')),
                    'compression_active':       handle_empty_value(data.get('compression_active')),
                    'compression_virtual_capacity': handle_empty_value(data.get('compression_virtual_capacity')),
                    'compression_compressed_capacity': handle_empty_value(data.get('compression_compressed_capacity')),
                    'compression_uncompressed_capacity': handle_empty_value(data.get('compression_uncompressed_capacity')),
                    'cache_prefetch':             handle_empty_value(data.get('cache_prefetch')),
                    'email_organization':         handle_empty_value(data.get('email_organization')),
                    'email_machine_address':      handle_empty_value(data.get('email_machine_address')),
                    'email_machine_city':         handle_empty_value(data.get('email_machine_city')),
                    'email_machine_state':        handle_empty_value(data.get('email_machine_state')),
                    'email_machine_zip':          handle_empty_value(data.get('email_machine_zip')),
                    'email_machine_country':      handle_empty_value(data.get('email_machine_country')),
                    'total_drive_raw_capacity':   handle_empty_value(data.get('total_drive_raw_capacity')),
                    'compression_destage_mode':   handle_empty_value(data.get('compression_destage_mode')),
                    'local_fc_port_mask':         handle_empty_value(data.get('local_fc_port_mask')),
                    'partner_fc_port_mask':       handle_empty_value(data.get('partner_fc_port_mask')),
                    'high_temp_mode':             handle_empty_value(data.get('high_temp_mode')),
                    'topology':                   handle_empty_value(data.get('topology')),
                    'topology_status':            handle_empty_value(data.get('topology_status')),
                    'rc_auth_method':             handle_empty_value(data.get('rc_auth_method')),
                    'vdisk_protection_time':      handle_empty_value(data.get('vdisk_protection_time')),
                    'vdisk_protection_enabled':   handle_empty_value(data.get('vdisk_protection_enabled')),
                    'product_name':               handle_empty_value(data.get('product_name')),
                    'odx':                        handle_empty_value(data.get('odx')),
                    'max_replication_delay':      handle_empty_value(data.get('max_replication_delay')),
                    'partnership_exclusion_threshold': handle_empty_value(data.get('partnership_exclusion_threshold')),
                    'gen1_compatibility_mode_enabled': handle_empty_value(data.get('gen1_compatibility_mode_enabled')),
                    'ibm_customer':              handle_empty_value(data.get('ibm_customer')),
                    'ibm_component':             handle_empty_value(data.get('ibm_component')),
                    'ibm_country':               handle_empty_value(data.get('ibm_country')),
                    'tier_scm_compressed_data_used':       handle_empty_value(data.get('tier_scm_compressed_data_used')),
                    'tier0_flash_compressed_data_used':     handle_empty_value(data.get('tier0_flash_compressed_data_used')),
                    'tier1_flash_compressed_data_used':     handle_empty_value(data.get('tier1_flash_compressed_data_used')),
                    'tier_enterprise_compressed_data_used': handle_empty_value(data.get('tier_enterprise_compressed_data_used')),
                    'tier_nearline_compressed_data_used':   handle_empty_value(data.get('tier_nearline_compressed_data_used')),
                    'total_reclaimable_capacity': handle_empty_value(data.get('total_reclaimable_capacity')),
                    'physical_capacity':          handle_empty_value(data.get('physical_capacity')),
                    'physical_free_capacity':     handle_empty_value(data.get('physical_free_capacity')),
                    'used_capacity_before_reduction': handle_empty_value(data.get('used_capacity_before_reduction')),
                    'used_capacity_after_reduction':  handle_empty_value(data.get('used_capacity_after_reduction')),
                    'overhead_capacity':          handle_empty_value(data.get('overhead_capacity')),
                    'deduplication_capacity_saving': handle_empty_value(data.get('deduplication_capacity_saving')),
                    'enhanced_callhome':          handle_empty_value(data.get('enhanced_callhome')),
                    'censor_callhome':            handle_empty_value(data.get('censor_callhome')),
                    'host_unmap':                 handle_empty_value(data.get('host_unmap')),
                    'backend_unmap':              handle_empty_value(data.get('backend_unmap')),
                    'quorum_mode':                handle_empty_value(data.get('quorum_mode')),
                    'quorum_site_id':             handle_empty_value(data.get('quorum_site_id')),
                    'quorum_site_name':           handle_empty_value(data.get('quorum_site_name')),
                    'quorum_lease':               handle_empty_value(data.get('quorum_lease')),
                    'automatic_vdisk_analysis_enabled': handle_empty_value(data.get('automatic_vdisk_analysis_enabled')),
                    'callhome_accepted_usage':     handle_empty_value(data.get('callhome_accepted_usage')),
                    'safeguarded_copy_suspended': handle_empty_value(data.get('safeguarded_copy_suspended')),
                    
                    # Timestamp for each inserted row
                    'timestamp': record_timestamp
                }

                # Build the INSERT command. We flatten everything, including
                # one set of columns for each 'tier' entry.
                sql_command = (
                    "INSERT INTO ibm_storage_system ("
                    "id, name, location, partnership, total_mdisk_capacity, space_in_mdisk_grps, "
                    "space_allocated_to_vdisks, total_free_space, total_vdiskcopy_capacity, total_used_capacity, "
                    "total_overallocation, total_vdisk_capacity, total_allocated_extent_capacity, statistics_status, "
                    "statistics_frequency, cluster_locale, time_zone, code_level, console_IP, id_alias, gm_link_tolerance, "
                    "gm_inter_cluster_delay_simulation, gm_intra_cluster_delay_simulation, gm_max_host_delay, email_reply, "
                    "email_contact, email_contact_primary, email_contact_alternate, email_contact_location, email_contact2, "
                    "email_contact2_primary, email_contact2_alternate, email_state, inventory_mail_interval, "
                    "cluster_ntp_IP_address, cluster_isns_IP_address, iscsi_auth_method, iscsi_chap_secret, "
                    "auth_service_configured, auth_service_enabled, auth_service_url, auth_service_user_name, "
                    "auth_service_pwd_set, auth_service_cert_set, auth_service_type, relationship_bandwidth_limit, "
                    "tiers_tier, tiers_tier_capacity, tiers_tier_free_capacity, easy_tier_acceleration, has_nas_key, "
                    "layer, rc_buffer_size, compression_active, compression_virtual_capacity, compression_compressed_capacity, "
                    "compression_uncompressed_capacity, cache_prefetch, email_organization, email_machine_address, "
                    "email_machine_city, email_machine_state, email_machine_zip, email_machine_country, "
                    "total_drive_raw_capacity, compression_destage_mode, local_fc_port_mask, partner_fc_port_mask, "
                    "high_temp_mode, topology, topology_status, rc_auth_method, vdisk_protection_time, vdisk_protection_enabled, "
                    "product_name, odx, max_replication_delay, partnership_exclusion_threshold, gen1_compatibility_mode_enabled, "
                    "ibm_customer, ibm_component, ibm_country, tier_scm_compressed_data_used, tier0_flash_compressed_data_used, "
                    "tier1_flash_compressed_data_used, tier_enterprise_compressed_data_used, tier_nearline_compressed_data_used, "
                    "total_reclaimable_capacity, physical_capacity, physical_free_capacity, used_capacity_before_reduction, "
                    "used_capacity_after_reduction, overhead_capacity, deduplication_capacity_saving, enhanced_callhome, "
                    "censor_callhome, host_unmap, backend_unmap, quorum_mode, quorum_site_id, quorum_site_name, "
                    "quorum_lease, automatic_vdisk_analysis_enabled, callhome_accepted_usage, safeguarded_copy_suspended, "
                    "timestamp"
                    ") VALUES ("
                    f"'{flattened_record['id']}', '{flattened_record['name']}', '{flattened_record['location']}', "
                    f"'{flattened_record['partnership']}', '{flattened_record['total_mdisk_capacity']}', "
                    f"'{flattened_record['space_in_mdisk_grps']}', '{flattened_record['space_allocated_to_vdisks']}', "
                    f"'{flattened_record['total_free_space']}', '{flattened_record['total_vdiskcopy_capacity']}', "
                    f"'{flattened_record['total_used_capacity']}', {flattened_record['total_overallocation']}, "
                    f"'{flattened_record['total_vdisk_capacity']}', '{flattened_record['total_allocated_extent_capacity']}', "
                    f"'{flattened_record['statistics_status']}', '{flattened_record['statistics_frequency']}', "
                    f"'{flattened_record['cluster_locale']}', '{flattened_record['time_zone']}', "
                    f"'{flattened_record['code_level']}', '{flattened_record['console_IP']}', "
                    f"'{flattened_record['id_alias']}', {flattened_record['gm_link_tolerance']}, "
                    f"{flattened_record['gm_inter_cluster_delay_simulation']}, "
                    f"{flattened_record['gm_intra_cluster_delay_simulation']}, "
                    f"{flattened_record['gm_max_host_delay']}, '{flattened_record['email_reply']}', "
                    f"'{flattened_record['email_contact']}', '{flattened_record['email_contact_primary']}', "
                    f"'{flattened_record['email_contact_alternate']}', '{flattened_record['email_contact_location']}', "
                    f"'{flattened_record['email_contact2']}', '{flattened_record['email_contact2_primary']}', "
                    f"'{flattened_record['email_contact2_alternate']}', '{flattened_record['email_state']}', "
                    f"{flattened_record['inventory_mail_interval']}, '{flattened_record['cluster_ntp_IP_address']}', "
                    f"'{flattened_record['cluster_isns_IP_address']}', '{flattened_record['iscsi_auth_method']}', "
                    f"'{flattened_record['iscsi_chap_secret']}', '{flattened_record['auth_service_configured']}', "
                    f"'{flattened_record['auth_service_enabled']}', '{flattened_record['auth_service_url']}', "
                    f"'{flattened_record['auth_service_user_name']}', '{flattened_record['auth_service_pwd_set']}', "
                    f"'{flattened_record['auth_service_cert_set']}', '{flattened_record['auth_service_type']}', "
                    f"{flattened_record['relationship_bandwidth_limit']}, '{flattened_record['tiers_tier']}', "
                    f"'{flattened_record['tiers_tier_capacity']}', '{flattened_record['tiers_tier_free_capacity']}', "
                    f"'{flattened_record['easy_tier_acceleration']}', '{flattened_record['has_nas_key']}', "
                    f"'{flattened_record['layer']}', {flattened_record['rc_buffer_size']}, "
                    f"'{flattened_record['compression_active']}', '{flattened_record['compression_virtual_capacity']}', "
                    f"'{flattened_record['compression_compressed_capacity']}', "
                    f"'{flattened_record['compression_uncompressed_capacity']}', "
                    f"'{flattened_record['cache_prefetch']}', '{flattened_record['email_organization']}', "
                    f"'{flattened_record['email_machine_address']}', '{flattened_record['email_machine_city']}', "
                    f"'{flattened_record['email_machine_state']}', '{flattened_record['email_machine_zip']}', "
                    f"'{flattened_record['email_machine_country']}', '{flattened_record['total_drive_raw_capacity']}', "
                    f"'{flattened_record['compression_destage_mode']}', '{flattened_record['local_fc_port_mask']}', "
                    f"'{flattened_record['partner_fc_port_mask']}', '{flattened_record['high_temp_mode']}', "
                    f"'{flattened_record['topology']}', '{flattened_record['topology_status']}', "
                    f"'{flattened_record['rc_auth_method']}', {flattened_record['vdisk_protection_time']}, "
                    f"'{flattened_record['vdisk_protection_enabled']}', '{flattened_record['product_name']}', "
                    f"'{flattened_record['odx']}', {flattened_record['max_replication_delay']}, "
                    f"{flattened_record['partnership_exclusion_threshold']}, "
                    f"'{flattened_record['gen1_compatibility_mode_enabled']}', '{flattened_record['ibm_customer']}', "
                    f"'{flattened_record['ibm_component']}', '{flattened_record['ibm_country']}', "
                    f"'{flattened_record['tier_scm_compressed_data_used']}', "
                    f"'{flattened_record['tier0_flash_compressed_data_used']}', "
                    f"'{flattened_record['tier1_flash_compressed_data_used']}', "
                    f"'{flattened_record['tier_enterprise_compressed_data_used']}', "
                    f"'{flattened_record['tier_nearline_compressed_data_used']}', "
                    f"'{flattened_record['total_reclaimable_capacity']}', '{flattened_record['physical_capacity']}', "
                    f"'{flattened_record['physical_free_capacity']}', '{flattened_record['used_capacity_before_reduction']}', "
                    f"'{flattened_record['used_capacity_after_reduction']}', '{flattened_record['overhead_capacity']}', "
                    f"'{flattened_record['deduplication_capacity_saving']}', '{flattened_record['enhanced_callhome']}', "
                    f"'{flattened_record['censor_callhome']}', '{flattened_record['host_unmap']}', "
                    f"'{flattened_record['backend_unmap']}', '{flattened_record['quorum_mode']}', "
                    f"'{flattened_record['quorum_site_id']}', '{flattened_record['quorum_site_name']}', "
                    f"'{flattened_record['quorum_lease']}', '{flattened_record['automatic_vdisk_analysis_enabled']}', "
                    f"'{flattened_record['callhome_accepted_usage']}', '{flattened_record['safeguarded_copy_suspended']}', "
                    f"'{flattened_record['timestamp']}');"
                )

                print(sql_command.strip())
                processed_records += 1
        delete_file(json_file)
    except Exception as e:
        print(f"An error occurred: {e}")

def flatten_node_stats(json_file):
    """
    Reads a JSON file, groups stats by node_id and node_name, and generates SQL INSERT statements.
    """
    try:
        with open(json_file, "r") as f:
            data = json.load(f)

        # Group stats by node_id and node_name
        grouped = defaultdict(lambda: defaultdict(dict))

        for entry in data:
            node_id = entry["node_id"]
            node_name = entry["node_name"]
            stat_name = entry["stat_name"]
            stat_current = entry["stat_current"]

            # Ensure node_id and node_name are included in the grouped structure
            grouped[node_id]["node_id"] = node_id
            grouped[node_id]["node_name"] = node_name

            # Add the stat_current value under the stat_name key
            grouped[node_id][stat_name] = stat_current

        # Convert from nested defaultdict to a list of dicts
        result = [dict(stats) for stats in grouped.values()]

        # Generate SQL INSERT statements
        utc_plus_3 = timezone(timedelta(hours=3))
        current_time = datetime.now(utc_plus_3)

        processed_records = 0
        for record in result:
            try:
                record_timestamp = current_time.isoformat()

                # Build the SQL INSERT statement
                sql_command = (
                    "INSERT INTO ibm_storage_node_stats ("
                    "node_id, node_name, compression_cpu_pc, cpu_pc, fc_mb, fc_io, "
                    "sas_mb, sas_io, iscsi_mb, iscsi_io, write_cache_pc, total_cache_pc, "
                    "vdisk_mb, vdisk_io, vdisk_ms, mdisk_mb, mdisk_io, mdisk_ms, drive_mb, "
                    "drive_io, drive_ms, vdisk_r_mb, vdisk_r_io, vdisk_r_ms, vdisk_w_mb, "
                    "vdisk_w_io, vdisk_w_ms, mdisk_r_mb, mdisk_r_io, mdisk_r_ms, mdisk_w_mb, "
                    "mdisk_w_io, mdisk_w_ms, drive_r_mb, drive_r_io, drive_r_ms, drive_w_mb, "
                    "drive_w_io, drive_w_ms, iplink_mb, iplink_io, iplink_comp_mb, cloud_up_mb, "
                    "cloud_up_ms, cloud_down_mb, cloud_down_ms, iser_mb, iser_io, timestamp"
                    ") VALUES ("
                    f"{handle_empty_value(record['node_id'])}, "
                    f"'{handle_empty_value(record['node_name'])}', "
                    f"{handle_empty_value(record.get('compression_cpu_pc', 'NULL'))}, "
                    f"{handle_empty_value(record.get('cpu_pc', 'NULL'))}, "
                    f"{handle_empty_value(record.get('fc_mb', 'NULL'))}, "
                    f"{handle_empty_value(record.get('fc_io', 'NULL'))}, "
                    f"{handle_empty_value(record.get('sas_mb', 'NULL'))}, "
                    f"{handle_empty_value(record.get('sas_io', 'NULL'))}, "
                    f"{handle_empty_value(record.get('iscsi_mb', 'NULL'))}, "
                    f"{handle_empty_value(record.get('iscsi_io', 'NULL'))}, "
                    f"{handle_empty_value(record.get('write_cache_pc', 'NULL'))}, "
                    f"{handle_empty_value(record.get('total_cache_pc', 'NULL'))}, "
                    f"{handle_empty_value(record.get('vdisk_mb', 'NULL'))}, "
                    f"{handle_empty_value(record.get('vdisk_io', 'NULL'))}, "
                    f"{handle_empty_value(record.get('vdisk_ms', 'NULL'))}, "
                    f"{handle_empty_value(record.get('mdisk_mb', 'NULL'))}, "
                    f"{handle_empty_value(record.get('mdisk_io', 'NULL'))}, "
                    f"{handle_empty_value(record.get('mdisk_ms', 'NULL'))}, "
                    f"{handle_empty_value(record.get('drive_mb', 'NULL'))}, "
                    f"{handle_empty_value(record.get('drive_io', 'NULL'))}, "
                    f"{handle_empty_value(record.get('drive_ms', 'NULL'))}, "
                    f"{handle_empty_value(record.get('vdisk_r_mb', 'NULL'))}, "
                    f"{handle_empty_value(record.get('vdisk_r_io', 'NULL'))}, "
                    f"{handle_empty_value(record.get('vdisk_r_ms', 'NULL'))}, "
                    f"{handle_empty_value(record.get('vdisk_w_mb', 'NULL'))}, "
                    f"{handle_empty_value(record.get('vdisk_w_io', 'NULL'))}, "
                    f"{handle_empty_value(record.get('vdisk_w_ms', 'NULL'))}, "
                    f"{handle_empty_value(record.get('mdisk_r_mb', 'NULL'))}, "
                    f"{handle_empty_value(record.get('mdisk_r_io', 'NULL'))}, "
                    f"{handle_empty_value(record.get('mdisk_r_ms', 'NULL'))}, "
                    f"{handle_empty_value(record.get('mdisk_w_mb', 'NULL'))}, "
                    f"{handle_empty_value(record.get('mdisk_w_io', 'NULL'))}, "
                    f"{handle_empty_value(record.get('mdisk_w_ms', 'NULL'))}, "
                    f"{handle_empty_value(record.get('drive_r_mb', 'NULL'))}, "
                    f"{handle_empty_value(record.get('drive_r_io', 'NULL'))}, "
                    f"{handle_empty_value(record.get('drive_r_ms', 'NULL'))}, "
                    f"{handle_empty_value(record.get('drive_w_mb', 'NULL'))}, "
                    f"{handle_empty_value(record.get('drive_w_io', 'NULL'))}, "
                    f"{handle_empty_value(record.get('drive_w_ms', 'NULL'))}, "
                    f"{handle_empty_value(record.get('iplink_mb', 'NULL'))}, "
                    f"{handle_empty_value(record.get('iplink_io', 'NULL'))}, "
                    f"{handle_empty_value(record.get('iplink_comp_mb', 'NULL'))}, "
                    f"{handle_empty_value(record.get('cloud_up_mb', 'NULL'))}, "
                    f"{handle_empty_value(record.get('cloud_up_ms', 'NULL'))}, "
                    f"{handle_empty_value(record.get('cloud_down_mb', 'NULL'))}, "
                    f"{handle_empty_value(record.get('cloud_down_ms', 'NULL'))}, "
                    f"{handle_empty_value(record.get('iser_mb', 'NULL'))}, "
                    f"{handle_empty_value(record.get('iser_io', 'NULL'))}, "
                    f"'{record_timestamp}'"
                    ");"
                )

                print(sql_command)
                processed_records += 1
            except Exception as e:
                print(f"Error processing record {record}: {e}")
        delete_file(json_file)
    except Exception as e:
        print(f"An error occurred: {e}")


def flatten_enclosure_stats(json_file):
    """
    """
    try:
        with open(json_file, "r") as f:
            data = json.load(f)

        # Step 1: Group stats by enclosure_id
        grouped = defaultdict(dict)

        for entry in data:
            enclosure_id = entry["enclosure_id"]
            stat_name = entry["stat_name"]
            stat_current = entry["stat_current"]

            # Ensure the enclosure_id key is set in grouped
            if "enclosure_id" not in grouped[enclosure_id]:
                grouped[enclosure_id]["enclosure_id"] = enclosure_id

            # Store the stat_current under the stat_name
            grouped[enclosure_id][stat_name] = stat_current

        # Convert from dict-of-dicts to a list of dicts
        result = list(grouped.values())

        # Step 2: Generate SQL INSERT statements
        utc_plus_3 = timezone(timedelta(hours=3))
        current_time = datetime.now(utc_plus_3)

        processed_records = 0
        for record in result:
            try:
                record_timestamp = current_time.isoformat()

                # Build the SQL INSERT statement
                sql_command = (
                    "INSERT INTO ibm_storage_enclosure_stats ("
                    "enclosure_id, power_w, temp_c, temp_f, timestamp"
                    ") VALUES ("
                    f"{handle_empty_value(record['enclosure_id'])}, "
                    f"{handle_empty_value(record.get('power_w', 'NULL'))}, "
                    f"{handle_empty_value(record.get('temp_c', 'NULL'))}, "
                    f"{handle_empty_value(record.get('temp_f', 'NULL'))}, "
                    f"'{record_timestamp}'"
                    ");"
                )

                print(sql_command)
                processed_records += 1
            except Exception as e:
                print(f"Error processing record {record}: {e}")


        delete_file(json_file)
    
    except Exception as e:
        print(f"An error occurred: {e}")

 #######################

######################
def generate_insert_commands_for_fc_port(json_file):
    """
    Generates SQL INSERT statements for IBM Storage FC ports.
    """
    try:
        with open(json_file, "r") as f:
            data = json.load(f)

        utc_plus_3 = timezone(timedelta(hours=3))
        current_time = datetime.now(utc_plus_3)

        processed_records = 0
        for record in data:
            try:
                record_timestamp = current_time.isoformat()

                sql_command = (
                    "INSERT INTO ibm_storage_fcport ("
                    "id, fc_io_port_id, port_id, type, port_speed, node_id, node_name, "
                    "WWPN, nportid, status, attachment, cluster_use, adapter_location, "
                    "adapter_port_id, timestamp"
                    ") VALUES ("
                    f"{handle_empty_value(record['id'])}, "
                    f"{handle_empty_value(record['fc_io_port_id'])}, "
                    f"{handle_empty_value(record['port_id'])}, "
                    f"'{handle_empty_value(record['type'])}', "
                    f"'{handle_empty_value(record['port_speed'])}', "
                    f"{handle_empty_value(record['node_id'])}, "
                    f"'{handle_empty_value(record['node_name'])}', "
                    f"'{handle_empty_value(record['WWPN'])}', "
                    f"'{handle_empty_value(record['nportid'])}', "
                    f"'{handle_empty_value(record['status'])}', "
                    f"'{handle_empty_value(record['attachment'])}', "
                    f"'{handle_empty_value(record['cluster_use'])}', "
                    f"'{handle_empty_value(record['adapter_location'])}', "
                    f"{handle_empty_value(record['adapter_port_id'])}, "
                    f"'{record_timestamp}');"
                )

                print(sql_command.strip())
                processed_records += 1
            except Exception as e:
                print(f"Error processing record {record}: {e}")
        delete_file(json_file)
    except Exception as e:
        print(f"An error occurred: {e}")



def generate_insert_commands_for_vdisk_mapping_host(json_file):
    """
    Generates SQL INSERT statements for IBM Storage SCSI mappings.
    """
    try:
        with open(json_file, "r") as f:
            data = json.load(f)

        utc_plus_3 = timezone(timedelta(hours=3))
        current_time = datetime.now(utc_plus_3)

        processed_records = 0
        for record in data:
            try:
                record_timestamp = current_time.isoformat()

                sql_command = (
                    "INSERT INTO ibm_storage_mdiskgrp_host_mapping ("
                    "vdisk_name, host_name, mdiskgrp_name, timestamp"
                    ") VALUES ("
                    f"'{handle_empty_value(record['vdisk_name'])}', "
                    f"'{handle_empty_value(record['host_name'])}', "
                    f"'{handle_empty_value(record['mdiskgrp_name'])}', "
                    f"'{record_timestamp}');"
                )

                print(sql_command.strip())
                processed_records += 1
            except Exception as e:
                print(f"Error processing record {record}: {e}")
        delete_file(json_file)
    except Exception as e:
        print(f"An error occurred: {e}")






def generate_insert_commands_for_vdisk_mapping(json_file):
    """
    Generates SQL INSERT statements for IBM Storage SCSI mappings.
    """
    try:
        with open(json_file, "r") as f:
            data = json.load(f)

        utc_plus_3 = timezone(timedelta(hours=3))
        current_time = datetime.now(utc_plus_3)

        processed_records = 0
        for record in data:
            try:
                record_timestamp = current_time.isoformat()

                sql_command = (
                    "INSERT INTO ibm_storage_vdisk_mapping ("
                    "id, name, SCSI_id, vdisk_id, vdisk_name, vdisk_UID, IO_group_id, "
                    "IO_group_name, mapping_type, host_cluster_id, host_cluster_name, "
                    "protocol, timestamp"
                    ") VALUES ("
                    f"{handle_empty_value(record['id'])}, "
                    f"'{handle_empty_value(record['name'])}', "
                    f"{handle_empty_value(record['SCSI_id'])}, "
                    f"{handle_empty_value(record['vdisk_id'])}, "
                    f"'{handle_empty_value(record['vdisk_name'])}', "
                    f"'{handle_empty_value(record['vdisk_UID'])}', "
                    f"{handle_empty_value(record['IO_group_id'])}, "
                    f"'{handle_empty_value(record['IO_group_name'])}', "
                    f"'{handle_empty_value(record['mapping_type'])}', "
                    f"{handle_empty_value(record['host_cluster_id'])}, "
                    f"'{handle_empty_value(record['host_cluster_name'])}', "
                    f"'{handle_empty_value(record['protocol'])}', "
                    f"'{record_timestamp}');"
                )

                print(sql_command.strip())
                processed_records += 1
            except Exception as e:
                print(f"Error processing record {record}: {e}")
        delete_file(json_file)
    except Exception as e:
        print(f"An error occurred: {e}")
###################### 
def generate_insert_commands_for_lsmdisk(json_file):
    """
    This function handles 'lsmdisk_response.json' data and generates SQL INSERT commands 
    for each lsmdisk record. It follows a structure similar to the lsmdiskgrp function.
    """
    try:
        with open(json_file, "r") as f:
            data = json.load(f)

        # Set the timezone offset (UTC+3)
        utc_plus_3 = timezone(timedelta(hours=3))
        
        processed_records = 0
        # Iterate over the list of lsmdisk records
        for record in data:
            try:
                # Compute the timestamp inside the loop (each record gets a timestamp)
                record_timestamp = datetime.now(utc_plus_3).isoformat()

                # Build the SQL INSERT statement
                sql_command = (
                    "INSERT INTO ibm_storage_mdisk ("
                    "id, name, status, mode, mdisk_grp_id, mdisk_grp_name, capacity, \"ctrl_LUN_#\", "
                    "controller_name, UID, tier, encrypt, site_id, site_name, distributed, dedupe, "
                    "over_provisioned, supports_unmap, timestamp"
                    ") VALUES ("
                    f"'{handle_empty_value(record.get('id', ''))}', "
                    f"'{handle_empty_value(record.get('name', ''))}', "
                    f"'{handle_empty_value(record.get('status', ''))}', "
                    f"'{handle_empty_value(record.get('mode', ''))}', "
                    f"'{handle_empty_value(record.get('mdisk_grp_id', ''))}', "
                    f"'{handle_empty_value(record.get('mdisk_grp_name', ''))}', "
                    f"'{handle_empty_value(record.get('capacity', ''))}', "
                    f"'{handle_empty_value(record.get('ctrl_LUN_#', ''))}', "
                    f"'{handle_empty_value(record.get('controller_name', ''))}', "
                    f"'{handle_empty_value(record.get('UID', ''))}', "
                    f"'{handle_empty_value(record.get('tier', ''))}', "
                    f"'{handle_empty_value(record.get('encrypt', ''))}', "
                    f"'{handle_empty_value(record.get('site_id', ''))}', "
                    f"'{handle_empty_value(record.get('site_name', ''))}', "
                    f"'{handle_empty_value(record.get('distributed', ''))}', "
                    f"'{handle_empty_value(record.get('dedupe', ''))}', "
                    f"'{handle_empty_value(record.get('over_provisioned', ''))}', "
                    f"'{handle_empty_value(record.get('supports_unmap', ''))}', "
                    f"'{record_timestamp}');"
                )

                print(sql_command.strip())
                processed_records += 1

            except Exception as e:
                print(f"Error processing record {record.get('id', 'Unknown')}: {e}")

        delete_file(json_file)
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: hmc_storage_parse.py <input_json_file>")
        sys.exit(1)

    input_file = sys.argv[1]

    if input_file == "lsmdisk_by_id_responses.json":
        generate_insert_commands_for_lsmdiskgrp_by_id(input_file)
    elif input_file == "lshost_by_id_responses.json":
        generate_insert_commands_for_lshost_by_id(input_file)
    elif input_file == "lshost_response.json":
        generate_filtered_insert_commands(input_file)
    elif input_file == "lsmdiskgrp_response.json":
        generate_insert_commands_for_lsmdiskgrp(input_file)
    elif input_file == "lsvdisk_response.json":
        generate_insert_commands_for_lsvdisk(input_file)
    elif input_file == "lssystem_response.json":
        generate_insert_commands_for_lssystem(input_file)
    elif input_file == "lsnodestats_response.json":
        flatten_node_stats(input_file)
    elif input_file == "lsenclosurestats_response.json":
        flatten_enclosure_stats(input_file)
    ################
    elif input_file == "lssystemstats_response.json":
        generate_insert_commands_for_lssystem_stats(input_file)

    elif input_file == "merge_vdisk_mappings_response.json":
        generate_insert_commands_for_vdisk_mapping_host(input_file)
    
    elif input_file == "lshostvdiskmap_response.json":
        generate_insert_commands_for_vdisk_mapping(input_file)
    elif input_file == "lsmdisk_response.json":
        generate_insert_commands_for_lsmdisk(input_file)
    elif input_file == "lsportfc_response.json":
        generate_insert_commands_for_fc_port(input_file)
    else:
        print(f"Unsupported input file: {input_file}")
        sys.exit(1)
