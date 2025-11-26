-- cluster_metrics tablosundaki yinelenenleri sil
DELETE FROM cluster_metrics a
WHERE a.ctid <> (
    SELECT min(b.ctid)
    FROM cluster_metrics b
    WHERE a.datacenter = b.datacenter
      AND a.cluster = b.cluster
      AND a.collection_time = b.collection_time
);

-- datacenter_metrics tablosundaki yinelenenleri sil
DELETE FROM datacenter_metrics a
WHERE a.ctid <> (
    SELECT min(b.ctid)
    FROM datacenter_metrics b
    WHERE a.datacenter = b.datacenter
      AND a.collection_time = b.collection_time
);

-- vmhost_metrics tablosundaki yinelenenleri sil
DELETE FROM vmhost_metrics a
WHERE a.ctid <> (
    SELECT min(b.ctid)
    FROM vmhost_metrics b
    WHERE a.datacenter = b.datacenter
      AND a.cluster = b.cluster
      AND a.vmhost = b.vmhost
      AND a.collection_time = b.collection_time
);

-- vm_metrics tablosundaki yinelenenleri sil
DELETE FROM vm_metrics a
WHERE a.ctid <> (
    SELECT min(b.ctid)
    FROM vm_metrics b
    WHERE a.datacenter = b.datacenter
      AND a.cluster = b.cluster
      AND a.vmhost = b.vmhost
      AND a.uuid = b.uuid
      AND a.collection_time = b.collection_time
);