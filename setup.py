# -*- coding: utf-8 -*-
"""
Üniversite Kulüp Yönetim Sistemi - SQL Server (SSMS) Kurulum Scripti (setup.py)
Bu script projenin tüm yapısını (Python, HTML, CSS ve Microsoft SQL Server Veritabanı) oluşturur
ve Masaüstünüze hızlı başlatma kısayolu ekler.
"""

import os
import sys

# Proje dizini (setup.py'nin bulunduğu dizin)
PROJE_DIZINI = os.path.abspath(os.path.dirname(__file__))
TEMPLATES_DIZINI = os.path.join(PROJE_DIZINI, 'templates')
STATIC_DIZINI = os.path.join(PROJE_DIZINI, 'static')
CSS_DIZINI = os.path.join(STATIC_DIZINI, 'css')

print("--------------------------------------------------")
print("Üniversite Kulüp Yönetim Sistemi Kurulumu (SQL Server)")
print("--------------------------------------------------")
print(f"Hedef Proje Dizini: {PROJE_DIZINI}")

# 1. Dizin Yapısının Oluşturulması
print("\n[1/6] Dizinler oluşturuluyor...")
os.makedirs(TEMPLATES_DIZINI, exist_ok=True)
os.makedirs(CSS_DIZINI, exist_ok=True)
print("Dizinler başarıyla oluşturuldu.")

# 2. Flask Python Kodunun Yazılması (app.py)
print("\n[2/6] Flask uygulama dosyası (app.py) oluşturuluyor...")

APP_PY_ICERIK = """# -*- coding: utf-8 -*-
import os
import pyodbc
import webbrowser
from functools import wraps
from threading import Timer
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
# Flask oturum yönetimi için gizli anahtar
app.secret_key = 'kulup_sistemi_gizli_anahtar_12345'

# VERİTABANI BAĞLANTI AYARLARI
# Kendi bilgisayarınızdaki SQL Server durumuna göre sunucu adını değiştirebilirsiniz.
# Genellikle '.' veya 'localhost' veya '.\\SQLEXPRESS' kullanılır.
SQL_SERVER_NAME = 'DESKTOP-OGPL55D\\\\SQLEXPRESS'
SQL_DATABASE_NAME = 'club_system'

# sqlite3.Row davranışını pyodbc ile taklit etmek için sarmalayıcı (wrapper) sınıflar
class DictCursor:
    def __init__(self, cursor):
        self.cursor = cursor
    def execute(self, sql, params=()):
        self.cursor.execute(sql, params)
        return self
    def fetchall(self):
        if not self.cursor.description:
            return []
        cols = [col[0] for col in self.cursor.description]
        return [dict(zip(cols, row)) for row in self.cursor.fetchall()]
    def fetchone(self):
        row = self.cursor.fetchone()
        if not row:
            return None
        cols = [col[0] for col in self.cursor.description]
        return dict(zip(cols, row))

class ConnectionWrapper:
    def __init__(self, conn):
        self.conn = conn
    def execute(self, sql, params=()):
        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        return DictCursor(cursor)
    def commit(self):
        self.conn.commit()
    def close(self):
        self.conn.close()

def get_db_connection():
    \"\"\"SQL Server veritabanı bağlantısı oluşturur (Windows Authentication kullanarak).\"\"\"
    try:
        conn = pyodbc.connect(
            f'Driver={{SQL Server}};'
            f'Server={SQL_SERVER_NAME};'
            f'Database={SQL_DATABASE_NAME};'
            f'Trusted_Connection=yes;'
        )
        return ConnectionWrapper(conn)
    except Exception as e:
        # local veya SQLEXPRESS denemesi yap
        try:
            conn = pyodbc.connect(
                f'Driver={{SQL Server}};'
                f'Server=.\\\\SQLEXPRESS;'
                f'Database={SQL_DATABASE_NAME};'
                f'Trusted_Connection=yes;'
            )
            return ConnectionWrapper(conn)
        except Exception:
            raise ConnectionError(
                "SQL Server'a bağlanılamadı! Lütfen sunucu servislerinizin çalıştığından ve "
                f"app.py içerisindeki SQL_SERVER_NAME değişkeninin doğruluğundan emin olun. Hata: {e}"
            )

# Giriş Kontrol Dekoratörü
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'kullanici_id' not in session:
            flash('Bu işlemi gerçekleştirmek için lütfen önce giriş yapın.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Kulüp Yetkisi Kontrolü
def has_club_permission(kulup_id):
    if session.get('rol') == 'super':
        return True
    if session.get('rol') == 'kulup' and session.get('kulup_id') == int(kulup_id):
        return True
    return False

# ----------------- WEB ROTASYONLARI (ROUTES) -----------------

# Ana Sayfa (Kulüp Listesi)
@app.route('/')
def index():
    conn = get_db_connection()
    
    kulupler = conn.execute('''
        SELECT k.*, 
               (SELECT COUNT(*) FROM ogrenci WHERE kulup_id = k.id) as ogrenci_sayisi,
               (SELECT COUNT(*) FROM etkinlik WHERE kulup_id = k.id) as etkinlik_sayisi
        FROM kulup k
    ''').fetchall()
    
    # Genel sistem istatistikleri (SQL Server'da isimsiz kolonlar boş string olarak döner)
    stats = {
        'kulup_sayisi': conn.execute('SELECT COUNT(*) FROM kulup').fetchone()[''],
        'ogrenci_sayisi': conn.execute('SELECT COUNT(*) FROM ogrenci').fetchone()[''],
        'etkinlik_sayisi': conn.execute('SELECT COUNT(*) FROM etkinlik').fetchone()[''],
        'gorev_sayisi': conn.execute('SELECT COUNT(*) FROM gorev').fetchone()['']
    }
    
    conn.close()
    return render_template('index.html', kulupler=kulupler, stats=stats)

# Yönetici Girişi
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'kullanici_id' in session:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        kullanici_adi = request.form['kullanici_adi']
        sifre = request.form['sifre']
        
        conn = get_db_connection()
        yonetici = conn.execute(
            'SELECT * FROM yonetici WHERE kullanici_adi = ? AND sifre = ?', 
            (kullanici_adi, sifre)
        ).fetchone()
        conn.close()
        
        if yonetici:
            session['kullanici_id'] = yonetici['id']
            session['kullanici_adi'] = yonetici['kullanici_adi']
            session['rol'] = yonetici['rol']
            session['kulup_id'] = yonetici['kulup_id']
            flash(f'Hoş geldiniz, {kullanici_adi}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Kullanıcı adı veya şifre hatalı!', 'danger')
            
    return render_template('login.html')

# Çıkış Yap
@app.route('/logout')
def logout():
    session.clear()
    flash('Başarıyla çıkış yapıldı.', 'success')
    return redirect(url_for('index'))

# Kulüp Detay Sayfası
@app.route('/kulup/<int:id>')
def kulup_detay(id):
    conn = get_db_connection()
    kulup = conn.execute('SELECT * FROM kulup WHERE id = ?', (id,)).fetchone()
    
    if not kulup:
        flash('Aradığınız kulüp bulunamadı!', 'danger')
        conn.close()
        return redirect(url_for('index'))
        
    ogrenciler = conn.execute('SELECT * FROM ogrenci WHERE kulup_id = ?', (id,)).fetchall()
    etkinlikler = conn.execute('SELECT * FROM etkinlik WHERE kulup_id = ?', (id,)).fetchall()
    gorevler = conn.execute('SELECT * FROM gorev WHERE kulup_id = ?', (id,)).fetchall()
    conn.close()
    
    is_admin = False
    if 'kullanici_id' in session:
        is_admin = has_club_permission(id)
        
    return render_template(
        'kulup_detay.html', 
        kulup=kulup, 
        ogrenciler=ogrenciler, 
        etkinlikler=etkinlikler, 
        gorevler=gorevler, 
        is_admin=is_admin
    )

# ----------------- TÜM LİSTELERİ GÖSTEREN GENEL ROTALAR -----------------

@app.route('/ogrenciler')
def ogrenciler():
    conn = get_db_connection()
    ogrenciler_list = conn.execute('''
        SELECT o.*, k.ad as kulup_ad
        FROM ogrenci o
        LEFT JOIN kulup k ON o.kulup_id = k.id
        ORDER BY o.ad ASC
    ''').fetchall()
    
    yonetilen_kulupler = []
    if 'kullanici_id' in session:
        if session.get('rol') == 'super':
            yonetilen_kulupler = [o['kulup_id'] for o in ogrenciler_list if o['kulup_id']]
        else:
            yonetilen_kulupler = [session.get('kulup_id')]
            
    conn.close()
    return render_template('ogrenciler.html', ogrenciler=ogrenciler_list, yonetilen_kulupler=yonetilen_kulupler)

@app.route('/etkinlikler')
def etkinlikler():
    conn = get_db_connection()
    etkinlikler_list = conn.execute('''
        SELECT e.*, k.ad as kulup_ad
        FROM etkinlik e
        JOIN kulup k ON e.kulup_id = k.id
        ORDER BY e.tarih ASC
    ''').fetchall()
    
    yonetilen_kulupler = []
    if 'kullanici_id' in session:
        if session.get('rol') == 'super':
            yonetilen_kulupler = [e['kulup_id'] for e in etkinlikler_list]
        else:
            yonetilen_kulupler = [session.get('kulup_id')]
            
    conn.close()
    return render_template('etkinlikler.html', etkinlikler=etkinlikler_list, yonetilen_kulupler=yonetilen_kulupler)

@app.route('/gorevler')
def gorevler():
    conn = get_db_connection()
    gorevler_list = conn.execute('''
        SELECT g.*, k.ad as kulup_ad
        FROM gorev g
        JOIN kulup k ON g.kulup_id = k.id
        ORDER BY g.son_tarih ASC
    ''').fetchall()
    
    yonetilen_kulupler = []
    if 'kullanici_id' in session:
        if session.get('rol') == 'super':
            yonetilen_kulupler = [g['kulup_id'] for g in gorevler_list]
        else:
            yonetilen_kulupler = [session.get('kulup_id')]
            
    conn.close()
    return render_template('gorevler.html', gorevler=gorevler_list, yonetilen_kulupler=yonetilen_kulupler)

# ----------------- CRUD İŞLEMLERİ (KULÜP) -----------------

@app.route('/kulup/ekle', methods=['GET', 'POST'])
@login_required
def kulup_ekle():
    if session.get('rol') != 'super':
        flash('Bu işlem için yetkiniz yok!', 'danger')
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        ad = request.form['ad']
        aciklama = request.form['aciklama']
        kurulus_tarihi = request.form['kurulus_tarihi']
        
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO kulup (ad, aciklama, kurulus_tarihi) VALUES (?, ?, ?)',
            (ad, aciklama, kurulus_tarihi)
        )
        conn.commit()
        conn.close()
        flash('Yeni kulüp başarıyla eklendi.', 'success')
        return redirect(url_for('index'))
        
    return render_template('kulup_form.html', kulup=None)

@app.route('/kulup/duzenle/<int:id>', methods=['GET', 'POST'])
@login_required
def kulup_duzenle(id):
    if session.get('rol') != 'super':
        flash('Bu işlem için yetkiniz yok!', 'danger')
        return redirect(url_for('index'))
        
    conn = get_db_connection()
    kulup = conn.execute('SELECT * FROM kulup WHERE id = ?', (id,)).fetchone()
    
    if not kulup:
        flash('Kulüp bulunamadı!', 'danger')
        conn.close()
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        ad = request.form['ad']
        aciklama = request.form['aciklama']
        kurulus_tarihi = request.form['kurulus_tarihi']
        
        conn.execute(
            'UPDATE kulup SET ad = ?, aciklama = ?, kurulus_tarihi = ? WHERE id = ?',
            (ad, aciklama, kurulus_tarihi, id)
        )
        conn.commit()
        conn.close()
        flash('Kulüp bilgileri başarıyla güncellendi.', 'success')
        return redirect(url_for('index'))
        
    conn.close()
    return render_template('kulup_form.html', kulup=kulup)

@app.route('/kulup/sil/<int:id>')
@login_required
def kulup_sil(id):
    if session.get('rol') != 'super':
        flash('Bu işlem için yetkiniz yok!', 'danger')
        return redirect(url_for('index'))
        
    conn = get_db_connection()
    conn.execute('DELETE FROM kulup WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Kulüp ve kulübe ait tüm veriler silindi.', 'success')
    return redirect(url_for('index'))

# ----------------- CRUD İŞLEMLERİ (ÖĞRENCİ) -----------------

@app.route('/ogrenci/ekle', methods=['GET', 'POST'])
@login_required
def ogrenci_ekle_genel():
    if session.get('rol') != 'super':
        flash('Bu işlem için yetkiniz yok!', 'danger')
        return redirect(url_for('index'))
        
    conn = get_db_connection()
    kulupler = conn.execute('SELECT * FROM kulup').fetchall()
    
    if request.method == 'POST':
        ad = request.form['ad']
        soyad = request.form['soyad']
        eposta = request.form['eposta']
        telefon = request.form['telefon']
        kulup_id = request.form['kulup_id']
        
        conn.execute(
            'INSERT INTO ogrenci (ad, soyad, eposta, telefon, kulup_id) VALUES (?, ?, ?, ?, ?)',
            (ad, soyad, eposta, telefon, kulup_id)
        )
        conn.commit()
        conn.close()
        flash('Yeni üye başarıyla eklendi.', 'success')
        return redirect(url_for('ogrenciler'))
        
    conn.close()
    return render_template('ogrenci_form.html', ogrenci=None, kulupler=kulupler, kulup_id=None)

@app.route('/ogrenci/ekle/<int:kulup_id>', methods=['GET', 'POST'])
@login_required
def ogrenci_ekle(kulup_id):
    if not has_club_permission(kulup_id):
        flash('Bu kulübe üye ekleme yetkiniz yok!', 'danger')
        return redirect(url_for('kulup_detay', id=kulup_id))
        
    conn = get_db_connection()
    kulupler = None
    if session.get('rol') == 'super':
        kulupler = conn.execute('SELECT * FROM kulup').fetchall()
        
    if request.method == 'POST':
        ad = request.form['ad']
        soyad = request.form['soyad']
        eposta = request.form['eposta']
        telefon = request.form['telefon']
        secilen_kulup_id = request.form.get('kulup_id', kulup_id)
        
        conn.execute(
            'INSERT INTO ogrenci (ad, soyad, eposta, telefon, kulup_id) VALUES (?, ?, ?, ?, ?)',
            (ad, soyad, eposta, telefon, secilen_kulup_id)
        )
        conn.commit()
        conn.close()
        flash('Öğrenci kulübe başarıyla eklendi.', 'success')
        return redirect(url_for('kulup_detay', id=secilen_kulup_id))
        
    conn.close()
    return render_template('ogrenci_form.html', ogrenci=None, kulupler=kulupler, kulup_id=kulup_id)

@app.route('/ogrenci/duzenle/<int:id>', methods=['GET', 'POST'])
@login_required
def ogrenci_duzenle(id):
    conn = get_db_connection()
    ogrenci = conn.execute('SELECT * FROM ogrenci WHERE id = ?', (id,)).fetchone()
    
    if not ogrenci:
        flash('Öğrenci bulunamadı!', 'danger')
        conn.close()
        return redirect(url_for('index'))
        
    kulup_id = ogrenci['kulup_id']
    if not has_club_permission(kulup_id):
        flash('Bu işlem için yetkiniz yok!', 'danger')
        conn.close()
        return redirect(url_for('kulup_detay', id=kulup_id))
        
    kulupler = None
    if session.get('rol') == 'super':
        kulupler = conn.execute('SELECT * FROM kulup').fetchall()
        
    if request.method == 'POST':
        ad = request.form['ad']
        soyad = request.form['soyad']
        eposta = request.form['eposta']
        telefon = request.form['telefon']
        yeni_kulup_id = request.form.get('kulup_id', kulup_id)
        
        conn.execute(
            'UPDATE ogrenci SET ad = ?, soyad = ?, eposta = ?, telefon = ?, kulup_id = ? WHERE id = ?',
            (ad, soyad, eposta, telefon, yeni_kulup_id, id)
        )
        conn.commit()
        conn.close()
        flash('Öğrenci bilgileri güncellendi.', 'success')
        return redirect(url_for('ogrenciler' if session.get('rol') == 'super' else 'kulup_detay', id=yeni_kulup_id))
        
    conn.close()
    return render_template('ogrenci_form.html', ogrenci=ogrenci, kulupler=kulupler, kulup_id=kulup_id)

@app.route('/ogrenci/sil/<int:id>')
@login_required
def ogrenci_sil(id):
    conn = get_db_connection()
    ogrenci = conn.execute('SELECT * FROM ogrenci WHERE id = ?', (id,)).fetchone()
    
    if not ogrenci:
        flash('Öğrenci bulunamadı!', 'danger')
        conn.close()
        return redirect(url_for('index'))
        
    kulup_id = ogrenci['kulup_id']
    if not has_club_permission(kulup_id):
        flash('Bu işlem için yetkiniz yok!', 'danger')
        conn.close()
        return redirect(url_for('kulup_detay', id=kulup_id))
        
    conn.execute('DELETE FROM ogrenci WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Öğrenci kulüpten/sistemden silindi.', 'success')
    return redirect(request.referrer or url_for('index'))

# ----------------- CRUD İŞLEMLERİ (ETKİNLİK) -----------------

@app.route('/etkinlik/ekle/<int:kulup_id>', methods=['GET', 'POST'])
@login_required
def etkinlik_ekle(kulup_id):
    if not has_club_permission(kulup_id):
        flash('Bu işlem için yetkiniz yok!', 'danger')
        return redirect(url_for('kulup_detay', id=kulup_id))
        
    if request.method == 'POST':
        etkinlik_adi = request.form['etkinlik_adi']
        tarih = request.form['tarih']
        yer = request.form['yer']
        
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO etkinlik (etkinlik_adi, tarih, yer, kulup_id) VALUES (?, ?, ?, ?)',
            (etkinlik_adi, tarih, yer, kulup_id)
        )
        conn.commit()
        conn.close()
        flash('Etkinlik başarıyla programlandı.', 'success')
        return redirect(url_for('kulup_detay', id=kulup_id))
        
    return render_template('etkinlik_form.html', etkinlik=None, kulup_id=kulup_id)

@app.route('/etkinlik/duzenle/<int:id>', methods=['GET', 'POST'])
@login_required
def etkinlik_duzenle(id):
    conn = get_db_connection()
    etkinlik = conn.execute('SELECT * FROM etkinlik WHERE id = ?', (id,)).fetchone()
    
    if not etkinlik:
        flash('Etkinlik bulunamadı!', 'danger')
        conn.close()
        return redirect(url_for('index'))
        
    kulup_id = etkinlik['kulup_id']
    if not has_club_permission(kulup_id):
        flash('Bu işlem için yetkiniz yok!', 'danger')
        conn.close()
        return redirect(url_for('kulup_detay', id=kulup_id))
        
    if request.method == 'POST':
        etkinlik_adi = request.form['etkinlik_adi']
        tarih = request.form['tarih']
        yer = request.form['yer']
        
        conn.execute(
            'UPDATE etkinlik SET etkinlik_adi = ?, tarih = ?, yer = ? WHERE id = ?',
            (etkinlik_adi, tarih, yer, id)
        )
        conn.commit()
        conn.close()
        flash('Etkinlik bilgileri güncellendi.', 'success')
        return redirect(url_for('etkinlikler' if session.get('rol') == 'super' else 'kulup_detay', id=kulup_id))
        
    conn.close()
    return render_template('etkinlik_form.html', etkinlik=etkinlik, kulup_id=kulup_id)

@app.route('/etkinlik/sil/<int:id>')
@login_required
def etkinlik_sil(id):
    conn = get_db_connection()
    etkinlik = conn.execute('SELECT * FROM etkinlik WHERE id = ?', (id,)).fetchone()
    
    if not etkinlik:
        flash('Etkinlik bulunamadı!', 'danger')
        conn.close()
        return redirect(url_for('index'))
        
    kulup_id = etkinlik['kulup_id']
    if not has_club_permission(kulup_id):
        flash('Bu işlem için yetkiniz yok!', 'danger')
        conn.close()
        return redirect(url_for('kulup_detay', id=kulup_id))
        
    conn.execute('DELETE FROM etkinlik WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Etkinlik programdan silindi.', 'success')
    return redirect(request.referrer or url_for('index'))

# ----------------- CRUD İŞLEMLERİ (GÖREV) -----------------

@app.route('/gorev/ekle/<int:kulup_id>', methods=['GET', 'POST'])
@login_required
def gorev_ekle(kulup_id):
    if not has_club_permission(kulup_id):
        flash('Bu işlem için yetkiniz yok!', 'danger')
        return redirect(url_for('kulup_detay', id=kulup_id))
        
    if request.method == 'POST':
        gorev_tanimi = request.form['gorev_tanimi']
        son_tarih = request.form['son_tarih']
        durum = request.form['durum']
        
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO gorev (gorev_tanimi, son_tarih, durum, kulup_id) VALUES (?, ?, ?, ?)',
            (gorev_tanimi, son_tarih, durum, kulup_id)
        )
        conn.commit()
        conn.close()
        flash('Haftalık görev başarıyla tanımlandı.', 'success')
        return redirect(url_for('kulup_detay', id=kulup_id))
        
    return render_template('gorev_form.html', gorev=None, kulup_id=kulup_id)

@app.route('/gorev/duzenle/<int:id>', methods=['GET', 'POST'])
@login_required
def gorev_duzenle(id):
    conn = get_db_connection()
    gorev = conn.execute('SELECT * FROM gorev WHERE id = ?', (id,)).fetchone()
    
    if not gorev:
        flash('Görev bulunamadı!', 'danger')
        conn.close()
        return redirect(url_for('index'))
        
    kulup_id = gorev['kulup_id']
    if not has_club_permission(kulup_id):
        flash('Bu işlem için yetkiniz yok!', 'danger')
        conn.close()
        return redirect(url_for('kulup_detay', id=kulup_id))
        
    if request.method == 'POST':
        gorev_tanimi = request.form['gorev_tanimi']
        son_tarih = request.form['son_tarih']
        durum = request.form['durum']
        
        conn.execute(
            'UPDATE gorev SET gorev_tanimi = ?, son_tarih = ?, durum = ? WHERE id = ?',
            (gorev_tanimi, son_tarih, durum, id)
        )
        conn.commit()
        conn.close()
        flash('Görev başarıyla güncellendi.', 'success')
        return redirect(url_for('gorevler' if session.get('rol') == 'super' else 'kulup_detay', id=kulup_id))
        
    conn.close()
    return render_template('gorev_form.html', gorev=gorev, kulup_id=kulup_id)

@app.route('/gorev/sil/<int:id>')
@login_required
def gorev_sil(id):
    conn = get_db_connection()
    gorev = conn.execute('SELECT * FROM gorev WHERE id = ?', (id,)).fetchone()
    
    if not gorev:
        flash('Görev bulunamadı!', 'danger')
        conn.close()
        return redirect(url_for('index'))
        
    kulup_id = gorev['kulup_id']
    if not has_club_permission(kulup_id):
        flash('Bu işlem için yetkiniz yok!', 'danger')
        conn.close()
        return redirect(url_for('kulup_detay', id=kulup_id))
        
    conn.execute('DELETE FROM gorev WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Görev başarıyla silindi.', 'success')
    return redirect(request.referrer or url_for('index'))

# ----------------- YÖNETİCİ EKLEME (SÜPER ADMİN) -----------------

@app.route('/yonetici/ekle', methods=['GET', 'POST'])
@login_required
def yonetici_ekle():
    if session.get('rol') != 'super':
        flash('Bu sayfaya erişim yetkiniz yok!', 'danger')
        return redirect(url_for('index'))
        
    conn = get_db_connection()
    kulupler = conn.execute('SELECT * FROM kulup').fetchall()
    
    if request.method == 'POST':
        kullanici_adi = request.form['kullanici_adi']
        sifre = request.form['sifre']
        rol = request.form['rol']
        kulup_id = request.form['kulup_id']
        
        if rol == 'super':
            kulup_id = None
            
        try:
            conn.execute(
                'INSERT INTO yonetici (kullanici_adi, sifre, rol, kulup_id) VALUES (?, ?, ?, ?)',
                (kullanici_adi, sifre, rol, kulup_id)
            )
            conn.commit()
            flash('Yeni yönetici başarıyla oluşturuldu.', 'success')
            conn.close()
            return redirect(url_for('index'))
        except Exception:
            flash('Bu kullanıcı adı zaten sistemde mevcut veya veri hatası oluştu!', 'danger')
            
    conn.close()
    return render_template('yonetici_form.html', kulupler=kulupler)

# Sunucu Başlatma
if __name__ == '__main__':
    def open_browser():
        webbrowser.open_new("http://127.0.0.1:5000")
        
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        Timer(1.5, open_browser).start()
        
    app.run(debug=True, port=5000)
"""

with open(os.path.join(PROJE_DIZINI, 'app.py'), 'w', encoding='utf-8') as f:
    f.write(APP_PY_ICERIK)
print("app.py yazıldı.")

# 3. HTML Şablonlarının (Templates) Yazılması
print("\n[3/6] HTML şablonları oluşturuluyor...")

TEMPLATES = {
    'base.html': """<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Kulüp Yönetim Sistemi{% endblock %}</title>
    <!-- Bootstrap 5 CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-9ndCyUaIbzAi2FUVXJi0CjmCapSmO7SnpJef0486qhLnuZ2cdeRhO02iuK6FUUVM" crossorigin="anonymous">
    <!-- Bootstrap Icons -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css">
    <!-- Google Fonts Outfit -->
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <!-- Custom CSS -->
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
    <!-- Navbar -->
    <nav class="navbar navbar-expand-lg navbar-light sticky-top">
        <div class="container">
            <a class="navbar-brand d-flex align-items-center" href="{{ url_for('index') }}">
                <i class="bi bi-mortarboard-fill me-2 fs-3 text-primary"></i>
                <span class="fs-4 fw-bold">Kulüp<span class="text-primary">Yönetim</span></span>
            </a>
            <button class="navbar-toggler btn border-0 d-lg-none" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav me-auto mb-2 mb-lg-0 ms-lg-4">
                    <li class="nav-item">
                        <a class="nav-link fw-semibold" href="{{ url_for('index') }}">Ana Sayfa</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link fw-semibold" href="{{ url_for('ogrenciler') }}">Öğrenciler</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link fw-semibold" href="{{ url_for('etkinlikler') }}">Etkinlikler</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link fw-semibold" href="{{ url_for('gorevler') }}">Görevler</a>
                    </li>
                </ul>
                <div class="d-flex align-items-center gap-3">
                    {% if session.get('kullanici_id') %}
                        <span class="navbar-text fw-medium text-dark me-2">
                            <i class="bi bi-person-circle text-primary me-1"></i>
                            {{ session.get('kullanici_adi') }} 
                            <span class="badge bg-primary-subtle text-primary border border-primary-subtle rounded-pill">{{ 'Süper Admin' if session.get('rol') == 'super' else 'Kulüp Yöneticisi' }}</span>
                        </span>
                        {% if session.get('rol') == 'super' %}
                            <a href="{{ url_for('yonetici_ekle') }}" class="btn btn-outline-primary btn-sm"><i class="bi bi-person-plus-fill me-1"></i>Yönetici Ekle</a>
                        {% endif %}
                        <a href="{{ url_for('logout') }}" class="btn btn-danger btn-sm"><i class="bi bi-box-arrow-right me-1"></i>Çıkış Yap</a>
                    {% else %}
                        <a href="{{ url_for('login') }}" class="btn btn-primary btn-sm"><i class="bi bi-box-arrow-in-right me-1"></i>Yönetici Girişi</a>
                    {% endif %}
                </div>
            </div>
        </div>
    </nav>

    <!-- Main Content -->
    <main class="container my-5 flex-grow-1">
        <!-- Flash Messages -->
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category if category != 'error' else 'danger' }} alert-dismissible fade show border-0 shadow-sm rounded-3 mb-4" role="alert">
                        <div class="d-flex align-items-center">
                            {% if category == 'success' %}
                                <i class="bi bi-check-circle-fill me-2 fs-5"></i>
                            {% elif category == 'danger' or category == 'error' %}
                                <i class="bi bi-exclamation-triangle-fill me-2 fs-5"></i>
                            {% else %}
                                <i class="bi bi-info-circle-fill me-2 fs-5"></i>
                            {% endif %}
                            <div>{{ message }}</div>
                        </div>
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Kapat"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        {% block content %}{% endblock %}
    </main>

    <!-- Footer -->
    <footer class="py-4 border-top mt-auto bg-white">
        <div class="container text-center">
            <span class="text-muted small">© 2026 Üniversite Kulüp Yönetim Sistemi | Öğrenci Projesi</span>
        </div>
    </footer>

    <!-- Bootstrap 5 Bundle JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js" integrity="sha384-geWF76RCwLtnZ8qwWowPQNguL3RmwHVBC9FhGdlKrxdiJJigb/j/68SIy3Te4Bkz" crossorigin="anonymous"></script>
</body>
</html>""",

    'index.html': """{% extends 'base.html' %}

{% block title %}Ana Sayfa - Üniversite Kulüp Yönetim Sistemi{% endblock %}

{% block content %}
<!-- Hero Section -->
<div class="row align-items-center mb-5 hero-section py-5 px-4 rounded-4 shadow-sm text-white mx-0">
    <div class="col-lg-8">
        <h1 class="display-5 fw-bold mb-3">Kulüp Yönetim Sistemi</h1>
        <p class="lead mb-0">Üniversitemizin aktif öğrenci kulüplerini keşfedin, üye olun, etkinlikleri takip edin ve haftalık görevleri yönetin.</p>
    </div>
    <div class="col-lg-4 text-end d-none d-lg-block">
        <i class="bi bi-rocket-takeoff text-white opacity-75" style="font-size: 8rem;"></i>
    </div>
</div>

<!-- Stats Section -->
<div class="row g-4 mb-5">
    <div class="col-md-3">
        <a href="#clubsGrid" class="text-decoration-none h-100 d-block">
            <div class="card border-0 border-start border-4 border-primary shadow-sm h-100 py-2">
                <div class="card-body">
                    <div class="row align-items-center">
                        <div class="col">
                            <div class="text-xs font-weight-bold text-primary text-uppercase mb-1" style="font-size: 0.8rem; letter-spacing: 0.05rem;">Toplam Kulüp</div>
                            <div class="h3 mb-0 fw-bold text-dark">{{ stats.kulup_sayisi }}</div>
                        </div>
                        <div class="col-auto">
                            <i class="bi bi-building fs-1 text-primary-subtle text-primary"></i>
                        </div>
                    </div>
                </div>
            </div>
        </a>
    </div>
    <div class="col-md-3">
        <a href="{{ url_for('ogrenciler') }}" class="text-decoration-none h-100 d-block">
            <div class="card border-0 border-start border-4 border-info shadow-sm h-100 py-2">
                <div class="card-body">
                    <div class="row align-items-center">
                        <div class="col">
                            <div class="text-xs font-weight-bold text-info text-uppercase mb-1" style="font-size: 0.8rem; letter-spacing: 0.05rem;">Toplam Öğrenci</div>
                            <div class="h3 mb-0 fw-bold text-dark">{{ stats.ogrenci_sayisi }}</div>
                        </div>
                        <div class="col-auto">
                            <i class="bi bi-people fs-1 text-info-subtle text-info"></i>
                        </div>
                    </div>
                </div>
            </div>
        </a>
    </div>
    <div class="col-md-3">
        <a href="{{ url_for('etkinlikler') }}" class="text-decoration-none h-100 d-block">
            <div class="card border-0 border-start border-4 border-success shadow-sm h-100 py-2">
                <div class="card-body">
                    <div class="row align-items-center">
                        <div class="col">
                            <div class="text-xs font-weight-bold text-success text-uppercase mb-1" style="font-size: 0.8rem; letter-spacing: 0.05rem;">Aktif Etkinlikler</div>
                            <div class="h3 mb-0 fw-bold text-dark">{{ stats.etkinlik_sayisi }}</div>
                        </div>
                        <div class="col-auto">
                            <i class="bi bi-calendar-event fs-1 text-success-subtle text-success"></i>
                        </div>
                    </div>
                </div>
            </div>
        </a>
    </div>
    <div class="col-md-3">
        <a href="{{ url_for('gorevler') }}" class="text-decoration-none h-100 d-block">
            <div class="card border-0 border-start border-4 border-warning shadow-sm h-100 py-2">
                <div class="card-body">
                    <div class="row align-items-center">
                        <div class="col">
                            <div class="text-xs font-weight-bold text-warning text-uppercase mb-1" style="font-size: 0.8rem; letter-spacing: 0.05rem;">Haftalık Görevler</div>
                            <div class="h3 mb-0 fw-bold text-dark">{{ stats.gorev_sayisi }}</div>
                        </div>
                        <div class="col-auto">
                            <i class="bi bi-list-task fs-1 text-warning-subtle text-warning"></i>
                        </div>
                    </div>
                </div>
            </div>
        </a>
    </div>
</div>

<!-- Header & Controls -->
<div class="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-4">
    <div>
        <h2 class="fw-bold mb-1 text-dark" id="clubsGrid">Aktif Kulüpler</h2>
        <p class="text-muted mb-0">Detayları görmek için kulüp kartlarına tıklayın veya arama yapın.</p>
    </div>
    <div class="d-flex gap-2">
        <div class="input-group" style="max-width: 300px;">
            <span class="input-group-text bg-white border-end-0"><i class="bi bi-search text-muted"></i></span>
            <input type="text" id="clubSearch" class="form-control border-start-0" placeholder="Kulüp adı ara...">
        </div>
        {% if session.get('rol') == 'super' %}
            <a href="{{ url_for('kulup_ekle') }}" class="btn btn-primary d-flex align-items-center gap-1 shadow-sm">
                <i class="bi bi-plus-circle-fill"></i> Yeni Kulüp Ekle
            </a>
        {% endif %}
    </div>
</div>

<!-- Clubs Grid -->
<div class="row g-4">
    {% for kulup in kulupler %}
        <div class="col-md-6 col-lg-4 club-card-col">
            <div class="card h-100 border-0 shadow-sm position-relative overflow-hidden">
                <div class="card-body p-4 d-flex flex-column">
                    <div class="d-flex justify-content-between align-items-start mb-3">
                        <span class="badge bg-primary-subtle text-primary border border-primary-subtle rounded-pill px-3 py-2 small">
                            <i class="bi bi-calendar3 me-1"></i> Kuruluş: {{ kulup.kurulus_tarihi }}
                        </span>
                    </div>
                    <h4 class="card-title fw-bold text-dark mb-2">{{ kulup.ad }}</h4>
                    <p class="card-text text-muted mb-4 text-truncate-3 flex-grow-1">{{ kulup.aciklama }}</p>
                    
                    <div class="d-flex justify-content-between align-items-center pt-3 border-top mt-auto">
                        <div class="d-flex gap-3 text-muted small">
                            <span><i class="bi bi-people-fill text-info me-1"></i>{{ kulup.ogrenci_sayisi }} Üye</span>
                            <span><i class="bi bi-calendar2-check-fill text-success me-1"></i>{{ kulup.etkinlik_sayisi }} Etkinlik</span>
                        </div>
                    </div>
                    
                    <a href="{{ url_for('kulup_detay', id=kulup.id) }}" class="stretched-link mt-3 btn btn-outline-primary btn-sm">Detayları Gör <i class="bi bi-arrow-right ms-1"></i></a>
                </div>
                {% if session.get('rol') == 'super' %}
                    <div class="position-absolute top-0 end-0 p-3 d-flex gap-1" style="z-index: 10;">
                        <a href="{{ url_for('kulup_duzenle', id=kulup.id) }}" class="btn btn-light btn-sm shadow-sm rounded-circle p-2" title="Kulübü Düzenle"><i class="bi bi-pencil-fill text-primary"></i></a>
                        <a href="{{ url_for('kulup_sil', id=kulup.id) }}" class="btn btn-light btn-sm shadow-sm rounded-circle p-2" onclick="return confirm('Bu kulübü ve kulübe ait TÜM verileri silmek istediğinize emin misiniz?')" title="Kulübü Sil"><i class="bi bi-trash-fill text-danger"></i></a>
                    </div>
                {% endif %}
            </div>
        </div>
    {% endfor %}
</div>

<!-- JS search script -->
<script>
    document.getElementById('clubSearch').addEventListener('input', function(e) {
        const query = e.target.value.toLowerCase();
        const cards = document.querySelectorAll('.club-card-col');
        cards.forEach(card => {
            const name = card.querySelector('.card-title').textContent.toLowerCase();
            const desc = card.querySelector('.card-text').textContent.toLowerCase();
            if (name.includes(query) || desc.includes(query)) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        });
    });
</script>
{% endblock %}""",

    'login.html': """{% extends 'base.html' %}

{% block title %}Giriş Yap - Üniversite Kulüp Yönetim Sistemi{% endblock %}

{% block content %}
<div class="row justify-content-center py-5">
    <div class="col-md-5">
        <div class="card border-0 shadow-lg rounded-4 overflow-hidden">
            <div class="bg-primary py-4 text-center text-white">
                <i class="bi bi-shield-lock-fill fs-1"></i>
                <h3 class="fw-bold mt-2">Yönetici Girişi</h3>
                <p class="mb-0 text-white-50 small">Sistemi yönetmek için giriş bilgilerinizi kullanın.</p>
            </div>
            <div class="card-body p-4 p-md-5">
                <form method="POST">
                    <div class="mb-3">
                        <label for="kullanici_adi" class="form-label fw-semibold">Kullanıcı Adı</label>
                        <div class="input-group">
                            <span class="input-group-text bg-light border-end-0"><i class="bi bi-person-fill text-muted"></i></span>
                            <input type="text" class="form-control bg-light border-start-0" id="kullanici_adi" name="kullanici_adi" placeholder="Kullanıcı adı girin..." required>
                        </div>
                    </div>
                    <div class="mb-4">
                        <label for="sifre" class="form-label fw-semibold">Şifre</label>
                        <div class="input-group">
                            <span class="input-group-text bg-light border-end-0"><i class="bi bi-lock-fill text-muted"></i></span>
                            <input type="password" class="form-control bg-light border-start-0" id="sifre" name="sifre" placeholder="Şifre girin..." required>
                        </div>
                    </div>
                    <button type="submit" class="btn btn-primary w-100 py-2 fw-semibold fs-5 rounded-3 shadow-sm">Giriş Yap</button>
                </form>
            </div>
            <div class="card-footer bg-light text-center py-3 border-0">
                <a href="{{ url_for('index') }}" class="text-decoration-none text-muted small"><i class="bi bi-arrow-left me-1"></i>Ana Sayfaya Dön</a>
            </div>
        </div>
        
        <div class="card mt-4 border-0 shadow-sm rounded-3 bg-info-subtle border-start border-4 border-info">
            <div class="card-body text-dark py-3">
                <div class="d-flex align-items-center">
                    <i class="bi bi-info-circle-fill text-info fs-4 me-2"></i>
                    <div>
                        <h6 class="fw-bold mb-0">Hızlı Test Girişleri:</h6>
                        <small class="d-block">Süper Admin (Baş Admin): <strong>admin</strong> / <strong>admin123</strong></small>
                        <small class="d-block">Yazılım Kulübü Yöneticisi: <strong>yazilim_admin</strong> / <strong>yazilim123</strong></small>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}""",

    'kulup_detay.html': """{% extends 'base.html' %}

{% block title %}{{ kulup.ad }} - Kulüp Detayları{% endblock %}

{% block content %}
<!-- Club Header -->
<div class="card border-0 shadow-sm rounded-4 p-4 mb-4 bg-white border-top border-4 border-primary">
    <div class="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3">
        <div>
            <h1 class="fw-bold text-dark mb-2">{{ kulup.ad }}</h1>
            <p class="lead text-muted mb-0">{{ kulup.aciklama }}</p>
        </div>
        <div class="text-md-end">
            <span class="badge bg-light text-dark border rounded-pill px-3 py-2">
                <i class="bi bi-calendar3 me-1 text-primary"></i> Kuruluş: {{ kulup.kurulus_tarihi }}
            </span>
            <div class="mt-2 text-muted small">
                <strong>{{ ogrenciler|length }}</strong> Kayıtlı Üye
            </div>
        </div>
    </div>
</div>

<!-- Back button & Admin Tools -->
<div class="d-flex justify-content-between align-items-center mb-4">
    <a href="{{ url_for('index') }}" class="btn btn-outline-secondary btn-sm d-flex align-items-center gap-1">
        <i class="bi bi-arrow-left"></i> Kulüp Listesine Dön
    </a>
</div>

<!-- Details Navigation (Tabs) -->
<div class="row g-4">
    <div class="col-lg-12">
        <div class="card border-0 shadow-sm rounded-4">
            <div class="card-header bg-white border-0 pt-4 px-4">
                <ul class="nav nav-pills" id="detailTabs" role="tablist">
                    <li class="nav-item" role="presentation">
                        <button class="nav-link active" id="students-tab" data-bs-toggle="pill" data-bs-target="#students" type="button" role="tab" aria-controls="students" aria-selected="true">
                            <i class="bi bi-people-fill me-2"></i>Üyeler ({{ ogrenciler|length }})
                        </button>
                    </li>
                    <li class="nav-item" role="presentation">
                        <button class="nav-link" id="events-tab" data-bs-toggle="pill" data-bs-target="#events" type="button" role="tab" aria-controls="events" aria-selected="false">
                            <i class="bi bi-calendar-event-fill me-2"></i>Etkinlikler ({{ etkinlikler|length }})
                        </button>
                    </li>
                    <li class="nav-item" role="presentation">
                        <button class="nav-link" id="tasks-tab" data-bs-toggle="pill" data-bs-target="#tasks" type="button" role="tab" aria-controls="tasks" aria-selected="false">
                            <i class="bi bi-list-task me-2"></i>Haftalık Görevler ({{ gorevler|length }})
                        </button>
                    </li>
                </ul>
            </div>
            
            <div class="card-body p-4">
                <div class="tab-content" id="detailTabsContent">
                    <!-- Tab 1: Students -->
                    <div class="tab-pane fade show active" id="students" role="tabpanel" aria-labelledby="students-tab">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h5 class="fw-bold text-dark mb-0">Kayıtlı Öğrenci Listesi</h5>
                            {% if is_admin %}
                                <a href="{{ url_for('ogrenci_ekle', kulup_id=kulup.id) }}" class="btn btn-primary btn-sm d-flex align-items-center gap-1 shadow-sm">
                                    <i class="bi bi-plus-circle"></i> Yeni Üye Ekle
                                </a>
                            {% endif %}
                        </div>
                        <div class="table-responsive">
                            <table class="table table-hover align-middle">
                                <thead class="table-light">
                                    <tr>
                                        <th scope="col" style="width: 80px;">ID</th>
                                        <th scope="col">Ad Soyad</th>
                                        <th scope="col">E-posta</th>
                                        <th scope="col">Telefon</th>
                                        {% if is_admin %}
                                            <th scope="col" class="text-end" style="width: 150px;">İşlemler</th>
                                        {% endif %}
                                    </tr>
                                </thead>
                                <tbody>
                                    {% if ogrenciler %}
                                        {% for ogrenci in ogrenciler %}
                                            <tr>
                                                <td class="fw-semibold">#{{ ogrenci.id }}</td>
                                                <td class="fw-medium">{{ ogrenci.ad }} {{ ogrenci.soyad }}</td>
                                                <td><a href="mailto:{{ ogrenci.eposta }}" class="text-decoration-none">{{ ogrenci.eposta }}</a></td>
                                                <td>{{ ogrenci.telefon }}</td>
                                                {% if is_admin %}
                                                    <td class="text-end">
                                                        <a href="{{ url_for('ogrenci_duzenle', id=ogrenci.id) }}" class="btn btn-outline-primary btn-sm rounded-3 px-2 me-1" title="Düzenle"><i class="bi bi-pencil"></i></a>
                                                        <a href="{{ url_for('ogrenci_sil', id=ogrenci.id) }}" class="btn btn-outline-danger btn-sm rounded-3 px-2" onclick="return confirm('Bu öğrenciyi kulüpten silmek istediğinize emin misiniz?')" title="Sil"><i class="bi bi-trash"></i></a>
                                                    </td>
                                                {% endif %}
                                            </tr>
                                        {% endfor %}
                                    {% else %}
                                        <tr>
                                            <td colspan="5" class="text-center py-4 text-muted">
                                                <i class="bi bi-people fs-2 d-block mb-2 opacity-50"></i>
                                                Bu kulübe henüz kayıtlı öğrenci bulunmuyor.
                                            </td>
                                        </tr>
                                    {% endif %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                    
                    <!-- Tab 2: Events -->
                    <div class="tab-pane fade" id="events" role="tabpanel" aria-labelledby="events-tab">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h5 class="fw-bold text-dark mb-0">Etkinlik Programı</h5>
                            {% if is_admin %}
                                <a href="{{ url_for('etkinlik_ekle', kulup_id=kulup.id) }}" class="btn btn-primary btn-sm d-flex align-items-center gap-1 shadow-sm">
                                    <i class="bi bi-plus-circle"></i> Yeni Etkinlik Ekle
                                </a>
                            {% endif %}
                        </div>
                        <div class="table-responsive">
                            <table class="table table-hover align-middle">
                                <thead class="table-light">
                                    <tr>
                                        <th scope="col" style="width: 80px;">ID</th>
                                        <th scope="col">Etkinlik Adı</th>
                                        <th scope="col">Tarih</th>
                                        <th scope="col">Yer</th>
                                        {% if is_admin %}
                                            <th scope="col" class="text-end" style="width: 150px;">İşlemler</th>
                                        {% endif %}
                                    </tr>
                                </thead>
                                <tbody>
                                    {% if etkinlikler %}
                                        {% for etkinlik in etkinlikler %}
                                            <tr>
                                                <td class="fw-semibold">#{{ etkinlik.id }}</td>
                                                <td class="fw-medium">{{ etkinlik.etkinlik_adi }}</td>
                                                <td>
                                                    <span class="badge bg-success-subtle text-success border border-success-subtle rounded-pill">
                                                        <i class="bi bi-calendar-event me-1"></i> {{ etkinlik.tarih }}
                                                    </span>
                                                </td>
                                                <td><i class="bi bi-geo-alt-fill text-danger me-1"></i>{{ etkinlik.yer }}</td>
                                                {% if is_admin %}
                                                    <td class="text-end">
                                                        <a href="{{ url_for('etkinlik_duzenle', id=etkinlik.id) }}" class="btn btn-outline-primary btn-sm rounded-3 px-2 me-1" title="Düzenle"><i class="bi bi-pencil"></i></a>
                                                        <a href="{{ url_for('etkinlik_sil', id=etkinlik.id) }}" class="btn btn-outline-danger btn-sm rounded-3 px-2" onclick="return confirm('Bu etkinliği programdan silmek istediğinize emin misiniz?')" title="Sil"><i class="bi bi-trash"></i></a>
                                                    </td>
                                                {% endif %}
                                            </tr>
                                        {% endfor %}
                                    {% else %}
                                        <tr>
                                            <td colspan="5" class="text-center py-4 text-muted">
                                                <i class="bi bi-calendar2-x fs-2 d-block mb-2 opacity-50"></i>
                                                Planlanmış bir etkinlik bulunmuyor.
                                            </td>
                                        </tr>
                                    {% endif %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                    
                    <!-- Tab 3: Tasks -->
                    <div class="tab-pane fade" id="tasks" role="tabpanel" aria-labelledby="tasks-tab">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h5 class="fw-bold text-dark mb-0">Haftalık Görevler</h5>
                            {% if is_admin %}
                                <a href="{{ url_for('gorev_ekle', kulup_id=kulup.id) }}" class="btn btn-primary btn-sm d-flex align-items-center gap-1 shadow-sm">
                                    <i class="bi bi-plus-circle"></i> Yeni Görev Ekle
                                </a>
                            {% endif %}
                        </div>
                        <div class="table-responsive">
                            <table class="table table-hover align-middle">
                                <thead class="table-light">
                                    <tr>
                                        <th scope="col" style="width: 80px;">ID</th>
                                        <th scope="col">Görev Tanımı</th>
                                        <th scope="col">Son Tarih</th>
                                        <th scope="col">Durum</th>
                                        {% if is_admin %}
                                            <th scope="col" class="text-end" style="width: 150px;">İşlemler</th>
                                        {% endif %}
                                    </tr>
                                </thead>
                                <tbody>
                                    {% if gorevler %}
                                        {% for gorev in gorevler %}
                                            <tr>
                                                <td class="fw-semibold">#{{ gorev.id }}</td>
                                                <td class="fw-medium">{{ gorev.gorev_tanimi }}</td>
                                                <td>
                                                    <span class="text-muted small">
                                                        <i class="bi bi-clock me-1"></i> {{ gorev.son_tarih }}
                                                    </span>
                                                </td>
                                                <td>
                                                    {% if gorev.durum == 'Tamamlandı' %}
                                                        <span class="badge bg-success rounded-pill px-3 py-1"><i class="bi bi-check-circle-fill me-1"></i>Tamamlandı</span>
                                                    {% elif gorev.durum == 'Yapılıyor' %}
                                                        <span class="badge bg-warning text-dark rounded-pill px-3 py-1"><i class="bi bi-hourglass-split me-1"></i>Yapılıyor</span>
                                                    {% else %}
                                                        <span class="badge bg-secondary rounded-pill px-3 py-1"><i class="bi bi-circle me-1"></i>Yapılacak</span>
                                                    {% endif %}
                                                </td>
                                                {% if is_admin %}
                                                    <td class="text-end">
                                                        <a href="{{ url_for('gorev_duzenle', id=gorev.id) }}" class="btn btn-outline-primary btn-sm rounded-3 px-2 me-1" title="Düzenle"><i class="bi bi-pencil"></i></a>
                                                        <a href="{{ url_for('gorev_sil', id=gorev.id) }}" class="btn btn-outline-danger btn-sm rounded-3 px-2" onclick="return confirm('Bu görevi silmek istediğinize emin misiniz?')" title="Sil"><i class="bi bi-trash"></i></a>
                                                    </td>
                                                {% endif %}
                                            </tr>
                                        {% endfor %}
                                    {% else %}
                                        <tr>
                                            <td colspan="5" class="text-center py-4 text-muted">
                                                <i class="bi bi-list-check fs-2 d-block mb-2 opacity-50"></i>
                                                Tanımlanmış haftalık görev bulunmuyor.
                                            </td>
                                        </tr>
                                    {% endif %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}""",

    'kulup_form.html': """{% extends 'base.html' %}

{% block title %}{{ 'Kulübü Düzenle' if kulup else 'Yeni Kulüp Ekle' }} - Kulüp Yönetim Sistemi{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-8 col-lg-6">
        <div class="card border-0 shadow-sm rounded-4">
            <div class="card-header bg-white border-0 pt-4 px-4">
                <h3 class="fw-bold text-dark mb-0">{{ 'Kulübü Düzenle' if kulup else 'Yeni Kulüp Ekle' }}</h3>
                <p class="text-muted small">Kulüp detaylı bilgilerini girerek sisteme kaydedin.</p>
            </div>
            <div class="card-body p-4">
                <form method="POST">
                    <div class="mb-3">
                        <label for="ad" class="form-label fw-medium">Kulüp Adı</label>
                        <input type="text" class="form-control" id="ad" name="ad" value="{{ kulup.ad if kulup else '' }}" required>
                    </div>
                    <div class="mb-3">
                        <label for="aciklama" class="form-label fw-medium">Kulüp Açıklaması</label>
                        <textarea class="form-control" id="aciklama" name="aciklama" rows="4" required>{{ kulup.aciklama if kulup else '' }}</textarea>
                    </div>
                    <div class="mb-4">
                        <label for="kurulus_tarihi" class="form-label fw-medium">Kuruluş Tarihi</label>
                        <input type="date" class="form-control" id="kurulus_tarihi" name="kurulus_tarihi" value="{{ kulup.kurulus_tarihi if kulup else '' }}" required>
                    </div>
                    <div class="d-flex gap-2">
                        <button type="submit" class="btn btn-primary px-4 fw-medium"><i class="bi bi-save me-1"></i>Kaydet</button>
                        <a href="{{ url_for('index') }}" class="btn btn-outline-secondary px-4">İptal</a>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}""",

    'ogrenci_form.html': """{% extends 'base.html' %}

{% block title %}{{ 'Öğrenci Bilgilerini Düzenle' if ogrenci else 'Yeni Üye Ekle' }} - Kulüp Yönetim Sistemi{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-8 col-lg-6">
        <div class="card border-0 shadow-sm rounded-4">
            <div class="card-header bg-white border-0 pt-4 px-4">
                <h3 class="fw-bold text-dark mb-0">{{ 'Öğrenci Bilgilerini Düzenle' if ogrenci else 'Yeni Üye Ekle' }}</h3>
                <p class="text-muted small">Kulübe kayıt olacak öğrencinin kişisel ve iletişim bilgilerini girin.</p>
            </div>
            <div class="card-body p-4">
                <form method="POST">
                    <div class="mb-3">
                        <label for="ad" class="form-label fw-medium">Öğrenci Adı</label>
                        <input type="text" class="form-control" id="ad" name="ad" value="{{ ogrenci.ad if ogrenci else '' }}" required>
                    </div>
                    <div class="mb-3">
                        <label for="soyad" class="form-label fw-medium">Öğrenci Soyadı</label>
                        <input type="text" class="form-control" id="soyad" name="soyad" value="{{ ogrenci.soyad if ogrenci else '' }}" required>
                    </div>
                    <div class="mb-3">
                        <label for="eposta" class="form-label fw-medium">E-posta Adresi</label>
                        <input type="email" class="form-control" id="eposta" name="eposta" value="{{ ogrenci.eposta if ogrenci else '' }}" required>
                    </div>
                    <div class="mb-4">
                        <label for="telefon" class="form-label fw-medium">Telefon Numarası</label>
                        <input type="tel" class="form-control" id="telefon" name="telefon" placeholder="05XXXXXXXXX" value="{{ ogrenci.telefon if ogrenci else '' }}" required>
                    </div>
                    
                    {% if kulupler %}
                    <div class="mb-4">
                        <label for="kulup_id" class="form-label fw-medium">Üye Olacağı Kulüp</label>
                        <select class="form-select" id="kulup_id" name="kulup_id" required>
                            <option value="" disabled {{ 'selected' if not ogrenci else '' }}>Kulüp Seçin...</option>
                            {% for k in kulupler %}
                                <option value="{{ k.id }}" {{ 'selected' if (ogrenci and ogrenci.kulup_id == k.id) or (kulup_id == k.id) else '' }}>{{ k.ad }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    {% else %}
                        <input type="hidden" name="kulup_id" value="{{ kulup_id }}">
                    {% endif %}
                    
                    <div class="d-flex gap-2">
                        <button type="submit" class="btn btn-primary px-4 fw-medium"><i class="bi bi-save me-1"></i>Kaydet</button>
                        <a href="{{ url_for('ogrenciler' if session.get('rol') == 'super' else 'kulup_detay', id=kulup_id) }}" class="btn btn-outline-secondary px-4">İptal</a>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}""",

    'etkinlik_form.html': """{% extends 'base.html' %}

{% block title %}{{ 'Etkinliği Düzenle' if etkinlik else 'Yeni Etkinlik Ekle' }} - Kulüp Yönetim Sistemi{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-8 col-lg-6">
        <div class="card border-0 shadow-sm rounded-4">
            <div class="card-header bg-white border-0 pt-4 px-4">
                <h3 class="fw-bold text-dark mb-0">{{ 'Etkinliği Düzenle' if etkinlik else 'Yeni Etkinlik Ekle' }}</h3>
                <p class="text-muted small">Kulüp etkinlik programına yeni bir planlama ekleyin.</p>
            </div>
            <div class="card-body p-4">
                <form method="POST">
                    <div class="mb-3">
                        <label for="etkinlik_adi" class="form-label fw-medium">Etkinlik Adı</label>
                        <input type="text" class="form-control" id="etkinlik_adi" name="etkinlik_adi" value="{{ etkinlik.etkinlik_adi if etkinlik else '' }}" required>
                    </div>
                    <div class="mb-3">
                        <label for="tarih" class="form-label fw-medium">Etkinlik Tarihi</label>
                        <input type="date" class="form-control" id="tarih" name="tarih" value="{{ etkinlik.tarih if etkinlik else '' }}" required>
                    </div>
                    <div class="mb-4">
                        <label for="yer" class="form-label fw-medium">Etkinlik Yeri</label>
                        <input type="text" class="form-control" id="yer" name="yer" value="{{ etkinlik.yer if etkinlik else '' }}" placeholder="örn: Amfi 1, Kamp Bahçesi" required>
                    </div>
                    <div class="d-flex gap-2">
                        <button type="submit" class="btn btn-primary px-4 fw-medium"><i class="bi bi-save me-1"></i>Kaydet</button>
                        <a href="{{ url_for('etkinlikler' if session.get('rol') == 'super' else 'kulup_detay', id=kulup_id) }}" class="btn btn-outline-secondary px-4">İptal</a>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}""",

    'gorev_form.html': """{% extends 'base.html' %}

{% block title %}{{ 'Görevi Düzenle' if gorev else 'Yeni Haftalık Görev Ekle' }} - Kulüp Yönetim Sistemi{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-8 col-lg-6">
        <div class="card border-0 shadow-sm rounded-4">
            <div class="card-header bg-white border-0 pt-4 px-4">
                <h3 class="fw-bold text-dark mb-0">{{ 'Görevi Düzenle' if gorev else 'Yeni Görev Ekle' }}</h3>
                <p class="text-muted small">Kulüp organizasyonu için haftalık bir görev tanımlayın veya güncelleyin.</p>
            </div>
            <div class="card-body p-4">
                <form method="POST">
                    <div class="mb-3">
                        <label for="gorev_tanimi" class="form-label fw-medium">Görev Tanımı</label>
                        <input type="text" class="form-control" id="gorev_tanimi" name="gorev_tanimi" value="{{ gorev.gorev_tanimi if gorev else '' }}" required>
                    </div>
                    <div class="mb-3">
                        <label for="son_tarih" class="form-label fw-medium">Son Teslim Tarihi</label>
                        <input type="date" class="form-control" id="son_tarih" name="son_tarih" value="{{ gorev.son_tarih if gorev else '' }}" required>
                    </div>
                    <div class="mb-4">
                        <label for="durum" class="form-label fw-medium">Durum</label>
                        <select class="form-select" id="durum" name="durum" required>
                            <option value="Yapılacak" {{ 'selected' if gorev and gorev.durum == 'Yapılacak' else '' }}>Yapılacak</option>
                            <option value="Yapılıyor" {{ 'selected' if gorev and gorev.durum == 'Yapılıyor' else '' }}>Yapılıyor</option>
                            <option value="Tamamlandı" {{ 'selected' if gorev and gorev.durum == 'Tamamlandı' else '' }}>Tamamlandı</option>
                        </select>
                    </div>
                    <div class="d-flex gap-2">
                        <button type="submit" class="btn btn-primary px-4 fw-medium"><i class="bi bi-save me-1"></i>Kaydet</button>
                        <a href="{{ url_for('gorevler' if session.get('rol') == 'super' else 'kulup_detay', id=kulup_id) }}" class="btn btn-outline-secondary px-4">İptal</a>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}""",

    'yonetici_form.html': """{% extends 'base.html' %}

{% block title %}Yeni Yönetici Ekle - Kulüp Yönetim Sistemi{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-8 col-lg-6">
        <div class="card border-0 shadow-sm rounded-4">
            <div class="card-header bg-white border-0 pt-4 px-4">
                <h3 class="fw-bold text-dark mb-0">Yeni Yönetici Ekle</h3>
                <p class="text-muted small">Sisteme yeni bir yönetici veya kulüp yöneticisi ekleyin.</p>
            </div>
            <div class="card-body p-4">
                <form method="POST">
                    <div class="mb-3">
                        <label for="kullanici_adi" class="form-label fw-medium">Kullanıcı Adı</label>
                        <input type="text" class="form-control" id="kullanici_adi" name="kullanici_adi" required>
                    </div>
                    <div class="mb-3">
                        <label for="sifre" class="form-label fw-medium">Şifre</label>
                        <input type="password" class="form-control" id="sifre" name="sifre" required>
                    </div>
                    <div class="mb-3">
                        <label for="rol" class="form-label fw-medium">Yönetici Rolü</label>
                        <select class="form-select" id="rol" name="rol" required onchange="toggleClubSelect()">
                            <option value="kulup" selected>Kulüp Yöneticisi</option>
                            <option value="super">Süper Yönetici (Tüm Sistem)</option>
                        </select>
                    </div>
                    <div class="mb-4" id="clubSelectDiv">
                        <label for="kulup_id" class="form-label fw-medium">Yöneteceği Kulüp</label>
                        <select class="form-select" id="kulup_id" name="kulup_id">
                            {% for kulup in kulupler %}
                                <option value="{{ kulup.id }}">{{ kulup.ad }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="d-flex gap-2">
                        <button type="submit" class="btn btn-primary px-4 fw-medium"><i class="bi bi-save me-1"></i>Kaydet</button>
                        <a href="{{ url_for('index') }}" class="btn btn-outline-secondary px-4">İptal</a>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>

<script>
    function toggleClubSelect() {
        const rol = document.getElementById('rol').value;
        const div = document.getElementById('clubSelectDiv');
        const select = document.getElementById('kulup_id');
        if (rol === 'super') {
            div.style.display = 'none';
            select.removeAttribute('required');
        } else {
            div.style.display = 'block';
            select.setAttribute('required', 'required');
        }
    }
    // Başlangıçta çalıştır
    toggleClubSelect();
</script>
{% endblock %}""",

    'ogrenciler.html': """{% extends 'base.html' %}

{% block title %}Öğrenciler - Kulüp Yönetim Sistemi{% endblock %}

{% block content %}
<div class="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-4">
    <div>
        <h2 class="fw-bold mb-1 text-dark">Kayıtlı Öğrenciler</h2>
        <p class="text-muted mb-0">Sistemdeki tüm kayıtlı kulüp üyeleri.</p>
    </div>
    <div class="d-flex gap-2">
        <div class="input-group" style="max-width: 300px;">
            <span class="input-group-text bg-white border-end-0"><i class="bi bi-search text-muted"></i></span>
            <input type="text" id="studentSearch" class="form-control border-start-0" placeholder="Öğrenci ara...">
        </div>
        {% if session.get('rol') == 'super' %}
            <a href="{{ url_for('ogrenci_ekle_genel') }}" class="btn btn-primary d-flex align-items-center gap-1 shadow-sm">
                <i class="bi bi-plus-circle-fill"></i> Yeni Üye Ekle
            </a>
        {% endif %}
    </div>
</div>

<div class="card border-0 shadow-sm rounded-4">
    <div class="card-body p-4">
        <div class="table-responsive">
            <table class="table table-hover align-middle" id="studentsTable">
                <thead class="table-light">
                    <tr>
                        <th scope="col" style="width: 80px;">ID</th>
                        <th scope="col">Ad Soyad</th>
                        <th scope="col">Kulübü</th>
                        <th scope="col">E-posta</th>
                        <th scope="col">Telefon</th>
                        {% if session.get('kullanici_id') %}
                            <th scope="col" class="text-end" style="width: 150px;">İşlemler</th>
                        {% endif %}
                    </tr>
                </thead>
                <tbody>
                    {% if ogrenciler %}
                        {% for ogrenci in ogrenciler %}
                            <tr>
                                <td class="fw-semibold">#{{ ogrenci.id }}</td>
                                <td class="fw-medium">{{ ogrenci.ad }} {{ ogrenci.soyad }}</td>
                                <td>
                                    {% if ogrenci.kulup_ad %}
                                        <span class="badge bg-primary-subtle text-primary border border-primary-subtle rounded-pill px-3 py-2 fs-7">
                                            {{ ogrenci.kulup_ad }}
                                        </span>
                                    {% else %}
                                        <span class="badge bg-secondary-subtle text-secondary border border-secondary-subtle rounded-pill px-3 py-2 fs-7">
                                            Kulüpsüz
                                        </span>
                                    {% endif %}
                                </td>
                                <td><a href="mailto:{{ ogrenci.eposta }}" class="text-decoration-none">{{ ogrenci.eposta }}</a></td>
                                <td>{{ ogrenci.telefon }}</td>
                                {% if session.get('kullanici_id') %}
                                    <td class="text-end">
                                        {% if ogrenci.kulup_id in yonetilen_kulupler %}
                                            <a href="{{ url_for('ogrenci_duzenle', id=ogrenci.id) }}" class="btn btn-outline-primary btn-sm rounded-3 px-2 me-1" title="Düzenle"><i class="bi bi-pencil"></i></a>
                                            <a href="{{ url_for('ogrenci_sil', id=ogrenci.id) }}" class="btn btn-outline-danger btn-sm rounded-3 px-2" onclick="return confirm('Bu öğrenciyi silmek istediğinize emin misiniz?')" title="Sil"><i class="bi bi-trash"></i></a>
                                        {% else %}
                                            <span class="text-muted small">Yetki Yok</span>
                                        {% endif %}
                                    </td>
                                {% endif %}
                            </tr>
                        {% endfor %}
                    {% else %}
                        <tr>
                            <td colspan="6" class="text-center py-4 text-muted">
                                <i class="bi bi-people fs-2 d-block mb-2 opacity-50"></i>
                                Kayıtlı öğrenci bulunmuyor.
                            </td>
                        </tr>
                    {% endif %}
                </tbody>
            </table>
        </div>
    </div>
</div>

<script>
    document.getElementById('studentSearch').addEventListener('input', function(e) {
        const query = e.target.value.toLowerCase();
        const rows = document.querySelectorAll('#studentsTable tbody tr');
        rows.forEach(row => {
            const name = row.cells[1].textContent.toLowerCase();
            const club = row.cells[2].textContent.toLowerCase();
            const email = row.cells[3].textContent.toLowerCase();
            if (name.includes(query) || club.includes(query) || email.includes(query)) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    });
</script>
{% endblock %}""",

    'etkinlikler.html': """{% extends 'base.html' %}

{% block title %}Etkinlikler - Kulüp Yönetim Sistemi{% endblock %}

{% block content %}
<div class="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-4">
    <div>
        <h2 class="fw-bold mb-1 text-dark">Tüm Etkinlikler</h2>
        <p class="text-muted mb-0">Üniversitemiz genelindeki kulüp faaliyet takvimi.</p>
    </div>
    <div class="d-flex gap-2">
        <div class="input-group" style="max-width: 300px;">
            <span class="input-group-text bg-white border-end-0"><i class="bi bi-search text-muted"></i></span>
            <input type="text" id="eventSearch" class="form-control border-start-0" placeholder="Etkinlik ara...">
        </div>
    </div>
</div>

<div class="card border-0 shadow-sm rounded-4">
    <div class="card-body p-4">
        <div class="table-responsive">
            <table class="table table-hover align-middle" id="eventsTable">
                <thead class="table-light">
                    <tr>
                        <th scope="col" style="width: 80px;">ID</th>
                        <th scope="col">Etkinlik Adı</th>
                        <th scope="col">Düzenleyen Kulüp</th>
                        <th scope="col">Tarih</th>
                        <th scope="col">Yer</th>
                        {% if session.get('kullanici_id') %}
                            <th scope="col" class="text-end" style="width: 150px;">İşlemler</th>
                        {% endif %}
                    </tr>
                </thead>
                <tbody>
                    {% if etkinlikler %}
                        {% for etkinlik in etkinlikler %}
                            <tr>
                                <td class="fw-semibold">#{{ etkinlik.id }}</td>
                                <td class="fw-medium">{{ etkinlik.etkinlik_adi }}</td>
                                <td>
                                    <span class="badge bg-primary-subtle text-primary border border-primary-subtle rounded-pill px-3 py-2 fs-7">
                                        {{ etkinlik.kulup_ad }}
                                    </span>
                                </td>
                                <td>
                                    <span class="badge bg-success-subtle text-success border border-success-subtle rounded-pill">
                                        <i class="bi bi-calendar-event me-1"></i> {{ etkinlik.tarih }}
                                    </span>
                                </td>
                                <td><i class="bi bi-geo-alt-fill text-danger me-1"></i>{{ etkinlik.yer }}</td>
                                {% if session.get('kullanici_id') %}
                                    <td class="text-end">
                                        {% if etkinlik.kulup_id in yonetilen_kulupler %}
                                            <a href="{{ url_for('etkinlik_duzenle', id=etkinlik.id) }}" class="btn btn-outline-primary btn-sm rounded-3 px-2 me-1" title="Düzenle"><i class="bi bi-pencil"></i></a>
                                            <a href="{{ url_for('etkinlik_sil', id=etkinlik.id) }}" class="btn btn-outline-danger btn-sm rounded-3 px-2" onclick="return confirm('Bu etkinliği silmek istediğinize emin misiniz?')" title="Sil"><i class="bi bi-trash"></i></a>
                                        {% else %}
                                            <span class="text-muted small">Yetki Yok</span>
                                        {% endif %}
                                    </td>
                                {% endif %}
                            </tr>
                        {% endfor %}
                    {% else %}
                        <tr>
                            <td colspan="6" class="text-center py-4 text-muted">
                                <i class="bi bi-calendar-x fs-2 d-block mb-2 opacity-50"></i>
                                Kayıtlı etkinlik bulunmuyor.
                            </td>
                        </tr>
                    {% endif %}
                </tbody>
            </table>
        </div>
    </div>
</div>

<script>
    document.getElementById('eventSearch').addEventListener('input', function(e) {
        const query = e.target.value.toLowerCase();
        const rows = document.querySelectorAll('#eventsTable tbody tr');
        rows.forEach(row => {
            const name = row.cells[1].textContent.toLowerCase();
            const club = row.cells[2].textContent.toLowerCase();
            const location = row.cells[4].textContent.toLowerCase();
            if (name.includes(query) || club.includes(query) || location.includes(query)) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    });
</script>
{% endblock %}""",

    'gorevler.html': """{% extends 'base.html' %}

{% block title %}Haftalık Görevler - Kulüp Yönetim Sistemi{% endblock %}

{% block content %}
<div class="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-4">
    <div>
        <h2 class="fw-bold mb-1 text-dark">Haftalık Görevler</h2>
        <p class="text-muted mb-0">Tüm kulüpler için planlanan aktif görevler ve durumları.</p>
    </div>
    <div class="d-flex gap-2">
        <div class="input-group" style="max-width: 300px;">
            <span class="input-group-text bg-white border-end-0"><i class="bi bi-search text-muted"></i></span>
            <input type="text" id="taskSearch" class="form-control border-start-0" placeholder="Görev ara...">
        </div>
    </div>
</div>

<div class="card border-0 shadow-sm rounded-4">
    <div class="card-body p-4">
        <div class="table-responsive">
            <table class="table table-hover align-middle" id="tasksTable">
                <thead class="table-light">
                    <tr>
                        <th scope="col" style="width: 80px;">ID</th>
                        <th scope="col">Görev Tanımı</th>
                        <th scope="col">İlgili Kulüp</th>
                        <th scope="col">Son Tarih</th>
                        <th scope="col">Durum</th>
                        {% if session.get('kullanici_id') %}
                            <th scope="col" class="text-end" style="width: 150px;">İşlemler</th>
                        {% endif %}
                    </tr>
                </thead>
                <tbody>
                    {% if gorevler %}
                        {% for gorev in gorevler %}
                            <tr>
                                <td class="fw-semibold">#{{ gorev.id }}</td>
                                <td class="fw-medium">{{ gorev.gorev_tanimi }}</td>
                                <td>
                                    <span class="badge bg-primary-subtle text-primary border border-primary-subtle rounded-pill px-3 py-2 fs-7">
                                        {{ gorev.kulup_ad }}
                                    </span>
                                </td>
                                <td>
                                    <span class="text-muted small">
                                        <i class="bi bi-clock me-1"></i> {{ gorev.son_tarih }}
                                    </span>
                                </td>
                                <td>
                                    {% if gorev.durum == 'Tamamlandı' %}
                                        <span class="badge bg-success rounded-pill px-3 py-1"><i class="bi bi-check-circle-fill me-1"></i>Tamamlandı</span>
                                    {% elif gorev.durum == 'Yapılıyor' %}
                                        <span class="badge bg-warning text-dark rounded-pill px-3 py-1"><i class="bi bi-hourglass-split me-1"></i>Yapılıyor</span>
                                    {% else %}
                                        <span class="badge bg-secondary rounded-pill px-3 py-1"><i class="bi bi-circle me-1"></i>Yapılacak</span>
                                    {% endif %}
                                </td>
                                {% if session.get('kullanici_id') %}
                                    <td class="text-end">
                                        {% if gorev.kulup_id in yonetilen_kulupler %}
                                            <a href="{{ url_for('gorev_duzenle', id=gorev.id) }}" class="btn btn-outline-primary btn-sm rounded-3 px-2 me-1" title="Düzenle"><i class="bi bi-pencil"></i></a>
                                            <a href="{{ url_for('gorev_sil', id=gorev.id) }}" class="btn btn-outline-danger btn-sm rounded-3 px-2" onclick="return confirm('Bu görevi silmek istediğinize emin misiniz?')" title="Sil"><i class="bi bi-trash"></i></a>
                                        {% else %}
                                            <span class="text-muted small">Yetki Yok</span>
                                        {% endif %}
                                    </td>
                                {% endif %}
                            </tr>
                        {% endfor %}
                    {% else %}
                        <tr>
                            <td colspan="6" class="text-center py-4 text-muted">
                                <i class="bi bi-list-check fs-2 d-block mb-2 opacity-50"></i>
                                Kayıtlı görev bulunmuyor.
                            </td>
                        </tr>
                    {% endif %}
                </tbody>
            </table>
        </div>
    </div>
</div>

<script>
    document.getElementById('taskSearch').addEventListener('input', function(e) {
        const query = e.target.value.toLowerCase();
        const rows = document.querySelectorAll('#tasksTable tbody tr');
        rows.forEach(row => {
            const name = row.cells[1].textContent.toLowerCase();
            const club = row.cells[2].textContent.toLowerCase();
            const status = row.cells[4].textContent.toLowerCase();
            if (name.includes(query) || club.includes(query) || status.includes(query)) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    });
</script>
{% endblock %}"""
}

for dosya_adi, icerik in TEMPLATES.items():
    yol = os.path.join(TEMPLATES_DIZINI, dosya_adi)
    with open(yol, 'w', encoding='utf-8') as f:
        f.write(icerik)
    print(f"Template yazıldı: {dosya_adi}")

# 4. CSS Kodlarının (Style.css) Yazılması
print("\n[4/6] CSS dosyası (style.css) oluşturuluyor...")

CSS_ICERIK = """@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

:root {
    --primary-color: #6366f1;
    --primary-hover: #4f46e5;
    --primary-light: #e0e7ff;
    --secondary-color: #06b6d4;
    --background-color: #f8fafc;
    --card-background: #ffffff;
    --text-color: #1e293b;
    --text-muted: #64748b;
    --border-color: #e2e8f0;
    --success-color: #10b981;
    --warning-color: #f59e0b;
    --danger-color: #ef4444;
}

body {
    font-family: 'Outfit', sans-serif;
    background-color: var(--background-color);
    color: var(--text-color);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
}

/* Glassmorphism Navigation Bar */
.navbar {
    background: rgba(255, 255, 255, 0.85);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border-bottom: 1px solid var(--border-color);
    box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
}

.navbar-brand {
    font-weight: 700;
}

/* Beautiful Hero Banner */
.hero-section {
    background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
    position: relative;
    overflow: hidden;
}

.hero-section::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -20%;
    width: 300px;
    height: 300px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.1);
    filter: blur(50px);
}

/* Modern Card Styling */
.card {
    background-color: var(--card-background);
    border: 1px solid var(--border-color);
    border-radius: 16px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.card:hover {
    transform: translateY(-5px);
    box-shadow: 0 12px 20px -8px rgba(0, 0, 0, 0.08), 0 4px 6px -2px rgba(0, 0, 0, 0.04) !important;
}

.club-card-col .card {
    border-top: 4px solid var(--primary-color);
}

.club-card-col:nth-child(2n) .card {
    border-top-color: var(--secondary-color);
}

.club-card-col:nth-child(3n) .card {
    border-top-color: var(--success-color);
}

/* Stat Cards */
.stat-card {
    border-radius: 16px;
}

/* Custom Text Limit for description */
.text-truncate-3 {
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;  
    overflow: hidden;
}

/* Inputs & Form Elements */
.form-control, .form-select {
    border-radius: 10px;
    border: 1px solid var(--border-color);
    padding: 10px 14px;
    font-size: 0.95rem;
    transition: all 0.2s ease-in-out;
}

.form-control:focus, .form-select:focus {
    border-color: var(--primary-color);
    box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.15);
}

/* Table Style Improvements */
.table {
    margin-bottom: 0;
}

.table th {
    font-weight: 600;
    text-transform: uppercase;
    font-size: 0.75rem;
    letter-spacing: 0.05em;
    color: var(--text-muted);
}

.table td {
    padding: 1rem 0.75rem;
    color: var(--text-color);
}

/* Pills & Tabs Styling */
.nav-pills .nav-link {
    border-radius: 10px;
    color: var(--text-muted);
    font-weight: 500;
    padding: 10px 20px;
    transition: all 0.2s ease;
}

.nav-pills .nav-link.active {
    background-color: var(--primary-color);
    color: #ffffff;
}

/* Buttons */
.btn {
    border-radius: 10px;
    font-weight: 500;
    transition: all 0.2s ease;
}

.btn-primary {
    background-color: var(--primary-color);
    border-color: var(--primary-color);
}

.btn-primary:hover {
    background-color: var(--primary-hover);
    border-color: var(--primary-hover);
}

/* Custom Badges */
.badge {
    font-weight: 500;
}
"""

with open(os.path.join(CSS_DIZINI, 'style.css'), 'w', encoding='utf-8') as f:
    f.write(CSS_ICERIK)
print("style.css yazıldı.")

# 5. SQL Server Veritabanı Kurulumu ve Tablo Tanımları (club_system)
print("\n[5/6] SQL Server veritabanı kuruluyor...")
try:
    import pyodbc
    
    # 1. Master veritabanına bağlanıp veritabanını oluştur
    sunucu = 'DESKTOP-OGPL55D\\SQLEXPRESS'
    master_conn = None
    try:
        master_conn = pyodbc.connect('Driver={SQL Server};Server=DESKTOP-OGPL55D\\SQLEXPRESS;Database=master;Trusted_Connection=yes;', autocommit=True)
    except Exception:
        try:
            sunucu = 'localhost'
            master_conn = pyodbc.connect('Driver={SQL Server};Server=localhost;Database=master;Trusted_Connection=yes;', autocommit=True)
        except Exception:
            try:
                sunucu = '.\\SQLEXPRESS'
                master_conn = pyodbc.connect('Driver={SQL Server};Server=.\\SQLEXPRESS;Database=master;Trusted_Connection=yes;', autocommit=True)
            except Exception as e:
                print("SQL Server'a bağlanılamadı! Lütfen SQL Server servislerinizin açık olduğundan emin olun.")
                raise e
            
    cursor = master_conn.cursor()
    cursor.execute("IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'club_system') CREATE DATABASE club_system")
    cursor.close()
    master_conn.close()
    print("club_system veritabanı doğrulandı/oluşturuldu.")
    
    # 2. Yeni oluşturulan veritabanına bağlanıp tabloları ve verileri ekle
    conn = pyodbc.connect(f'Driver={{SQL Server}};Server={sunucu};Database=club_system;Trusted_Connection=yes;')
    cursor = conn.cursor()
    
    # Eskileri temizle
    print("Eski tablolar temizleniyor...")
    cursor.execute("IF OBJECT_ID('dbo.ogrenci', 'U') IS NOT NULL DROP TABLE dbo.ogrenci")
    cursor.execute("IF OBJECT_ID('dbo.yonetici', 'U') IS NOT NULL DROP TABLE dbo.yonetici")
    cursor.execute("IF OBJECT_ID('dbo.gorev', 'U') IS NOT NULL DROP TABLE dbo.gorev")
    cursor.execute("IF OBJECT_ID('dbo.etkinlik', 'U') IS NOT NULL DROP TABLE dbo.etkinlik")
    cursor.execute("IF OBJECT_ID('dbo.kulup', 'U') IS NOT NULL DROP TABLE dbo.kulup")
    conn.commit()
    
    # Tabloları oluştur
    print("Tablolar oluşturuluyor...")
    cursor.execute("""
    CREATE TABLE kulup (
        id INT IDENTITY(1,1) PRIMARY KEY,
        ad VARCHAR(255) NOT NULL,
        aciklama VARCHAR(MAX),
        kurulus_tarihi VARCHAR(50)
    )
    """)
    cursor.execute("""
    CREATE TABLE ogrenci (
        id INT IDENTITY(1,1) PRIMARY KEY,
        ad VARCHAR(100) NOT NULL,
        soyad VARCHAR(100) NOT NULL,
        eposta VARCHAR(255),
        telefon VARCHAR(20),
        kulup_id INT,
        FOREIGN KEY(kulup_id) REFERENCES kulup(id) ON DELETE CASCADE
    )
    """)
    cursor.execute("""
    CREATE TABLE yonetici (
        id INT IDENTITY(1,1) PRIMARY KEY,
        kullanici_adi VARCHAR(100) NOT NULL UNIQUE,
        sifre VARCHAR(100) NOT NULL,
        rol VARCHAR(50) NOT NULL,
        kulup_id INT,
        FOREIGN KEY(kulup_id) REFERENCES kulup(id) ON DELETE CASCADE
    )
    """)
    cursor.execute("""
    CREATE TABLE gorev (
        id INT IDENTITY(1,1) PRIMARY KEY,
        gorev_tanimi VARCHAR(MAX) NOT NULL,
        son_tarih VARCHAR(50),
        durum VARCHAR(50) DEFAULT 'Yapılacak',
        kulup_id INT,
        FOREIGN KEY(kulup_id) REFERENCES kulup(id) ON DELETE CASCADE
    )
    """)
    cursor.execute("""
    CREATE TABLE etkinlik (
        id INT IDENTITY(1,1) PRIMARY KEY,
        etkinlik_adi VARCHAR(255) NOT NULL,
        tarih VARCHAR(50),
        yer VARCHAR(255),
        kulup_id INT,
        FOREIGN KEY(kulup_id) REFERENCES kulup(id) ON DELETE CASCADE
    )
    """)
    conn.commit()
    
    # Örnek test verilerini ekle
    print("Örnek veriler yükleniyor...")
    
    # Kulüpler
    cursor.executemany("INSERT INTO kulup (ad, aciklama, kurulus_tarihi) VALUES (?, ?, ?)", [
        ('Yazılım ve Yapay Zeka Kulübü', 'Yazılım geliştirme, yapay zeka ve teknoloji odaklı projeler üretir.', '2022-10-15'),
        ('Müzik ve Sahne Sanatları Kulübü', 'Müzik dinletileri, tiyatro oyunları ve sanat atölyeleri düzenler.', '2019-04-12'),
        ('Gezi ve Dağcılık Kulübü', 'Doğa yürüyüşleri, kamp etkinlikleri ve kültür gezileri organize eder.', '2020-09-01'),
        ('Fotoğrafçılık ve Görsel Sanatlar Kulübü', 'Sokak fotoğrafçılığı, sergiler ve dijital kurgu atölyeleri düzenler.', '2021-03-20'),
        ('Spor ve Sağlıklı Yaşam Kulübü', 'Futbol turnuvaları, trekking gezileri ve sağlıklı yaşam seminerleri sunar.', '2023-02-10')
    ])
    conn.commit()
    
    # Yöneticiler
    cursor.executemany("INSERT INTO yonetici (kullanici_adi, sifre, rol, kulup_id) VALUES (?, ?, ?, ?)", [
        ('admin', 'admin123', 'super', None),
        ('yazilim_admin', 'yazilim123', 'kulup', 1),
        ('muzik_admin', 'muzik123', 'kulup', 2),
        ('gezi_admin', 'gezi123', 'kulup', 3),
        ('fotograf_admin', 'fotograf123', 'kulup', 4),
        ('spor_admin', 'spor123', 'kulup', 5)
    ])
    conn.commit()
    
    # Öğrenciler
    cursor.executemany("INSERT INTO ogrenci (ad, soyad, eposta, telefon, kulup_id) VALUES (?, ?, ?, ?, ?)", [
        # Yazılım (7 üye)
        ('Ahmet', 'Yılmaz', 'ahmet.yilmaz@edu.tr', '05551112233', 1),
        ('Ayşe', 'Kaya', 'ayse.kaya@edu.tr', '05551112244', 1),
        ('Can', 'Özkan', 'can.ozkan@edu.tr', '05551112299', 1),
        ('Derya', 'Güneş', 'derya.gunes@edu.tr', '05551112300', 1),
        ('Eren', 'Yıldız', 'eren.yildiz@edu.tr', '05551112311', 1),
        ('Füsun', 'Yavuz', 'fusun.yavuz@edu.tr', '05551112322', 1),
        ('Gökhan', 'Aydın', 'gokhan.aydin@edu.tr', '05551112333', 1),
        
        # Müzik (4 üye)
        ('Mehmet', 'Demir', 'mehmet.demir@edu.tr', '05551112255', 2),
        ('Fatma', 'Çelik', 'fatma.celik@edu.tr', '05551112266', 2),
        ('Hakan', 'Şahin', 'hakan.sahin@edu.tr', '05551112344', 2),
        ('İrem', 'Bulut', 'irem.bulut@edu.tr', '05551112355', 2),
        
        # Gezi (6 üye)
        ('Ali', 'Öztürk', 'ali.ozturk@edu.tr', '05551112277', 3),
        ('Zeynep', 'Arslan', 'zeynep.arslan@edu.tr', '05551112288', 3),
        ('Kaan', 'Kartal', 'kaan.kartal@edu.tr', '05551112366', 3),
        ('Leyla', 'Polat', 'leyla.polat@edu.tr', '05551112377', 3),
        ('Murat', 'Koç', 'murat.koc@edu.tr', '05551112388', 3),
        ('Nihal', 'Tekin', 'nihal.tekin@edu.tr', '05551112399', 3),
        
        # Fotoğrafçılık (5 üye)
        ('Oğuz', 'Sarı', 'oguz.sari@edu.tr', '05551112400', 4),
        ('Pelin', 'Aksoy', 'pelin.aksoy@edu.tr', '05551112411', 4),
        ('Rıza', 'Turan', 'riza.turan@edu.tr', '05551112422', 4),
        ('Selin', 'Köse', 'selin.kose@edu.tr', '05551112433', 4),
        ('Tolga', 'Uçar', 'tolga.ucar@edu.tr', '05551112444', 4),
        
        # Spor (8 üye)
        ('Umut', 'Kılıç', 'umut.kilic@edu.tr', '05551112455', 5),
        ('Vildan', 'Çetin', 'vildan.cetin@edu.tr', '05551112466', 5),
        ('Yusuf', 'Eser', 'yusuf.eser@edu.tr', '05551112477', 5),
        ('Zehra', 'Aslan', 'zehra.aslan@edu.tr', '05551112488', 5),
        ('Barış', 'Deniz', 'baris.deniz@edu.tr', '05551112499', 5),
        ('Ceren', 'Yılmaz', 'ceren.yilmaz2@edu.tr', '05551112500', 5),
        ('Deniz', 'Taş', 'deniz.tas@edu.tr', '05551112511', 5),
        ('Elif', 'Toprak', 'elif.toprak@edu.tr', '05551112522', 5)
    ])
    conn.commit()
    
    # Etkinlikler
    cursor.executemany("INSERT INTO etkinlik (etkinlik_adi, tarih, yer, kulup_id) VALUES (?, ?, ?, ?)", [
        ('Python & Flask Eğitimi', '2026-06-05', 'Mühendislik Fakültesi D-101', 1),
        ('Yıl Sonu Bahar Konseri', '2026-06-12', 'Üniversite Amfi Tiyatro', 2),
        ('Uludağ Kampı ve Doğa Yürüyüşü', '2026-06-20', 'Bursa - Uludağ Milli Parkı', 3),
        ('Sokak Fotoğrafçılığı Atölyesi', '2026-06-08', 'Karaköy ve Tarihi Yarımada', 4),
        ('Bahar Dönemi Futbol Turnuvası', '2026-06-15', 'Üniversite Halı Sahası', 5)
    ])
    conn.commit()
    
    # Görevler
    cursor.executemany("INSERT INTO gorev (gorev_tanimi, son_tarih, durum, kulup_id) VALUES (?, ?, ?, ?)", [
        ('Afiş tasarımı ve sosyal medya paylaşımları', '2026-06-01', 'Yapılıyor', 1),
        ('Katılımcı kayıt listesinin hazırlanması', '2026-06-04', 'Yapılacak', 1),
        ('Müzik aletlerinin kiralanması ve ses sistemi kontrolü', '2026-06-10', 'Yapılacak', 2),
        ('Kamp izin dilekçesinin Rektörlüğe sunulması', '2026-06-05', 'Tamamlandı', 3),
        ('Gerekli kamp malzemelerinin listelenmesi', '2026-06-10', 'Yapılıyor', 3),
        ('Fotoğraf sergisi salonunun rezerve edilmesi', '2026-06-03', 'Yapılacak', 4),
        ('Turnuva ödüllerinin sipariş edilmesi', '2026-06-12', 'Yapılacak', 5)
    ])
    conn.commit()
    
    cursor.close()
    conn.close()
    print("club_system veritabanı SQL Server üzerinde başarıyla oluşturuldu ve ilklendirildi.")
    
except Exception as e:
    print(f"\n[UYARI] SQL Server bağlantısı kurulamadı: {e}")
    print("Proje kodları başarıyla oluşturuldu fakat yerel SQL Server veritabanınız otomatik başlatılamadı.")
    print("Lütfen SQL Server servisinizin çalıştığından emin olup 'ssms_veritabanı_kodları.sql' dosyasını SSMS 2021'de kendiniz çalıştırın.")

# 6. Kısayol Dosyasının (Masaüstü Otomasyonu) Yazılması
print("\n[6/6] Masaüstü kısayolu oluşturuluyor...")

def find_desktop():
    user_profile = os.environ.get('USERPROFILE', '')
    if not user_profile:
        return None
    candidates = [
        os.path.join(user_profile, 'Desktop'),
        os.path.join(user_profile, 'Masaüstü'),
        os.path.join(user_profile, 'OneDrive', 'Desktop'),
        os.path.join(user_profile, 'OneDrive', 'Masaüstü')
    ]
    for c in candidates:
        if os.path.exists(c) and os.path.isdir(c):
            return c
    return None

desktop_yolu = find_desktop()

if sys.platform == 'win32':
    kisayol_adi = "Kulüp Sistemini Başlat.bat"
    
    BAT_ICERIK = f"""@echo off
title Universite Kulup Yonetim Sistemi
cd /d "{PROJE_DIZINI}"
echo ========================================================
echo   UNIVERSITE KULUP YONETIM SISTEMI BASLATILIYOR...
echo ========================================================
echo.
echo SQL Server baglantisi kontrol ediliyor ve Flask sunucusu aciliyor.
echo Kapatmak icin bu pencereyi kapatabilir veya Ctrl+C yapabilirsiniz.
echo.
:: Tarayiciyi paralel olarak 2 saniye gecikmeyle ac
start "" cmd /c "timeout /t 2 >nul && start http://127.0.0.1:5000"
:: Flask sunucusunu baslat
python app.py
pause
"""
    
    if desktop_yolu:
        bat_yolu = os.path.join(desktop_yolu, kisayol_adi)
        with open(bat_yolu, 'w', encoding='ansi') as f:
            f.write(BAT_ICERIK)
        print(f"Windows Masaüstü kısayolu oluşturuldu: {bat_yolu}")
    else:
        bat_yolu = os.path.join(PROJE_DIZINI, kisayol_adi)
        with open(bat_yolu, 'w', encoding='ansi') as f:
            f.write(BAT_ICERIK)
        print(f"Masaüstü konumu bulunamadı. Kısayol proje klasörüne yazıldı: {bat_yolu}")

# Flask ve pyodbc gereksinimleri için requirements.txt yaz
with open(os.path.join(PROJE_DIZINI, 'requirements.txt'), 'w', encoding='utf-8') as f:
    f.write("Flask>=2.0.0\npyodbc>=4.0.0\n")
print("requirements.txt yazıldı.")

print("\n--------------------------------------------------")
print("KURULUM TAMAMLANDI VE SQL SERVER UYUMLU HALE GETİRİLDİ!")
print("Projeyi başlatmak için Masaüstünüzdeki kısayola çift tıklayın.")
print("Veritabanınızı SSMS 2021 üzerinden takip etmek için 'ssms_veritabanı_kodları.sql' dosyasını inceleyin.")
print("--------------------------------------------------")
