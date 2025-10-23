## Datalake Projesi

Kısa amaç: Çoklu DC’lerdeki altyapı verilerini (sanallaştırma, storage, network, yedekleme, envanter) tek merkezde toplamak, kayıpsız işlemek ve görselleştirmek.

- Desteklenen kaynaklar: VMware, Nutanix, IBM HMC, IBM Storage/Storwize, Brocade SAN, Fortinet/Sophos (Zabbix üzerinden), NetBackup, IBM S3 ICOS.
- Çalışma modeli: Remote NiFi + Queue (PostgreSQL) üzerinden DC13’teki Main NiFi ve Datalake DB’ye akış. test


### Topoloji özeti

- DC13: Main NiFi Cluster + Datalake DB
- Uzak DC’ler: Remote NiFi Cluster + Queue (PostgreSQL)
- Akış: Collector Script → Remote NiFi → Queue → Main NiFi → DB → Grafana

### Çıktılar

- Grafana panelleri (DC/Cluster/Host/VM, Storage, SAN, Network, Backup, Envanter)
- Veri sözlüğü ve tablo referansları (docs/architecture-database.md)