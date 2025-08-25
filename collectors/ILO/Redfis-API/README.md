# **HPE ILO \- Redfish API Veri Toplayıcı**

**Versiyon:** 2.0

**Tarih:** 19.07.2025

**Hazırlayan:** Can İlbey Sezgin

### **1\. Amaç ve Kapsam**

#### **1.1. Amaç**

Bu dokümanın temel amacı, HPE ProLiant sunucu altyapısının iLO (Integrated Lights-Out) yönetim arayüzlerinden, DMTF Redfish API standardı aracılığıyla kapsamlı donanım envanteri ile zaman serisi performans metriklerinin toplanmasını sağlayan sistemin düşük seviyeli teknik tasarımını detaylandırmaktır. Proje, veri merkezi operasyonlarının verimliliğini artırmayı, proaktif sorun tespiti sağlamayı, kapasite planlaması için güvenilir bir veri temeli oluşturmayı ve sunucu filosu genelinde konfigürasyon standartlarını denetlemeyi hedeflemektedir.

#### **1.2. Kapsam**

Bu tasarım, veri toplama ve işleme boru hattının (pipeline) tüm bileşenlerini kapsar:

* **Veri Kaynağı:** HPE ProLiant DL560 Gen10 sunucularının iLO 5 arayüzü.  
* **Veri Protokolü:** DMTF Redfish API.  
* **Veri Toplama:** Python ile geliştirilmiş bir kolektör betiği.  
* **Orkestrasyon:** Apache NiFi ile veri akışının yönetimi ve zamanlanması.  
* **Veri Depolama:** PostgreSQL üzerinde oluşturulmuş ilişkisel veritabanı yapısı.  
* **Veri Sunumu:** Sorgulamayı kolaylaştıran PostgreSQL VIEW'ları.

### **2\. API Kullanımı ve Veri Çekme Metodu**

#### **2.1. API Seçimi: Redfish**

Veri toplama için, modern, standartlara dayalı ve satıcıdan bağımsız bir arayüz olan Redfish API tercih edilmiştir. RESTful prensiplerine dayalı olması ve JSON formatında veri sunması, programatik entegrasyonu ve veri ayrıştırmayı (parsing) kolaylaştırmaktadır.

#### **2.2. Kimlik Doğrulama Metodu**

Redfish API, HTTP Basic Auth ve Session tabanlı kimlik doğrulama yöntemlerini desteklemektedir. Bu projede, her bir API çağrısında kullanıcı adı/şifre göndermenin getireceği ek yükü ve güvenlik riskini ortadan kaldırmak amacıyla **Session tabanlı kimlik doğrulama** yöntemi seçilmiştir.

**Süreç:** Betik, ilk olarak /redfish/v1/SessionService/Sessions endpoint'ine bir POST isteği göndererek bir X-Auth-Token ve oturum URI'si alır. Sonraki tüm GET istekleri, bu token'ı HTTP başlığında (Header) göndererek gerçekleştirilir. İşlem bittiğinde, oturum URI'sine bir DELETE isteği gönderilerek oturum güvenli bir şekilde sonlandırılır.

#### **2.3. Kullanılan API Endpoint'leri**

Keşif çalışmaları sonucunda, hedeflenen tüm verileri toplamak için aşağıdaki Redfish API kaynak URI'lerinin kullanılmasına karar verilmiştir:

| Endpoint | Açıklama |
| :---- | :---- |
| /redfish/v1/UpdateService/FirmwareInventory/ | Sunucudaki tüm donanım ve yazılım bileşenlerinin (BIOS, iLO, NIC, Disk vb.) firmware versiyonlarını listeler. |
| /redfish/v1/Systems/1/SmartStorage/ArrayControllers/{id}/DiskDrives/ | HPE'ye özel RAID denetleyicisine bağlı fiziksel disklerin envanterini ve detaylı sağlık metriklerini içerir. |
| /redfish/v1/Chassis/1/Power/ | Güç kaynaklarının (PSU) envanterini ve her bir PSU'nun anlık güç tüketimini barındırır. |
| /redfish/v1/Systems/1/EthernetInterfaces/ | Sunucudaki tüm ağ arayüzlerinin (NIC) envanterini (MAC, IP, Hız vb.) içerir. |
| /redfish/v1/Systems/1/Bios/ | Sunucunun tüm BIOS/UEFI ayarlarının tam dökümünü (Attributes nesnesi altında) sunar. |
| Diğerleri | Systems, Chassis, Processors, Memory, Thermal gibi standart endpoint'ler. |

### **3\. Orkestrasyon Yapısı: Apache NiFi**

Veri toplama sürecinin otomasyonu ve ölçeklenebilirliği, tasarlanmış bir Apache NiFi veri akışı ile sağlanmaktadır.

#### **3.1. Dinamik Cihaz Entegrasyonu**

Akışın ilk bölümü, birden fazla iLO cihazından dinamik olarak veri toplamayı sağlar:

1. **FetchFile:** İzlenecek tüm iLO cihazlarının IP adresi, kullanıcı adı ve şifre bilgilerini içeren bir konfigürasyon dosyasını (örn: CSV veya JSON) okur.  
2. **SplitText / SplitJson:** Konfigürasyon dosyasını, her bir cihaz için ayrı bir FlowFile olacak şekilde böler.  
3. **ExtractText / EvaluateJsonPath:** Her bir FlowFile'dan IP, kullanıcı adı ve şifre bilgilerini ayıklayarak bunları FlowFile özniteliklerine (attributes) atar.

#### **3.2. Ana Veri Toplama Akışı**

Yukarıdaki adımlardan geçen her bir FlowFile, aşağıdaki ana akışı tetikler:

1. **ExecuteStreamCommand:** Python kolektör betiğini çalıştırır. Betiğe, FlowFile özniteliklerinden okunan \--host, \--username ve \--password argümanlarını dinamik olarak geçirir. Betiğin standart çıktısından (stdout) gelen kapsamlı JSON verisi, bu işlemcinin çıktısı olur.  
2. **SplitJson:** Betikten gelen JSON dizisini, her bir envanter veya metrik kaydı için ayrı bir FlowFile olacak şekilde atomik kayıtlara ayrıştırır (JsonPath Expression: $.\*).  
3. **EvaluateJsonPath:** Her kaydın data\_type alanını okuyup bir FlowFile özniteliği olarak atar.  
4. **RouteOnAttribute:** Akışın merkezi yönlendiricisidir. FlowFile'ları, data\_type özniteliğinin değerine göre (inventory\_disk, metric\_cpu vb.) ilgili veritabanı yazıcısına giden doğru yola yönlendirir.  
5. **PutDatabaseRecord:** Her bir tablo için ayrı olarak yapılandırılmış olan bu işlemciler, gelen kaydı ilgili PostgreSQL tablosuna INSERT eder.

### **4\. Kullanılan JSON Şeması ve Gerekçesi**

NiFi'nin PutDatabaseRecord işlemcisi, gelen veriyi veritabanı sütunlarıyla eşleştirmek için bir şemaya ihtiyaç duyar.

**Karşılaşılan Sorun:** Python betiği, tek bir çalıştırmada çok farklı yapılara sahip (farklı alanlar içeren) 13'ten fazla data\_type üretir. NiFi'nin varsayılan **Infer Schema** (Şemayı Tahmin Et) stratejisi, akışın başında gördüğü ilk birkaç kayda göre bir şema oluşturur. Bu şemada bulunmayan alanlar (örn: psu\_id, cpu\_id), daha sonra gelen kayıtlarda mevcut olsalar bile görmezden gelinir. Bu durum, veritabanında null value in column ... violates not-null constraint hatalarına neden olmuştur.

**Uygulanan Çözüm:** Bu sorunu çözmek ve veri işlemeyi deterministik hale getirmek için JsonTreeReader servisinde **Use 'Schema Text' Property** stratejisi benimsenmiştir. Bu strateji ile, betiğin üretebileceği tüm olası alanları ve veri tiplerini (string, int, double vb.) içeren kapsamlı bir Avro şeması manuel olarak tanımlanmıştır. Bu sayede NiFi, her bir kaydı bu genel şemaya göre okur ve bir alana sahip olmayan kayıtlar için o alanı null olarak kabul eder, ancak var olan hiçbir alanı gözden kaçırmaz. Bu, heterojen veri yapılarını işlemede en sağlam ve güvenilir yöntemdir.

### **5\. Veri Modeli: Tablolar ve Kolon Anlamları**

Veritabanı, envanter ve metrik verilerini ayrı tablolarda saklayacak şekilde tasarlanmıştır.

#### **5.1. Envanter Tabloları**

**ilo\_inventory**

| Kolon Adı | Veri Tipi | Açıklama |
| :---- | :---- | :---- |
| id | serial4 | Kayıt için otomatik artan benzersiz birincil anahtar. |
| collection\_timestamp | timestamptz | Verinin toplandığı zaman damgası. |
| chassis\_serial\_number | varchar(255) | Sunucunun benzersiz seri numarası. |
| chassis\_model | varchar(255) | Sunucunun modeli (örn: ProLiant DL560 Gen10). |
| chassis\_manufacturer | varchar(255) | Sunucu üreticisi (örn: HPE). |
| system\_hostname | varchar(255) | İşletim sistemi tarafından tanımlanan sunucu adı. |
| system\_power\_state | varchar(50) | Sunucunun anlık güç durumu (örn: On, Off). |
| processor\_count | int4 | Sunucudaki fiziksel işlemci soketi sayısı. |
| processor\_model | varchar(255) | İşlemcilerin modeli. |
| processor\_status\_health | varchar(50) | İşlemci alt sisteminin genel sağlık durumu. |
| total\_system\_memory\_gib | int4 | Sunucudaki toplam bellek miktarı (GiB). |
| memory\_status\_health | varchar(50) | Bellek alt sisteminin genel sağlık durumu. |

**ilo\_inventory\_bios**

| Kolon Adı | Veri Tipi | Açıklama |
| :---- | :---- | :---- |
| collection\_timestamp | timestamptz | Verinin toplandığı zaman damgası. |
| chassis\_serial\_number | varchar(255) | Sunucunun benzersiz seri numarası. |
| workloadprofile | varchar(255) | Sunucunun performans profili ayarı. |
| prochyperthreading | varchar(50) | Intel Hyper-Threading teknolojisinin durumu. |
| procvirtualization | varchar(50) | Sanallaştırma teknolojisinin (VT-x) durumu. |
| powerregulator | varchar(50) | Güç yönetimi modu. |
| sriov | varchar(50) | SR-IOV sanallaştırma desteğinin durumu. |
| bootmode | varchar(50) | Sunucunun önyükleme modu (örn: Uefi). |

**ilo\_inventory\_disk**

| Kolon Adı | Veri Tipi | Açıklama |
| :---- | :---- | :---- |
| collection\_timestamp | timestamptz | Verinin toplandığı zaman damgası. |
| chassis\_serial\_number | varchar(255) | Sunucunun benzersiz seri numarası. |
| disk\_id | varchar(50) | Diskin denetleyici üzerindeki ID'si. |
| model | varchar(255) | Diskin tam modeli. |
| capacity\_bytes | int8 | Diskin bayt cinsinden kapasitesi. |
| protocol | varchar(50) | Bağlantı arayüzü (örn: SATA, SAS, NVMe). |
| media\_type | varchar(50) | Diskin medyasının türü (örn: HDD, SSD). |
| serial\_number | varchar(255) | Diskin benzersiz seri numarası. |
| status\_health | varchar(50) | Diskin genel sağlık durumu. |
| status\_state | varchar(50) | Diskin aktif durumu (örn: Enabled). |
| firmware\_version | varchar(50) | Diskin kendi firmware sürümü. |
| block\_size\_bytes | int4 | Diskin fiziksel sektör boyutu. |

**ilo\_inventory\_firmware**

| Kolon Adı | Veri Tipi | Açıklama |
| :---- | :---- | :---- |
| collection\_timestamp | timestamptz | Verinin toplandığı zaman damgası. |
| chassis\_serial\_number | varchar(255) | Sunucunun benzersiz seri numarası. |
| component\_name | varchar(255) | Firmware'in ait olduğu bileşenin adı. |
| version | varchar(255) | Bileşenin firmware versiyonu. |
| updateable | bool | Firmware'in güncellenebilir olup olmadığı. |
| device\_context | varchar(255) | Bileşenin fiziksel/mantıksal konumu. |

**ilo\_inventory\_memory**

| Kolon Adı | Veri Tipi | Açıklama |
| :---- | :---- | :---- |
| collection\_timestamp | timestamptz | Verinin toplandığı zaman damgası. |
| chassis\_serial\_number | varchar(255) | Sunucunun benzersiz seri numarası. |
| dimm\_id | varchar(50) | Bellek modülünün sistemdeki ID'si. |
| memory\_type | varchar(50) | Bellek modülünün tipi (örn: DRAM). |
| capacity\_mib | int4 | Bellek modülünün Megabyte cinsinden kapasitesi. |
| operating\_speed\_mhz | int4 | Anlık çalışma hızı (MHz). |
| manufacturer | varchar(255) | DIMM üreticisi. |
| part\_number | varchar(255) | DIMM parça numarası. |
| status\_health | varchar(50) | DIMM'in sağlık durumu. |
| status\_state | varchar(50) | DIMM'in aktif durumu. |

**ilo\_inventory\_nic**

| Kolon Adı | Veri Tipi | Açıklama |
| :---- | :---- | :---- |
| collection\_timestamp | timestamptz | Verinin toplandığı zaman damgası. |
| chassis\_serial\_number | varchar(255) | Sunucunun benzersiz seri numarası. |
| interface\_id | varchar(50) | Ağ arayüzünün sistemdeki ID'si. |
| name | varchar(255) | İşletim sistemi tarafından atanan arayüz adı. |
| mac\_address | varchar(50) | Arayüzün fiziksel MAC adresi. |
| speed\_mbps | int4 | Anlaşılmış bağlantı hızı (Mbps). |
| link\_status | varchar(50) | Fiziksel bağlantı durumu. |
| full\_duplex | bool | Bağlantının full-duplex modda olup olmadığı. |
| ipv4\_addresses | text | Arayüze atanmış IPv4 adreslerini içeren JSON metni. |
| status\_health | varchar(50) | Ağ arayüzünün sağlık durumu. |

**ilo\_inventory\_processor**

| Kolon Adı | Veri Tipi | Açıklama |
| :---- | :---- | :---- |
| collection\_timestamp | timestamptz | Verinin toplandığı zaman damgası. |
| chassis\_serial\_number | varchar(255) | Sunucunun benzersiz seri numarası. |
| processor\_id | varchar(50) | İşlemcinin sistemdeki ID'si. |
| model | varchar(255) | İşlemcinin tam modeli. |
| max\_speed\_mhz | int4 | İşlemcinin maksimum saat hızı (MHz). |
| total\_cores | int4 | İşlemcideki fiziksel çekirdek sayısı. |
| total\_threads | int4 | İşlemcideki mantıksal çekirdek sayısı. |
| status\_health | varchar(50) | İşlemcinin sağlık durumu. |
| status\_state | varchar(50) | İşlemcinin aktif durumu. |

**ilo\_inventory\_psu**

| Kolon Adı | Veri Tipi | Açıklama |
| :---- | :---- | :---- |
| collection\_timestamp | timestamptz | Verinin toplandığı zaman damgası. |
| chassis\_serial\_number | varchar(255) | Sunucunun benzersiz seri numarası. |
| psu\_id | varchar(50) | Güç kaynağının yuva (bay) numarası. |
| model | varchar(255) | Güç kaynağının model numarası. |
| serial\_number | varchar(255) | Güç kaynağının seri numarası. |
| part\_number | varchar(255) | Güç kaynağının parça numarası. |
| firmware\_version | varchar(50) | Güç kaynağının firmware sürümü. |
| power\_capacity\_watts | int4 | Güç kaynağının maksimum kapasitesi (Watt). |
| status\_health | varchar(50) | Güç kaynağının sağlık durumu. |

#### 

#### 

#### **5.2. Metrik Tabloları**

**ilo\_metrics\_cpu**

| Kolon Adı | Veri Tipi | Açıklama |
| :---- | :---- | :---- |
| collection\_timestamp | timestamptz | Ölçümün yapıldığı zaman damgası. |
| chassis\_serial\_number | varchar(255) | Sunucunun benzersiz seri numarası. |
| cpu\_id | int4 | Metriğin ait olduğu işlemcinin ID'si. |
| power\_watts | float4 | İşlemcinin anlık güç tüketimi. |
| frequency\_mhz | float4 | İşlemcinin anlık ortalama çalışma frekansı. |

**ilo\_metrics\_disk**

| Kolon Adı | Veri Tipi | Açıklama |
| :---- | :---- | :---- |
| collection\_timestamp | timestamptz | Ölçümün yapıldığı zaman damgası. |
| chassis\_serial\_number | varchar(255) | Sunucunun benzersiz seri numarası. |
| disk\_id | varchar(50) | Metriğin ait olduğu diskin ID'si. |
| power\_on\_hours | int4 | Diskin toplam çalıştığı saat miktarı. |
| temperature\_celsius | float4 | Diskin anlık sıcaklığı (°C). |
| endurance\_utilization\_percent | float4 | SSD'nin yıpranma payı kullanım yüzdesi. |
| uncorrected\_read\_errors | int4 | Düzeltilemeyen okuma hataları sayısı. |
| uncorrected\_write\_errors | int4 | Düzeltilemeyen yazma hataları sayısı. |

**ilo\_metrics\_fan**

| Kolon Adı | Veri Tipi | Açıklama |
| :---- | :---- | :---- |
| collection\_timestamp | timestamptz | Ölçümün yapıldığı zaman damgası. |
| chassis\_serial\_number | varchar(255) | Sunucunun benzersiz seri numarası. |
| fan\_name | varchar(255) | Fanın sistemdeki adı (örn: Fan 1). |
| reading\_percent | float4 | Fanın maksimum hızına oranla anlık çalışma yüzdesi. |
| reading\_units | varchar(50) | Okunan değerin birimi (örn: Percent). |
| status\_health | varchar(50) | Fanın sağlık durumu. |

**ilo\_metrics\_power**

| Kolon Adı | Veri Tipi | Açıklama |
| :---- | :---- | :---- |
| collection\_timestamp | timestamptz | Ölçümün yapıldığı zaman damgası. |
| chassis\_serial\_number | varchar(255) | Sunucunun benzersiz seri numarası. |
| psu\_id | int4 | Metriğin ait olduğu güç kaynağının ID'si. |
| power\_output\_watts | float4 | Güç kaynağının anlık olarak sağladığı güç (Watt). |

**ilo\_metrics\_system**

| Kolon Adı | Veri Tipi | Açıklama |
| :---- | :---- | :---- |
| collection\_timestamp | timestamptz | Ölçümün yapıldığı zaman damgası. |
| chassis\_serial\_number | varchar(255) | Sunucunun benzersiz seri numarası. |
| cpu\_utilization\_percent | float4 | Tüm işlemcilerin ortalama anlık kullanım yüzdesi. |
| memory\_bus\_utilization\_percent | float4 | Bellek veriyolunun anlık kullanım yüzdesi. |

**ilo\_metrics\_temperature**

| Kolon Adı | Veri Tipi | Açıklama |
| :---- | :---- | :---- |
| collection\_timestamp | timestamptz | Ölçümün yapıldığı zaman damgası. |
| chassis\_serial\_number | varchar(255) | Sunucunun benzersiz seri numarası. |
| sensor\_name | varchar(255) | Sıcaklık sensörünün adı (örn: 01-Inlet Ambient). |
| reading\_celsius | float4 | Sensörün okuduğu anlık sıcaklık değeri (°C). |
| status\_health | varchar(50) | Sensörün sağlık durumu. |

### 

### **6\. Tablolar Arası İlişkilendirme**

Veritabanındaki tablolar arasında doğrudan FOREIGN KEY kısıtlamaları kullanılmamıştır, çünkü bu bir zaman serisi veri ambarı (data warehouse) modelidir. İlişkilendirme, sorgu zamanında JOIN operasyonları ile gerçekleştirilir.

**Anahtar Sütunlar:**

* **chassis\_serial\_number**: Tüm tablolarda bulunur ve verinin hangi fiziksel sunucuya ait olduğunu belirtir.  
* **collection\_timestamp**: Tüm tablolarda bulunur ve verinin hangi toplama anına ait olduğunu belirten bir "snapshot ID" görevi görür.

**İlişki Örnekleri:**

* Belirli bir sunucunun, belirli bir zamandaki tüm disk envanterini ve metriklerini birleştirmek için ilo\_inventory\_disk ve ilo\_metrics\_disk tabloları chassis\_serial\_number ve collection\_timestamp üzerinden JOIN edilir.  
* Bir sunucunun genel envanter bilgisi ile BIOS ayarlarını birleştirmek için ilo\_inventory ve ilo\_inventory\_bios tabloları aynı anahtarlar üzerinden birleştirilir.

### **7\. Veri Görünümleri (Views) ve Amaçları**

Ham veriyi anlamlı bilgilere dönüştürmek ve sorgulamayı basitleştirmek için üç ana VIEW oluşturulmuştur:

* **v\_server\_summary\_current**: DISTINCT ON (chassis\_serial\_number) kullanarak her sunucunun en son envanter ve metrik kayıtlarını birleştirir. Bu, anlık izleme panelleri için ideal, her zaman güncel bir özet sunar.  
* **v\_component\_inventory\_current**: UNION ALL kullanarak farklı envanter tablolarındaki (CPU, RAM, Disk vb.) verileri standart bir formatta bir araya getirir. Bu, "Bana X sunucusundaki tüm donanımları listele" gibi varlık yönetimi sorgularını basitleştirir.  
* **v\_bios\_settings\_current**: Her sunucunun en son kaydedilen BIOS ayarlarını, her ayar bir sütun olacak şekilde geniş formatta gösterir. Bu, "Sanallaştırma profili X olmayan sunucuları bul" gibi konfigürasyon denetim sorgularını mümkün kılar.

### 

### **8\. Gelecek Geliştirmeleri ve Düzenlenecek Noktalar**

Bu sistem, modüler yapısı sayesinde kolayca genişletilebilir. Gelecekteki geliştirmeler için aşağıdaki adımlar izlenmelidir:

1. **Python Betiğini Güncelleme:** Yeni bir veri tipi toplamak için main() fonksiyonuna yeni bir blok eklenir. Bu blok, ilgili Redfish endpoint'ini sorgular ve yeni bir data\_type ile etiketlenmiş JSON kayıtları üretir.  
2. **PostgreSQL Tablosu Oluşturma:** Yeni veri tipini saklamak için CREATE TABLE komutu ile yeni bir veritabanı tablosu oluşturulur.  
3. **NiFi Akışını Genişletme:**  
   * RouteOnAttribute işlemcisine, yeni data\_type için bir yönlendirme kuralı eklenir.  
   * Bu yeni rotanın sonuna, yeni oluşturulan tabloya veri yazacak bir PutDatabaseRecord işlemcisi eklenir.  
   * JsonTreeReader hizmetindeki Schema Text alanına, yeni JSON kayıtlarının içereceği yeni alanlar eklenir.

Bu adımlar izlenerek, sisteme Mantıksal Diskler, Detaylı Güç Metrikleri veya Sistem Olay Logları gibi yeni veri setleri kolayca entegre edilebilir.