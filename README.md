# Takbis - Tapu Kayıt Belgeleri Analiz ve Raporlama Yazılımı

Bu yazılım, tapu kayıt belgelerini (Takbis) otomatik olarak analiz eden, veritabanına kaydeden ve çeşitli formatlarda raporlar oluşturan bir araçtır. Gayrimenkul değerleme uzmanları için geliştirilmiştir.

## Özellikler

- 📄 Tapu belgelerini (PDF) otomatik analiz etme
- 💾 Verileri SQLite veritabanında saklama
- 📊 İpotek ve takyidat bilgilerini çıkarma
- 📝 Detaylı takyidat raporları oluşturma
- 📑 Çoklu taşınmaz analizi ve karşılaştırmalı raporlama
- 📈 Hisse tablosu Excel formatında dışa aktarma

## Kurulum

### Gereksinimler

- Python 3.7+
- PyQt5
- pdfplumber
- PyMuPDF (fitz)
- openpyxl
- sqlite3

### Kurulum Adımları

```bash
# Repoyu klonlayın
git clone https://github.com/quleman/takbis.git
cd takbis-analiz

# Gerekli kütüphaneleri yükleyin
pip install -r requirements.txt

# Uygulamayı çalıştırın
python takproson.py
```

## Kullanım

1. **Takbisleri Seç** butonuyla tapu belgelerini (PDF) seçin
2. **İçeri Aktar** butonuyla belgeleri işleyin
3. İşlenen tapu kayıtları sol panelde görüntülenir
4. **Tekli Raporla** veya **Çoklu Raporla** butonlarıyla raporlar oluşturun
5. Raporları metin (.txt) olarak kaydedin veya **Hisse Tablosu** butonuyla Excel formatında dışa aktarın

## Modüller

- `takproson.py` - Ana uygulama ve arayüz
- `basliklar.py` - Takbis başlıklarını analiz eder
- `ipotek_extractor.py` - İpotek bilgilerini çıkarır
- `takbis_inceleme.py` - Tek taşınmaz inceleme
- `takbisler_inceleme.py` - Çoklu taşınmaz inceleme
- `takbisduzenle.py` - Veri düzenleme işlemleri

## Katkıda Bulunma

1. Bu projeyi fork edin
2. Kendi feature branch'inizi oluşturun (`git checkout -b feature/AmazingFeature`)
3. Değişikliklerinizi commit edin (`git commit -m 'Add some AmazingFeature'`)
4. Branch'inize push edin (`git push origin feature/AmazingFeature`)
5. Pull Request oluşturun

## Lisans

Bu proje [MIT](LICENSE) lisansı altında lisanslanmıştır.

## İletişim

Ahmet Nazif UFUK - anufuk@gmail.com 

Proje Linki: [https://github.com/quleman/takbis.git]

--------------------  =  --------------------
Takbis Belgeleri İşleme / Analiz / Raporlama Uygulaması Kullanıcı Dokümantasyonu

 

1. Giriş

Bu uygulama, tapu ve kadastro belgelerinin (TAKBIS) analizini yapmak, verileri düzenlemek ve raporlamak için tasarlanmıştır. PDF formatındaki TAKBIS belgelerini işleyerek veritabanına kaydeder, gerekli düzenlemeleri yapar ve kullanıcıya detaylı raporlar sunar.

 

2. Sistem Gereksinimleri

Uygulamayı kullanabilmeniz için aşağıdaki gereksinimlerin karşılanması gerekir:

 

İşletim Sistemi: Windows

Kütüphaneler: (PyQt5 pdfplumber openpyxl PyMuPDF (fitz) sqlite3)

 

3.Veritabanı Oluşturma

Uygulama ilk açıldığında otomatik olarak veritabani.db adlı bir SQLite veritabanı oluşturur. Veritabanı, tüm analiz sonuçlarını ve kullanıcı verilerini saklar.

 

4. Arayüz ve İşlevler

Uygulama, kullanıcı dostu bir grafik arayüze sahiptir. Aşağıda, ana bileşenler ve işlevleri açıklanmaktadır.

 

4.1. Ana Ekran

Ana ekran, aşağıdaki bölümlerden oluşur:

 

Sol Panel (Ağaç Görünüm):

İşlenen TAKBIS belgelerini listeler.

Her bir taşınmaz için Ada/Parsel, nitelik, il/ilçe, mahalle ve taşınmaz numarası gibi bilgiler gösterilir.

Orta Panel (PDF İçeriği):

Seçilen TAKBIS belgesinin ham içeriğini görüntüler.

Sağ Panel (Analiz Sonuçları):

Seçilen belgenin analiz sonuçlarını ve raporlarını görüntüler.

Alt Panel (Durum Çubuğu):

İşlemlerin durumunu ve sistem mesajlarını gösterir.

4.2. Ana İşlevler

4.2.1. Takbis Belgelerini Seçme

Buton: 🔰 Takbisleri Seç

Açıklama: Birden fazla PDF dosyasını seçmek için kullanılır.

Adımlar:

"Takbisleri Seç" butonuna tıklayın.

Dosya seçici penceresinden PDF dosyalarını seçin.

Seçilen dosyalar sol panelde listelenir.

4.2.2. Toplu İşleme

Buton: 🟥 İçeri Aktar

Açıklama: Seçilen PDF dosyalarını toplu olarak işler.

Adımlar:

"İçeri Aktar" butonuna tıklayın.

İşleme başlamadan önce bir onay penceresi açılır.

İşlem tamamlandığında, başarılı ve başarısız dosyalar hakkında bilgi alırsınız.

4.2.3. Tekli Raporlama

Buton: 📄 Tekli Raporla

Açıklama: Seçilen bir TAKBIS belgesi için detaylı rapor oluşturur.

Adımlar:

Sol panelden bir taşınmaz seçin.

"Tekli Raporla" butonuna tıklayın.

Sağ panelde rapor görüntülenir.

4.2.4. Çoklu Raporlama

Buton: 📑 Çoklu Raporla

Açıklama: Tüm işlenen TAKBIS belgeleri için genel bir rapor oluşturur.

Adımlar:

"Çoklu Raporla" butonuna tıklayın.

Rapor sağ panelde görüntülenir.

4.2.5. Excel'e Aktarma

Buton: 📊 Hisse Tablosu

Açıklama: Seçilen taşınmaz için hisse dağılımını Excel tablosu olarak dışa aktarır.

Adımlar:

Sol panelden bir taşınmaz seçin.

"Hisse Tablosu" butonuna tıklayın.

Kaydetme konumunu seçin ve Excel dosyasını indirin.

4.2.6. Temizleme

Buton: 🧹 Temizle

Açıklama: Veritabanını ve arayüzü temizler.

Adımlar:

"Temizle" butonuna tıklayın.

Onay penceresinde "Evet" seçeneğini işaretleyin.

5. Hata Yönetimi ve Günlük Kayıtları

Uygulama, işlemler sırasında oluşan hataları günlüğe kaydeder.

Günlük dosyaları logs klasöründe bulunur ve her gün için ayrı bir dosya oluşturulur.

Günlük dosyalarını incelemek için:

logs klasörüne gidin.

İlgili günlük dosyasını metin editörüyle açın.

6. İpuçları ve En İyi Uygulamalar

PDF Formatı: TAKBIS belgeleri standart PDF formatında olmalıdır.

Veritabanı Yedekleme: Düzenli olarak veritabanını yedekleyin.

Hata Bildirimi: Bir hata alırsanız, lütfen günlük dosyalarını ve hatayı bildirin.

7. Destek ve Geri Bildirim

Herhangi bir sorunuz veya geri bildiriminiz varsa, lütfen aşağıdaki iletişim bilgilerini kullanarak bize ulaşın:

 

E-posta: anufuk@gmail.com

Versiyon: 1.0
