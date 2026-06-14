-- ========================================================
-- ÜNİVERSİTE KULÜP YÖNETİM SİSTEMİ - VERİTABANI KODLARI (MSSQL)
-- SSMS 2021 veya benzeri MS SQL Server istemcileri için uyumludur.
-- ========================================================

-- 1. Veritabanını Oluşturma
IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'club_system')
BEGIN
    CREATE DATABASE club_system;
END
GO

USE club_system;
GO

-- 2. Eski Tabloları Temizleme (Temiz Kurulum İçin)
IF OBJECT_ID('dbo.ogrenci', 'U') IS NOT NULL DROP TABLE dbo.ogrenci;
IF OBJECT_ID('dbo.yonetici', 'U') IS NOT NULL DROP TABLE dbo.yonetici;
IF OBJECT_ID('dbo.gorev', 'U') IS NOT NULL DROP TABLE dbo.gorev;
IF OBJECT_ID('dbo.etkinlik', 'U') IS NOT NULL DROP TABLE dbo.etkinlik;
IF OBJECT_ID('dbo.kulup', 'U') IS NOT NULL DROP TABLE dbo.kulup;
GO

-- 3. Tabloların Oluşturulması (DDL)

CREATE TABLE kulup (
    id INT IDENTITY(1,1) PRIMARY KEY,
    ad VARCHAR(255) NOT NULL,
    aciklama VARCHAR(MAX),
    kurulus_tarihi VARCHAR(50)
);

CREATE TABLE ogrenci (
    id INT IDENTITY(1,1) PRIMARY KEY,
    ad VARCHAR(100) NOT NULL,
    soyad VARCHAR(100) NOT NULL,
    eposta VARCHAR(255),
    telefon VARCHAR(20),
    kulup_id INT,
    FOREIGN KEY(kulup_id) REFERENCES kulup(id) ON DELETE CASCADE
);

CREATE TABLE yonetici (
    id INT IDENTITY(1,1) PRIMARY KEY,
    kullanici_adi VARCHAR(100) NOT NULL UNIQUE,
    sifre VARCHAR(100) NOT NULL,
    rol VARCHAR(50) NOT NULL, -- 'super' veya 'kulup'
    kulup_id INT,
    FOREIGN KEY(kulup_id) REFERENCES kulup(id) ON DELETE CASCADE
);

CREATE TABLE gorev (
    id INT IDENTITY(1,1) PRIMARY KEY,
    gorev_tanimi VARCHAR(MAX) NOT NULL,
    son_tarih VARCHAR(50),
    durum VARCHAR(50) DEFAULT 'Yapılacak', -- 'Yapılacak', 'Yapılıyor', 'Tamamlandı'
    kulup_id INT,
    FOREIGN KEY(kulup_id) REFERENCES kulup(id) ON DELETE CASCADE
);

CREATE TABLE etkinlik (
    id INT IDENTITY(1,1) PRIMARY KEY,
    etkinlik_adi VARCHAR(255) NOT NULL,
    tarih VARCHAR(50),
    yer VARCHAR(255),
    kulup_id INT,
    FOREIGN KEY(kulup_id) REFERENCES kulup(id) ON DELETE CASCADE
);
GO

-- 4. Örnek Test Verilerinin Eklenmesi (DML)

-- Kulüpler
INSERT INTO kulup (ad, aciklama, kurulus_tarihi) VALUES 
('Yazılım ve Yapay Zeka Kulübü', 'Yazılım geliştirme, yapay zeka ve teknoloji odaklı projeler üretir.', '2022-10-15'),
('Müzik ve Sahne Sanatları Kulübü', 'Müzik dinletileri, tiyatro oyunları ve sanat atölyeleri düzenler.', '2019-04-12'),
('Gezi ve Dağcılık Kulübü', 'Doğa yürüyüşleri, kamp etkinlikleri ve kültür gezileri organize eder.', '2020-09-01'),
('Fotoğrafçılık ve Görsel Sanatlar Kulübü', 'Sokak fotoğrafçılığı, sergiler ve dijital kurgu atölyeleri düzenler.', '2021-03-20'),
('Spor ve Sağlıklı Yaşam Kulübü', 'Futbol turnuvaları, trekking gezileri ve sağlıklı yaşam seminerleri sunar.', '2023-02-10');

-- Yöneticiler
INSERT INTO yonetici (kullanici_adi, sifre, rol, kulup_id) VALUES
('admin', 'admin123', 'super', NULL),
('yazilim_admin', 'yazilim123', 'kulup', 1),
('muzik_admin', 'muzik123', 'kulup', 2),
('gezi_admin', 'gezi123', 'kulup', 3),
('fotograf_admin', 'fotograf123', 'kulup', 4),
('spor_admin', 'spor123', 'kulup', 5);

-- Öğrenciler (Farklı sayılarda, toplam 30 üye)
INSERT INTO ogrenci (ad, soyad, eposta, telefon, kulup_id) VALUES
-- Yazılım Kulübü Üyeleri (7 Üye)
('Ahmet', 'Yılmaz', 'ahmet.yilmaz@edu.tr', '05551112233', 1),
('Ayşe', 'Kaya', 'ayse.kaya@edu.tr', '05551112244', 1),
('Can', 'Özkan', 'can.ozkan@edu.tr', '05551112299', 1),
('Derya', 'Güneş', 'derya.gunes@edu.tr', '05551112300', 1),
('Eren', 'Yıldız', 'eren.yildiz@edu.tr', '05551112311', 1),
('Füsun', 'Yavuz', 'fusun.yavuz@edu.tr', '05551112322', 1),
('Gökhan', 'Aydın', 'gokhan.aydin@edu.tr', '05551112333', 1),

-- Müzik Kulübü Üyeleri (4 Üye)
('Mehmet', 'Demir', 'mehmet.demir@edu.tr', '05551112255', 2),
('Fatma', 'Çelik', 'fatma.celik@edu.tr', '05551112266', 2),
('Hakan', 'Şahin', 'hakan.sahin@edu.tr', '05551112344', 2),
('İrem', 'Bulut', 'irem.bulut@edu.tr', '05551112355', 2),

-- Gezi Kulübü Üyeleri (6 Üye)
('Ali', 'Öztürk', 'ali.ozturk@edu.tr', '05551112277', 3),
('Zeynep', 'Arslan', 'zeynep.arslan@edu.tr', '05551112288', 3),
('Kaan', 'Kartal', 'kaan.kartal@edu.tr', '05551112366', 3),
('Leyla', 'Polat', 'leyla.polat@edu.tr', '05551112377', 3),
('Murat', 'Koç', 'murat.koc@edu.tr', '05551112388', 3),
('Nihal', 'Tekin', 'nihal.tekin@edu.tr', '05551112399', 3),

-- Fotoğrafçılık Kulübü Üyeleri (5 Üye)
('Oğuz', 'Sarı', 'oguz.sari@edu.tr', '05551112400', 4),
('Pelin', 'Aksoy', 'pelin.aksoy@edu.tr', '05551112411', 4),
('Rıza', 'Turan', 'riza.turan@edu.tr', '05551112422', 4),
('Selin', 'Köse', 'selin.kose@edu.tr', '05551112433', 4),
('Tolga', 'Uçar', 'tolga.ucar@edu.tr', '05551112444', 4),

-- Spor Kulübü Üyeleri (8 Üye)
('Umut', 'Kılıç', 'umut.kilic@edu.tr', '05551112455', 5),
('Vildan', 'Çetin', 'vildan.cetin@edu.tr', '05551112466', 5),
('Yusuf', 'Eser', 'yusuf.eser@edu.tr', '05551112477', 5),
('Zehra', 'Aslan', 'zehra.aslan@edu.tr', '05551112488', 5),
('Barış', 'Deniz', 'baris.deniz@edu.tr', '05551112499', 5),
('Ceren', 'Yılmaz', 'ceren.yilmaz2@edu.tr', '05551112500', 5),
('Deniz', 'Taş', 'deniz.tas@edu.tr', '05551112511', 5),
('Elif', 'Toprak', 'elif.toprak@edu.tr', '05551112522', 5);

-- Etkinlikler
INSERT INTO etkinlik (etkinlik_adi, tarih, yer, kulup_id) VALUES
('Python & Flask Eğitimi', '2026-06-05', 'Mühendislik Fakültesi D-101', 1),
('Yıl Sonu Bahar Konseri', '2026-06-12', 'Üniversite Amfi Tiyatro', 2),
('Uludağ Kampı ve Doğa Yürüyüşü', '2026-06-20', 'Bursa - Uludağ Milli Parkı', 3),
('Sokak Fotoğrafçılığı Atölyesi', '2026-06-08', 'Karaköy ve Tarihi Yarımada', 4),
('Bahar Dönemi Futbol Turnuvası', '2026-06-15', 'Üniversite Halı Sahası', 5);

-- Görevler
INSERT INTO gorev (gorev_tanimi, son_tarih, durum, kulup_id) VALUES
('Afiş tasarımı ve sosyal medya paylaşımları', '2026-06-01', 'Yapılıyor', 1),
('Katılımcı kayıt listesinin hazırlanması', '2026-06-04', 'Yapılacak', 1),
('Müzik aletlerinin kiralanması ve ses sistemi kontrolü', '2026-06-10', 'Yapılacak', 2),
('Kamp izin dilekçesinin Rektörlüğe sunulması', '2026-06-05', 'Tamamlandı', 3),
('Gerekli kamp malzemelerinin listelenmesi', '2026-06-10', 'Yapılıyor', 3),
('Fotoğraf sergisi salonunun rezerve edilmesi', '2026-06-03', 'Yapılacak', 4),
('Turnuva ödüllerinin sipariş edilmesi', '2026-06-12', 'Yapılacak', 5);
GO
