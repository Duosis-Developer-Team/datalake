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
- **ServiceCore ITSM**: ServiceCore Operations Support API ile incident ve service request discovery (UPSERT). Yapılandırma yolu `python ... --config <path>` ile verilir; NiFi için tek birleşik Avro kaydı (`ServiceCoreDiscovery`). ITSM analitik ve SLA görünürlüğü; ham HTML yerine text-format alanları.

