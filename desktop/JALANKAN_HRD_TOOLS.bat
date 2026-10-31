@echo off
setlocal
cd /d "%~dp0"
title HRD TOOLS - PT. BERKAT KARUNIA SURYA

echo ==========================================
echo   HRD TOOLS - PT. BERKAT KARUNIA SURYA
echo ==========================================
echo.
echo [A] Memeriksa file aplikasi...
echo Folder kerja: %CD%

REM Unduh file yang hilang atau kosong dengan PowerShell bawaan Windows.
if not exist "hrd_tools.py" goto get_app
for %%A in ("hrd_tools.py") do if %%~zA LEQ 0 goto get_app
goto check_requirements

:get_app
echo Mengunduh hrd_tools.py dari GitHub...
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -UseBasicParsing 'https://raw.githubusercontent.com/hrdbks22/hrdbks-tools/desktop-tkinter-local/desktop/hrd_tools.py' -OutFile 'hrd_tools.py'; if ((Get-Item 'hrd_tools.py').Length -lt 1000) { throw 'File aplikasi terlalu kecil atau tidak valid' } } catch { Write-Host $_; exit 1 }"
if errorlevel 1 goto download_error

:check_requirements
if not exist "requirements.txt" goto get_requirements
for %%A in ("requirements.txt") do if %%~zA LEQ 0 goto get_requirements
goto check_python

:get_requirements
echo Mengunduh requirements.txt dari GitHub...
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -UseBasicParsing 'https://raw.githubusercontent.com/hrdbks22/hrdbks-tools/desktop-tkinter-local/desktop/requirements.txt' -OutFile 'requirements.txt'; if ((Get-Item 'requirements.txt').Length -lt 10) { throw 'File requirements tidak valid' } } catch { Write-Host $_; exit 1 }"
if errorlevel 1 goto download_error

:check_python
echo.
echo [B] Memeriksa Python 3.12...
set "PYTHON_EXE="
set "PYTHON_LAUNCHER="
where py >nul 2>nul
if not errorlevel 1 (
    py -3.12 --version >nul 2>nul
    if not errorlevel 1 set "PYTHON_LAUNCHER=py -3.12"
)
if not defined PYTHON_LAUNCHER if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python312\python.exe"

if not defined PYTHON_LAUNCHER if not defined PYTHON_EXE (
    echo Python 3.12 belum ditemukan. Mencoba instalasi otomatis...
    where winget >nul 2>nul
    if errorlevel 1 goto no_winget
    winget install --id Python.Python.3.12 -e --scope user --silent --accept-package-agreements --accept-source-agreements
    if errorlevel 1 goto install_error
    if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python312\python.exe"
)
if not defined PYTHON_LAUNCHER if not defined PYTHON_EXE goto install_error

if defined PYTHON_LAUNCHER (
    %PYTHON_LAUNCHER% --version
) else (
    "%PYTHON_EXE%" --version
)
if errorlevel 1 goto python_error

echo.
echo [C] Menyiapkan lingkungan aplikasi...
if not exist ".venv\Scripts\python.exe" (
    if defined PYTHON_LAUNCHER (
        %PYTHON_LAUNCHER% -m venv .venv
    ) else (
        "%PYTHON_EXE%" -m venv .venv
    )
    if errorlevel 1 goto venv_error
)

echo.
echo Memasang pustaka aplikasi di .venv...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto package_error

echo.
echo [D] Menjalankan HRD Tools...
".venv\Scripts\python.exe" hrd_tools.py
if errorlevel 1 echo Aplikasi berhenti. Periksa hrd_tools_error.log.
pause
exit /b 0

:download_error
echo [GAGAL] Tidak dapat mengunduh file dari GitHub.
echo Pastikan internet aktif dan akses GitHub tidak diblokir.
pause
exit /b 1
:no_winget
echo [GAGAL] winget tidak ditemukan untuk memasang Python otomatis.
echo Silakan perbarui App Installer dari Microsoft Store.
pause
exit /b 1
:install_error
echo [GAGAL] Instalasi Python 3.12 otomatis gagal.
pause
exit /b 1
:python_error
echo [GAGAL] Python tidak dapat dijalankan.
pause
exit /b 1
:venv_error
echo [GAGAL] Gagal membuat .venv.
pause
exit /b 1
:package_error
echo [GAGAL] Instalasi pustaka gagal. Periksa koneksi internet.
pause
exit /b 1
