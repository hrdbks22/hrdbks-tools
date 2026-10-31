@echo off
title HRD Tools - PT. Berkat Karunia Surya
cd /d "%~dp0"

echo ==========================================
echo       HRD TOOLS - LOCAL SQLITE VERSION
echo ==========================================
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python Launcher (py) tidak ditemukan.
    echo Instal Python 3.12 64-bit dari https://www.python.org/downloads/
    echo Pastikan Python Launcher ikut terpasang.
    pause
    exit /b 1
)

py -3.12 --version >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python 3.12 belum ditemukan.
    echo Instal Python 3.12 64-bit dari https://www.python.org/downloads/
    pause
    exit /b 1
)

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3,12) else 1)" >nul 2>nul
    if errorlevel 1 (
        echo [INFO] Virtual environment lama bukan Python 3.12.
        echo [INFO] Menghapus environment lama, database tidak dihapus...
        rmdir /s /q ".venv"
    )
)

if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Membuat virtual environment dengan Python 3.12...
    py -3.12 -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Gagal membuat virtual environment.
        pause
        exit /b 1
    )
)

echo [INFO] Memasang library...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo [ERROR] Gagal memperbarui pip.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m pip install --no-cache-dir -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Gagal memasang library. Periksa koneksi internet.
    pause
    exit /b 1
)

echo.
echo [INFO] Memeriksa NumPy dan Pandas...
".venv\Scripts\python.exe" -c "import numpy, pandas; print('NumPy', numpy.__version__, '- Pandas', pandas.__version__)"
if errorlevel 1 (
    echo [ERROR] NumPy/Pandas gagal dimuat.
    echo Coba instal Microsoft Visual C++ Redistributable 2015-2022 x64.
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
