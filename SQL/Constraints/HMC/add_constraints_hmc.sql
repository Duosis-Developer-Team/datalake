-- IBM LPAR General
ALTER TABLE ibm_lpar_general 
add CONSTRAINT unique_ibm_lpar_metric_entry UNIQUE (lparname, "time");

-- IBM LPAR Net Virtual
ALTER TABLE ibm_lpar_net_virtual 
add CONSTRAINT unique_ibm_lpar_net_virtual_metric_entry UNIQUE (lparname, vlanid, "time");

-- IBM LPAR Storage VFC
ALTER TABLE ibm_lpar_storage_vfc 
add CONSTRAINT unique_ibm_lpar_storag_vfc_metric_entry UNIQUE (lparname, wwpn, wwpn2, "time");

-- IBM Server General
ALTER TABLE ibm_server_general 
add CONSTRAINT unique_ibm_server_metric_entry UNIQUE (servername, "time");

-- IBM Server Power
ALTER TABLE ibm_server_power 
add CONSTRAINT unique_ibm_server_power_metric_entry UNIQUE (server_name, "timestamp");

-- IBM VIOS General
ALTER TABLE ibm_vios_general 
add CONSTRAINT unique_ibm_vios_general_metric_entry UNIQUE (viosname, "time");

-- IBM VIOS Network Generic
ALTER TABLE ibm_vios_network_generic 
add CONSTRAINT unique_ibm_vios_network_generic_metric_entry UNIQUE (viosname, id, "time");

-- IBM VIOS Network Virtual
ALTER TABLE ibm_vios_network_virtual 
add CONSTRAINT unique_ibm_vios_network_virtual_metric_entry UNIQUE (viosname, vswitchid, vlanid, "time");

-- IBM VIOS Storage FC
ALTER TABLE ibm_vios_storage_fc 
add CONSTRAINT unique_ibm_vioss_storage_fc_metric_entry UNIQUE (viosname, id, wwpn, "time");

-- IBM VIOS Storage Physical
ALTER TABLE ibm_vios_storage_physical 
add CONSTRAINT unique_ibm_vios_storage_physical_metric_entry UNIQUE (viosname, id, "time");

-- IBM VIOS Storage Virtual
ALTER TABLE ibm_vios_storage_virtual 
add CONSTRAINT unique_ibm_vios_storage_virtual_metric_entry UNIQUE (viosname, id, "time");