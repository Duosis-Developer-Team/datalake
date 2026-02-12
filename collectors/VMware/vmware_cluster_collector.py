#!/usr/bin/env python3
"""
VMware Cluster Collector - Raw Data Extraction (Zero Transformation)

This script extracts raw cluster configuration from VMware vCenter API
with NO calculations. It produces:
- vmware_cluster_config: Cluster configuration and summary

Output: Single JSON array to stdout
"""

import json
import ssl
import argparse
import sys
from datetime import datetime, timezone
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='VMware Cluster Collector - Raw Data Extraction'
    )
    parser.add_argument('--vmware-ip', required=True,
                        help='vCenter hostname or IP')
    parser.add_argument('--vmware-port', type=int, default=443,
                        help='vCenter port (default: 443)')
    parser.add_argument('--vmware-username', required=True,
                        help='Username for vCenter authentication')
    parser.add_argument('--vmware-password', required=True,
                        help='Password for vCenter authentication')
    return parser.parse_args()


def safe_get_attr(obj, attr_path, default=None):
    """Safely get nested attribute value."""
    try:
        parts = attr_path.split('.')
        value = obj
        for part in parts:
            value = getattr(value, part, None)
            if value is None:
                return default
        return value
    except (AttributeError, TypeError):
        return default


def extract_cluster_config(cluster, vcenter_uuid, collection_timestamp, datacenter_moid):
    """
    Extract cluster configuration AS-IS from VMware API.
    Source: cluster.configuration, cluster.summary
    """
    summary = cluster.summary
    config = cluster.configuration
    
    return {
        "data_type": "vmware_cluster_config",
        "collection_timestamp": collection_timestamp,
        "vcenter_uuid": vcenter_uuid,
        "datacenter_moid": datacenter_moid,
        "cluster_moid": cluster._moId,
        "name": cluster.name,
        
        # cluster.summary fields (AS-IS)
        "summary_num_hosts": safe_get_attr(summary, 'numHosts'),
        "summary_num_cpu_cores": safe_get_attr(summary, 'numCpuCores'),
        "summary_num_cpu_threads": safe_get_attr(summary, 'numCpuThreads'),
        "summary_effective_cpu": safe_get_attr(summary, 'effectiveCpu'),
        "summary_total_cpu": safe_get_attr(summary, 'totalCpu'),
        "summary_num_effective_hosts": safe_get_attr(summary, 'numEffectiveHosts'),
        "summary_total_memory": safe_get_attr(summary, 'totalMemory'),
        "summary_effective_memory": safe_get_attr(summary, 'effectiveMemory'),
        "summary_overall_status": safe_get_attr(summary, 'overallStatus'),
        
        # cluster.configuration.dasConfig (HA)
        "config_das_enabled": safe_get_attr(config, 'dasConfig.enabled'),
        "config_das_vm_monitoring": safe_get_attr(config, 'dasConfig.vmMonitoring'),
        "config_das_host_monitoring": safe_get_attr(config, 'dasConfig.hostMonitoring'),
        
        # cluster.configuration.drsConfig (DRS)
        "config_drs_enabled": safe_get_attr(config, 'drsConfig.enabled'),
        "config_drs_default_vm_behavior": safe_get_attr(config, 'drsConfig.defaultVmBehavior'),
        "config_drs_vmotion_rate": safe_get_attr(config, 'drsConfig.vmotionRate'),
        
        # cluster.configuration.dpmConfigInfo (DPM)
        "config_dpm_enabled": safe_get_attr(config, 'dpmConfigInfo.enabled'),
    }


def main():
    """Main execution."""
    args = parse_args()
    
    collection_timestamp = datetime.now(timezone.utc).isoformat()
    all_records = []
    si = None
    
    try:
        # Connect to vCenter
        context = ssl._create_unverified_context()
        si = SmartConnect(
            host=args.vmware_ip,
            user=args.vmware_username,
            pwd=args.vmware_password,
            port=args.vmware_port,
            sslContext=context
        )
        
        content = si.RetrieveContent()
        vcenter_uuid = content.about.instanceUuid
        
        # Iterate through datacenters
        for datacenter in content.rootFolder.childEntity:
            if not hasattr(datacenter, 'hostFolder'):
                continue
            
            datacenter_moid = datacenter._moId
            
            for entity in datacenter.hostFolder.childEntity:
                if not isinstance(entity, vim.ClusterComputeResource):
                    continue
                
                # Extract cluster config
                all_records.append(extract_cluster_config(entity, vcenter_uuid, collection_timestamp, datacenter_moid))
        
        # Output single JSON array
        print(json.dumps(all_records, default=str, indent=2))
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    finally:
        if si:
            Disconnect(si)


if __name__ == '__main__':
    main()
