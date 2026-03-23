# **Zabbix \- Network Collector (Data Collector) LLD**

**Versiyon:** 1.0

**Tarih:** 23 Mart 2026

## **1\. Amaç ve Kapsam**

### **1.1. Amaç**

Bu dokümanın temel amacı, Zabbix izleme (monitoring) sistemi üzerinde bulunan ağ cihazlarına (Switch, Router, Firewall vb.) ait anlık durum, performans (CPU, RAM) ve detaylı arayüz (port, interface) trafik/hata verilerinin Datalake (Veri Gölü) ortamına aktarılmasını sağlayan mimarinin düşük seviyeli teknik tasarımını (LLD) detaylandırmaktır. Proje; karmaşık ve farklı isimlendirmelere sahip metrikleri standartlaştırmayı, Datalake ortamındaki (S3 ICOS ve iLO projelerine benzer) zaman serisi analitiği için güvenilir bir temel oluşturmayı hedeflemektedir.

### **1.2. Kapsam**

Bu tasarım, veri toplama ve işleme boru hattının (pipeline) tüm bileşenlerini kapsar:

* **Veri Kaynağı:** Zabbix (JSON-RPC API).  
* **Veri Toplama:** Python ile geliştirilmiş özel kolektör betiği (zabbix\_network.py).  
* **Veri Standartlaştırma (Normalizasyon):** Farklı Zabbix şablonlarının (template) tek bir formata dönüştürülmesi.  
* **Orkestrasyon:** Apache NiFi ile verinin yönlendirilmesi, ayrıştırılması ve veritabanına yazılması.  
* **Veri Depolama:** PostgreSQL / TimescaleDB üzerinde optimize edilmiş, zaman serisi (hypertable) veritabanı yapısı.

## **2\. Veri Kaynağı ve Çekme Yöntemi**

Zabbix veritabanına doğrudan (SQL ile) bağlanmak yerine, Zabbix'in sunduğu **JSON-RPC API** kullanılmaktadır. Bu yaklaşım, Zabbix'in kendi iç yetkilendirme (Auth), rol ve izin mekanizmalarına sadık kalmayı sağlar.

* **Endpoint:** http://\<ZABBIX\_IP\>/api\_jsonrpc.php  
* **Yöntem:** Python betiği, Zabbix sunucusuna \--group (Örn: "Network Devices") ve opsiyonel olarak \--template (Örn: "BLT \- Arista SNMP") parametreleri ile istek atar.  
* **Optimizasyon:** Veriler host bazlı (host.get) ve item bazlı (selectItems) çekilir. Etiketler (tags) aracılığıyla cihazın lokasyon (location) ve Datalake bağlayıcı ID'leri (loki\_id) dinamik olarak metadata'ya eklenir.

## **3\. Veri Standartlaştırma ve Normalizasyon (Standardization)**

Zabbix'teki "Item" isimleri, kullanılan donanım markasına (Cisco, Arista, Fortinet vb.) veya şablona göre büyük değişiklik gösterir. Datalake ortamında sorgu kolaylığı sağlamak için Python betiği içinde ciddi bir normalizasyon katmanı kurgulanmıştır.

### **3.1. Genel Cihaz Metrikleri (Device Metrics)**

Farklı şablonlardan gelen benzer metrikler, Datalake için tek bir standart sütun ismine eşlenir (Mapping):

* ICMP ping veya Ping status ![][image1] icmp\_status  
* CPU utilization ![][image1] cpu\_utilization\_pct  
* Birimler (Örn: "s", "%", "B") ham veriden temizlenir. Örneğin; saniye (s) cinsinden gelen ping süreleri otomatik olarak milisaniyeye (ms) çevrilir.

### **3.2. Arayüz Parçalama (Interface Parsing)**

Zabbix, port verilerini tek bir uzun metin olarak tutar: Interface GigabitEthernet1/0/1(ALIAS\_NAME): Duplex status. Bu yapı, betik içindeki **Regex (Düzenli İfadeler)** ile parçalanır:

* **Arayüz Adı:** GigabitEthernet1/0/1  
* **Arayüz Açıklaması (Alias):** ALIAS\_NAME  
* **Metrik:** duplex\_status

### **3.3. "0" ve Boş (Null) Değerlerin Yönetimi**

Veri analizi sırasında "0" değerlerinin taşıdığı anlamlar standartize edilmiştir:

* **Sağlıklı Durum "0"ları:** inbound\_packets\_discarded gibi hata paket sayaçlarının 0 gelmesi sistemin sağlıklı olduğunu gösterir. Aynen tutulur.  
* **Kapalı (Down) Portlar:** operational\_status: 2 (Down) olan portların trafik değerleri doğal olarak 0 gelir. Datalake kapasite analizi için olduğu gibi yazılır.  
* **Toplanamayan Veriler:** Eğer cihaz (örneğin bir Linux tabanlı Firewall) RAM metriklerini desteklemiyorsa, veri 0 olarak değil, null (boş) olarak bırakılır ki analitik ortalamalar (Average) bozulmasın.

### **3.4. Düz Kayıt (Flat Record) ve data\_type**

Veritabanına yazım ve Apache NiFi orkestrasyonunu basitleştirmek için, içiçe (nested) JSON yerine **Flat (Düz) JSON** mimarisi kullanılmıştır. Çıktıdaki her JSON objesi bir data\_type etiketi alır:

* "data\_type": "network\_device" (Cihaz geneli özet metrikler)  
* "data\_type": "network\_interface" (Sadece o porta ait metrikler)

## **4\. Orkestrasyon ve Veri Akışı (Apache NiFi)**

Apache NiFi, Python betiğinden gelen düz JSON dizisini alıp TimescaleDB'ye yazmaktan sorumludur. Tüm veri akışı tek bir birleşik (Unified) Avro Şeması (zabbixDataRecord) kullanılarak yönetilir.

**Akış Adımları (NiFi Flow):**

1. **ExecuteStreamCommand:** Python betiğini (zabbix\_network.py) belirli argümanlarla çalıştırır ve stdout çıktısını (JSON Array) alır.  
2. **SplitJson:** $\[\*\] JSON path ifadesi kullanılarak dizideki her bir JSON objesi (cihaz veya arayüz kaydı) tekil bir FlowFile'a dönüştürülür.  
3. **EvaluateJsonPath:** JSON içindeki data\_type alanı okunarak NiFi FlowFile Attribute'una (zabbix.data\_type) atanır.  
4. **RouteOnAttribute:** Veriler data\_type değerine göre yönlendirilir:  
   * *Device\_Route:* ${zabbix.data\_type:equals('network\_device')}  
   * *Interface\_Route:* ${zabbix.data\_type:equals('network\_interface')}  
5. **PutDatabaseRecord:** İki farklı rotadan gelen veriler, ilgili veritabanı tablolarına yazılır.  
   * **Kritik Ayar:** Unmatched Field Behavior \= Ignore Unmatched Fields. Bu ayar sayesinde tek bir geniş şema kullanılmasına rağmen, tabloda olmayan sütunlar (Örn: Arayüz tablosuna yazılırken CPU verisi) hata vermeden yoksayılır.  
   * **Zaman Damgası (Timestamp) Ayarı:** JsonTreeReader içinde Timestamp formatı yyyy-MM-dd'T'HH:mm:ss'Z' olarak belirtilmiş ve şemada "logicalType": "timestamp-millis" kullanılmıştır. Bu, PostgreSQL TIMESTAMPTZ veri tipi uyumsuzluğu hatalarını engeller.

## **5\. Veri Depolama Mimarisi (TimescaleDB)**

Veriler, zaman serisi analitiği ve dashboard (Grafana vb.) performansını maksimize etmek için PostgreSQL üzerine kurulu **TimescaleDB** eklentisi kullanılarak depolanır.

### **5.1. Tablo Yapıları ve DDL**

**1\. Cihaz Metrikleri Tablosu (zabbix\_network\_device\_metrics):**

Ağ cihazlarının donanım kullanımını (CPU, RAM) ve genel port özetlerini tutar.

CREATE TABLE zabbix\_network\_device\_metrics (  
    id BIGSERIAL,  
    collection\_timestamp TIMESTAMPTZ NOT NULL,  
    data\_type VARCHAR(50) NOT NULL,  
    host VARCHAR(255) NOT NULL,  
    location VARCHAR(255),  
    loki\_id VARCHAR(100),  
    applied\_templates TEXT,  
    icmp\_status INT,  
    icmp\_loss\_pct NUMERIC(5,2),  
    icmp\_response\_time\_ms NUMERIC(10,4),  
    cpu\_utilization\_pct NUMERIC(5,2),  
    memory\_utilization\_pct NUMERIC(5,2),  
    uptime\_seconds BIGINT,  
    system\_name VARCHAR(255),  
    system\_description TEXT,  
    total\_ports\_count INT,  
    active\_ports\_count INT,  
    PRIMARY KEY (id, collection\_timestamp)  
);  
CREATE INDEX idx\_zabbix\_net\_device\_host ON zabbix\_network\_device\_metrics (host, collection\_timestamp DESC);  
SELECT create\_hypertable('zabbix\_network\_device\_metrics', 'collection\_timestamp');

**2\. Arayüz (Port) Metrikleri Tablosu (zabbix\_network\_interface\_metrics):**

Cihazların port bazlı detaylı hız, trafik (in/out) ve hata verilerini tutar.

CREATE TABLE zabbix\_network\_interface\_metrics (  
    id BIGSERIAL,  
    collection\_timestamp TIMESTAMPTZ NOT NULL,  
    data\_type VARCHAR(50) NOT NULL,  
    host VARCHAR(255) NOT NULL,  
    interface\_name VARCHAR(255) NOT NULL,  
    interface\_alias VARCHAR(255),  
    operational\_status INT,  
    duplex\_status INT,  
    speed BIGINT,  
    bits\_received BIGINT,  
    bits\_sent BIGINT,  
    inbound\_packets\_discarded BIGINT,  
    inbound\_packets\_with\_errors BIGINT,  
    outbound\_packets\_discarded BIGINT,  
    outbound\_packets\_with\_errors BIGINT,  
    interface\_type INT,  
    PRIMARY KEY (id, collection\_timestamp)  
);  
CREATE INDEX idx\_zabbix\_net\_iface\_host\_name ON zabbix\_network\_interface\_metrics (host, interface\_name, collection\_timestamp DESC);  
SELECT create\_hypertable('zabbix\_network\_interface\_metrics', 'collection\_timestamp');

### **5.2. TimescaleDB Optimizasyonları**

* **Hypertable:** create\_hypertable fonksiyonu ile tablolar zaman bazlı partition'lara (chunk) ayrılmıştır.  
* **Primary Key Kısıtlaması:** TimescaleDB mimarisi gereği partition anahtarı olan collection\_timestamp, Primary Key dizilimine zorunlu olarak eklenmiştir.  
* **Chunking (Bölütleme):** Sistem başlangıcında varsayılan chunk ayarlarıyla (genellikle 7 günlük) devreye alınmıştır. İlerleyen dönemde veri hacmine göre sıkıştırma (compression) ve otomatik silme (retention policy) politikaları devreye alınacaktır.

## **6\. Gelecek Geliştirmeler ve Genişletilebilirlik**

Bu sistemin en büyük avantajı "Tek Şema, Çoklu Tablo" (Single Schema, Multi-Table) metodolojisidir. Zabbix üzerinden ağ cihazları dışında, örneğin **Sunucu (Server)** veya **Veritabanı** metrikleri toplanmak istendiğinde;

1. **Betik (Python):** Yeni şablonlardan gelen veriler için script'e yeni bir data\_type (Örn: server\_device) eklenir.  
2. **Şema (NiFi):** zabbixDataRecord şemasına sadece sunuculara özel yeni alanlar (disk\_usage, process\_count vb.) null-sınıflı olarak eklenir. Mevcut ağ akışları bundan etkilenmez.  
3. **Veritabanı (PostgreSQL):** Sadece zabbix\_server\_metrics adında yeni bir tablo oluşturulur.  
4. **Rota (NiFi):** RouteOnAttribute işlemcisine ${zabbix.data\_type:equals('server\_device')} koşuluyla yeni bir ok çizilir ve tabloya bağlanır.

Bu modüler yapı sayesinde Datalake ortamına yeni veri kaynaklarının entegrasyonu dakikalar içerisinde sıfır kesintiyle gerçekleştirilebilir.

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABMAAAAXCAYAAADpwXTaAAAA0klEQVR4Xq2QyQ3CMBBFY4ky4iU9IHGhAyTKoQeOFEQu3DlyoAwKQHyThMTjZWyTJ00Uj/+8jNI0QNjHOlgVr+MTOQQtftPvfAm1Q72B+E0utYaKuWmEjKZMqTsHJqi1vjIRSjwO2Xt5jic9bHQRx6tSao86zU0O5nPY7m46s/NyUsptTrXkbIx5QtpT2bGmIHrYgmLjCEvBVheIDrRfjFa6g+w8nelv80kksNGL9qqB7EZ7DvMiiZUIv2TRMBMRggk4iNFXMrNqmLkeGFfMyv7DB9DWIJiF2/aKAAAAAElFTkSuQmCC>