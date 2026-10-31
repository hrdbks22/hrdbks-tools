@echo off
setlocal
cd /d "%~dp0"
title HRD TOOLS - PT. BERKAT KARUNIA SURYA

echo ==========================================
echo   HRD TOOLS - PT. BERKAT KARUNIA SURYA
echo ==========================================
echo.

set "PYTHON_CMD="
where py >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=py -3"

if not defined PYTHON_CMD (
    where python >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    echo [GAGAL] Python 3 belum ditemukan di komputer ini.
    echo Silakan instal Python 3 dari https://www.python.org/downloads/
    echo Saat instalasi, centang pilihan "Add Python to PATH".
    echo Setelah selesai, jalankan file BAT ini kembali.
    echo.
    pause
    exit /b 1
)

echo [1/3] Memeriksa Python...
%PYTHON_CMD% --version
if errorlevel 1 goto python_error

echo.
echo [2/3] Memasang / memeriksa pustaka Excel...
%PYTHON_CMD% -m pip --version >nul 2>nul
if errorlevel 1 (
    echo [GAGAL] pip tidak tersedia pada instalasi Python.
    echo Perbaiki instalasi Python atau aktifkan pip, lalu coba lagi.
    pause
    exit /b 1
)
%PYTHON_CMD% -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [GAGAL] Instalasi pustaka tidak berhasil.
    echo Periksa koneksi internet lalu jalankan ulang file BAT ini.
    pause
    exit /b 1
)

echo.
echo [3/3] Menjalankan aplikasi HRD Tools...
%PYTHON_CMD% hrd_tools.py
if errorlevel 1 (
    echo.
    echo [GAGAL] Aplikasi berhenti karena terjadi kesalahan.
    echo Jika muncul pesan error di atas, kirimkan foto atau salin pesannya.
)

echo.
echo Proses selesai.
pause
exit /b 0

:python_error
echo [GAGAL] Python tidak dapat dijalankan.
echo Pastikan instalasi Python 3 sudah benar.
pause
exit /b 1
