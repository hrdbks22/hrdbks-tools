# HRD Tools — Implementasi Hybrid Cloud + LAN

## Keputusan operasional
- Data lama CSV/aplikasi lama tidak dimigrasikan. Database baru dimulai kosong.
- Jangan menghapus file lama atau mengganti deployment aktif sebelum cutover disetujui setelah uji penerimaan.
- Target: server LAN tetap dapat dipakai saat internet terputus; perubahan disinkronkan ke Cloud setelah koneksi pulih.

## Komponen target
1. Aplikasi Streamlit di server LAN kantor.
2. PostgreSQL lokal persisten di server LAN.
3. Aplikasi Streamlit Cloud.
4. PostgreSQL Cloud persisten (layanan terkelola).
5. Sync worker dua arah dengan outbox/inbox, UUID event, idempotency, versi entitas, retry, dan conflict queue.
6. Audit log dan backup/restore teruji.

PostgreSQL lokal dan Cloud tidak otomatis saling sinkron. Sinkronisasi harus dilakukan oleh worker aplikasi melalui koneksi TLS dan autentikasi khusus. Jangan membuka port database ke internet publik.

## Fondasi pada branch ini
- deploy/docker-compose.yml: layanan PostgreSQL lokal untuk server LAN.
- deploy/.env.example: contoh konfigurasi; wajib mengganti password.
- migrations/postgres/001_sync_foundation.sql: tabel node, event, konflik, dan audit.
- Ini baru fondasi; belum ada adapter PostgreSQL untuk seluruh modul HRD dan belum ada worker sync siap produksi.

## Menjalankan PostgreSQL lokal
1. Salin deploy/.env.example menjadi deploy/.env.
2. Ganti POSTGRES_PASSWORD dengan rahasia acak yang kuat.
3. Jalankan dari folder deploy: docker compose --env-file .env up -d.
4. Pastikan volume hrd_postgres_data tersimpan di disk server yang dibackup.
5. Terapkan migrasi ke database baru dengan akun migrasi khusus.

Secara default database hanya bind ke 127.0.0.1. Jangan ubah POSTGRES_BIND ke 0.0.0.0 sebelum firewall, VLAN, kredensial, dan kebutuhan akses jaringan ditinjau.

## Pekerjaan wajib sebelum produksi
- Port seluruh fungsi CRUD aplikasi dari SQLite ke PostgreSQL.
- Buat transactional outbox pada transaksi yang sama dengan perubahan data bisnis.
- Buat worker sync dua arah, checkpoint/cursor, retry exponential backoff, dan idempotent inbox.
- Konflik perubahan data karyawan harus masuk antrean resolusi; jangan menimpa otomatis dengan last-write-wins.
- Terapkan autentikasi antar-node, TLS, rotasi kredensial, dan pembatasan akses.
- Tambahkan status sinkronisasi, halaman resolusi konflik, dan alarm kegagalan.
- Buat backup terenkripsi dan uji restore.
- Uji putus internet, pemulihan koneksi, dua pengguna mengedit data yang sama, duplikasi event, dan restart server.

## Status
Belum siap produksi. File fondasi ini tidak mengubah deployment Streamlit Cloud yang sedang aktif dan tidak melakukan migrasi atau penghapusan data.
