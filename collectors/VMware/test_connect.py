#!/usr/bin/env python3
"""Quick test: connect to vCenter, RetrieveContent, count hosts. Prints progress."""
import sys
import ssl
from datetime import datetime
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim

def main():
    host = "10.34.1.230"
    user = "zabbix@blt.vc"
    pwd = "2u4Mzf7RJC"
    port = 443
    print("Connecting...", flush=True)
    t0 = datetime.now()
    si = SmartConnect(host=host, user=user, pwd=pwd, port=port, sslContext=ssl._create_unverified_context())
    print(f"  SmartConnect OK in {(datetime.now() - t0).total_seconds():.1f}s", flush=True)
    t1 = datetime.now()
    content = si.RetrieveContent()
    print(f"  RetrieveContent OK in {(datetime.now() - t1).total_seconds():.1f}s", flush=True)
    n_dc = len(content.rootFolder.childEntity)
    n_hosts = 0
    for dc in content.rootFolder.childEntity:
        if not hasattr(dc, 'hostFolder'):
            continue
        for entity in dc.hostFolder.childEntity:
            if isinstance(entity, vim.ClusterComputeResource):
                n_hosts += len(entity.host)
    print(f"  Datacenters: {n_dc}, Hosts: {n_hosts}", flush=True)
    Disconnect(si)
    print("Done.", flush=True)

if __name__ == "__main__":
    main()
    sys.exit(0)
