from flask import Flask, request, jsonify, g
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime

DB_PATH = "urunler.db"

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH, check_same_thread=False)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS urunler (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            ad      TEXT    NOT NULL,
            miktar  INTEGER NOT NULL DEFAULT 0,
            birim   TEXT    NOT NULL DEFAULT 'adet',
            fiyat   REAL    NOT NULL DEFAULT 0,
            silindi INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS stok_hareketleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            urun_id INTEGER NOT NULL,
            hareket_tipi TEXT NOT NULL,
            miktar INTEGER NOT NULL,
            tarih TEXT NOT NULL,
            aciklama TEXT,
            FOREIGN KEY (urun_id) REFERENCES urunler(id)
        );
    """)
    db.close()

if not os.path.exists(DB_PATH):
    init_db()

@app.route("/urunler", methods=["GET"])
def urun_listele():
    db = get_db()
    arama = request.args.get("arama", "").strip()
    sql = "SELECT * FROM urunler WHERE silindi = 0"
    params = ()
    if arama:
        sql += " AND ad LIKE ?"
        params = (f"%{arama}%",)
    rows = db.execute(sql, params).fetchall()
    urunler = [dict(r) for r in rows]
    return jsonify(urunler), 200

@app.route("/copkutusu", methods=["GET"])
def cop_kutusu():
    db = get_db()
    rows = db.execute("SELECT * FROM urunler WHERE silindi = 1").fetchall()
    silinenler = [dict(r) for r in rows]
    return jsonify(silinenler), 200

@app.route("/urunler", methods=["POST"])
def urun_ekle():
    data = request.json or {}
    ad = data.get("ad")
    miktar = data.get("miktar", 0)
    birim = data.get("birim", "adet")
    fiyat = data.get("fiyat", 0)
    if not ad:
        return jsonify({"hata": "ad alanı zorunludur"}), 400
    if fiyat is None or fiyat == "":
        return jsonify({"hata": "fiyat alanı zorunludur"}), 400

    db = get_db()
    # Hatalı giriş kontrolü: Aynı isimde aktif ürün varsa ekleme
    var_mi = db.execute("SELECT COUNT(*) FROM urunler WHERE ad = ? AND silindi = 0", (ad,)).fetchone()[0]
    if var_mi > 0:
        return jsonify({"hata": "Aynı isimde başka bir ürün zaten mevcut."}), 400

    cur = db.execute(
        "INSERT INTO urunler (ad, miktar, birim, fiyat) VALUES (?, ?, ?, ?)",
        (ad, miktar, birim, fiyat),
    )
    db.commit()
    urun_id = cur.lastrowid
    if miktar > 0:
        db.execute(
            "INSERT INTO stok_hareketleri (urun_id, hareket_tipi, miktar, tarih, aciklama) VALUES (?, 'giris', ?, ?, ?)",
            (urun_id, miktar, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "İlk ekleme"),
        )
        db.commit()
    return jsonify({"durum": "ok", "id": urun_id}), 201

@app.route("/urunler/<int:uid>", methods=["PUT"])
def urun_guncelle(uid):
    data = request.json or {}
    yeni_ad = data.get("ad")
    yeni_fiyat = data.get("fiyat")
    aciklama_ek = data.get("aciklama", "")

    db = get_db()
    eski = db.execute("SELECT * FROM urunler WHERE id=? AND silindi = 0", (uid,)).fetchone()
    if eski is None:
        return jsonify({"hata": "ürün bulunamadı"}), 404

    # Hatalı giriş kontrolü: İsmi başka bir üründe kullanılıyorsa ve değiştiriliyorsa engelle
    if yeni_ad is not None and yeni_ad != eski["ad"]:
        var_mi = db.execute("SELECT COUNT(*) FROM urunler WHERE ad = ? AND silindi = 0 AND id != ?", (yeni_ad, uid)).fetchone()[0]
        if var_mi > 0:
            return jsonify({"hata": "Bu isimde başka bir ürün var."}), 400

    eski_ad = eski["ad"]
    eski_fiyat = eski["fiyat"]

    degisimler = []
    if yeni_ad is not None and yeni_ad != eski_ad:
        degisimler.append(f"İsim değişikliği: '{eski_ad}' → '{yeni_ad}'")
    if yeni_fiyat is not None and float(yeni_fiyat) != float(eski_fiyat):
        degisimler.append(f"Fiyat değişikliği: {eski_fiyat}₺ → {yeni_fiyat}₺")
    if not degisimler:
        degisimler.append("Değişiklik yapılmadı.")

    aciklama = "; ".join(degisimler)
    if aciklama_ek.strip():
        aciklama += f"\nAçıklama: {aciklama_ek.strip()}"

    db.execute(
        """
        UPDATE urunler
        SET ad     = COALESCE(?, ad),
            fiyat  = COALESCE(?, fiyat)
        WHERE id = ?
        """,
        (yeni_ad, yeni_fiyat, uid),
    )
    db.execute(
        "INSERT INTO stok_hareketleri (urun_id, hareket_tipi, miktar, tarih, aciklama) VALUES (?, 'duzenleme', 0, ?, ?)",
        (uid, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), aciklama),
    )
    db.commit()
    return jsonify({"durum": "güncellendi"}), 200

@app.route("/urunler/<int:uid>", methods=["DELETE"])
def urun_sil(uid):
    db = get_db()
    row = db.execute("SELECT * FROM urunler WHERE id=? AND silindi = 0", (uid,)).fetchone()
    if row is None:
        return jsonify({"hata": "ürün bulunamadı"}), 404

    db.execute("UPDATE urunler SET silindi = 1 WHERE id = ?", (uid,))
    db.commit()
    return jsonify({"durum": "soft delete ile silindi"}), 200

@app.route("/urunler/<int:uid>/geri-al", methods=["PATCH"])
def urun_geri_al(uid):
    db = get_db()
    row = db.execute("SELECT * FROM urunler WHERE id=? AND silindi = 1", (uid,)).fetchone()
    if row is None:
        return jsonify({"hata": "silinen ürün bulunamadı"}), 404

    db.execute("UPDATE urunler SET silindi = 0 WHERE id = ?", (uid,))
    db.commit()
    return jsonify({"durum": "ürün geri getirildi"}), 200

@app.route("/hareketler", methods=["GET"])
def hareket_liste():
    urun_id = request.args.get("urun_id")
    db = get_db()
    if urun_id:
        hareketler = db.execute("""
            SELECT h.*, u.ad as urun_adi 
            FROM stok_hareketleri h 
            JOIN urunler u ON h.urun_id = u.id
            WHERE h.urun_id = ?
            ORDER BY h.tarih DESC
        """, (urun_id,)).fetchall()
    else:
        hareketler = db.execute("""
            SELECT h.*, u.ad as urun_adi 
            FROM stok_hareketleri h 
            JOIN urunler u ON h.urun_id = u.id
            ORDER BY h.tarih DESC
        """).fetchall()
    return jsonify([dict(h) for h in hareketler]), 200

@app.route("/hareketler", methods=["POST"])
def hareket_ekle():
    data = request.json or {}
    urun_id = data.get("urun_id")
    hareket_tipi = data.get("hareket_tipi")
    miktar = data.get("miktar", 0)
    aciklama = data.get("aciklama", "")

    db = get_db()
    urun = db.execute("SELECT * FROM urunler WHERE id=? AND silindi=0", (urun_id,)).fetchone()
    if urun is None:
        return jsonify({"hata": "ürün bulunamadı"}), 404

    mevcut = urun["miktar"]
    yeni = mevcut + miktar if hareket_tipi == "giris" else mevcut - miktar
    if yeni < 0:
        return jsonify({"hata": "Stok yetersiz"}), 400

    db.execute("UPDATE urunler SET miktar=? WHERE id=?", (yeni, urun_id))
    db.execute(
        "INSERT INTO stok_hareketleri (urun_id, hareket_tipi, miktar, tarih, aciklama) VALUES (?, ?, ?, ?, ?)",
        (urun_id, hareket_tipi, miktar, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), aciklama),
    )
    db.commit()
    return jsonify({"durum": "kaydedildi", "yeni_miktar": yeni}), 201

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
