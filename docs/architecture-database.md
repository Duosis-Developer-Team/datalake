### Architecture – Database

Bu doküman, Datalake veritabanındaki ana alanları ve saklama yaklaşımlarını müşteri odaklı olarak özetler.

#### Alanlar (Domains)

- Sanallaştırma: VMware, Nutanix (envanter + metrik)
- IBM HMC: Server/VIOS/LPAR + enerji
- Storage: IBM Storwize/Spectrum kullanımı; Brocade SAN port metrikleri
- Network: Fortinet, Sophos (Zabbix üzerinden)
- Yedekleme: NetBackup job’ları ve disk-pool metrikleri
- S3 ICOS: Vault inventory/metrics ve pool metrics
- Envanter: Loki/NetBox konum, rack, cihaz, VM

#### Model Prensipleri

- Envanter tabloları: Daha az değişen kimlik/özellik bilgileri
- Metrik tabloları: Zaman serisi; `collection_timestamp` ile indekslenir
- İsimlendirme: `<kaynak>_<alan>_<inventory|metrics>`

#### Saklama ve İndeksleme

- Zaman serisi: `collection_timestamp DESC` indeksleri
- Saklama: Varsayılan 90 gün (müşteri onayıyla değiştirilebilir)
- Arşiv: Gerektiğinde dış diske JSON/CSV export (opsiyonel)

#### Örnekler

- S3 ICOS tabloları (özet):
  - `s3icos_vault_inventory(vault_id, vault_name, quota..., collection_timestamp)`
  - `s3icos_vault_metrics(vault_id, used_*_bytes, object_count_estimate, collection_timestamp)`
  - `s3icos_pool_metrics(vault_id, pool_id, total_bytes, used_bytes, collection_timestamp)`

#### Erişim ve Yetki

- Uygulama yazma kullanıcısı (INSERT)
- Raporlama okuyucu (SELECT)
- Şema değişiklikleri değişiklik kaydı ve onay gerektirir
