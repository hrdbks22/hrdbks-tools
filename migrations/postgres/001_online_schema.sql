BEGIN;
CREATE TABLE IF NOT EXISTS users (
 username TEXT PRIMARY KEY, nama TEXT NOT NULL, role TEXT NOT NULL,
 shift TEXT, require_password INTEGER NOT NULL DEFAULT 0,
 password_hash TEXT, active INTEGER NOT NULL DEFAULT 1,
 created_at TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS menu_permissions (
 role TEXT NOT NULL, menu TEXT NOT NULL, allowed INTEGER NOT NULL DEFAULT 0,
 PRIMARY KEY(role,menu)
);
CREATE TABLE IF NOT EXISTS employees (
 nik TEXT PRIMARY KEY, nama TEXT NOT NULL, bagian TEXT, shift TEXT,
 masuk TEXT, keluar TEXT, status TEXT, sumber TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS attendance (
 id BIGSERIAL PRIMARY KEY, nik TEXT NOT NULL REFERENCES employees(nik),
 tanggal TEXT NOT NULL, jenis TEXT NOT NULL CHECK(jenis IN ('Sakit','Izin','Alpa')),
 hari DOUBLE PRECISION NOT NULL DEFAULT 1, catatan TEXT, created_by TEXT, created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_attendance_nik_date ON attendance(nik,tanggal);
CREATE TABLE IF NOT EXISTS warnings (
 id BIGSERIAL PRIMARY KEY, nik TEXT NOT NULL REFERENCES employees(nik),
 jenis TEXT NOT NULL CHECK(jenis IN ('SP1','SP2','SP3')),
 tanggal TEXT NOT NULL, nomor TEXT, catatan TEXT, created_by TEXT, created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_warnings_nik_date ON warnings(nik,tanggal);
CREATE TABLE IF NOT EXISTS evaluations (
 id BIGSERIAL PRIMARY KEY, nik TEXT NOT NULL REFERENCES employees(nik),
 milestone INTEGER NOT NULL, tanggal_evaluasi TEXT NOT NULL, masa_kerja_bulan INTEGER NOT NULL,
 sakit_hari DOUBLE PRECISION NOT NULL, izin_hari DOUBLE PRECISION NOT NULL,
 alpa_hari DOUBLE PRECISION NOT NULL, sp1 INTEGER NOT NULL, sp2 INTEGER NOT NULL,
 sp3 INTEGER NOT NULL, skor INTEGER NOT NULL, rincian TEXT NOT NULL, catatan TEXT,
 rekomendasi TEXT, dibuat_oleh TEXT, dibuat_pada TEXT, UNIQUE(nik,milestone)
);
CREATE TABLE IF NOT EXISTS nonrenew_requests (
 id BIGSERIAL PRIMARY KEY, nik TEXT NOT NULL REFERENCES employees(nik),
 tanggal_permintaan TEXT NOT NULL, atasan TEXT NOT NULL, alasan TEXT NOT NULL,
 catatan_hrd TEXT, status TEXT NOT NULL, dibuat_oleh TEXT, dibuat_pada TEXT
);
CREATE TABLE IF NOT EXISTS calls (
 id BIGSERIAL PRIMARY KEY, nik TEXT NOT NULL REFERENCES employees(nik),
 tanggal TEXT NOT NULL, alasan TEXT NOT NULL, petugas TEXT
);
CREATE TABLE IF NOT EXISTS import_log (
 id BIGSERIAL PRIMARY KEY, waktu TEXT, nama_file TEXT,
 jumlah_baris INTEGER, ditambah INTEGER, diperbarui INTEGER, diabaikan INTEGER, petugas TEXT
);
COMMIT;
