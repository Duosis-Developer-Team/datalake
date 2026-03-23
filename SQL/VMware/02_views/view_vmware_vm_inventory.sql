-- BÜYÜK GRUP
ALTER TABLE ibm_vios_network_generic RENAME TO ibm_vios_network_generic_old;
CREATE TABLE ibm_vios_network_generic (LIKE ibm_vios_network_generic_old INCLUDING ALL);
SELECT create_hypertable('ibm_vios_network_generic', 'time', chunk_time_interval => INTERVAL '7 days');

ALTER TABLE ibm_vios_network_virtual RENAME TO ibm_vios_network_virtual_old;
CREATE TABLE ibm_vios_network_virtual (LIKE ibm_vios_network_virtual_old INCLUDING ALL);
SELECT create_hypertable('ibm_vios_network_virtual', 'time', chunk_time_interval => INTERVAL '7 days');

ALTER TABLE ibm_lpar_net_virtual RENAME TO ibm_lpar_net_virtual_old;
CREATE TABLE ibm_lpar_net_virtual (LIKE ibm_lpar_net_virtual_old INCLUDING ALL);
SELECT create_hypertable('ibm_lpar_net_virtual', 'time', chunk_time_interval => INTERVAL '7 days');

ALTER TABLE ibm_lpar_general RENAME TO ibm_lpar_general_old;
CREATE TABLE ibm_lpar_general (LIKE ibm_lpar_general_old INCLUDING ALL);
SELECT create_hypertable('ibm_lpar_general', 'time', chunk_time_interval => INTERVAL '1 day');

ALTER TABLE ibm_lpar_storage_vfc RENAME TO ibm_lpar_storage_vfc_old;
CREATE TABLE ibm_lpar_storage_vfc (LIKE ibm_lpar_storage_vfc_old INCLUDING ALL);
SELECT create_hypertable('ibm_lpar_storage_vfc', 'time', chunk_time_interval => INTERVAL '1 day');