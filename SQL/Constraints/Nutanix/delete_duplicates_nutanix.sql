-- nutanix_cluster_metrics tablosundaki yinelenenleri sil
DELETE FROM nutanix_cluster_metrics a
WHERE a.ctid <> (
    SELECT min(b.ctid)
    FROM nutanix_cluster_metrics b
    WHERE a.cluster_uuid = b.cluster_uuid
      AND a.collection_time = b.collection_time
);

-- nutanix_host_metrics tablosundaki yinelenenleri sil
DELETE FROM nutanix_host_metrics a
WHERE a.ctid <> (
    SELECT min(b.ctid)
    FROM nutanix_host_metrics b
    WHERE a.host_uuid = b.host_uuid
      AND a.collectiontime = b.collectiontime -- Sütun adı 'collectiontime' (küçük harf)
);

-- nutanix_vm_metrics tablosundaki yinelenenleri sil
DELETE FROM nutanix_vm_metrics a
WHERE a.ctid <> (
    SELECT min(b.ctid)
    FROM nutanix_vm_metrics b
    WHERE a.vm_uuid = b.vm_uuid
      AND a.collection_time = b.collection_time
);