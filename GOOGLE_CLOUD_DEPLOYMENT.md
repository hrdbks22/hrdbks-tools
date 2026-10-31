# HRD Tools — Google Cloud Run + Cloud SQL

GUI Streamlit dipertahankan. Cloud Run menjalankan aplikasi; Cloud SQL for PostgreSQL menyimpan data permanen.

## 1. Buat Cloud SQL PostgreSQL
- Buat project Google Cloud dan aktifkan billing.
- Aktifkan Cloud SQL Admin API, Cloud Run API, Artifact Registry API, dan Cloud Build API.
- Buat instance Cloud SQL for PostgreSQL di region yang sama dengan Cloud Run.
- Buat database (misalnya `hrd_tools`) dan user khusus aplikasi (misalnya `hrd_app`) dengan password kuat.
- Catat **Instance connection name**: `PROJECT_ID:REGION:INSTANCE_ID`.
- Jangan gunakan akun database `postgres` untuk aplikasi sehari-hari.

## 2. Buat schema
Jalankan seluruh isi `migrations/postgres/001_online_schema.sql` pada database Cloud SQL yang masih kosong. Jangan jalankan ulang pada database yang sudah memiliki tabel kecuali setelah memeriksa migrasi.

## 3. (Opsional) Pindahkan data dari Neon
Lakukan backup dahulu. Dari komputer/Cloud Shell yang memiliki akses ke kedua database:
```bash
pg_dump "$NEON_DATABASE_URL" --format=custom --no-owner --no-acl --file=hrd_neon.dump
pg_restore --dbname="$CLOUD_SQL_DATABASE_URL" --data-only --no-owner --no-acl hrd_neon.dump
```
Perintah restore ini mengasumsikan schema Cloud SQL sudah dibuat dari file migrasi. Periksa jumlah baris tiap tabel dan login pengguna sebelum mengalihkan aplikasi. Jangan menghapus database Neon sebelum hasil migrasi diverifikasi dan backup aman.

## 4. Simpan password dengan Secret Manager
Buat secret bernama `hrd-db-password` berisi password user Cloud SQL. Berikan akses Secret Manager Secret Accessor hanya kepada service account Cloud Run.

## 5. Build dan deploy
Dari folder repository:
```bash
gcloud config set project PROJECT_ID
gcloud builds submit --tag REGION-docker.pkg.dev/PROJECT_ID/hrd-tools/hrd-tools
``
Buat Artifact Registry Docker repository bernama `hrd-tools` terlebih dahulu jika belum ada:
```bash
gcloud artifacts repositories create hrd-tools --repository-format=docker --location=REGION
``
Berikan role Cloud SQL Client kepada service account Cloud Run. Lalu deploy:
```bash
gcloud run deploy hrd-tools \
  --image=REGION-docker.pkg.dev/PROJECT_ID/hrd-tools/hrd-tools \
  --region=REGION \
  --platform=managed \
  --allow-unauthenticated \
  --add-cloudsql-instances=PROJECT_ID:REGION:INSTANCE_ID \
  --set-env-vars=INSTANCE_CONNECTION_NAME=PROJECT_ID:REGION:INSTANCE_ID,DB_NAME=hrd_tools,DB_USER=hrd_app \
  --set-secrets=DB_PASS=hrd-db-password:latest \
  --service-account=cloud-run-hrd@PROJECT_ID.iam.gserviceaccount.com
```
Ganti semua nilai contoh. Pastikan service account tersebut memiliki role `roles/cloudsql.client` dan `roles/secretmanager.secretAccessor`.

## 6. Akun login aplikasi
Aplikasi membuat akun awal dan mewajibkan password. Buat password awal yang berbeda dan kuat untuk setiap akun melalui mekanisme bootstrap yang sudah digunakan aplikasi saat ini. Jangan menaruh password di Git. Setelah akun dibuat, hash password disimpan di tabel `users`; kelola akun berikutnya dari menu Super Admin.

## 7. Penting: akses internet dan autentikasi
`--allow-unauthenticated` membuat URL Cloud Run dapat dibuka publik. Login aplikasi HRD tetap menjadi gerbang akses data. Pastikan semua akun awal sudah memiliki password kuat sebelum URL dibagikan. Untuk data HRD yang sensitif, pertimbangkan pembatasan tambahan (IAP/identity-aware access, VPN, atau kebijakan organisasi) setelah alur login aplikasi diuji.

## 8. Uji sebelum operasional
- Login Super Admin, Admin HRD, dan Tally.
- Uji tambah/edit/baca data master, absensi, SP, evaluasi, panggilan, dan permintaan tidak lanjut.
- Uji hak akses menu setiap role.
- Uji export Excel.
- Restart/redeploy Cloud Run dan pastikan data tetap ada.
- Uji backup dan restore Cloud SQL.
- Periksa Cloud Logging untuk error.

Cloud Run menggunakan filesystem container yang sementara; jangan menyimpan data operasional di SQLite atau file lokal. Pastikan Cloud SQL menjadi backend produksi.
