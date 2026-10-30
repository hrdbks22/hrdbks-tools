# Penguncian akses jaringan LAN

## Perilaku yang diinginkan
- Aplikasi LAN hanya menerima koneksi dari subnet kantor yang didaftarkan.
- Cloud tetap memakai login aplikasi dan kebijakan akses Cloud tersendiri.
- Deteksi IP lokal membantu administrator menemukan alamat server; deteksi bukan persetujuan otomatis.
- Jaringan baru tidak otomatis dipercaya. Super Admin/administrator jaringan harus mendaftarkan CIDR secara eksplisit.

## Deteksi jaringan
Di server LAN jalankan:
`python deploy/discover_lan.py`

Skrip menampilkan IPv4 private yang terdeteksi. Konfirmasikan subnet/CIDR yang benar dengan administrator router atau jaringan. Jangan mengasumsikan bahwa setiap jaringan kantor selalu /24.

## Kunci jaringan di reverse proxy
1. Pasang Nginx di server LAN.
2. Salin `deploy/nginx/hrd-lan.conf.example` ke konfigurasi site Nginx.
3. Ganti `192.168.10.0/24` dengan CIDR kantor yang telah diverifikasi.
4. Pastikan Streamlit hanya bind ke localhost (contoh: `streamlit run app.py --server.address 127.0.0.1 --server.port 8501`).
5. Pastikan firewall hanya membuka port proxy (80/443) untuk subnet yang diizinkan.
6. Uji dari perangkat kantor dan dari jaringan lain; jaringan yang tidak terdaftar harus ditolak.

## Penting untuk keamanan
- Jangan mengandalkan alamat IP dari header HTTP seperti X-Forwarded-For yang dikirim klien; header dapat dipalsukan jika proxy tidak dikonfigurasi dengan benar.
- Untuk HTTPS, gunakan sertifikat internal/CA perusahaan atau domain yang dikelola perusahaan.
- Jangan mengekspos port Streamlit 8501 atau PostgreSQL 5432 ke internet publik.
- IP/MAC address saja bukan autentikasi identitas perangkat. Pertimbangkan VPN perusahaan atau 802.1X/WPA-Enterprise untuk keamanan Wi-Fi.
- Jika kantor memakai beberapa VLAN/subnet, daftarkan hanya subnet yang diperlukan.
- Saat server pindah jaringan, admin harus memverifikasi dan memperbarui allowlist; jaringan baru tetap ditolak sampai disetujui.

Konfigurasi contoh memakai subnet dokumentasi dan WAJIB diganti sebelum digunakan.
