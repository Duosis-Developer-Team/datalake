### Dokümantasyon Planı ve Kuralları

Amaç: Müşteri odaklı, kısa ve güncel dokümantasyon.

#### Dosya Yapısı

- `README.md`: Ürün özeti ve hızlı bağlantılar
- `docs/architecture-*.md`: Mimari (overview/etl/database)
- `docs/collectors-purpose-cards.md`: Kolektör amaç kartları
- `docs/change-requests/CR-YYYYNN.md`: Talep ve onay kayıtları (opsiyonel)
- `docs/release-notes/yyyymmdd.md`: Sürüm notları (iş etkisi odaklı)
- `docs/runbook/*.md`: Sağlık kontrolü ve sorun giderme

#### Yazım İlkeleri

- Kısa cümleler, iş faydası önce
- Türkçe içerik; kod ve dosya adları İngilizce
- Her değişiklikte `CHANGELOG.md` ve ilgili doküman linki

#### Knowledge base

- Cross-module collector catalog (compliance, GUI mapping): see `datalake-platform-knowledge-base/wiki/datalake-collectors/00-Index.md` in the platform monorepo.

#### Sürdürme

- Sorumlular: Kolektör bazlı CODEOWNERS
- İnceleme: PR içinde dokümantasyon kontrolü zorunlu
- Versiyonlama: SemVer + sürüm notu

