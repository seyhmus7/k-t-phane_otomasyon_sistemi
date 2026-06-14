# -*- coding: utf-8 -*-
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
# Genellikle '.' veya 'localhost' veya '.\SQLEXPRESS' kullanılır.
SQL_SERVER_NAME = 'DESKTOP-OGPL55D\\SQLEXPRESS'
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
    """SQL Server veritabanı bağlantısı oluşturur (Windows Authentication kullanarak)."""
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
                f'Server=.\\SQLEXPRESS;'
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
