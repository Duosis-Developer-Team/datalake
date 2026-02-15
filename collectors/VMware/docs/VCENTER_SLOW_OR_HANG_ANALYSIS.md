# vCenter 10.34.1.230 – Script Takılma / Çok Uzun Süre Analizi

**vCenter:** 10.34.1.230  
**Kullanıcı:** zabbix@blt.vc  
**Şikayet:** Scriptler çok uzun süre takılı kalıyor, veri çekilemiyor.

**Güncelleme:** Script bu makineden çalışabiliyor; **eski yapıdaki** (`*_performance_metrics`) scriptler bu vCenter’dan veri toplayabiliyor. Yani ağ, firewall ve kimlik doğrulama sorunu yok. Asıl neden: **yeni collector scriptleri tamamen sıralı (sequential)** çalışıyor, eski scriptler ise **ThreadPoolExecutor ile paralel** çalışıyor. Aynı vCenter’da eski scriptler kısa sürede biterken yeni collector’lar VM/host sayısı × (QueryPerf + diğer API) kadar sıralı iş yaptığı için çok uzun sürüyor ve “takılı” gibi görünüyor.

---

## 1. Tespit Edilen Nedenler

### 1.1 Bağlantı / İstek Timeout Yok

- Tüm collector’larda **SmartConnect** kullanılıyor; **hiçbirinde connection timeout** parametresi yok.
- pyVmomi `SmartConnect` API’sinde timeout parametresi yok; varsayılan socket timeout’a kalıyor.
- Sonuç: Ağ erişilemez veya çok yavaşsa script **süresiz bekleyebilir** (TCP/SSL el sıkışması veya ilk yanıt için).

**Etkilenen dosyalar (örnek):**
- `vmware_datacenter_collector.py`, `vmware_host_collector.py`, `vmware_vm_collector.py`
- `vmware_*_performance_metrics.py`, `vmware_cluster_collector.py`
- `discovery/vmware-discovery.py` (bu script’te `pre_flight_check` var ama ana collector’larda kullanılmıyor)

### 1.2 Her VM / Her Host İçin Ayrı QueryPerf

- **vmware_vm_collector.py:** Her VM için ayrı `perf_mgr.QueryPerf(...)` çağrısı var (config + runtime + storage + **1 QueryPerf**).
- **vmware_host_collector.py:** Her host için aynı şekilde **1 QueryPerf** per host.
- QueryPerf **batch değil**, entity sayısı kadar round-trip yapılıyor.

Örnek:
- 50 host + 500 VM → en az **550** QueryPerf çağrısı (VM collector’da 500, host collector’da 50).
- Her çağrı 1–5+ saniye sürerse toplam süre **10–45+ dakika** olabilir; script “takılı” gibi görünür.

### 1.3 RetrieveContent ve Hiyerarşi

- `content = si.RetrieveContent()` tek seferde ama büyük vCenter’da yavaş olabilir.
- `content.rootFolder.childEntity` ve altındaki `hostFolder`, `host.vm` döngüleri property’leri çekerken ek round-trip’ler tetikleyebilir (lazy load). Bu da toplam süreyi uzatır.

### 1.4 Kimlik Doğrulama (zabbix@blt.vc)

- `zabbix@blt.vc` SSO veya domain kullanıcısı olabilir; vCenter bu durumda AD/LDAP’e gider.
- AD/LDAP yavaş veya erişilemezse **ilk bağlantı** (SmartConnect) uzun sürebilir veya timeout’suz bekleyebilir.

### 1.5 Ağ / Güvenlik Duvarı

- 10.34.1.230’a erişim: güvenlik duvarı, proxy, SSL inspection, yüksek gecikme script’i yavaşlatır veya bağlantıyı askıda bırakır.
- Timeout olmadığı için bu “takılma” süresiz devam eder.

---

## 2. Hızlı Kontrol Listesi

| Kontrol | Nasıl yapılır |
|--------|----------------|
| 443 açık mı? | `nc -zv 10.34.1.230 443` veya discovery’deki `pre_flight_check(ip, 443)` |
| Bağlantı süresi | `time curl -k -v https://10.34.1.230/` (SSL uyarısı normal, süreye bakın) |
| vCenter yanıt veriyor mu? | Discovery script’i sadece bağlanıp `RetrieveContent()` ile test: `python discovery/vmware-discovery.py --ip 10.34.1.230 --user 'zabbix@blt.vc' --pass '...'` |
| Çok sayıda VM/host var mı? | vCenter’da toplam host ve VM sayısı; VM collector = VM sayısı kadar QueryPerf |

---

## 3. Önerilen İyileştirmeler

### 3.1 Bağlantı Öncesi Port Kontrolü (Pre-flight)

- Tüm collector’larda, **SmartConnect’ten önce** `pre_flight_check(vmware_ip, vmware_port, timeout=10)` gibi bir çağrı eklenebilir (discovery’deki gibi).
- Port kapalıysa 10 saniyede hata verip çıkılır; süresiz takılma azalır.

### 3.2 Socket Timeout ile SmartConnect

- SmartConnect’ten önce global socket timeout ayarlanabilir:
  - `socket.setdefaulttimeout(60)` (sadece örnek; 30–120 saniye makul).
- Veya bağlantıyı kendi socket’inizle açıp pyVmomi’ye vermek (pyVmomi dokümantasyonuna göre uyarlanabilir).

### 3.3 QueryPerf Batch / Limit

- Mümkünse QueryPerf **batch** kullanın (birden fazla entity tek `QuerySpec` listesinde); vCenter’ın limit’ine dikkat edin (ör. 64 entity/sorgu).
- VM/host sayısı çok yüksekse: ilk aşamada sadece inventory (config/runtime) çekip, perf’i ayrı job’da veya limitli (ör. ilk N host/N VM) çekmek.

### 3.4 Zabbix / Zaman Aşımı

- Zabbix item’larında **timeout** (ör. 60–120 saniye) tanımlı olsun; script kendi içinde timeout’a uygun davranacak şekilde güncellenirse, Zabbix de uzun süre bekleyip “takılı” gibi görünmez.

---

## 4. Yapılan Düzeltme (Paralel Toplama)

- **vmware_vm_collector.py:** Eski `vmware_vm_performance_metrics.py` ile aynı model uygulandı. Tüm VM'ler için işler tek listede toplanıp **ThreadPoolExecutor(max_workers=32)** ile paralel işleniyor. `--max-workers` ile ayarlanabilir.
- **vmware_host_collector.py:** Aynı şekilde host'lar **ThreadPoolExecutor(max_workers=16)** ile paralel işleniyor. `--max-workers` ile ayarlanabilir.
- Böylece aynı vCenter'da yeni collector'lar da eski performance_metrics scriptleri gibi makul sürede tamamlanır.

## 5. Sonuç

- **Takılmanın asıl sebebi:** Yeni collector'ların **sıralı** çalışması; eski scriptlerin **paralel** çalışması. Ağ/auth bu makineden sorunsuz.
- **Yapılan:** VM ve host collector'lara paralel işleme eklendi.
- **İsteğe bağlı:** Pre-flight port kontrolü ve socket timeout eklenebilir; paralellik ana iyileştirme.

- **Önceki analiz notu:** Timeout yokluğu, sıralı QueryPerf, ağ/auth. Bu makineden eski scriptler çalıştığı için asıl neden sıralı işlemdi; paralellik eklendi.
