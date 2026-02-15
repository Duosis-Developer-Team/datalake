# Manuel Adımlar: vcenter_hostname ve location (DCxx) Eklemesi

Bu doküman, view ve materialized view güncellemelerinden **sonra** veritabanında yapmanız gereken manuel işlemleri listeler.

**ETL değişmez:** `vcenter_name` (vCenter görünen ad) ve `datacenter_name` (VMware datacenter adı) aynı anlamda kalmaya devam eder. Sadece **yeni** kolonlar eklendi: **vcenter_hostname** (cihaz DNS) ve **location** (DCxx lokasyon).

---

## 1. View'ları veritabanına uygulama

Güncellenen view'ları sırayla çalıştırın:

```bash
cd /path/to/datalake

# 02_views – hepsi sırayla
psql -U <user> -d <database> -f SQL/VMware/02_views/view_vmware_vm_inventory.sql
psql -U <user> -d <database> -f SQL/VMware/02_views/view_vmware_host_inventory.sql
psql -U <user> -d <database> -f SQL/VMware/02_views/view_vmware_host_health.sql
psql -U <user> -d <database> -f SQL/VMware/02_views/view_vmware_host_capacity.sql
psql -U <user> -d <database> -f SQL/VMware/02_views/view_vmware_host_storage_detail.sql
psql -U <user> -d <database> -f SQL/VMware/02_views/view_vmware_host_power.sql
psql -U <user> -d <database> -f SQL/VMware/02_views/view_vmware_cluster_inventory.sql
psql -U <user> -d <database> -f SQL/VMware/02_views/view_vmware_cluster_metrics.sql
```

Veya tek seferde:

```bash
for f in SQL/VMware/02_views/view_vmware_*.sql; do
  psql -U <user> -d <database> -f "$f"
done
```

---

## 2. Materialized view'ları yeniden oluşturma

MV'ların tanımı değiştiği için (yeni kolonlar: vcenter_hostname, location) **DROP + CREATE** yapmanız gerekir. `REFRESH MATERIALIZED VIEW` sadece veriyi günceller, kolon eklemez.

### Seçenek A: DROP sonra CREATE (kısa kesinti)

```sql
-- MV'ları kaldır
DROP MATERIALIZED VIEW IF EXISTS mv_vmware_vm_metrics_latest;
DROP MATERIALIZED VIEW IF EXISTS mv_vmware_host_metrics_latest;
DROP MATERIALIZED VIEW IF EXISTS mv_vmware_cluster_latest;
DROP MATERIALIZED VIEW IF EXISTS mv_vmware_cluster_metrics_latest;
DROP MATERIALIZED VIEW IF EXISTS mv_vmware_datacenter_latest;
DROP MATERIALIZED VIEW IF EXISTS mv_vmware_vm_latest;
DROP MATERIALIZED VIEW IF EXISTS mv_vmware_host_latest;
```

Ardından DDL dosyalarını çalıştırın:

```bash
for f in SQL/VMware/03_materialized_views/mv_vmware_*.sql; do
  psql -U <user> -d <database> -f "$f"
done
```

### Seçenek B: Sadece kolon tanımı değişen MV'ları DROP + CREATE

`mv_vmware_vm_latest` ve `mv_vmware_host_latest` base view'dan `SELECT *` kullandığı için, view'ları deploy ettikten sonra bu ikisi için **sadece REFRESH** yeterli (yeni kolonlar view'dan gelir).  
Kolon listesi **içinde** değişen MV'lar:

- `mv_vmware_cluster_latest`
- `mv_vmware_cluster_metrics_latest`
- `mv_vmware_datacenter_latest`
- `mv_vmware_vm_metrics_latest`
- `mv_vmware_host_metrics_latest`

Bunlar için önce DROP, sonra ilgili `.sql` dosyası ile CREATE yapın.

---

## 3. Refresh fonksiyonunu ve pg_cron'u kontrol

`refresh_vmware_materialized_views()` tüm MV'ları listeliyorsa ekstra bir şey yapmanız gerekmez.  
MV'ları DROP/CREATE ettikten sonra bir kez manuel refresh yapın:

```sql
SELECT * FROM refresh_vmware_materialized_views();
```

---

## 4. Discovery tablolarında vcenter_hostname

**vcenter_hostname** (yeni kolon) = cihaz DNS. Kaynak: `discovery_vmware_inventory_vcenter.vcenter_hostname`.  
Bu kolon boşsa view'larda `vcenter_hostname` NULL gelir.

Kontrol:

```sql
SELECT vcenter_uuid, name, vcenter_hostname 
FROM discovery_vmware_inventory_vcenter;
```

Eksikse discovery script'inin vCenter FQDN'ini `vcenter_hostname` olarak yazdığından emin olun.

---

## 5. Cluster isimlendirme kuralı (DCxx → location)

**location** (yeni kolon) = DCxx lokasyon. Şu an `SPLIT_PART(cluster_name, '-', 1)` ile türetiliyor.  
Örnek: `DC01-Production` → `DC01`, `DC02-Dev` → `DC02`.

Cluster adında **`-` yoksa** (örn. sadece `Production`) tüm string location olur.  
Farklı bir ayraç veya kural kullanıyorsanız view ve MV'lardaki `SPLIT_PART(cl.name, '-', 1)` ifadesini buna göre değiştirmeniz gerekir.

---

## 6. Kolon özeti (ETL uyumu)

| Kolon | Anlam | Değişti mi? |
|-------|--------|-------------|
| vcenter_name | vCenter görünen ad (vc.name) | Hayır – aynı |
| datacenter_name | VMware datacenter adı (dc.name) | Hayır – aynı |
| vcenter_hostname | Cihaz DNS (vc.vcenter_hostname) | **Yeni** |
| location | DCxx lokasyon (SPLIT_PART(cl.name,'-',1)) | **Yeni** |

Mevcut ETL rapor/dashboard'lar **vcenter_name** ve **datacenter_name** kullanmaya devam edebilir; ek olarak **vcenter_hostname** ve **location** kullanılabilir.

---

## 7. Özet kontrol listesi

| Adım | Açıklama | Yapıldı |
|------|----------|---------|
| 1 | Tüm güncellenmiş view'ları psql ile çalıştır | ☐ |
| 2 | Kolon tanımı değişen MV'ları DROP + CREATE et | ☐ |
| 3 | mv_vmware_vm_latest, mv_vmware_host_latest için REFRESH çalıştır | ☐ |
| 4 | refresh_vmware_materialized_views() ile bir kez tüm MV'ları refresh et | ☐ |
| 5 | discovery_vmware_inventory_vcenter.vcenter_hostname dolu mu kontrol et | ☐ |
| 6 | Cluster isimlendirme (DCxx → location) kuralını doğrula | ☐ |

---

**Son güncelleme:** vcenter_hostname ve location eklendi; vcenter_name ve datacenter_name aynen bırakıldı (ETL değişikliği yok).
