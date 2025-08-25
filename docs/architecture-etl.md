### Architecture – ETL (NiFi Patterns)

NiFi akışları müşteri ortamında çalışan Python kolektörlerini tetikler, JSON kayıtlarını böler ve PostgreSQL’e yazar.

#### Standart örüntü

1) GenerateFlowFile (schedule)
2) ExecuteStreamCommand (collector.py)
3) SplitJson ($.*)
4) EvaluateJsonPath (record.type | data_type)
5) RouteOnAttribute (to_inventory | to_metrics | to_pool_metrics ...)
6) PutDatabaseRecord (JsonTreeReader + DBCPConnectionPool)

#### Parametreler

- ExecuteStreamCommand argümanları: kaynaklara özel `--host/--username/--password` veya config yolu
- JsonTreeReader şeması: özel alanlar için union tipler ve nullable tanımlar
- DBCP: Müşteri PostgreSQL bağlantı havuzu; SSL/Kerberos gereksinimi yoksa kapalı

#### Hata yönetimi

- Split/Route çıkışları özel `log/error` kuyruğuna
- PutDatabaseRecord: “Fail” çıkışı ayrık; backpressure ve retry politikaları
- Queue Postgres: Uzak DC’de kalıcı tampon; Main NiFi erişilemediğinde süreli saklama

#### Güvenlik

- Kimlik bilgileri NiFi Parameter Context üzerinde; repo’da saklanmaz
- Script logları JSON formatında; kişisel veri içermez

