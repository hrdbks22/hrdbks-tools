# HRD Tools Desktop

Aplikasi desktop lokal untuk administrasi HRD PT. Berkat Karunia Surya.

## Menjalankan
1. Install Python 3.10 atau lebih baru.
2. Buka Command Prompt pada folder proyek.
3. Jalankan: `py -m pip install -r requirements.txt`
4. Jalankan: `py hrd_tools.py`

Database SQLite dibuat lokal sebagai `hrd_tools.db` di folder aplikasi. Tidak menggunakan server atau hosting.

## Format impor
Pembaca mendeteksi isi file: XLSX/XLSM, XLSB, XLS lama, dan HTML table yang memakai ekstensi XLS.
Ekspor saat ini hanya XLSX.

## Catatan status
Ini adalah fondasi desktop tahap awal: login lokal, database, dashboard, impor/ekspor master karyawan, dan navigasi modul. Modul absensi, SP, evaluasi H3, kontrak, panggilan, riwayat, serta pengaturan izin rinci masih perlu diselesaikan dan diuji dengan workbook HRIS Presensi dan Employee Tracker asli.
