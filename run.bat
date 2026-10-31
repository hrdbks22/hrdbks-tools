@echo off
title HRD Tools - PT. Berkat Karunia Surya
cd /d "%~dp0"

echo ==========================================
echo       HRD TOOLS - LOCAL SQLITE VERSION
echo ==========================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python belum terpasang atau belum masuk PATH.
    echo Instal Python 3.10 atau lebih baru, lalu aktifkan opsi Add Python to PATH.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Membuat virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Gagal membuat virtual environment.
        pause
        exit /b 1
    )
)

echo [INFO] Memasang atau memperbarui library...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo [ERROR] Gagal memperbarui pip.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Gagal memasang library. Periksa koneksi internet.
    pause
    exit /b 1
)

echo.
echo [INFO] Menjalankan aplikasi HRD Tools...
echo Buka browser: http://localhost:8501
echo Biarkan jendela ini tetap terbuka selama aplikasi digunakan.
echo.

".venv\Scripts\python.exe" -m streamlit run app.py

echo.
echo Aplikasi sudah berhenti.
pause
