@echo off
setlocal EnableExtensions
title HRD Tools - PT. Berkat Karunia Surya
cd /d "%~dp0"

echo =================================================
echo       HRD TOOLS - PEMERIKSAAN DAN INSTALASI
echo =================================================
echo.

REM --- Cek package manager untuk instalasi otomatis ---
where winget >nul 2>nul
if errorlevel 1 (
    echo [PERINGATAN] winget tidak ditemukan.
    echo Jika Python 3.12 atau VC++ belum tersedia, installer otomatis
    echo tidak dapat dijalankan. Silakan instal dari tautan yang ditampilkan.
    set "HAS_WINGET=0"
) else (
    set "HAS_WINGET=1"
)

REM --- Cek dan instal Python 3.12 ---
echo [1/5] Memeriksa Python 3.12...
where py >nul 2>nul
if errorlevel 1 goto INSTALL_PYTHON
py -3.12 --version >nul 2>nul
if not errorlevel 1 goto PYTHON_OK

:INSTALL_PYTHON
if "%HAS_WINGET%"=="0" goto PYTHON_MANUAL
echo Python 3.12 belum tersedia. Mencoba instal otomatis...
winget install --id Python.Python.3.12 --exact --scope user --silent --accept-package-agreements --accept-source-agreements
if errorlevel 1 (
    echo [PERINGATAN] Instalasi otomatis Python tidak berhasil.
    goto PYTHON_MANUAL
)
REM Refresh PATH untuk sesi ini setelah instalasi
set "PATH=%LOCALAPPDATA%\Programs\Python\Launcher;%LOCALAPPDATA%\Programs\Python\Python312;%PATH%"
where py >nul 2>nul
if errorlevel 1 goto PYTHON_MANUAL
py -3.12 --version >nul 2>nul
if errorlevel 1 goto PYTHON_MANUAL
goto PYTHON_OK

:PYTHON_MANUAL
echo.
echo [GAGAL] Python 3.12 belum siap.
echo Instal Python 3.12 64-bit: https://www.python.org/downloads/release/python-31210/
echo Saat instalasi, centang "Add Python to PATH" dan Python Launcher.
echo Setelah selesai, jalankan run.bat kembali.
pause
exit /b 1

:PYTHON_OK
for /f "tokens=*" %%V in ('py -3.12 --version') do echo Ditemukan %%V
echo.

REM --- Cek dan instal Microsoft Visual C++ Runtime x64 ---
echo [2/5] Memeriksa Microsoft Visual C++ Runtime x64...
reg query "HKLM\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" /v Installed 2>nul | find "0x1" >nul
if not errorlevel 1 goto VC_OK

echo Visual C++ Runtime belum terdeteksi. Mencoba instal otomatis...
if "%HAS_WINGET%"=="0" goto VC_MANUAL
winget install --id Microsoft.VCRedist.2015+.x64 --exact --silent --accept-package-agreements --accept-source-agreements
if errorlevel 1 (
    echo [PERINGATAN] Instalasi otomatis Visual C++ tidak berhasil.
    goto VC_MANUAL
)
goto VC_OK

:VC_MANUAL
echo.
echo Instal Microsoft Visual C++ Redistributable x64:
echo https://aka.ms/vs/17/release/vc_redist.x64.exe
echo Jalankan installer tersebut, lalu jalankan run.bat kembali.
pause
exit /b 1

:VC_OK
echo Visual C++ Runtime siap atau instalasi telah dijalankan.
echo.

REM --- Pastikan virtual environment menggunakan Python 3.12 ---
echo [3/5] Memeriksa lingkungan aplikasi...
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3,12) else 1)" >nul 2>nul
    if errorlevel 1 (
        echo Environment lama bukan Python 3.12. Membuat ulang...
        rmdir /s /q ".venv"
    )
)

if not exist ".venv\Scripts\python.exe" (
    echo Membuat virtual environment Python 3.12...
    py -3.12 -m venv ".venv"
    if errorlevel 1 (
        echo [ERROR] Gagal membuat virtual environment.
        pause
        exit /b 1
    )
)

REM --- Instal dependensi proyek ---
echo.
echo [4/5] Memeriksa dan memasang seluruh dependensi...
".venv\Scripts\python.exe" -m ensurepip --upgrade
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo [ERROR] Pip gagal diperbarui. Periksa koneksi internet.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m pip install --no-cache-dir -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Instalasi dependensi gagal. Periksa koneksi internet.
    pause
    exit /b 1
)

REM --- Uji modul penting ---
echo.
echo [5/5] Menguji NumPy, Pandas, dan Streamlit...
".venv\Scripts\python.exe" -c "import numpy, pandas, streamlit; print('NumPy:', numpy.__version__); print('Pandas:', pandas.__version__); print('Streamlit:', streamlit.__version__)"
if errorlevel 1 (
    echo.
    echo [ERROR] Uji library gagal.
    echo Jika pesan menyebut DLL, restart Windows setelah instal VC++,
    echo lalu jalankan run.bat kembali.
    pause
    exit /b 1
)

echo.
echo =================================================
echo Semua pemeriksaan selesai. Menjalankan HRD Tools.
echo Browser: http://localhost:8501
echo Database lokal: hrd_tools.db
echo Jangan tutup jendela ini selama aplikasi digunakan.
echo =================================================
echo.

".venv\Scripts\python.exe" -m streamlit run app.py

echo.
echo Aplikasi HRD Tools telah berhenti.
pause
endlocal
