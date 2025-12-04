-- VMware Cluster
ALTER TABLE cluster_metrics 
add CONSTRAINT unique_cluster_metric_entry UNIQUE (datacenter, cluster, collection_time);

-- VMware Datacenter
ALTER TABLE datacenter_metrics 
add constraint unique_dc_metric_entry UNIQUE (datacenter, collection_time);

-- VMware Host
ALTER TABLE vmhost_metrics 
add CONSTRAINT unique_vmhost_metric_entry UNIQUE (datacenter, cluster, vmhost, collection_time);

-- VMware VM
ALTER TABLE vm_metrics 
add CONSTRAINT unique_vm_metric_entry UNIQUE (datacenter, cluster, vmhost, uuid, collection_time);