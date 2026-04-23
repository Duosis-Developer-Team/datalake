### Collectors – Amaç Kartları

- **VMware**: vCenter’dan DC/Cluster/Host/VM envanter ve metrikleri toplar. Kapasite planlama ve performans analizi için temel veri.
- **Nutanix**: Prism API ile Cluster/Host/VM ve Data Protection (snapshot) verileri. Kaynak kullanımı ve koruma görünürlüğü.
- **IBM HMC**: Server/VIOS/LPAR envanter ve kullanım; ayrıca enerji metrikleri. Kurumsal Power altyapısı görünürlüğü.
- **IBM Storage (Storwize/Spectrum)**: Cihaz kullanımı ve iostats çıktılarının işlenmesi. Havuz/volume kapasiteleri ve trend.
- **Brocade SAN**: SNMP ile port durum/metrikleri. Bağlantı sağlığı ve performans izleme.
- **Network (Fortinet, Sophos)**: Zabbix API üzerinden cihaz metrikleri. Güvenlik katmanı kapasite ve durum görünürlüğü.
- **NetBackup**: Job durumları ve disk pool metrikleri. Yedekleme başarım takibi ve kapasite.
- **S3 ICOS**: Vault inventory/metrics ve pool metrics. Nesne depolama kapasite/kullanım izleme.
- **Envanter (Loki/NetBox)**: Lokasyon, rack, cihaz, VM envanteri. Panellerin filtreleme ve eşlemesi için referans.
- **ServiceCore ITSM**: ServiceCore Operations Support API ile incident, service request ve kullanıcı kataloğu (`User/GetAllUsers`, isteğe `--skip-users`) discovery (UPSERT). Stdout **sparse JSON** (`data_type` başına yalnızca ilgili alanlar; çapraz-null yok). NiFi kolon/tip sözleşmesi için tek Avro kaydı (`ServiceCoreDiscovery`); SR filtresi `RequestDate`, incident `LastUpdatedDate`. ITSM analitik ve SLA; tenant `org_user_support_account_*` ve kullanıcı join.

- **CRM Dynamics 365**: Microsoft Dynamics 365 OData v4 Web API ile accounts (müşteri master), ürün kataloğu (products/pricelevels/productpricelevels), tam satış hunisi (opportunity→quote→salesorder→invoice + line items) ve contracts discovery. ServiceCore pattern: tek script `crm-dynamics-discovery.py`, 14 `data_type`, tek Avro schema `CrmDynamicsDiscovery`, tek NiFi flow. Master data her çalıştırmada full snapshot; sales/contracts incremental (`modifiedon` lookback). `discovery_crm_customer_alias` tablosu CRM GUID'lerini platform canonical key ve NetBox `custom_fields_musteri` ile eşleştirir. GUI: customer-api `/sales/*` (YTD revenue, pipeline, MRR, line items, efficiency) ve datacenter-api `/sales-potential` (boş kapasite × katalog fiyatı).
