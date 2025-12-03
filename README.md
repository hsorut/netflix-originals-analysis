#  Netflix Originals — Veri Analizi

Bu proje, bir **Netflix Originals** CSV dosyasını analiz etmenizi sağlayan etkileşimli bir web uygulamasıdır.

Veriyi yükleyip, filtreleyerek sonuçları anında grafikler üzerinde görebilir ve kısa bir özet rapor indirebilirsiniz.

---

##  Hızlı Başlangıç

1.  **Gerekli kütüphaneleri kurun:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Uygulamayı çalıştırın:**
    ```bash
    streamlit run app.py
    ```

3.  **Tarayıcıda Veri Yükleyin:**
    * Açılan arayüzde, kenar çubuğundan (Sidebar) kendi CSV dosyanızı yükleyin.
    * Veya "Klasördeki `NetflixOriginals.csv` dosyasını kullan" seçeneğini işaretleyin.

---

##  Özellikler

* **Filtreleme:** Yıl aralığı, kategori, dil ve popüler türlere göre veriyi süzün.
* **Etkileşimli Grafikler:** Yıllara göre adet, popüler türler, içerik durumu (Bitti/Devam ediyor) ve bölüm uzunluklarını görün.
* **Rapor İndirme:** Filtrelenmiş verinin kısa bir özetini `.txt` formatında indirin.
* **Veri Önizleme:** Filtrelenmiş verinin ilk 50 satırını bir tabloda görün.

---

## 🗃️ Veri Gereksinimleri

Uygulamanın çalışması için CSV dosyanızda **en az** şu sütunlar olmalıdır:

* `Title` (İçerik adı)
* `Premiere` (Yayın tarihi, örn: `1-Feb-13`)

Diğer sütunlar (Genre, Language, Status vb.) varsa, ilgili grafikler ve filtreler otomatik olarak çalışacaktır.