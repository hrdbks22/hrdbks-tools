import streamlit as st
import pandas as pd
import sqlite3
import io
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="HRD Tools | PT. Berkat Karunia Surya", page_icon="📋", layout="wide")
DB = "hrd_tools.db"
ADMIN_USERS = {"agung", "niko", "iis", "nurhayat"}
TALLY_USERS = {"23010202": "E", "26090328": "F", "26092377": "G"}
ACTIVE_STATUSES = {"S3", "S4"}
MILESTONES = [1, 2, 3, 6, 9, 12]

def db():
    return sqlite3.connect(DB, check_same_thread=False)

def init_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS employees(
          nik TEXT PRIMARY KEY, nama TEXT NOT NULL, bagian TEXT, shift TEXT,
          masuk TEXT, status TEXT, sumber TEXT, updated_at TEXT
        );
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
init_db()

def read_table(name):
    with db() as c:
        return pd.read_sql_query(f"SELECT * FROM {name}", c)

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

# Login: akun dan password wajib disiapkan di Streamlit Secrets.
if "user" not in st.session_state: st.session_state.user = None
if not st.session_state.user:
    st.title("🔐 HRD Tools")
    st.caption("PT. BERKAT KARUNIA SURYA")
    st.info("Akses memerlukan konfigurasi [users] di Streamlit Secrets. Username saja tidak lagi cukup untuk melindungi data karyawan.")
    try: users = dict(st.secrets["users"])
    except Exception: users = {}
    if not users:
        st.error("Belum ada akun. Tambahkan username dan password pada Streamlit Secrets sebelum aplikasi digunakan.")
        st.stop()
    with st.form("login"):
        u = st.text_input("Username").strip().lower()
        p = st.text_input("Password", type="password")
        ok = st.form_submit_button("Masuk", type="primary")
    if ok:
        if u in users and str(users[u]) == p:
            st.session_state.user = u
            st.rerun()
        else: st.error("Username atau password salah.")
    st.stop()

user = st.session_state.user
is_admin = user in ADMIN_USERS
st.sidebar.title("HRD Tools")
st.sidebar.caption(f"Login: {user.upper()} · {'Admin' if is_admin else 'User'}")
menus = ["Dashboard", "Panggilan Karyawan"]
if is_admin:
    menus = ["Dashboard","Master Data Karyawan","Data Absensi","Arsip & Monitoring SP",
             "Evaluasi Karyawan (H3)","Daftar Karyawan Tidak Lanjut Kontrak",
             "Panggilan Karyawan","Riwayat Karyawan"]
menu = st.sidebar.radio("Menu", menus)
if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()

st.title("PT. BERKAT KARUNIA SURYA")
st.caption("Sistem Administrasi Human Resources")

if menu == "Dashboard":
    em = read_table("employees")
    at = read_table("attendance")
    sp = read_table("warnings")
    nr = read_table("nonrenew_requests")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Master Karyawan",len(em))
    c2.metric("Data Absensi",len(at))
    c3.metric("Catatan SP",len(sp))
    c4.metric("Permintaan Tidak Lanjut",len(nr[nr.status!="Selesai"]) if len(nr) else 0)
    st.subheader("Kontrak mendekati akhir")
    if len(em) and "keluar" in em.columns:
        st.dataframe(em, use_container_width=True)
    else:
        st.info("Tambahkan tanggal MASUK dan KELUAR melalui impor Master Data untuk memulai monitoring kontrak.")
    st.caption("Data dan keputusan HRD harus diverifikasi. Sistem tidak menetapkan keputusan perpanjangan atau pemutusan kontrak otomatis.")

elif menu == "Master Data Karyawan":
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
                                c.execute("""INSERT INTO employees(nik,nama,bagian,shift,masuk,status,sumber,updated_at)
                                VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(nik) DO UPDATE SET
                                nama=excluded.nama,bagian=excluded.bagian,shift=excluded.shift,
                                masuk=CASE WHEN excluded.masuk='' THEN employees.masuk ELSE excluded.masuk END,
                                status=CASE WHEN excluded.status='' THEN employees.status ELSE excluded.status END,
                                sumber=excluded.sumber,updated_at=excluded.updated_at""",
                                (r.NIK,r.NAMA,r.BAGIAN,r.SHIFT,r.MASUK,r.STATUS,up.name,datetime.now().isoformat(timespec="seconds")))
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

elif menu == "Data Absensi":
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

elif menu == "Arsip & Monitoring SP":
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

elif menu == "Evaluasi Karyawan (H3)":
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

elif menu == "Daftar Karyawan Tidak Lanjut Kontrak":
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

elif menu == "Panggilan Karyawan":
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

elif menu == "Riwayat Karyawan":
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
