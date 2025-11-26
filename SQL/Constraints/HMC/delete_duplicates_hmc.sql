-- ibm_lpar_general tablosundaki yinelenenleri sil
DELETE FROM ibm_lpar_general a
WHERE a.ctid <> (
    SELECT min(b.ctid)
    FROM ibm_lpar_general b
    WHERE a.lparname = b.lparname
      AND a."time" = b."time" -- Çift tırnaklı sütun adı
);

-- ibm_lpar_net_virtual tablosundaki yinelenenleri sil
DELETE FROM ibm_lpar_net_virtual a
WHERE a.ctid <> (
    SELECT min(b.ctid)
    FROM ibm_lpar_net_virtual b
    WHERE a.lparname = b.lparname
      AND a.vlanid = b.vlanid
      AND a."time" = b."time" -- Çift tırnaklı sütun adı
);

-- ibm_lpar_storage_vfc tablosundaki yinelenenleri sil
DELETE FROM ibm_lpar_storage_vfc a
WHERE a.ctid <> (
    SELECT min(b.ctid)
    FROM ibm_lpar_storage_vfc b
    WHERE a.lparname = b.lparname
      AND a.wwpn = b.wwpn
      AND a.wwpn2 = b.wwpn2
      AND a."time" = b."time" -- Çift tırnaklı sütun adı
);

-- ibm_server_general tablosundaki yinelenenleri sil
DELETE FROM ibm_server_general a
WHERE a.ctid <> (
    SELECT min(b.ctid)
    FROM ibm_server_general b
    WHERE a.servername = b.servername
      AND a."time" = b."time" -- Çift tırnaklı sütun adı
);

-- ibm_server_power tablosundaki yinelenenleri sil
DELETE FROM ibm_server_power a
WHERE a.ctid <> (
    SELECT min(b.ctid)
    FROM ibm_server_power b
    WHERE a.server_name = b.server_name
      AND a."timestamp" = b."timestamp" -- Çift tırnaklı sütun adı
);

-- ibm_vios_general tablosundaki yinelenenleri sil
DELETE FROM ibm_vios_general a
WHERE a.ctid <> (
    SELECT min(b.ctid)
    FROM ibm_vios_general b
    WHERE a.viosname = b.viosname
      AND a."time" = b."time" -- Çift tırnaklı sütun adı
);

-- ibm_vios_network_generic tablosundaki yinelenenleri sil
DELETE FROM ibm_vios_network_generic a
WHERE a.ctid <> (
    SELECT min(b.ctid)
    FROM ibm_vios_network_generic b
    WHERE a.viosname = b.viosname
      AND a.id = b.id
      AND a."time" = b."time" -- Çift tırnaklı sütun adı
);

-- ibm_vios_network_virtual tablosundaki yinelenenleri sil
DELETE FROM ibm_vios_network_virtual a
WHERE a.ctid <> (
    SELECT min(b.ctid)
    FROM ibm_vios_network_virtual b
    WHERE a.viosname = b.viosname
      AND a.vswitchid = b.vswitchid
      AND a.vlanid = b.vlanid
      AND a."time" = b."time" -- Çift tırnaklı sütun adı
);

-- ibm_vios_storage_fc tablosundaki yinelenenleri sil
DELETE FROM ibm_vios_storage_fc a
WHERE a.ctid <> (
    SELECT min(b.ctid)
    FROM ibm_vios_storage_fc b
    WHERE a.viosname = b.viosname
      AND a.id = b.id
      AND a.wwpn = b.wwpn
      AND a."time" = b."time" -- Çift tırnaklı sütun adı
);

-- ibm_vios_storage_physical tablosundaki yinelenenleri sil
DELETE FROM ibm_vios_storage_physical a
WHERE a.ctid <> (
    SELECT min(b.ctid)
    FROM ibm_vios_storage_physical b
    WHERE a.viosname = b.viosname
      AND a.id = b.id
      AND a."time" = b."time" -- Çift tırnaklı sütun adı
);

-- ibm_vios_storage_virtual tablosundaki yinelenenleri sil
DELETE FROM ibm_vios_storage_virtual a
WHERE a.ctid <> (
    SELECT min(b.ctid)
    FROM ibm_vios_storage_virtual b
    WHERE a.viosname = b.viosname
      AND a.id = b.id
      AND a."time" = b."time" -- Çift tırnaklı sütun adı
);