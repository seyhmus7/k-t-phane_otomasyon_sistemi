@echo off
title Universite Kulup Yonetim Sistemi
cd /d "C:\Users\User\.gemini\antigravity\scratch\kulup_yonetim_sistemi"
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
