# VMware Collector Optimizasyon Test Sonuçları ve Beklentiler

**vCenter:** 10.34.1.230 (problemli vCenter – önceden script tamamlanmıyordu)  
**Test tarihi:** Optimizasyon sonrası

---

## 1. Test Sonuçları

| Test | Parametre | Süre | Sonuç |
|------|-----------|------|--------|
| Host collector | `--max-hosts 5` | **11.4 s** | 1925 kayıt (5 host) |
| Host collector | `--max-hosts 24` | **47.4 s** | 9595 kayıt (24 host) |
| VM collector | `--max-vms 10` | **12.7 s** | 570 kayıt (10 VM) |
| **Host collector** | **Tüm host’lar (96)** | **181 s (3.0 dk)** | 42575 kayıt, 96 host |
| **VM collector** | **Tüm VM’ler (5132)** | **751 s (12.5 dk)** | 217682 kayıt, 5132 VM |

- Tüm testler **exit code 0** ile bitti; timeout veya hata yok.
- **96 host** toplama süresi **~3 dakika**; **5132 VM** toplama süresi **~12.5 dakika**; ikisi de hedeflenen 15 dakikanın altında.

---

## 2. Beklentiler (Optimizasyon Sonrası)

### 2.1 Süre
- **Host collector (bu vCenter, 96 host):** Tam toplama **~3–5 dakika** civarında bitmeli (test: 3.0 dk).
- **VM collector:** VM sayısına bağlı. Kabaca 10 VM ~12 s ise, 500 VM için batch sayısı ~21; **tahmini 8–15 dakika** (ağ ve vCenter yüküne göre değişir).
- **Genel hedef:** Tek vCenter için toplama **15 dakikadan kısa**; timeout 30 dk ile güvence altında.

### 2.2 API kullanımı
- **QueryPerf çağrı sayısı:**  
  - 96 host → **4** çağrı (batch_size=24).  
  - 5132 VM → **214** çağrı (batch_size=24). Önceden 5132 ayrı çağrı yapılırdı.  
  Round-trip sayısı belirgin azalır.

### 2.3 Ölçeklendirme
- Host/VM arttıkça süre kabaca **doğrusala yakın** artar (batch sayısı = ceil(N / perf_batch_size)).
- Çok büyük ortamlarda (ör. 1000+ VM) `--perf-batch-size 24` veya `--max-workers 32` yeterli olmazsa artırılabilir; timeout (30 dk) yine üst sınırı korur.

### 2.4 Zaman aşımı
- Varsayılan **timeout 30 dakika (1800 s)**.  
- Beklenen süre 15 dk’nın altında olduğu için normal koşullarda timeout’a düşülmemesi beklenir.  
- Ağ/vCenter yavaşlığında kısmi sonuç + stderr mesajı ile çıkış olur.

---

## 3. Özet

- **Test:** Problemli vCenter’da host collector 96 host ile **~3 dakikada**, VM collector 5132 VM ile **~12.5 dakikada** tamamlandı.
- **Beklenti:** Aynı ortamda host toplama **~3 dk**, VM toplama **~12–13 dk**; ikisi de **15 dakikanın altında**.
- **Optimizasyon etkisi:** Batch QueryPerf ve iki fazlı (config paralel + batch perf) akış sayesinde API round-trip ve toplam süre ciddi azaldı; önceki “tamamlanamıyor” davranışı giderildi.
