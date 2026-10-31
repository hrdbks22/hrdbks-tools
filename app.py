import streamlit as st
import pandas as pd
import sqlite3
import re
import psycopg
from psycopg.rows import tuple_row
import io
import hashlib
import json
import hmac
import os
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="HRD Tools | PT. Berkat Karunia Surya", page_icon="📋", layout="wide")
DB = "hrd_tools.db"

# Cloud Run + Cloud SQL (PostgreSQL) uses the Cloud SQL Unix socket.
# Credentials are injected as environment variables / Secret Manager secrets.
CLOUD_SQL_INSTANCE = os.environ.get("INSTANCE_CONNECTION_NAME", "").strip()
CLOUD_SQL_DB = os.environ.get("DB_NAME", "").strip()
CLOUD_SQL_USER = os.environ.get("DB_USER", "").strip()
CLOUD_SQL_PASSWORD = os.environ.get("DB_PASS", "")

if CLOUD_SQL_INSTANCE and CLOUD_SQL_DB and CLOUD_SQL_USER and CLOUD_SQL_PASSWORD:
    DATABASE_URL = psycopg.conninfo.make_conninfo(
        host=f"/cloudsql/{CLOUD_SQL_INSTANCE}",
        dbname=CLOUD_SQL_DB,
        user=CLOUD_SQL_USER,
        password=CLOUD_SQL_PASSWORD,
        connect_timeout=10,
    )
else:
    try:
        STREAMLIT_DATABASE_URL = str(st.secrets.get("DATABASE_URL", "")).strip()
    except Exception:
        STREAMLIT_DATABASE_URL = ""
    DATABASE_URL = (
        os.environ.get("APP_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or STREAMLIT_DATABASE_URL
    ).strip()

class PostgresCompat:
    """Connection wrapper retaining the app's positional ? placeholders."""
    def __init__(self, dsn):
        self.conn = psycopg.connect(dsn, row_factory=tuple_row)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            self.conn.commit() if exc_type is None else self.conn.rollback()
        finally:
            self.conn.close()

    def execute(self, sql, params=()):
        return self.conn.execute(sql.replace("?", "%s"), params)

MENU_ITEMS = ["Dashboard","Master Data Karyawan","Data Absensi","Arsip & Monitoring SP","Evaluasi Karyawan (H3)","Daftar Karyawan Tidak Lanjut Kontrak","Panggilan Karyawan","Riwayat Karyawan"]
ROLE_NAMES = ["Super Admin","Admin HRD","Tally"]
INITIAL_USERS = [
    ("niko","Niko","Super Admin","",0),
    ("agung","Agung","Admin HRD","",0),
    ("iis","Iis","Admin HRD","",0),
    ("nurhayat","Nurhayat","Admin HRD","",1),
    ("23010202","Tally Shift E","Tally","E",0),
    ("26090328","Tally Shift F","Tally","F",0),
    ("26092377","Tally Shift G","Tally","G",0),
]
ACTIVE_STATUSES = {"S3", "S4"}
MILESTONES = [1, 2, 3, 6, 9, 12]

def db():
    if DATABASE_URL:
        return PostgresCompat(DATABASE_URL)
    return sqlite3.connect(DB, check_same_thread=False)

def init_db():
    if DATABASE_URL:
        # Online accounts must always use passwords. Bootstrap passwords are supplied
        # only through Streamlit Secrets and are stored as salted PBKDF2 hashes.
        try:
            bootstrap_users = dict(st.secrets.get("users", {}))
        except Exception:
            bootstrap_users = {}
        # Cloud Run can supply bootstrap credentials through Secret Manager.
        # The JSON secret should map each seeded username to a unique password.
        try:
            cloud_bootstrap_users = json.loads(os.environ.get("BOOTSTRAP_USERS_JSON", "{}"))
            if isinstance(cloud_bootstrap_users, dict):
                bootstrap_users.update(cloud_bootstrap_users)
        except (TypeError, ValueError):
            cloud_bootstrap_users = {}
        with db() as c:
            now = datetime.now().isoformat(timespec="seconds")
            for username,nama,role,shift,_ in INITIAL_USERS:
                bootstrap_password = str(bootstrap_users.get(username, "")).strip()
                if bootstrap_password and not bootstrap_password.startswith("GANTI_"):
                    salt = os.urandom(16)
                    digest = hashlib.pbkdf2_hmac("sha256", bootstrap_password.encode("utf-8"), salt, 310000)
                    bootstrap_hash = salt.hex() + ":" + digest.hex()
                else:
                    bootstrap_hash = None
                c.execute("""INSERT INTO users(username,nama,role,shift,require_password,password_hash,active,created_at,updated_at)
                             VALUES(?,?,?,?,1,?,1,?,?)
                             ON CONFLICT(username) DO UPDATE SET
                               require_password=1,
                               password_hash=COALESCE(users.password_hash, EXCLUDED.password_hash),
                               updated_at=EXCLUDED.updated_at""",
                          (username,nama,role,shift,bootstrap_hash,now,now))
            defaults = {"Admin HRD": MENU_ITEMS, "Tally": ["Dashboard","Panggilan Karyawan"]}
            for role, menus_for_role in defaults.items():
                existing = c.execute("SELECT COUNT(*) FROM menu_permissions WHERE role=?", (role,)).fetchone()[0]
                if existing == 0:
                    for item in MENU_ITEMS:
                        c.execute("INSERT INTO menu_permissions(role,menu,allowed) VALUES(?,?,?)",
                                  (role,item,1 if item in menus_for_role else 0))
        return
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(
          username TEXT PRIMARY KEY, nama TEXT NOT NULL, role TEXT NOT NULL,
          shift TEXT, require_password INTEGER NOT NULL DEFAULT 0,
          password_hash TEXT, active INTEGER NOT NULL DEFAULT 1,
          created_at TEXT, updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS menu_permissions(
          role TEXT NOT NULL, menu TEXT NOT NULL, allowed INTEGER NOT NULL DEFAULT 0,
          PRIMARY KEY(role,menu)
        );
        CREATE TABLE IF NOT EXISTS employees(
          nik TEXT PRIMARY KEY, nama TEXT NOT NULL, bagian TEXT, shift TEXT,
          masuk TEXT, keluar TEXT, status TEXT, sumber TEXT, updated_at TEXT
        );
        """)
        cols = {row[1] for row in c.execute("PRAGMA table_info(employees)").fetchall()}
        if "keluar" not in cols:
            c.execute("ALTER TABLE employees ADD COLUMN keluar TEXT")
        c.executescript("""
        CREATE TABLE IF NOT EXISTS attendance(
          id INTEGER PRIMARY KEY AUTOINCREMENT, nik TEXT NOT NULL, tanggal TEXT NOT NULL,
          jenis TEXT NOT NULL CHECK(jenis IN ('Sakit','Izin','Alpa')), hari REAL NOT NULL DEFAULT 1,
          catatan TEXT, created_by TEXT, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS warnings(
          id INTEGER PRIMARY KEY AUTOINCREMENT, nik TEXT NOT NULL, jenis TEXT NOT NULL CHECK(jenis IN ('SP1','SP2','SP3')),
          tanggal TEXT NOT NULL, nomor TEXT, catatan TEXT, created_by TEXT, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS evaluations(
          id INTEGER PRIMARY KEY AUTOINCREMENT, nik TEXT NOT NULL, milestone INTEGER NOT NULL,
          tanggal_evaluasi TEXT NOT NULL, masa_kerja_bulan INTEGER NOT NULL,
          sakit_hari REAL NOT NULL, izin_hari REAL NOT NULL, alpa_hari REAL NOT NULL,
          sp1 INTEGER NOT NULL, sp2 INTEGER NOT NULL, sp3 INTEGER NOT NULL,
          skor INTEGER NOT NULL, rincian TEXT NOT NULL, catatan TEXT, rekomendasi TEXT,
          dibuat_oleh TEXT, dibuat_pada TEXT, UNIQUE(nik,milestone)
        );
        CREATE TABLE IF NOT EXISTS nonrenew_requests(
          id INTEGER PRIMARY KEY AUTOINCREMENT, nik TEXT NOT NULL, tanggal_permintaan TEXT NOT NULL,
          atasan TEXT NOT NULL, alasan TEXT NOT NULL, catatan_hrd TEXT, status TEXT NOT NULL,
          dibuat_oleh TEXT, dibuat_pada TEXT
        );
        CREATE TABLE IF NOT EXISTS calls(
          id INTEGER PRIMARY KEY AUTOINCREMENT, nik TEXT NOT NULL, tanggal TEXT NOT NULL,
          alasan TEXT NOT NULL, petugas TEXT
        );
        CREATE TABLE IF NOT EXISTS import_log(
          id INTEGER PRIMARY KEY AUTOINCREMENT, waktu TEXT, nama_file TEXT,
          jumlah_baris INTEGER, ditambah INTEGER, diperbarui INTEGER, diabaikan INTEGER, petugas TEXT
        );
        """)
    with db() as c:
        now = datetime.now().isoformat(timespec="seconds")
        for username,nama,role,shift,require_password in INITIAL_USERS:
            c.execute("""INSERT OR IGNORE INTO users(username,nama,role,shift,require_password,active,created_at,updated_at)
                         VALUES(?,?,?,?,?,1,?,?)""",(username,nama,role,shift,require_password,now,now))
        defaults = {"Admin HRD": MENU_ITEMS, "Tally": ["Dashboard","Panggilan Karyawan"]}
        for role, menus_for_role in defaults.items():
            existing = c.execute("SELECT COUNT(*) FROM menu_permissions WHERE role=?", (role,)).fetchone()[0]
            if existing == 0:
                for item in MENU_ITEMS:
                    c.execute("INSERT INTO menu_permissions(role,menu,allowed) VALUES(?,?,?)",
                              (role,item,1 if item in menus_for_role else 0))
init_db()

def password_hash(password, salt=None):
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310000)
    return salt.hex() + ":" + digest.hex()

def verify_password(password, stored):
    if not stored or ":" not in stored: return False
    salt_hex, digest_hex = stored.split(":",1)
    candidate = password_hash(password, bytes.fromhex(salt_hex)).split(":",1)[1]
    return hmac.compare_digest(candidate,digest_hex)

def get_user(username):
    with db() as c:
        return c.execute("SELECT username,nama,role,shift,require_password,password_hash,active FROM users WHERE username=?",
                         (str(username).strip().lower(),)).fetchone()

def allowed_menus(role):
    if role == "Super Admin": return MENU_ITEMS + ["Pengaturan Username","Pengaturan Hak Akses Menu"]
    with db() as c:
        rows = c.execute("SELECT menu FROM menu_permissions WHERE role=? AND allowed=1 ORDER BY menu",(role,)).fetchall()
    return [r[0] for r in rows if r[0] in MENU_ITEMS]

def read_table(name):
    allowed = {"users","menu_permissions","employees","attendance","warnings",
               "evaluations","nonrenew_requests","calls","import_log"}
    if name not in allowed:
        raise ValueError("Tabel tidak diizinkan")
    with db() as c:
        cur = c.execute(f"SELECT * FROM {name}")
        rows = cur.fetchall()
        columns = [d.name if hasattr(d, "name") else d[0] for d in cur.description]
        return pd.DataFrame(rows, columns=columns)

def employee(nik):
    with db() as c:
        return c.execute("SELECT nik,nama,bagian,shift,masuk,status FROM employees WHERE nik=?", (str(nik),)).fetchone()

def months_service(masuk, on_date=None):
    if not masuk: return None
    try:
        start = date.fromisoformat(str(masuk)[:10])
        end = on_date or date.today()
        if end < start: return 0
        delta = relativedelta(end, start)
        return delta.years * 12 + delta.months
    except Exception: return None

def xlsx_bytes(df, sheet="Data"):
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name=sheet[:31])
    return out.getvalue()

def score_employee(nik, milestone, asof):
    emp = employee(nik)
    if not emp or not emp[4]: return None
    with db() as c:
        rows = c.execute("""SELECT jenis, SUM(hari) FROM attendance
          WHERE nik=? AND tanggal<=? AND tanggal>=? GROUP BY jenis""",
          (nik, asof.isoformat(), emp[4])).fetchall()
        sp = c.execute("""SELECT jenis,COUNT(*) FROM warnings WHERE nik=? AND tanggal<=?
          AND tanggal>=? GROUP BY jenis""", (nik, asof.isoformat(), emp[4])).fetchall()
    totals = {k: float(v or 0) for k,v in rows}
    sanctions = {k:int(v) for k,v in sp}
    sakit, izin, alpa = totals.get("Sakit",0), totals.get("Izin",0), totals.get("Alpa",0)
    excess = max(0, sakit + izin - 5)
    deduction = excess*3 + alpa*10 + sanctions.get("SP1",0)*10 + sanctions.get("SP2",0)*20 + sanctions.get("SP3",0)*30
    score = max(0, 100-round(deduction))
    detail = f"Sakit {sakit:g} hari + Izin {izin:g} hari (toleransi gabungan 5; kelebihan {excess:g} x 3), Alpa {alpa:g} x 10, SP1 {sanctions.get('SP1',0)} x 10, SP2 {sanctions.get('SP2',0)} x 20, SP3 {sanctions.get('SP3',0)} x 30"
    return {"emp":emp,"bulan":months_service(emp[4],asof),"sakit":sakit,"izin":izin,"alpa":alpa,
            "sp1":sanctions.get("SP1",0),"sp2":sanctions.get("SP2",0),"sp3":sanctions.get("SP3",0),
            "skor":score,"detail":detail,"milestone":milestone}

# Login berbasis akun lokal; password bersifat opsional per akun.
if "user" not in st.session_state: st.session_state.user = None
if not st.session_state.user:
    st.title("🔐 HRD Tools")
    st.caption("PT. BERKAT KARUNIA SURYA")
    username = st.text_input("Username / NIK", key="login_username").strip().lower()
    account = get_user(username) if username else None
    password = ""
    if account and account[6] == 1 and account[4] == 1:
        password = st.text_input("Password", type="password", key="login_password")
    if st.button("Masuk",type="primary"):
        account = get_user(username)
        if not account or account[6] != 1:
            st.error("Akun tidak ditemukan atau sudah nonaktif.")
        elif account[4] == 1 and (not account[5] or not password or not verify_password(password,account[5])):
            st.error("Password belum disiapkan atau password salah. Hubungi Super Admin.")
        else:
            st.session_state.user = account[0]
            st.rerun()
    st.stop()

user = st.session_state.user
account = get_user(user)
if not account or account[6] != 1:
    st.session_state.user = None
    st.error("Akun tidak aktif atau tidak ditemukan.")
    st.stop()
user_role = account[2]
is_super_admin = user_role == "Super Admin"
is_admin = user_role in ("Super Admin","Admin HRD")
st.sidebar.title("HRD Tools")
st.sidebar.caption(f"Login: {account[1]} · {user_role}")
menus = allowed_menus(user_role)
if is_super_admin:
    menus = menus + ["Pengaturan Username","Pengaturan Hak Akses Menu"]
menu = st.sidebar.radio("Menu", menus)
if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()

st.title("PT. BERKAT KARUNIA SURYA")
st.caption("Sistem Administrasi Human Resources")

if menu == "Pengaturan Username" and is_super_admin:
    st.subheader("Pengaturan Username")
    st.caption("Password disimpan sebagai hash dan tidak dapat dibaca kembali.")
    accounts_df = read_table("users")
    st.dataframe(accounts_df.drop(columns=["password_hash"],errors="ignore"),use_container_width=True)
    with st.form("account_add"):
        st.markdown("**Tambah akun**")
        new_username = st.text_input("Username / NIK").strip().lower()
        new_name = st.text_input("Nama pengguna")
        new_role = st.selectbox("Role",ROLE_NAMES[1:])
        new_shift = st.selectbox("Shift",["","E","F","G"]) if new_role=="Tally" else ""
        new_requires = st.checkbox("Wajib menggunakan password")
        new_password = st.text_input("Password baru",type="password") if new_requires else ""
        add_account = st.form_submit_button("Tambah akun")
    if add_account:
        if not new_username or not new_name: st.error("Username dan nama pengguna wajib diisi.")
        elif new_requires and not new_password: st.error("Password wajib dibuat jika checkbox dicentang.")
        else:
            with db() as c:
                try:
                    c.execute("""INSERT INTO users(username,nama,role,shift,require_password,password_hash,active,created_at,updated_at)
                                 VALUES(?,?,?,?,?,?,1,?,?)""",
                              (new_username,new_name,new_role,new_shift,int(new_requires),password_hash(new_password) if new_requires else None,datetime.now().isoformat(),datetime.now().isoformat()))
                    st.success("Akun berhasil ditambahkan."); st.rerun()
                except (sqlite3.IntegrityError, psycopg.IntegrityError): st.error("Username sudah terdaftar.")
    st.markdown("**Ubah akun yang sudah terdaftar**")
    choices = accounts_df.username.tolist() if len(accounts_df) else []
    if choices:
        selected = st.selectbox("Pilih akun",choices)
        selected_row = get_user(selected)
        with st.form("account_edit"):
            edit_name = st.text_input("Nama",value=selected_row[1])
            edit_role = st.selectbox("Role",ROLE_NAMES,index=ROLE_NAMES.index(selected_row[2]))
            edit_shift = st.selectbox("Shift",["","E","F","G"],index=["","E","F","G"].index(selected_row[3] or "")) if edit_role=="Tally" else ""
            edit_active = st.checkbox("Akun aktif",value=bool(selected_row[6]))
            edit_requires = st.checkbox("Wajib menggunakan password",value=bool(selected_row[4]))
            edit_password = st.text_input("Password baru (kosongkan jika tidak ingin mengganti)",type="password")
            save_account = st.form_submit_button("Simpan perubahan")
        if save_account:
            if selected=="niko" and (edit_role!="Super Admin" or not edit_active):
                st.error("Akun Niko sebagai Super Admin tidak boleh dinonaktifkan atau diturunkan role-nya.")
            elif edit_requires and not (edit_password or selected_row[5]):
                st.error("Buat password terlebih dahulu sebelum mewajibkan password.")
            else:
                new_hash = password_hash(edit_password) if edit_password else selected_row[5]
                if not edit_requires: new_hash = None
                with db() as c:
                    c.execute("""UPDATE users SET nama=?,role=?,shift=?,active=?,require_password=?,password_hash=?,updated_at=? WHERE username=?""",
                              (edit_name,edit_role,edit_shift,int(edit_active),int(edit_requires),new_hash,datetime.now().isoformat(),selected))
                st.success("Pengaturan akun diperbarui."); st.rerun()

elif menu == "Pengaturan Hak Akses Menu" and is_super_admin:
    st.subheader("Pengaturan Hak Akses Menu")
    st.caption("Super Admin selalu memiliki akses penuh. Pilih menu yang boleh dibuka oleh masing-masing role.")
    for role in ["Admin HRD","Tally"]:
        with db() as c:
            current = [r[0] for r in c.execute("SELECT menu FROM menu_permissions WHERE role=? AND allowed=1",(role,)).fetchall()]
        chosen = st.multiselect(f"Menu yang dapat diakses — {role}",MENU_ITEMS,default=current,key=f"perm_{role}")
        if st.button(f"Simpan hak akses {role}",key=f"save_perm_{role}"):
            with db() as c:
                c.execute("DELETE FROM menu_permissions WHERE role=?",(role,))
                for item in MENU_ITEMS:
                    c.execute("INSERT INTO menu_permissions(role,menu,allowed) VALUES(?,?,?)",(role,item,int(item in chosen)))
            st.success(f"Hak akses {role} berhasil diperbarui."); st.rerun()

elif menu == "Dashboard":
    em = read_table("employees")
    at = read_table("attendance")
    sp = read_table("warnings")
    nr = read_table("nonrenew_requests")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Master Karyawan",len(em))
    c2.metric("Data Absensi",len(at))
    c3.metric("Catatan SP",len(sp))
    c4.metric("Permintaan Tidak Lanjut",len(nr[nr.status!="Selesai"]) if len(nr) else 0)
    st.subheader("Monitoring tanggal akhir kontrak")
    if len(em) and "keluar" in em.columns:
        contracts=em.copy()
        contracts["Tanggal Akhir"]=pd.to_datetime(contracts["keluar"],errors="coerce")
        today=pd.Timestamp(date.today())
        contracts["Sisa Hari"]=(contracts["Tanggal Akhir"]-today).dt.days
        ending=contracts[contracts["Sisa Hari"].between(0,30)]
        expired=contracts[contracts["Sisa Hari"]<0]
        a,b=st.columns(2);a.metric("Berakhir 30 hari ke depan",len(ending));b.metric("Sudah lewat tanggal akhir",len(expired))
        st.dataframe(contracts[contracts["Tanggal Akhir"].notna()][["nik","nama","bagian","shift","masuk","keluar","status","Sisa Hari"]].sort_values("Sisa Hari"),use_container_width=True)
    else:
        st.info("Tambahkan tanggal MASUK dan KELUAR melalui impor Master Data untuk memulai monitoring kontrak.")
    st.caption("Data dan keputusan HRD harus diverifikasi. Sistem tidak menetapkan keputusan perpanjangan atau pemutusan kontrak otomatis.")

elif menu == "Master Data Karyawan" and menu in menus:
    st.subheader("Master Data Karyawan")
    st.warning("Impor menggunakan NIK sebagai kunci. Data yang tidak ada di file baru tidak dihapus; perubahan diperbarui setelah pratinjau.")
    template = pd.DataFrame(columns=["NIK","NAMA","BAGIAN","SHIFT","MASUK","KELUAR","STATUS"])
    st.download_button("Unduh template Excel",xlsx_bytes(template,"Master"),"template_master_karyawan.xlsx")
    up = st.file_uploader("Upload Excel/CSV",type=["xlsx","xls","csv"])
    if up:
        try:
            raw = pd.read_csv(up,dtype=str) if up.name.lower().endswith(".csv") else pd.read_excel(up,dtype=str)
            raw.columns = [str(x).strip().upper() for x in raw.columns]
            aliases = {"NIK":"NIK","NAMA":"NAMA","BAGIAN":"BAGIAN","DEPARTEMEN":"BAGIAN","SHIFT":"SHIFT","SHF":"SHIFT","MASUK":"MASUK","TGL MASUK":"MASUK","KELUAR":"KELUAR","TGL KELUAR":"KELUAR","STATUS":"STATUS"}
            raw = raw.rename(columns={c:aliases[c] for c in raw.columns if c in aliases})
            required = ["NIK","NAMA"]
            if not all(c in raw.columns for c in required): st.error("Kolom minimal NIK dan NAMA wajib tersedia.")
            else:
                for col in ["BAGIAN","SHIFT","MASUK","KELUAR","STATUS"]:
                    if col not in raw: raw[col] = ""
                raw = raw[["NIK","NAMA","BAGIAN","SHIFT","MASUK","KELUAR","STATUS"]].fillna("")
                raw["NIK"] = raw["NIK"].astype(str).str.strip()
                raw = raw[raw.NIK.ne("")]
                dup = raw[raw.NIK.duplicated(keep=False)]
                if len(dup): st.error("Ada NIK ganda dalam file. Perbaiki dahulu sebelum impor."); st.dataframe(dup)
                else:
                    st.write("Pratinjau impor"); st.dataframe(raw, use_container_width=True)
                    current = read_table("employees")
                    added = len(set(raw.NIK)-set(current.nik)) if len(current) else len(raw)
                    changed = sum(1 for _,r in raw.iterrows() if len(current) and r.NIK in set(current.nik) and str(current[current.nik==r.NIK].iloc[0].nama)!=str(r.NAMA))
                    st.info(f"Baris valid: {len(raw)} · NIK baru: {added} · Nama berubah (indikator): {changed} · Data lama yang tidak ada di file tetap disimpan.")
                    confirm = st.checkbox("Saya sudah memeriksa pratinjau dan menyetujui sinkronisasi berdasarkan NIK.")
                    if st.button("Sinkronkan Master Data",type="primary",disabled=not confirm):
                        nadd=nupd=0
                        with db() as c:
                            for _,r in raw.iterrows():
                                old=c.execute("SELECT nik FROM employees WHERE nik=?",(r.NIK,)).fetchone()
                                c.execute("""INSERT INTO employees(nik,nama,bagian,shift,masuk,keluar,status,sumber,updated_at)
                                VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(nik) DO UPDATE SET
                                nama=excluded.nama,bagian=excluded.bagian,shift=excluded.shift,
                                masuk=CASE WHEN excluded.masuk='' THEN employees.masuk ELSE excluded.masuk END,
                                keluar=CASE WHEN excluded.keluar='' THEN employees.keluar ELSE excluded.keluar END,
                                status=CASE WHEN excluded.status='' THEN employees.status ELSE excluded.status END,
                                sumber=excluded.sumber,updated_at=excluded.updated_at""",
                                (r.NIK,r.NAMA,r.BAGIAN,r.SHIFT,r.MASUK,r.KELUAR,r.STATUS,up.name,datetime.now().isoformat(timespec="seconds")))
                                if old:nupd+=1
                                else:nadd+=1
                            c.execute("INSERT INTO import_log(waktu,nama_file,jumlah_baris,ditambah,diperbarui,diabaikan,petugas) VALUES(?,?,?,?,?,?,?)",
                              (datetime.now().isoformat(timespec="seconds"),up.name,len(raw),nadd,nupd,0,user))
                        st.success(f"Sinkronisasi selesai. Baru: {nadd}, diperbarui: {nupd}. Data historis tidak dihapus.")
                        st.rerun()
        except Exception as e: st.error(f"Gagal membaca file: {e}")
    st.subheader("Data tersimpan")
    em=read_table("employees")
    st.dataframe(em,use_container_width=True)
    if len(em): st.download_button("Export Master Data Excel",xlsx_bytes(em),"master_karyawan.xlsx")

elif menu == "Data Absensi" and menu in menus:
    st.subheader("Pencatatan Sakit, Izin, dan Alpa")
    em=read_table("employees")
    if em.empty: st.warning("Isi Master Data terlebih dahulu.")
    else:
        with st.form("absen"):
            nik=st.selectbox("NIK",em.nik.tolist(),format_func=lambda n:f"{n} - {em[em.nik==n].iloc[0].nama}")
            tgl=st.date_input("Tanggal kejadian",value=date.today())
            jenis=st.selectbox("Jenis",["Sakit","Izin","Alpa"])
            hari=st.number_input("Jumlah hari",min_value=0.5,value=1.0,step=0.5)
            note=st.text_input("Catatan / referensi dokumen")
            save=st.form_submit_button("Simpan absensi",type="primary")
        if save:
            with db() as c:c.execute("INSERT INTO attendance(nik,tanggal,jenis,hari,catatan,created_by,created_at) VALUES(?,?,?,?,?,?,?)",(nik,tgl.isoformat(),jenis,hari,note,user,datetime.now().isoformat()))
            st.success("Absensi tercatat.")
    data=read_table("attendance"); st.dataframe(data,use_container_width=True)
    if len(data):st.download_button("Unduh Excel",xlsx_bytes(data),"data_absensi.xlsx")

elif menu == "Arsip & Monitoring SP" and menu in menus:
    st.subheader("Arsip Surat Peringatan")
    em=read_table("employees")
    if len(em):
        with st.form("sp"):
            nik=st.selectbox("NIK",em.nik.tolist(),format_func=lambda n:f"{n} - {em[em.nik==n].iloc[0].nama}")
            jenis=st.selectbox("Jenis SP",["SP1","SP2","SP3"])
            tgl=st.date_input("Tanggal SP",value=date.today())
            nomor=st.text_input("Nomor surat")
            note=st.text_area("Catatan")
            save=st.form_submit_button("Simpan SP")
        if save:
            with db() as c:c.execute("INSERT INTO warnings(nik,jenis,tanggal,nomor,catatan,created_by,created_at) VALUES(?,?,?,?,?,?,?)",(nik,jenis,tgl.isoformat(),nomor,note,user,datetime.now().isoformat()))
            st.success("SP tersimpan.")
    data=read_table("warnings");st.dataframe(data,use_container_width=True)
    if len(data):st.download_button("Unduh Excel",xlsx_bytes(data),"arsip_sp.xlsx")

elif menu == "Evaluasi Karyawan (H3)" and menu in menus:
    st.subheader("Evaluasi Karyawan H3")
    st.caption("Hanya karyawan berstatus H3. Pastikan STATUS dan MASUK terisi benar pada Master Data.")
    em=read_table("employees")
    h3=em[em.status.astype(str).str.upper().eq("H3")] if len(em) else em
    if h3.empty: st.warning("Belum ada karyawan berstatus H3. Sistem tidak menebak status H3 dari data lain.")
    else:
        n=st.text_input("Masukkan NIK (bisa banyak; pisahkan dengan koma, titik koma, atau baris baru)")
        asof=st.date_input("Tanggal evaluasi",value=date.today())
        nicks=[x.strip() for x in n.replace(";",",").replace("\n",",").split(",") if x.strip()]
        results=[]
        for nik in nicks:
            if nik not in set(h3.nik):
                st.error(f"NIK {nik} tidak ditemukan sebagai H3.")
                continue
            emp=employee(nik); m=months_service(emp[4],asof)
            due=[x for x in MILESTONES if x<= (m or 0)]
            milestone=st.selectbox(f"Periode evaluasi {nik} · {emp[1]} · masa kerja {m if m is not None else 'tidak diketahui'} bulan",due or [0],format_func=lambda x:"Belum Jatuh Tempo" if x==0 else f"{x} bulan",key=f"ms_{nik}")
            if milestone:
                result=score_employee(nik,milestone,asof)
                results.append(result)
        if results:
            st.write("Pratinjau hasil perhitungan")
            preview=pd.DataFrame([{"NIK":r["emp"][0],"Nama":r["emp"][1],"Bagian":r["emp"][2],"Shift":r["emp"][3],"MASUK":r["emp"][4],"Masa Kerja (bulan)":r["bulan"],"Periode":r["milestone"],"Sakit (hari)":r["sakit"],"Izin (hari)":r["izin"],"Alpa (hari)":r["alpa"],"SP1":r["sp1"],"SP2":r["sp2"],"SP3":r["sp3"],"Skor":r["skor"],"Rincian":r["detail"]} for r in results])
            st.dataframe(preview,use_container_width=True)
            catatan=st.text_area("Catatan HRD / rekomendasi (opsional)")
            if st.button("Simpan Evaluasi",type="primary"):
                saved=0
                with db() as c:
                    for r in results:
                        if r["milestone"]==0: continue
                        try:
                            c.execute("""INSERT INTO evaluations(nik,milestone,tanggal_evaluasi,masa_kerja_bulan,sakit_hari,izin_hari,alpa_hari,sp1,sp2,sp3,skor,rincian,catatan,rekomendasi,dibuat_oleh,dibuat_pada)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(r["emp"][0],r["milestone"],asof.isoformat(),r["bulan"] or 0,r["sakit"],r["izin"],r["alpa"],r["sp1"],r["sp2"],r["sp3"],r["skor"],r["detail"],catatan,"Perlu keputusan HRD; skor bukan keputusan kontrak",user,datetime.now().isoformat()))
                            saved+=1
                        except sqlite3.IntegrityError: st.warning(f"Evaluasi NIK {r['emp'][0]} periode {r['milestone']} bulan sudah ada. Tidak ditimpa.")
                st.success(f"{saved} evaluasi disimpan. Snapshot lama tidak ditimpa.")
            st.download_button("Unduh rekap Excel",xlsx_bytes(preview,"Evaluasi_H3"),"evaluasi_h3.xlsx")
    hist=read_table("evaluations")
    st.subheader("Riwayat evaluasi")
    st.dataframe(hist,use_container_width=True)

elif menu == "Daftar Karyawan Tidak Lanjut Kontrak" and menu in menus:
    st.subheader("Permintaan Karyawan Tidak Lanjut Kontrak")
    em=read_table("employees")
    if em.empty: st.warning("Master Data belum tersedia.")
    else:
        with st.form("nonrenew"):
            nik=st.selectbox("NIK",em.nik.tolist(),format_func=lambda n:f"{n} - {em[em.nik==n].iloc[0].nama}")
            tanggal=st.date_input("Tanggal permintaan",value=date.today())
            atasan=st.text_input("Nama atasan / supervisor")
            alasan=st.text_area("Alasan permintaan")
            save=st.form_submit_button("Catat Permintaan",type="primary")
        if save:
            if not atasan.strip() or not alasan.strip(): st.error("Atasan dan alasan wajib diisi.")
            else:
                with db() as c:
                    dup=c.execute("SELECT id FROM nonrenew_requests WHERE nik=? AND status!='Selesai'",(nik,)).fetchone()
                    if dup: st.error("Masih ada permintaan aktif untuk NIK ini. Perbarui permintaan yang ada.")
                    else:
                        c.execute("INSERT INTO nonrenew_requests(nik,tanggal_permintaan,atasan,alasan,status,dibuat_oleh,dibuat_pada) VALUES(?,?,?,?,?,?,?)",(nik,tanggal.isoformat(),atasan,alasan,"Permintaan Baru",user,datetime.now().isoformat()))
                        st.success("Permintaan tercatat; status karyawan tidak otomatis diubah.")
    req=read_table("nonrenew_requests")
    if len(req):
        st.dataframe(req,use_container_width=True)
        ids=req.id.tolist()
        rid=st.selectbox("Pilih nomor permintaan untuk tindak lanjut",ids)
        status=st.selectbox("Status",["Permintaan Baru","Menunggu Verifikasi","Kontrak Masih Aktif","Menunggu Akhir Kontrak","Selesai"])
        note=st.text_area("Catatan HRD")
        if st.button("Perbarui Status"):
            with db() as c:c.execute("UPDATE nonrenew_requests SET status=?,catatan_hrd=? WHERE id=?",(status,note,int(rid)))
            st.success("Status diperbarui.");st.rerun()
        st.download_button("Unduh daftar Excel",xlsx_bytes(req),"daftar_tidak_lanjut_kontrak.xlsx")
    else: st.info("Belum ada permintaan.")

elif menu == "Panggilan Karyawan" and menu in menus:
    st.subheader("Pencatatan Panggilan Karyawan")
    em=read_table("employees")
    if len(em):
        with st.form("call"):
            nik=st.selectbox("NIK",em.nik.tolist(),format_func=lambda n:f"{n} - {em[em.nik==n].iloc[0].nama}")
            tgl=st.date_input("Tanggal panggilan",value=date.today())
            alasan=st.text_area("Alasan panggilan")
            save=st.form_submit_button("Simpan panggilan")
        if save:
            if not alasan.strip():st.error("Alasan wajib diisi.")
            else:
                with db() as c:c.execute("INSERT INTO calls(nik,tanggal,alasan,petugas) VALUES(?,?,?,?)",(nik,tgl.isoformat(),alasan,user))
                st.success("Panggilan tercatat.")
    calls=read_table("calls");st.dataframe(calls,use_container_width=True)
    if len(calls):st.download_button("Unduh Excel",xlsx_bytes(calls),"riwayat_panggilan.xlsx")

elif menu == "Riwayat Karyawan" and menu in menus:
    st.subheader("Riwayat Karyawan")
    em=read_table("employees")
    if len(em):
        nik=st.selectbox("Pilih NIK",em.nik.tolist())
        st.write("Data karyawan");st.dataframe(em[em.nik==nik],use_container_width=True)
        for table,label in [("attendance","Absensi"),("warnings","SP"),("evaluations","Evaluasi"),("nonrenew_requests","Permintaan Tidak Lanjut"),("calls","Panggilan")]:
            data=read_table(table)
            st.markdown(f"**{label}**")
            if len(data) and "nik" in data: st.dataframe(data[data.nik==nik],use_container_width=True)
            else: st.caption("Belum ada data.")
