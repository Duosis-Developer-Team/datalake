# **Panduit PDU Veri Toplayıcı**

**Versiyon:** 1.0

**Tarih:** 17.08.2025

**Hazırlayan:** Can İlbey Sezgin

### **1\. Amaç ve Kapsam**

#### **1.1. Amaç**

Bu dokümanın temel amacı, Zabbix izleme sistemi üzerinden yönetilen Panduit PDU (Power Distribution Unit) cihazlarından, Zabbix API aracılığıyla kapsamlı envanter ve zaman serisi performans metriklerinin toplanmasını, işlenmesini ve yapısal bir veritabanına aktarılmasını sağlayan sistemin düşük seviyeli teknik tasarımını detaylandırmaktır. Proje, yalnızca reaktif bir izleme sağlamakla kalmaz, aynı zamanda proaktif hata tespiti, uzun vadeli kapasite planlaması ve enerji tüketim verilerine dayalı maliyet analizi gibi kritik iş hedeflerini desteklemeyi amaçlar. Veri merkezi güç altyapısının anlık ve geçmişe dönük durumunu analiz ederek, anormallikleri önceden tespit etmeyi, kaynak kullanımını optimize etmeyi ve operasyonel verimliliği en üst düzeye çıkarmayı hedeflemektedir.

#### **1.2. Kapsam**

Bu tasarım, veri toplama ve işleme boru hattının (pipeline) tüm teknik ve mantıksal bileşenlerini kapsar:

* **Veri Kaynağı:** Zabbix Sunucusu API'si, PDU'lar hakkındaki tüm metrikler için "tek doğru kaynak" (single source of truth) olarak kabul edilir. Bu, veri tutarlılığını garanti altına alır.  
* **Veri Protokolü:** JSON-RPC, verimli ve yapılandırılmış veri alışverişi için kullanılır.  
* **Veri Toplama:** Python ile geliştirilmiş, komut satırından çalıştırılabilen zabbix-get-data.py kolektör betiği. Bu betik, ham Zabbix verisini çekmekle kalmaz, aynı zamanda onu işleyerek veritabanı modeline uygun, temiz ve dikey bir formata dönüştürür.  
* **Orkestrasyon:** Apache NiFi, tüm veri akışının beyni olarak görev yapar. Veri toplama betiğinin periyodik olarak zamanlanması, hatalı durumlarda yeniden deneme (retry) mekanizmalarının işletilmesi, sistemler arasında oluşabilecek yavaşlıklara karşı geri basınç (backpressure) uygulama gibi özellikleriyle sürecin dayanıklılığını ve güvenilirliğini sağlar.  
* **Veri Depolama:** PostgreSQL üzerinde oluşturulmuş, panduit\_ önekine sahip ve mantıksal olarak ayrıştırılmış ilişkisel veritabanı yapısı. PostgreSQL'in seçilme nedeni, yapısal zaman serisi verilerini verimli bir şekilde saklama, karmaşık analitik sorguları (analytical queries) destekleme ve olgun bir ekosisteme sahip olmasıdır.

### **2\. API Kullanımı ve Veri Çekme Metodu**

#### **2.1. API Seçimi**

Veri toplama için, Zabbix'in standart olarak sunduğu JSON-RPC API'si tercih edilmiştir. Bu seçimin temel nedenleri şunlardır:

* **Verimlilik:** Tek bir API çağrısı ile birden fazla nesne (örneğin, yüzlerce host'a ait binlerce item) hakkında bilgi alınabilmesi, ağ trafiğini ve işlem süresini önemli ölçüde azaltır.  
* **Yapısal Veri:** API'nin her zaman öngörülebilir ve iyi tanımlanmış bir JSON yapısında yanıt vermesi, Python betiği içindeki veri işleme ve ayrıştırma mantığını basitleştirir.  
* **Zengin Fonksiyonellik:** host.get ve item.get gibi metotların sunduğu filtreleme ve çıktı formatlama seçenekleri, sadece ihtiyaç duyulan verinin alınmasını sağlayarak süreci optimize eder.

#### **2.2. Kimlik Doğrulama Metodu**

Zabbix API, oturum bazlı bir kimlik doğrulama mekanizması kullanır. Bu yöntem, güvenlik açısından önemlidir. Geliştirilen Python betiği, user.login metodu ile kullanıcı adı ve şifreyi sunucuya göndererek bir auth\_token alır. Bu token, oturum süresince yapılan sonraki tüm API çağrılarının auth parametresine eklenir. Şifre, betik içinde veya NiFi yapılandırmasında açık metin olarak saklanmaz; ExecuteStreamCommand işlemcisine bir argüman olarak geçirilir ve ideal olarak NiFi'ın "Sensitive Properties" özelliği ile korunur. İşlem tamamlandığında user.logout metodu ile oturum güvenli bir şekilde sonlandırılarak, token'ın gereksiz yere aktif kalması engellenir.

#### **2.3. Kullanılan API Metotları**

Kolektör betiği, belirtilen bir Host Grubu'ndaki tüm PDU verilerini toplamak için aşağıdaki temel API metotlarını mantıksal bir sıra ile kullanır:

| Metot | Açıklama |
| :---- | :---- |
| user.login | API'ye bağlanmak ve oturum anahtarı (auth token) almak için kullanılır. Bu, tüm operasyonların ilk adımıdır. |
| host.get | Belirtilen groupid'ye sahip tüm host'ların (PDU'ların) ID'lerini ve temel bilgilerini alır. output: \["hostid", "name"\] gibi parametrelerle sadece gerekli bilgiler çekilir. |
| item.get | host.get metodundan elde edilen host ID'leri hostids parametresine bir dizi olarak verilerek, bu PDU'lara ait tüm izleme kalemleri (items) tek bir çağrıda toplu olarak çekilir. output: "extend" parametresi, her bir item'ın adı, son değeri, anahtarı gibi tüm detaylarını getirmek için kullanılır. Bu, veri zenginleştirme için kritik öneme sahiptir. |
| user.logout | API oturumunu sonlandırır. Bu, betik başarıyla tamamlansa da bir hatayla sonlansa da her zaman çalıştırılması gereken bir adımdır. |

### **3\. Orkestrasyon Yapısı: Apache NiFi**

Veri toplama sürecinin otomasyonu, zamanlanması ve güvenilir bir şekilde yürütülmesi, tasarlanmış bir Apache NiFi veri akışı ile sağlanmaktadır. Her bir işlemci, veri boru hattında belirli ve kritik bir rol oynar.

* **GenerateFlowFile:** Akışın tetikleyicisidir. "Scheduling" sekmesindeki "CRON driven" stratejisi kullanılarak, örneğin 0 \*/15 \* \* \* ? ifadesiyle her 15 dakikanın başında çalışacak şekilde ayarlanır. Bu, veri toplama sıklığını merkezi olarak yönetmeyi sağlar.  
* **ExecuteStreamCommand:** Python kolektör betiğini (zabbix-get-data.py) çalıştırır. Bu işlemcinin en büyük avantajı, betiğin standart çıktı (stdout) ve standart hata (stderr) akışlarını ayırmasıdır. Başarılı bir çalıştırmada betiğin ürettiği JSON verisi (stdout), bir sonraki işlemciye aktarılacak olan FlowFile'ın içeriği olurken, betik içindeki print() veya hata mesajları (stderr) doğrudan NiFi'ın loglarına yazılır. Bu, betiğin sağlığını ve olası hataları NiFi arayüzünden ayrılmadan izlemeyi mümkün kılar.  
* **SplitJson:** ExecuteStreamCommand'den gelen ve içinde yüzlerce kayıt barındıran tek bir FlowFile'ı alır. $.\* JsonPath ifadesi kullanılarak, dizideki her bir JSON nesnesi için ayrı bir FlowFile oluşturulur. Bu "böl ve yönet" yaklaşımı, sürecin dayanıklılığını artırır. Eğer sonraki adımlarda tek bir kaydın işlenmesinde hata oluşursa, bu sadece o kayda ait FlowFile'ı etkiler; geri kalan yüzlerce kayıt işlenmeye devam eder.  
* **EvaluateJsonPath:** Bu işlemci, veri akışını zenginleştirme (enrichment) görevini üstlenir. Bölünmüş olan her bir FlowFile'ın içeriğini okur ve $.data\_type ifadesiyle kaydın türünü (örn: pdu\_inventory, pdu\_breaker\_metrics) ayıklar. Bu değer, record.type adında yeni bir FlowFile özniteliğine (attribute) atanır. Bu sayede, bir sonraki RouteOnAttribute işlemcisinin karar verme mantığı basitleşir ve daha performanslı çalışır.  
* **RouteOnAttribute:** Akışın merkezi yönlendiricisidir. Gelen FlowFile'ları, record.type özniteliğinin değerine göre ilgili veritabanı tablosuna veri yazacak olan PutDatabaseRecord işlemcisine yönlendirir. Her bir data\_type için, örneğin panduit\_pdu\_inventory adında bir rota ve ${record.type:equals('pdu\_inventory')} şeklinde bir kural tanımlanır. Bu, veri akışının görsel olarak kolayca anlaşılmasını ve bakımının yapılmasını sağlar.  
* **PutDatabaseRecord:** Her bir rota için ayrı olarak yapılandırılmış olan bu işlemciler, gelen kaydı ilgili PostgreSQL tablosuna INSERT eder. Bu işlemciler, kaynakları verimli kullanmak için paylaşılan Controller Servislerini kullanır: DBCPConnectionPool servisi, veritabanı bağlantılarını sürekli açıp kapatmak yerine bir havuzda yöneterek performansı artırır. JsonTreeReader servisi ise gelen JSON verisini, tanımlanan Avro şemasına göre okuyup veritabanı tipleriyle eşleştirir.

### **4\. Kullanılan JSON Şeması ve Gerekçesi**

NiFi'nin PutDatabaseRecord işlemcisi, gelen veriyi veritabanı sütunlarıyla eşleştirmek için bir şemaya ihtiyaç duyar. Python betiği, tek bir çalıştırmada 10 farklı yapıya sahip kayıt ürettiği için, tüm olası alanları içeren birleşik bir Avro şeması oluşturulmuştur.

JsonTreeReader servisinde **"Use 'Schema Text' Property"** stratejisi benimsenmiştir. Bu stratejinin en büyük avantajı esnekliktir. Bir pdu\_inventory kaydı işlenirken, şemada tanımlı olan ancak o kayıtta bulunmayan breaker\_index gibi alanlar hata vermeden null olarak kabul edilir. Bu, heterojen veri yapılarını tek bir akışta, karmaşık dallanma mantıkları olmadan işlemek için en sağlam ve sürdürülebilir yöntemdir.

collection\_timestamp Alanı İçin Özel Yapılandırma:  
Bu alan, veri mühendisliğinde sıkça karşılaşılan bir dönüşüm problemine zarif bir çözüm sunar. Gelen JSON'daki veri yyyy-MM-dd'T'HH:mm:ss.SSSSSSXXX formatında bir string iken, veritabanındaki hedef sütun TIMESTAMPTZ tipindedir. Bu dönüşümü doğru bir şekilde yapmak için iki bileşen birlikte çalışır:

1. **Avro Şeması:** collection\_timestamp alanı logicalType: "timestamp-millis" olarak tanımlanır. Bu, NiFi'ye bu alanın anlamsal olarak bir zaman damgası olduğunu söyler.  
2. JsonTreeReader: Timestamp Format özelliğine yyyy-MM-dd'T'HH:mm:ss.SSSSSSXXX değeri girilir.  
   Bu iki ayar sayesinde JsonTreeReader, string formatındaki alanı okur, belirtilen formata göre ayrıştırır ve PutDatabaseRecord işlemcisine veritabanının anlayacağı doğru zaman damgası formatında iletir. Bu, saat dilimi (timezone) bilgilerinin kaybolmamasını ve veri bütünlüğünün korunmasını garanti altına alır.

#### **Kullanılan Avro Şeması:**

{  
  "namespace": "com.bulutistan.panduit.pdu",  
  "type": "record",  
  "name": "PanduitPduRecord",  
  "doc": "Zabbix'ten toplanan tüm Panduit PDU veri türlerini kapsayan birleşik şema.",  
  "fields": \[  
    {  
      "name": "collection\_timestamp",  
      "type": { "type": "long", "logicalType": "timestamp-millis" },  
      "doc": "Verinin toplandığı zaman damgası"  
    },  
    { "name": "pdu\_id", "type": "string", "doc": "Zabbix'teki host ID" },  
    { "name": "pdu\_name", "type": "string", "doc": "PDU cihazının adı" },  
    { "name": "zabbix\_host\_name", "type": "string", "doc": "Zabbix'te tanımlı host adı" },  
    { "name": "data\_type", "type": "string", "doc": "Kaydın türünü belirten alan (örn: pdu\_inventory)" },  
    { "name": "breaker\_count", "type": \["null", "string"\], "default": null },  
    { "name": "device\_model", "type": \["null", "string"\], "default": null },  
    { "name": "door\_count", "type": \["null", "string"\], "default": null },  
    { "name": "dry\_count", "type": \["null", "string"\], "default": null },  
    { "name": "firmware\_version", "type": \["null", "string"\], "default": null },  
    { "name": "hardware\_version", "type": \["null", "string"\], "default": null },  
    { "name": "hid\_count", "type": \["null", "string"\], "default": null },  
    { "name": "humidity\_count", "type": \["null", "string"\], "default": null },  
    { "name": "input\_phase\_count", "type": \["null", "string"\], "default": null },  
    { "name": "outlet\_count", "type": \["null", "string"\], "default": null },  
    { "name": "rope\_count", "type": \["null", "string"\], "default": null },  
    { "name": "spot\_count", "type": \["null", "string"\], "default": null },  
    { "name": "system\_name", "type": \["null", "string"\], "default": null },  
    { "name": "temperature\_count", "type": \["null", "string"\], "default": null },  
    { "name": "location", "type": \["null", "string"\], "default": null },  
    { "name": "rack\_id", "type": \["null", "string"\], "default": null },  
    { "name": "pdu\_index", "type": \["null", "string"\], "default": null },  
    { "name": "frequency", "type": \["null", "string"\], "default": null },  
    { "name": "frequency\_status", "type": \["null", "string"\], "default": null },  
    { "name": "phase\_total\_current", "type": \["null", "string"\], "default": null },  
    { "name": "power\_factor", "type": \["null", "string"\], "default": null },  
    { "name": "power\_va", "type": \["null", "string"\], "default": null },  
    { "name": "power\_var", "type": \["null", "string"\], "default": null },  
    { "name": "power\_watts", "type": \["null", "string"\], "default": null },  
    { "name": "resettable\_energy", "type": \["null", "string"\], "default": null },  
    { "name": "total\_energy", "type": \["null", "string"\], "default": null },  
    { "name": "function\_status", "type": \["null", "string"\], "default": null },  
    { "name": "function\_upstream\_status", "type": \["null", "string"\], "default": null },  
    { "name": "input", "type": \["null", "string"\], "default": null },  
    { "name": "operation\_status", "type": \["null", "string"\], "default": null },  
    { "name": "pdu\_status", "type": \["null", "string"\], "default": null },  
    { "name": "temperature\_scale", "type": \["null", "string"\], "default": null },  
    { "name": "door\_sensor\_11\_state", "type": \["null", "string"\], "default": null },  
    { "name": "door\_sensor\_11\_status", "type": \["null", "string"\], "default": null },  
    { "name": "door\_sensor\_12\_state", "type": \["null", "string"\], "default": null },  
    { "name": "door\_sensor\_12\_status", "type": \["null", "string"\], "default": null },  
    { "name": "dry\_sensor\_11\_status", "type": \["null", "string"\], "default": null },  
    { "name": "dry\_sensor\_12\_status", "type": \["null", "string"\], "default": null },  
    { "name": "rope\_sensor\_11\_state", "type": \["null", "string"\], "default": null },  
    { "name": "rope\_sensor\_11\_status", "type": \["null", "string"\], "default": null },  
    { "name": "rope\_sensor\_12\_state", "type": \["null", "string"\], "default": null },  
    { "name": "rope\_sensor\_12\_status", "type": \["null", "string"\], "default": null },  
    { "name": "spot\_sensor\_11\_state", "type": \["null", "string"\], "default": null },  
    { "name": "spot\_sensor\_11\_status", "type": \["null", "string"\], "default": null },  
    { "name": "spot\_sensor\_12\_state", "type": \["null", "string"\], "default": null },  
    { "name": "spot\_sensor\_12\_status", "type": \["null", "string"\], "default": null },  
    { "name": "breaker\_index", "type": \["null", "string"\], "default": null },  
    { "name": "breaker\_status", "type": \["null", "string"\], "default": null },  
    { "name": "current", "type": \["null", "string"\], "default": null },  
    { "name": "current\_percent\_load", "type": \["null", "string"\], "default": null },  
    { "name": "current\_rating", "type": \["null", "string"\], "default": null },  
    { "name": "voltage", "type": \["null", "string"\], "default": null },  
    { "name": "phase\_index", "type": \["null", "string"\], "default": null },  
    { "name": "outlet\_index", "type": \["null", "string"\], "default": null },  
    { "name": "control\_status", "type": \["null", "string"\], "default": null },  
    { "name": "control\_switchable", "type": \["null", "string"\], "default": null },  
    { "name": "watts", "type": \["null", "string"\], "default": null },  
    { "name": "wh", "type": \["null", "string"\], "default": null },  
    { "name": "hid\_index", "type": \["null", "string"\], "default": null },  
    { "name": "aisle", "type": \["null", "string"\], "default": null },  
    { "name": "auto\_lock\_time", "type": \["null", "string"\], "default": null },  
    { "name": "door\_open\_time", "type": \["null", "string"\], "default": null },  
    { "name": "handle\_operation", "type": \["null", "string"\], "default": null },  
    { "name": "hid\_aisle\_control", "type": \["null", "string"\], "default": null },  
    { "name": "max\_door\_open\_time", "type": \["null", "string"\], "default": null },  
    { "name": "mechanical\_lock", "type": \["null", "string"\], "default": null },  
    { "name": "user\_pin\_length", "type": \["null", "string"\], "default": null },  
    { "name": "user\_pin\_mode", "type": \["null", "string"\], "default": null },  
    { "name": "sensor\_id", "type": \["null", "string"\], "default": null },  
    { "name": "value", "type": \["null", "string"\], "default": null },  
    { "name": "status", "type": \["null", "string"\], "default": null },  
    { "name": "th\_status", "type": \["null", "string"\], "default": null }  
  \]  
}

### **5\. Veri Modeli: Tablolar ve Kolon Anlamları**

Veritabanı, envanter ve farklı metrik türlerini ayrı tablolarda saklayacak şekilde 10 ana tabloya bölünmüştür. Tüm tablolar panduit\_ öneki ile başlar. Bu modüler yaklaşım, sorgu performansını artırır ve veri modelini anlaşılır kılar.

#### **5.1. panduit\_pdu\_inventory**

* **Açıklama:** PDU cihazlarının konum, model ve versiyon gibi statik envanter bilgilerini saklar. Bu verinin zamanla nadiren değişmesi beklenir.  
* **data\_type:** pdu\_inventory  
* **CREATE TABLE Sorgusu:**  
  CREATE TABLE panduit\_pdu\_inventory (  
      id SERIAL PRIMARY KEY,  
      collection\_timestamp TIMESTAMPTZ NOT NULL,  
      pdu\_id INT NOT NULL,  
      pdu\_name VARCHAR(255),  
      zabbix\_host\_name VARCHAR(255),  
      location VARCHAR(50),  
      rack\_id VARCHAR(50),  
      pdu\_index VARCHAR(50),  
      device\_model VARCHAR(255),  
      firmware\_version VARCHAR(50),  
      hardware\_version VARCHAR(50),  
      system\_name VARCHAR(255),  
      breaker\_count INT,  
      outlet\_count INT,  
      door\_count INT,  
      dry\_count INT,  
      hid\_count INT,  
      humidity\_count INT,  
      input\_phase\_count INT,  
      rope\_count INT,  
      spot\_count INT,  
      temperature\_count INT,  
      CONSTRAINT uq\_panduit\_inventory\_pdu\_timestamp UNIQUE (pdu\_id, collection\_timestamp)  
  );  
  CREATE INDEX idx\_panduit\_inventory\_pdu\_id\_timestamp ON panduit\_pdu\_inventory (pdu\_id, collection\_timestamp DESC);

#### **5.2. panduit\_pdu\_metrics\_input**

* **Açıklama:** PDU ana girişine ait frekans, toplam akım, güç faktörü ve enerji tüketimi gibi zaman serisi metriklerini içerir.  
* **data\_type:** pdu\_input\_metrics  
* **CREATE TABLE Sorgusu:**  
  CREATE TABLE panduit\_pdu\_metrics\_input (  
      id SERIAL PRIMARY KEY,  
      collection\_timestamp TIMESTAMPTZ NOT NULL,  
      pdu\_id INT NOT NULL,  
      frequency INT,  
      frequency\_status INT,  
      phase\_total\_current INT,  
      power\_factor INT,  
      power\_va BIGINT,  
      power\_var BIGINT,  
      power\_watts BIGINT,  
      resettable\_energy BIGINT,  
      total\_energy BIGINT,  
      CONSTRAINT uq\_panduit\_input\_metrics\_pdu\_timestamp UNIQUE (pdu\_id, collection\_timestamp)  
  );  
  CREATE INDEX idx\_panduit\_input\_metrics\_pdu\_id\_timestamp ON panduit\_pdu\_metrics\_input (pdu\_id, collection\_timestamp DESC);

#### **5.3. panduit\_pdu\_metrics\_global**

* **Açıklama:** PDU'nun genel çalışma durumunu (pdu\_status) ve bağlı olan ancak ayrı bir metrik tablosu olmayan sensörlerin varlık durumlarını (door\_sensor\_11\_status vb.) içeren zaman serisi metriklerini barındırır.  
* **data\_type:** pdu\_global\_metrics  
* **CREATE TABLE Sorgusu:**  
  CREATE TABLE panduit\_pdu\_metrics\_global (  
      id SERIAL PRIMARY KEY,  
      collection\_timestamp TIMESTAMPTZ NOT NULL,  
      pdu\_id INT NOT NULL,  
      pdu\_status INT,  
      temperature\_scale INT,  
      door\_sensor\_11\_state INT,  
      door\_sensor\_11\_status INT,  
      door\_sensor\_12\_state INT,  
      door\_sensor\_12\_status INT,  
      dry\_sensor\_11\_status INT,  
      dry\_sensor\_12\_status INT,  
      rope\_sensor\_11\_state INT,  
      rope\_sensor\_11\_status INT,  
      rope\_sensor\_12\_state INT,  
      rope\_sensor\_12\_status INT,  
      spot\_sensor\_11\_state INT,  
      spot\_sensor\_11\_status INT,  
      spot\_sensor\_12\_state INT,  
      spot\_sensor\_12\_status INT,  
      CONSTRAINT uq\_panduit\_global\_metrics\_pdu\_timestamp UNIQUE (pdu\_id, collection\_timestamp)  
  );  
  CREATE INDEX idx\_panduit\_global\_metrics\_pdu\_id\_timestamp ON panduit\_pdu\_metrics\_global (pdu\_id, collection\_timestamp DESC);

... (Diğer 7 tablo için de benzer şekilde CREATE TABLE komutları eklenir) ...

### **6\. Tablolar Arası İlişkilendirme**

Veritabanı, bir zaman serisi veri ambarı (data warehouse) modeline benzediği için tablolar arasında FOREIGN KEY kısıtlamaları kasıtlı olarak kullanılmamıştır. Bu tasarım tercihinin temel nedenleri şunlardır:

* **Yazma Performansı:** Yüksek hacimli ve sık aralıklarla veri yazma (ingestion) operasyonlarında, FOREIGN KEY kontrolleri her bir INSERT işlemi için ek bir yük getirir ve süreci yavaşlatabilir. Kısıtlamaların olmaması, verinin veritabanına çok daha hızlı bir şekilde aktarılmasını sağlar.  
* **Esneklik:** Veri kaynağında (Zabbix) yaşanabilecek anlık sorunlar nedeniyle bazı metriklerin geçici olarak toplanamaması durumunda, FOREIGN KEY kısıtlamaları veri yazma işlemlerinin tamamen durmasına neden olabilir. Bu tasarım, her bir metrik türünün birbirinden bağımsız olarak veritabanına yazılabilmesine olanak tanır.  
* **Analitik Odak:** İlişkisel bütünlük, veri yazma anında değil, veri sorgulama (analiz) anında sağlanır.

**Anahtar Sütunlar:**

* pdu\_id: Tüm tablolarda bulunur ve verinin hangi PDU cihazına ait olduğunu belirten ana birleştirme anahtarıdır. Bu, farklı metrik tablolarındaki verileri tek bir PDU etrafında birleştirmeyi sağlar.  
* collection\_timestamp: Tüm tablolarda bulunur ve verinin hangi toplama anına ait olduğunu belirten bir "snapshot ID" görevi görür. Bu sütun, belirli bir zaman dilimindeki veya anındaki tüm sistem durumunu birleştirmek için kullanılır.

İlişki Örneği (Gelişmiş Sorgu):  
"FR2 lokasyonundaki, belirli bir modele (346-415V...) sahip tüm PDU'ların son 24 saatteki ortalama güç tüketimini (power\_watts) ve en yüksek devre kesici yükünü (current\_percent\_load) bulmak" gibi bir analiz için aşağıdaki gibi bir sorgu kullanılabilir:  
SELECT  
    inv.pdu\_name,  
    AVG(inp.power\_watts) AS avg\_power\_watts,  
    MAX(brk.current\_percent\_load) AS max\_breaker\_load\_percent  
FROM  
    panduit\_pdu\_inventory inv  
JOIN  
    panduit\_pdu\_metrics\_input inp ON inv.pdu\_id \= inp.pdu\_id AND inv.collection\_timestamp \= inp.collection\_timestamp  
JOIN  
    panduit\_pdu\_metrics\_breaker brk ON inv.pdu\_id \= brk.pdu\_id AND inv.collection\_timestamp \= brk.collection\_timestamp  
WHERE  
    inv.location \= 'FR2'  
    AND inv.device\_model \= '346-415V, 32A, 22.0kVA, 50/60Hz'  
    AND inv.collection\_timestamp \>= NOW() \- INTERVAL '24 hours'  
GROUP BY  
    inv.pdu\_name  
ORDER BY  
    avg\_power\_watts DESC;  
