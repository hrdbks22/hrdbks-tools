@echo off
setlocal
cd /d "%~dp0"
title HRD TOOLS - PT. BERKAT KARUNIA SURYA

echo ==========================================
echo   HRD TOOLS - PT. BERKAT KARUNIA SURYA
echo ==========================================
echo.
echo Pemeriksaan file aplikasi dan Python...
echo.

REM Ambil file aplikasi dari GitHub jika belum ada di folder ini.
where curl >nul 2>nul
if errorlevel 1 goto no_curl

if not exist "hrd_tools.py" (
    echo Mengunduh hrd_tools.py dari GitHub...
    curl -fL --retry 3 -o "hrd_tools.py" "https://raw.githubusercontent.com/hrdbks22/hrdbks-tools/desktop-tkinter-local/desktop/hrd_tools.py"
    if errorlevel 1 goto download_error
)
if not exist "requirements.txt" (
    echo Mengunduh requirements.txt dari GitHub...
    curl -fL --retry 3 -o "requirements.txt" "https://raw.githubusercontent.com/hrdbks22/hrdbks-tools/desktop-tkinter-local/desktop/requirements.txt"
    if errorlevel 1 goto download_error
)

set "PYTHON_EXE="
set "PYTHON_LAUNCHER="

REM Cari Python 3.12 yang sudah terpasang.
where py >nul 2>nul
if not errorlevel 1 (
    py -3.12 --version >nul 2>nul
    if not errorlevel 1 set "PYTHON_LAUNCHER=py -3.12"
)

REM Coba lokasi instalasi per-user yang umum.
if not defined PYTHON_LAUNCHER (
    if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
        set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python312\python.exe"
    )
)

REM Pasang Python 3.12 otomatis jika belum ada.
if not defined PYTHON_LAUNCHER if not defined PYTHON_EXE (
    echo Python 3.12 belum ditemukan.
    where winget >nul 2>nul
    if errorlevel 1 goto no_winget
    echo Mengunduh dan memasang Python 3.12 64-bit...
    winget install --id Python.Python.3.12 -e --scope user --silent --accept-package-agreements --accept-source-agreements
    if errorlevel 1 goto install_error
    if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
        set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python312\python.exe"
    )
)
if not defined PYTHON_LAUNCHER if not defined PYTHON_EXE goto install_error

echo.
echo [1/3] Memeriksa Python...
if defined PYTHON_LAUNCHER (
    %PYTHON_LAUNCHER% --version
) else (
    "%PYTHON_EXE%" --version
)
if errorlevel 1 goto python_error

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo [2/3] Membuat lingkungan Python khusus aplikasi...
    if defined PYTHON_LAUNCHER (
        %PYTHON_LAUNCHER% -m venv .venv
    ) else (
        "%PYTHON_EXE%" -m venv .venv
    )
    if errorlevel 1 goto venv_error
) else (
    echo.
    echo [2/3] Lingkungan khusus aplikasi sudah tersedia.
)

echo.
echo Memasang pustaka aplikasi hanya di .venv...
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

:no_curl
echo [GAGAL] Perintah curl tidak tersedia pada Windows ini.
echo Gunakan Windows 10/11 yang sudah diperbarui, lalu coba lagi.
pause
exit /b 1

:download_error
echo [GAGAL] File aplikasi tidak berhasil diunduh dari GitHub.
echo Periksa koneksi internet, lalu jalankan ulang BAT.
pause
exit /b 1

:no_winget
echo [GAGAL] Python 3.12 belum ada dan winget tidak ditemukan.
echo Perbarui App Installer dari Microsoft Store, lalu ulangi.
pause
exit /b 1

:install_error
echo [GAGAL] Python 3.12 tidak berhasil dipasang atau tidak ditemukan.
echo Pastikan internet aktif dan Windows mendukung winget.
pause
exit /b 1

:python_error
echo [GAGAL] Python tidak dapat dijalankan.
pause
exit /b 1

:venv_error
echo [GAGAL] Lingkungan Python khusus tidak berhasil dibuat.
echo Pastikan instalasi Python menyertakan pip dan venv.
pause
exit /b 1

:package_error
echo [GAGAL] Pustaka aplikasi gagal dipasang.
echo Periksa koneksi internet dan coba jalankan kembali.
pause
exit /b 1
