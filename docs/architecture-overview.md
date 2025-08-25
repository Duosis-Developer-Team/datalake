### Architecture Overview (Müşteri Ortamı)

Amaç: Tüm müşteri DC’lerinden altyapı verilerini kayıpsız toplamak ve merkezde sunmak.

- **Merkez (DC13)**: Main NiFi Cluster + Datalake DB (PostgreSQL) + Grafana
- **Uzak DC’ler (DC11, DC12, DC14, DC15, DC16, DC17, ICT11, AZ11)**:
  - Remote NiFi Cluster
  - Queue Postgres (geçici tampon; kesinti/peak durumlarında veri kaybını azaltır)

#### Veri Akışı (Yüksek Seviye)

Collector Script → Remote NiFi → Queue (PostgreSQL) → Main NiFi (DC13) → Datalake DB → Grafana

#### Bileşenler

- **Collectors**: VMware (pyVmomi), Nutanix (Prism), IBM HMC, IBM Storage (API/SSH), Brocade SAN (SNMP), Zabbix (API), NetBackup (API), S3 ICOS (REST).
- **NiFi**: ExecuteStreamCommand ile script tetikleme, JSON bölme/yönlendirme, DB yazımı.
- **Queue DB**: Uzak lokasyonda geçici depolama (retry/backpressure).
- **Datalake DB**: Özet model: envanter + metrik odaklı alanlar.

#### HA ve Dayanıklılık

- Remote/Main NiFi cluster kurulumları
- Queue Postgres ile geçici saklama
- VIP üzerinden erişim ve bakım notları

