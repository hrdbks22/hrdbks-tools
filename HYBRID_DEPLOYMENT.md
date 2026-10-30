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
- deploy/docker-compose.yml dan deploy/Dockerfile: PostgreSQL lokal + container Streamlit LAN, database healthcheck, dan binding aplikasi hanya ke localhost host.
- deploy/.env.example: contoh konfigurasi; wajib mengganti password dan mengisi DSN aplikasi/worker.
- migrations/postgres/004_hrd_business_schema.sql: tabel bisnis yang dipakai modul HRD.
- app.py: mode koneksi PostgreSQL melalui APP_DATABASE_URL/DATABASE_URL; SQLite tetap menjadi mode default jika variabel tersebut kosong.
- migrations/postgres/001_sync_foundation.sql dan 003_sync_runtime_compat.sql: tabel node, event, konflik, audit, inbox, checkpoint, dan status retry.
- sync/engine.py: primitive outbox/inbox, idempotency, version checking, dan conflict queue.
- sync/service.py: API pertukaran event berbasis token; wajib dijalankan di belakang HTTPS.
- sync/worker.py: worker satu kali jalan untuk mengirim dan menerima event; jadwalkan dengan systemd timer.
- deploy/systemd/: contoh service/timer worker.
- deploy/network_guard.py dan deploy/NETWORK_ACCESS.md: fondasi pembatasan subnet LAN.

**Batas integrasi saat ini:** mode PostgreSQL untuk CRUD aplikasi sudah ditambahkan, tetapi belum diuji terhadap instance PostgreSQL nyata. Setiap perubahan bisnis juga belum ditulis ke transactional outbox; engine saat ini belum menerapkan payload event masuk ke tabel bisnis HRD. Karena itu sinkronisasi belum mereplikasi data HRD aktual dan belum boleh dipakai operasional.

## Menjalankan PostgreSQL lokal
1. Salin deploy/.env.example menjadi deploy/.env.
2. Ganti POSTGRES_PASSWORD dengan rahasia acak yang kuat.
3. Isi `DATABASE_URL` untuk worker host (host 127.0.0.1) dan `APP_DATABASE_URL` untuk container Streamlit (host Docker `hrd-db`). Pastikan password pada URL di-encode jika mengandung karakter khusus.
4. Jalankan dari folder deploy: `docker compose --env-file .env up -d --build`.
5. Pada volume PostgreSQL yang benar-benar baru, Docker menjalankan migrasi 001–004 otomatis. Migrasi init hanya berjalan saat volume data pertama kali dibuat; jangan menghapus volume berisi data untuk mengulang migrasi.
6. Pastikan volume hrd_postgres_data tersimpan di disk server yang dibackup.

Secara default database hanya bind ke 127.0.0.1. Jangan ubah POSTGRES_BIND ke 0.0.0.0 sebelum firewall, VLAN, kredensial, dan kebutuhan akses jaringan ditinjau.

## Cara menyiapkan worker (uji teknis, bukan cutover)
1. Terapkan migrasi 001, 002, dan 003 secara berurutan pada kedua database PostgreSQL.
2. Daftarkan kedua UUID node di tabel `sync_nodes` pada masing-masing database; tipe node adalah `lan` atau `cloud`.
3. Atur `DATABASE_URL`, `SYNC_NODE_ID`, `SYNC_TOKEN`, dan `SYNC_ENDPOINT` pada file environment yang tidak masuk Git.
4. Jalankan API dengan `uvicorn sync.service:app --host 127.0.0.1 --port 8765` di belakang reverse proxy HTTPS.
5. Pasang unit systemd pada `deploy/systemd`, sesuaikan path/user, lalu aktifkan `hrd-sync.timer`.
6. Jalankan hanya pada database uji sampai pengujian dua arah, duplikasi, konflik, retry, dan pemulihan koneksi lulus.

## Pekerjaan wajib sebelum produksi
- Jalankan uji CRUD seluruh modul terhadap PostgreSQL nyata dan perbaiki perbedaan perilaku SQLite/PostgreSQL.
- Hubungkan setiap transaksi perubahan data bisnis ke transactional outbox pada transaksi yang sama.
- Buat penerapan event masuk ke tabel bisnis aktual (bukan hanya tabel shadow sync_entity_state).
- Tambahkan otorisasi node yang kuat (token per-node, rotasi, dan pengikatan identitas node), validasi payload/schema, rate limiting, dan audit penerimaan.
- Implementasikan UI status sinkronisasi dan halaman resolusi konflik yang disetujui Admin HRD/Super Admin.
- Konflik perubahan data karyawan harus masuk antrean resolusi; jangan menimpa otomatis dengan last-write-wins.
- Terapkan autentikasi antar-node, TLS, rotasi kredensial, dan pembatasan akses.
- Tambahkan status sinkronisasi, halaman resolusi konflik, dan alarm kegagalan.
- Buat backup terenkripsi dan uji restore.
- Uji putus internet, pemulihan koneksi, dua pengguna mengedit data yang sama, duplikasi event, dan restart server.

## Status
Belum siap produksi. File fondasi ini tidak mengubah deployment Streamlit Cloud yang sedang aktif dan tidak melakukan migrasi atau penghapusan data.
