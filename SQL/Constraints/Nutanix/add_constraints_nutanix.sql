-- Nutanix Cluster
ALTER TABLE nutanix_cluster_metrics 
add CONSTRAINT unique_nutanix_cluster_metric_entry UNIQUE (cluster_uuid, collection_time);

-- Nutanix Host
ALTER TABLE nutanix_host_metrics 
add CONSTRAINT unique_nutanix_host_metric_entry UNIQUE (host_uuid, collectiontime);

-- Nutanix VM
ALTER TABLE nutanix_vm_metrics 
add CONSTRAINT unique_nutanix_vm_metric_entry UNIQUE (vm_uuid, collection_time);