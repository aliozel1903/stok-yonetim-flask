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
    git clone [https://github.com/KULLANICI_ADIN/REPO_ADIN.git](https://github.com/KULLANICI_ADIN/REPO_ADIN.git)
    cd REPO_ADIN
    ```

2.  **Gerekli kütüphaneleri yükleyin:**
    ```bash
    pip install flask flask-cors
    ```

3.  **Uygulamayı başlatın:**
    ```bash
    python app.py
    ```

4.  **Tarayıcıda açın:**
    Tarayıcınızda `http://localhost:5000` adresine gidin.
    * **Kullanıcı Adı:** admin
    * **Şifre:** admin123

## 📷 Ekran Görüntüleri

<img width="1914" height="908" alt="image" src="https://github.com/user-attachments/assets/1fc0e045-5795-4037-9908-f4e4cbfee32f" />
<img width="1911" height="909" alt="image" src="https://github.com/user-attachments/assets/485eea70-1433-469b-bda0-9c69f61e8ab2" />
<img width="1247" height="892" alt="image" src="https://github.com/user-attachments/assets/3d22abc9-51e1-411d-aa9f-0de67ad51469" />
<img width="1902" height="895" alt="image" src="https://github.com/user-attachments/assets/d7cccc05-56d3-4246-90e0-57ff02f79e81" />


---
