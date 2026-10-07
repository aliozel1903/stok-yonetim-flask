# 📦 Stok Yönetim Sistemi (Inventory Management System)

Bu proje, küçük ve orta ölçekli işletmelerin stok takibini kolaylaştırmak amacıyla geliştirilmiş **web tabanlı** bir envanter yönetim uygulamasıdır. **Python (Flask)** altyapısı ve **SQLite** veritabanı kullanılarak tasarlanmıştır.

## 🚀 Özellikler

* **Ürün Yönetimi:** Ürün ekleme, düzenleme ve silme işlemleri.
* **Güvenli Silme (Soft Delete):** Silinen ürünler veritabanından tamamen kalkmaz, "Çöp Kutusu"na taşınır ve istenirse geri getirilebilir.
* **Stok Hareketleri:** Her ürün için giriş-çıkış (Ekleme/Azaltma) işlemleri tarihçesiyle kaydedilir.
* **Dinamik Arama:** Ürünler arasında anlık filtreleme yapılabilir.
* **Karanlık Mod (Dark Mode):** Kullanıcı deneyimini artıran tema desteği.
* **Responsive Tasarım:** Mobil ve masaüstü uyumlu arayüz.
* **RESTful API:** Frontend ve Backend haberleşmesi JSON formatında API üzerinden sağlanır.

## 🛠️ Kullanılan Teknolojiler

* **Backend:** Python 3, Flask
* **Veritabanı:** SQLite (İlişkisel Veritabanı)
* **Frontend:** HTML5, CSS3, JavaScript (Fetch API)
* **Mimari:** MVC (Model-View-Controller) prensiplerine uygun yapı.

## 💻 Kurulum ve Çalıştırma

Projeyi yerel makinenizde çalıştırmak için aşağıdaki adımları izleyin:

1.  **Projeyi klonlayın:**
    ```bash
    git clone https://github.com/aliozel1903/stok-yonetim-flask.git
    cd stok-yonetim-flask
    ```

2.  **Gerekli kütüphaneyi yükleyin:**
    ```bash
    pip install flask
    ```

3.  **Bir kullanıcı oluşturun** (şifre en az 12 karakter, ekranda gösterilmeden sorulur):
    ```bash
    flask --app app kullanici-olustur admin
    ```

4.  **Uygulamayı başlatın:**
    ```bash
    python app.py
    ```

5.  **Tarayıcıda açın:** `http://127.0.0.1:5000`

    macOS'ta `localhost:5000` adresi AirPlay alıcısına gidebilir; bu yüzden `127.0.0.1` kullanın.

## 🔒 Güvenlik

* **Sunucu tarafında kimlik doğrulama:** Giriş bilgileri sunucuda kontrol edilir; tüm API uçları oturum açılmadan 401 döner.
* **Şifreler hash'lenir:** Veritabanında düz metin şifre tutulmaz (Werkzeug `scrypt`). Kodda varsayılan şifre yoktur.
* **Deneme yanılma koruması:** IP başına dakikada 5 hatalı giriş denemesinden sonra giriş geçici olarak kilitlenir.
* **Güvenli oturum çerezi:** `HttpOnly` ve `SameSite=Lax`; oturum 8 saat sonra sona erer. `STOK_SECRET_KEY` ortam değişkeni tanımlanmazsa her başlatmada rastgele anahtar üretilir.
* **XSS koruması:** Veritabanından gelen metinler ekrana basılmadan önce kaçışlanır.
* **Yalnızca gerekli dosyalar sunulur:** Uygulama kodu ve veritabanı dosyası tarayıcıdan indirilemez.
* **Güvenli varsayılanlar:** Sunucu yalnızca bu bilgisayardan erişilebilir (`127.0.0.1`); hata ayıklama modu kapalıdır ve yalnızca `STOK_DEBUG=1` ile açılır.

## 📷 Ekran Görüntüleri

<img width="1914" height="908" alt="image" src="https://github.com/user-attachments/assets/1fc0e045-5795-4037-9908-f4e4cbfee32f" />
<img width="1911" height="909" alt="image" src="https://github.com/user-attachments/assets/485eea70-1433-469b-bda0-9c69f61e8ab2" />
<img width="1247" height="892" alt="image" src="https://github.com/user-attachments/assets/3d22abc9-51e1-411d-aa9f-0de67ad51469" />
<img width="1902" height="895" alt="image" src="https://github.com/user-attachments/assets/d7cccc05-56d3-4246-90e0-57ff02f79e81" />


---
