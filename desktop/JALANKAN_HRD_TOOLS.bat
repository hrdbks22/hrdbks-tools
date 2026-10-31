@echo off
setlocal
cd /d "%~dp0"
title HRD TOOLS - PT. BERKAT KARUNIA SURYA

echo ==========================================
echo   HRD TOOLS - PT. BERKAT KARUNIA SURYA
echo ==========================================
echo.
echo Aplikasi akan menggunakan lingkungan Python khusus di folder .venv.
echo Pustaka HRD Tools tidak akan dipasang ke Python global komputer.
echo.

set "PYTHON_LAUNCHER="
where py >nul 2>nul
if not errorlevel 1 set "PYTHON_LAUNCHER=py -3"

if not defined PYTHON_LAUNCHER (
    where python >nul 2>nul
    if not errorlevel 1 set "PYTHON_LAUNCHER=python"
)

if not defined PYTHON_LAUNCHER (
    echo [GAGAL] Python 3 belum ditemukan.
    echo Instal Python 3.10 atau lebih baru dari:
    echo https://www.python.org/downloads/
    echo Saat instalasi, pastikan Tcl/Tk dan pip ikut dipasang.
    echo Setelah itu jalankan BAT ini kembali.
    pause
    exit /b 1
)

echo [1/3] Memeriksa Python...
%PYTHON_LAUNCHER% --version
if errorlevel 1 goto python_error

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo [2/3] Membuat lingkungan Python khusus aplikasi...
    %PYTHON_LAUNCHER% -m venv .venv
    if errorlevel 1 goto venv_error
) else (
    echo.
    echo [2/3] Lingkungan khusus aplikasi sudah tersedia.
)

echo.
echo Memasang pustaka yang diperlukan hanya di .venv...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto package_error

echo.
echo [3/3] Menjalankan aplikasi HRD Tools...
".venv\Scripts\python.exe" hrd_tools.py
if errorlevel 1 (
    echo.
    echo [GAGAL] Aplikasi berhenti karena terjadi kesalahan.
    echo Periksa file hrd_tools_error.log jika tersedia.
)

echo.
echo Selesai.
pause
exit /b 0

:python_error
echo [GAGAL] Python tidak dapat dijalankan. Periksa instalasi Python.
pause
exit /b 1

:venv_error
echo [GAGAL] Lingkungan Python khusus tidak berhasil dibuat.
echo Pastikan modul venv tersedia pada instalasi Python.
pause
exit /b 1

:package_error
echo [GAGAL] Pustaka aplikasi gagal dipasang.
echo Periksa koneksi internet dan coba jalankan kembali.
pause
exit /b 1
