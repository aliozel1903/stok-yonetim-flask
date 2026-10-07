from flask import Flask, request, jsonify, g, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, timedelta
from threading import Lock
import click
import os
import secrets
import sqlite3
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "urunler.db")

MIN_PASSWORD_LENGTH = 12
LOGIN_MAX_FAILURES = 5        # IP başına izin verilen hatalı giriş
LOGIN_WINDOW_SECONDS = 60     # ... bu süre içinde

# Sunucunun dışarıya verdiği dosyalar. Klasördeki diğer dosyalar
# (app.py, urunler.db) asla sunulmaz.
PUBLIC_FILES = {"index.html", "login-bg-port.png"}

app = Flask(__name__, static_folder=None)

# Oturum çerezini imzalayan anahtar. Ortam değişkeninde yoksa her başlatmada
# rastgele üretilir: güvenlidir ama sunucu yeniden başlayınca oturumlar kapanır.
secret_key = os.environ.get("STOK_SECRET_KEY")
if not secret_key:
    secret_key = secrets.token_hex(32)
    print("Uyarı: STOK_SECRET_KEY tanımlı değil, geçici anahtar kullanılıyor "
          "(sunucu yeniden başlayınca oturumlar kapanır).")

app.config.update(
    SECRET_KEY=secret_key,
    SESSION_COOKIE_HTTPONLY=True,      # Çerez JavaScript ile okunamaz
    SESSION_COOKIE_SAMESITE="Lax",     # Başka sitelerden gelen isteklerde çerez gönderilmez
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
)

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
        CREATE TABLE IF NOT EXISTS kullanicilar (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            kullanici_adi TEXT NOT NULL UNIQUE,
            sifre_hash    TEXT NOT NULL
        );
    """)
    db.close()

# Tablolar "IF NOT EXISTS" ile oluşturulduğu için mevcut veritabanlarına
# da yeni kullanıcı tablosu eklenir.
init_db()


# ---------------------------------------------------------------------------
# Kimlik doğrulama
# ---------------------------------------------------------------------------

# Kullanıcı bulunamadığında da şifre kontrolü yapılır; böylece cevap süresinden
# bir kullanıcı adının var olup olmadığı anlaşılamaz.
_DUMMY_HASH = generate_password_hash(secrets.token_hex(16))

_failed_logins = {}
_failed_logins_lock = Lock()

def _too_many_failures(ip):
    now = time.monotonic()
    with _failed_logins_lock:
        recent = [t for t in _failed_logins.get(ip, []) if now - t < LOGIN_WINDOW_SECONDS]
        _failed_logins[ip] = recent
        return len(recent) >= LOGIN_MAX_FAILURES

def _record_failure(ip):
    with _failed_logins_lock:
        _failed_logins.setdefault(ip, []).append(time.monotonic())

def login_required(view):
    """API uçlarını yalnızca oturum açmış kullanıcılara açar."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "kullanici_id" not in session:
            return jsonify({"hata": "Bu işlem için giriş yapmanız gerekiyor."}), 401
        return view(*args, **kwargs)
    return wrapped

@app.route("/giris", methods=["POST"])
def giris():
    ip = request.remote_addr or "bilinmiyor"
    if _too_many_failures(ip):
        return jsonify({"hata": "Çok fazla hatalı deneme. Lütfen bir dakika sonra tekrar deneyin."}), 429

    data = request.get_json(silent=True) or {}
    kullanici_adi = str(data.get("kullanici_adi", "")).strip().lower()
    sifre = str(data.get("sifre", ""))

    user = get_db().execute(
        "SELECT id, kullanici_adi, sifre_hash FROM kullanicilar WHERE kullanici_adi = ?", (kullanici_adi,)
    ).fetchone()

    sifre_dogru = check_password_hash(user["sifre_hash"] if user else _DUMMY_HASH, sifre)

    if not user or not sifre_dogru:
        _record_failure(ip)
        return jsonify({"hata": "Hatalı kullanıcı adı veya şifre!"}), 401

    session.clear()  # Oturum sabitleme saldırısına karşı eski oturumu sil
    session.permanent = True
    session["kullanici_id"] = user["id"]
    session["kullanici_adi"] = user["kullanici_adi"]
    return jsonify({"durum": "ok", "kullanici_adi": user["kullanici_adi"]}), 200

@app.route("/cikis", methods=["POST"])
def cikis():
    session.clear()
    return jsonify({"durum": "ok"}), 200

@app.route("/oturum", methods=["GET"])
def oturum():
    if "kullanici_id" not in session:
        return jsonify({"giris_yapildi": False}), 200
    return jsonify({"giris_yapildi": True, "kullanici_adi": session["kullanici_adi"]}), 200

@app.cli.command("kullanici-olustur")
@click.argument("kullanici_adi")
@click.password_option("--sifre", prompt="Şifre", confirmation_prompt="Şifre (tekrar)")
def kullanici_olustur(kullanici_adi, sifre):
    """Kullanıcı oluşturur ya da var olanın şifresini değiştirir."""
    if len(sifre) < MIN_PASSWORD_LENGTH:
        raise click.ClickException(f"Şifre en az {MIN_PASSWORD_LENGTH} karakter olmalıdır.")

    kullanici_adi = kullanici_adi.strip().lower()
    db = sqlite3.connect(DB_PATH)
    db.execute(
        """INSERT INTO kullanicilar (kullanici_adi, sifre_hash) VALUES (?, ?)
           ON CONFLICT(kullanici_adi) DO UPDATE SET sifre_hash = excluded.sifre_hash""",
        (kullanici_adi, generate_password_hash(sifre)),
    )
    db.commit()
    db.close()
    click.echo(f"'{kullanici_adi}' kullanıcısı kaydedildi.")


# ---------------------------------------------------------------------------
# Arayüz dosyaları (yalnızca izin verilenler)
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")

@app.route("/<path:dosya>")
def public_file(dosya):
    if dosya not in PUBLIC_FILES:
        return jsonify({"hata": "bulunamadı"}), 404
    return send_from_directory(BASE_DIR, dosya)


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@app.route("/urunler", methods=["GET"])
@login_required
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
@login_required
def cop_kutusu():
    db = get_db()
    rows = db.execute("SELECT * FROM urunler WHERE silindi = 1").fetchall()
    silinenler = [dict(r) for r in rows]
    return jsonify(silinenler), 200

@app.route("/urunler", methods=["POST"])
@login_required
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
@login_required
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
@login_required
def urun_sil(uid):
    db = get_db()
    row = db.execute("SELECT * FROM urunler WHERE id=? AND silindi = 0", (uid,)).fetchone()
    if row is None:
        return jsonify({"hata": "ürün bulunamadı"}), 404

    db.execute("UPDATE urunler SET silindi = 1 WHERE id = ?", (uid,))
    db.commit()
    return jsonify({"durum": "soft delete ile silindi"}), 200

@app.route("/urunler/<int:uid>/geri-al", methods=["PATCH"])
@login_required
def urun_geri_al(uid):
    db = get_db()
    row = db.execute("SELECT * FROM urunler WHERE id=? AND silindi = 1", (uid,)).fetchone()
    if row is None:
        return jsonify({"hata": "silinen ürün bulunamadı"}), 404

    db.execute("UPDATE urunler SET silindi = 0 WHERE id = ?", (uid,))
    db.commit()
    return jsonify({"durum": "ürün geri getirildi"}), 200

@app.route("/hareketler", methods=["GET"])
@login_required
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
@login_required
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
    # Varsayılan olarak yalnızca bu bilgisayardan erişilir ve hata ayıklama
    # kapalıdır. Debug modu ağa açıkken Werkzeug konsolu üzerinden kod
    # çalıştırılabileceği için yalnızca STOK_DEBUG=1 ile açılır.
    app.run(host="127.0.0.1", port=5000, debug=os.environ.get("STOK_DEBUG") == "1")
