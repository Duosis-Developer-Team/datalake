# **IBM S3 ICOS Veri Toplayıcı**

**Versiyon:** 1.0

**Tarih:** 24.07.2025

**Hazırlayan:** Can İlbey Sezgin

### **1\. Amaç ve Kapsam**

#### **1.1. Amaç**

Bu dokümanın temel amacı, IBM S3 ICOS (Information Cloud Object Storage) depolama altyapısının yönetim arayüzünden, REST API aracılığıyla kapsamlı "Vault" (Kasa) envanter ve zaman serisi performans metriklerinin toplanmasını, işlenmesini ve yapısal bir veritabanına aktarılmasını sağlayan sistemin düşük seviyeli teknik tasarımını detaylandırmaktır. Proje, depolama altyapısının izlenmesini otomatikleştirmeyi, kapasite planlaması için güvenilir bir veri temeli oluşturmayı ve operasyonel verimliliği artırmayı hedeflemektedir.

#### **1.2. Kapsam**

Bu tasarım, veri toplama ve işleme boru hattının (pipeline) tüm bileşenlerini kapsar:

* **Veri Kaynağı:** IBM S3 ICOS Yönetim Arayüzü.  
* **Veri Protokolü:** RESTful API (JSON formatında).  
* **Veri Toplama:** Python ile geliştirilmiş, komut satırından çalıştırılabilen bir kolektör betiği (s3-collector.py).  
* **Orkestrasyon:** Apache NiFi ile veri akışının yönetimi ve zamanlanması.  
* **Veri Depolama:** PostgreSQL üzerinde oluşturulmuş, mantıksal olarak gruplandırılmış ilişkisel veritabanı yapısı.

### **2\. API Kullanımı ve Veri Çekme Metodu**

#### **2.1. API Seçimi**

Veri toplama için, sistemin standart olarak sunduğu RESTful API tercih edilmiştir. JSON formatında veri sunması, programatik entegrasyonu ve veri ayrıştırmayı (parsing) kolaylaştırmaktadır.

#### **2.2. Kimlik Doğrulama Metodu**

API, **HTTP Basic Authentication** yöntemini desteklemektedir. Geliştirilen Python betiği, her bir API çağrısında kullanıcı adı ve şifreyi HTTP başlığında (Header) güvenli bir şekilde göndererek kimlik doğrulamayı gerçekleştirir.

#### **2.3. Kullanılan API Uç Noktası (Endpoint)**

Tüm "Vault" verilerini toplamak için aşağıdaki API kaynak URI'si kullanılmaktadır:

| Endpoint | Açıklama |
| :---- | :---- |
| /manager/api/json/1.0/listVaults.adm | Sistemdeki tüm depolama kasalarının (vaults) envanter ve metrik bilgilerini listeler. |

### **3\. Orkestrasyon Yapısı: Apache NiFi**

Veri toplama sürecinin otomasyonu, zamanlanması ve güvenilir bir şekilde yürütülmesi, tasarlanmış bir Apache NiFi veri akışı ile sağlanmaktadır.

1. **GenerateFlowFile:** Akışı periyodik olarak (örneğin her 15 dakikada bir) tetiklemek için kullanılır.  
2. **ExecuteStreamCommand:** Python kolektör betiğini (s3-collector.py) çalıştırır. Betiğe, işlemci ayarlarında tanımlanan \--host, \--username ve \--password argümanlarını geçirir. Betiğin standart çıktısından (stdout) gelen ve tüm kayıtları içeren JSON dizisi, bu işlemcinin çıktısı olarak yeni bir FlowFile'ın içeriği olur. Betiğin bilgilendirme ve hata mesajları (stderr) ise NiFi loglarına yazdırılır.  
3. **SplitJson:** ExecuteStreamCommand'den gelen ve içinde yüzlerce kayıt barındıran tek bir FlowFile'ı alır. $.\* JsonPath ifadesi kullanılarak, dizideki her bir JSON nesnesi için ayrı bir FlowFile oluşturulur. Bu adım, veriyi atomik kayıtlara bölerek paralel işlemeyi mümkün kılar.  
4. **EvaluateJsonPath:** Bölünmüş olan her bir FlowFile'ın içeriğini okur ve $.data\_type ifadesiyle kaydın türünü (s3icos\_vault\_inventory, s3icos\_vault\_metrics vb.) ayıklar. Bu değer, record.type adında yeni bir FlowFile özniteliğine (attribute) atanır.  
5. **RouteOnAttribute:** Akışın merkezi yönlendiricisidir. Gelen FlowFile'ları, record.type özniteliğinin değerine göre ilgili veritabanı yazıcısına giden doğru yola yönlendirir. Üç temel rota tanımlanmıştır: to\_inventory, to\_vault\_metrics ve to\_pool\_metrics.  
6. **PutDatabaseRecord:** Her bir rota için ayrı olarak yapılandırılmış olan bu işlemciler, gelen kaydı ilgili PostgreSQL tablosuna INSERT eder. Bu işlemciler, paylaşılan bir JsonTreeReader ve veritabanı bağlantı havuzu (DBCPConnectionPool) kullanır.

### **4\. Kullanılan JSON Şeması ve Gerekçesi**

NiFi'nin PutDatabaseRecord işlemcisi, gelen veriyi veritabanı sütunlarıyla eşleştirmek için bir şemaya ihtiyaç duyar. Python betiği, tek bir çalıştırmada üç farklı yapıya sahip kayıt ürettiği için, tüm olası alanları içeren birleşik bir Avro şeması oluşturulmuştur.

JsonTreeReader servisinde **"Use 'Schema Text' Property"** stratejisi benimsenmiştir. Bu strateji sayesinde, bir kayıtta bulunmayan alanlar (örneğin, bir envanter kaydında pool\_id alanının olmaması) hata vermeden null olarak kabul edilir. Bu, heterojen veri yapılarını tek bir akışta işlemede en sağlam yöntemdir.

collection\_timestamp Alanı İçin Özel Yapılandırma:  
Veritabanı (TIMESTAMPTZ) ve gelen veri (Epoch milisaniye) arasında doğru tür dönüşümünü sağlamak için şemada logicalType kullanılmıştır. Bu, NiFi'ye bu alanın basit bir sayı (long) değil, mantıksal olarak bir zaman damgası olduğunu bildirir.  
**Kullanılan Avro Şeması:**

{  
  "namespace": "com.bulutistan.s3icos",  
  "type": "record",  
  "name": "S3IcosRecord",  
  "doc": "Python betiği tarafından üretilen tüm s3icos veri türlerini kapsayan birleşik şema.",  
  "fields": \[  
    {  
      "name": "collection\_timestamp",  
      "type": { "type": "long", "logicalType": "timestamp-millis" },  
      "doc": "Verinin toplandığı zaman damgası (Epoch milisaniye olarak)"  
    },  
    { "name": "vault\_id", "type": "int" },  
    { "name": "vault\_name", "type": "string" },  
    { "name": "data\_type", "type": "string" },  
    { "name": "uuid", "type": \["null", "string"\], "default": null },  
    { "name": "description", "type": \["null", "string"\], "default": null },  
    { "name": "type", "type": \["null", "string"\], "default": null },  
    { "name": "width", "type": \["null", "int"\], "default": null },  
    { "name": "threshold", "type": \["null", "int"\], "default": null },  
    { "name": "write\_threshold", "type": \["null", "int"\], "default": null },  
    { "name": "privacy\_enabled", "type": \["null", "boolean"\], "default": null },  
    { "name": "vault\_purpose", "type": \["null", "string"\], "default": null },  
    { "name": "soft\_quota\_bytes", "type": \["null", "long"\], "default": null },  
    { "name": "hard\_quota\_bytes", "type": \["null", "long"\], "default": null },  
    { "name": "allotted\_size\_bytes", "type": \["null", "long"\], "default": null },  
    { "name": "object\_count\_estimate", "type": \["null", "long"\], "default": null },  
    { "name": "allotment\_usage", "type": \["null", "long"\], "default": null },  
    { "name": "pool\_id", "type": \["null", "int"\], "default": null },  
    { "name": "pool\_name", "type": \["null", "string"\], "default": null },  
    { "name": "usable\_size\_bytes", "type": \["null", "long"\], "default": null },  
    { "name": "used\_physical\_size\_bytes", "type": \["null", "long"\], "default": null },  
    { "name": "used\_logical\_size\_bytes", "type": \["null", "long"\], "default": null }  
  \]  
}

### **5\. Veri Modeli: Tablolar ve Kolon Anlamları**

Veritabanı, envanter ve metrik verilerini ayrı tablolarda saklayacak şekilde üç ana tabloya bölünmüştür.

#### **5.1. s3icos\_vault\_inventory Tablosu**

Her bir vault'un kimlik, konfigürasyon ve kota gibi nadiren değişen temel envanter bilgilerini saklar.

**CREATE TABLE Sorgusu:**

CREATE TABLE s3icos\_vault\_inventory (  
    id SERIAL PRIMARY KEY,  
    collection\_timestamp TIMESTAMPTZ NOT NULL,  
    vault\_id INT NOT NULL,  
    vault\_name VARCHAR(255),  
    uuid VARCHAR(255),  
    description TEXT,  
    type VARCHAR(50),  
    width INT,  
    threshold INT,  
    write\_threshold INT,  
    privacy\_enabled BOOLEAN,  
    vault\_purpose VARCHAR(50),  
    soft\_quota\_bytes BIGINT,  
    hard\_quota\_bytes BIGINT  
);

CREATE INDEX idx\_vault\_inventory\_vault\_id\_timestamp ON s3icos\_vault\_inventory (vault\_id, collection\_timestamp DESC);

#### **5.2. s3icos\_vault\_metrics Tablosu**

Her bir vault için anlık kapasite ve kullanım gibi sık değişen zaman serisi metriklerini saklar.

**CREATE TABLE Sorgusu:**

CREATE TABLE s3icos\_vault\_metrics (  
    id SERIAL PRIMARY KEY,  
    collection\_timestamp TIMESTAMPTZ NOT NULL,  
    vault\_id INT NOT NULL,  
    vault\_name VARCHAR(255),  
    allotted\_size\_bytes BIGINT,  
    usable\_size\_bytes BIGINT,  
    used\_physical\_size\_bytes BIGINT,  
    used\_logical\_size\_bytes BIGINT,  
    object\_count\_estimate BIGINT,  
    allotment\_usage BIGINT  
);

CREATE INDEX idx\_vault\_metrics\_vault\_id\_timestamp ON s3icos\_vault\_metrics (vault\_id, collection\_timestamp DESC);

#### **5.3. s3icos\_pool\_metrics Tablosu**

Bir vault'un parçası olan temel depolama havuzlarının (storage pools) metriklerini içerir.

**CREATE TABLE Sorgusu:**

CREATE TABLE s3icos\_pool\_metrics (  
    id SERIAL PRIMARY KEY,  
    collection\_timestamp TIMESTAMPTZ NOT NULL,  
    vault\_id INT NOT NULL,  
    pool\_id INT NOT NULL,  
    pool\_name VARCHAR(255),  
    usable\_size\_bytes BIGINT,  
    used\_physical\_size\_bytes BIGINT,  
    used\_logical\_size\_bytes BIGINT  
);

CREATE INDEX idx\_pool\_metrics\_vault\_id\_pool\_id\_timestamp ON s3icos\_pool\_metrics (vault\_id, pool\_id, collection\_timestamp DESC);

### **6\. Tablolar Arası İlişkilendirme**

Veritabanı, bir zaman serisi veri ambarı (data warehouse) modeline benzediği için tablolar arasında FOREIGN KEY kısıtlamaları kullanılmamıştır. İlişkilendirme, sorgu zamanında JOIN operasyonları ile gerçekleştirilir.

**Anahtar Sütunlar:**

* **vault\_id**: Tüm tablolarda bulunur ve verinin hangi vault'a ait olduğunu belirtir.  
* **collection\_timestamp**: Tüm tablolarda bulunur ve verinin hangi toplama anına ait olduğunu belirten bir "snapshot ID" görevi görür.

İlişki Örneği:  
Belirli bir vault'un, belirli bir zamandaki envanter bilgisi ile metriklerini birleştirmek için s3icos\_vault\_inventory ve s3icos\_vault\_metrics tabloları vault\_id ve collection\_timestamp üzerinden JOIN edilir.