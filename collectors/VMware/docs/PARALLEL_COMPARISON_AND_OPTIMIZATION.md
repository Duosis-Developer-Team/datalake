# VMware Collector: Eski vs Yeni Paralel İşleme Karşılaştırması ve Optimizasyon

## 1. Eski Scriptler (*_performance_metrics)

### vmware_host_performance_metrics.py
| Özellik | Değer |
|--------|--------|
| ThreadPoolExecutor | `ThreadPoolExecutor()` – **max_workers belirtilmemiş** (Python varsayılanı: min(32, cpu_count+4)) |
| İş per worker | Tek host: **1x QueryPerf** + summary (hardware, quickStats, datastore) – hafif |
| QueryPerf | **Host başına 1 API çağrısı** (N host = N round-trip) |
| Counter bilgisi | Her QueryPerf sonrası `cmap` kullanılır; `get_perf_counter_map` bir kez çağrılır |

### vmware_vm_performance_metrics.py
| Özellik | Değer |
|--------|--------|
| ThreadPoolExecutor | `ThreadPoolExecutor(max_workers=32)` |
| İş per worker | Tek VM: **1x QueryPerf** + summary (config, runtime, storage) – hafif |
| QueryPerf | **VM başına 1 API çağrısı** (M VM = M round-trip) |
| Counter bilgisi | `cmap` ve `mids` bir kez oluşturulur, tüm job’lara aynı referans gider |

---

## 2. Yeni Collector’lar (Optimizasyon Öncesi)

### vmware_host_collector.py (önceki)
| Özellik | Değer |
|--------|--------|
| max_workers | **16** (eskiden 32’den az) |
| İş per worker | Tek host: hardware + runtime + storage + **1x QueryPerf** + get_counter_info **her counter için** + perf_agg |
| QueryPerf | Host başına 1 çağrı → **N host = N API çağrısı** |
| Counter bilgisi | **Her host, her counter** için `get_counter_info(perf_mgr, counter_id)` – perf_mgr.perfCounter üzerinde tekrarlı döngü |

### vmware_vm_collector.py (önceki)
| Özellik | Değer |
|--------|--------|
| max_workers | 32 |
| İş per worker | Tek VM: config + runtime + storage + **1x QueryPerf** + get_counter_info **her counter için** + perf_agg |
| QueryPerf | VM başına 1 çağrı → **M VM = M API çağrısı** |
| Counter bilgisi | Aynı şekilde tekrarlı get_counter_info |

**Sonuç:** Yeni collector’lar hem daha az worker (host’ta 16) kullanıyordu hem de **entity başına bir QueryPerf** ile çok sayıda round-trip yapıyordu. Ayrıca counter metadata için sürekli `get_counter_info` ile perfCounter taranıyordu.

---

## 3. Yapılan Optimizasyonlar

### 3.1 Worker sayısı
- **vmware_host_collector:** `max_workers` varsayılan **16 → 32** (eski performance_metrics ile aynı seviye).

### 3.2 Counter info map (tek seferlik)
- **build_counter_info_map(perf_mgr, counter_ids)** eklendi.
- Counter ID → metadata eşlemesi **bir kez** hesaplanıyor, tüm host/VM işlemleri bu map’i kullanıyor.
- **Öncesi:** O(entities × counters) kez `get_counter_info` (her seferinde perf_mgr.perfCounter döngüsü).  
- **Sonrası:** O(counters) tek geçiş, sonrası O(1) map erişimi.

### 3.3 Batch QueryPerf (en büyük kazanç)
- **Öncesi:** N host veya M VM için **N veya M adet** `QueryPerf` çağrısı.
- **Sonrası:** Aynı entity’ler **batch’ler halinde** tek QueryPerf’e gönderiliyor:
  - `perf_mgr.QueryPerf(querySpec=[spec1, spec2, ..., specK])` ile **K entity tek çağrıda**.
- **perf_batch_size** (varsayılan 24, max 64): Her API çağrısına en fazla bu kadar entity veriliyor.
- **Örnek:** 96 host → önceden 96 çağrı, şimdi ceil(96/24) = **4 çağrı**.

### 3.4 İki fazlı akış
1. **Faz 1 (paralel):** Sadece config/inventory (host: hardware, runtime, storage; VM: config, runtime, storage). **QueryPerf yok**, sadece property okuma.
2. **Faz 2 (batch):** Tüm entity’ler için QueryPerf batch’ler halinde çağrılıyor; dönen sonuçlar entity bazında parse edilip perf_raw ve perf_agg üretiliyor.
3. **Birleştirme:** Her entity için faz 1 çıktıları + kendi perf_raw + perf_agg sırayla birleştirilip çıktıya yazılıyor.

---

## 4. Yeni parametreler

| Parametre | Script | Varsayılan | Açıklama |
|-----------|--------|------------|----------|
| `--perf-batch-size` | host, VM | 24 | Tek QueryPerf çağrısına verilen entity sayısı (vCenter limitine uygun; 64’ü geçmez). |
| `--max-workers` (host) | host | 32 | Paralel config-only worker sayısı (eski performance_metrics ile uyumlu). |

---

## 5. Beklenen süre etkisi

- **API round-trip:** 96 host için 96 yerine 4 QueryPerf; VM sayısı 500 ise 500 yerine 21 çağrı. Ağ ve vCenter tarafındaki gecikme ciddi azalır.
- **Counter lookup:** Tekrarlı perfCounter taraması kalktığı için CPU ve süre tasarrufu.
- **Paralellik:** Host collector’da 32 worker ile config fazı daha hızlı biter.

Bu sayede toplama süresinin **15 dakikanın altına** inmesi hedeflenir; büyük ortamlarda fark daha belirgin olur.
