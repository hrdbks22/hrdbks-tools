"""
HRD Tools Desktop - PT. Berkat Karunia Surya
Aplikasi lokal berbasis Tkinter + SQLite. Tidak memerlukan server.
"""
import os, sqlite3, hashlib, secrets, hmac, zipfile, traceback, sys
from pathlib import Path
from datetime import datetime, date
from html.parser import HTMLParser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

APP_NAME = "HRD TOOLS - PT. BERKAT KARUNIA SURYA"
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "hrd_tools.db"
MENUS = [
    "Dashboard", "Master Data Karyawan", "Data Absensi",
    "Arsip & Monitoring SP", "Evaluasi Karyawan (H3)",
    "Daftar Karyawan Tidak Lanjut Kontrak", "Panggilan Karyawan",
    "Riwayat Karyawan", "Pengaturan Pengguna"
]
ROLES = ("Super Admin", "Admin HRD", "Tally")

def db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c

def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 310000).hex()
    return salt, digest

def verify_password(password, salt, digest):
    return hmac.compare_digest(hash_password(password, salt)[1], digest)

def init_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(
          id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL,
          salt TEXT, password_hash TEXT, role TEXT NOT NULL,
          active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS menu_permissions(
          id INTEGER PRIMARY KEY, username TEXT NOT NULL, menu TEXT NOT NULL,
          allowed INTEGER NOT NULL DEFAULT 1,
          UNIQUE(username,menu),
          FOREIGN KEY(username) REFERENCES users(username) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS employees(
          nik TEXT PRIMARY KEY, nama TEXT, status TEXT, departemen TEXT,
          jabatan TEXT, tanggal_masuk TEXT, tanggal_keluar TEXT,
          sumber_data TEXT, updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS attendance(
          id INTEGER PRIMARY KEY, nik TEXT, nama TEXT, tanggal TEXT,
          sakit INTEGER DEFAULT 0, izin INTEGER DEFAULT 0, alpa INTEGER DEFAULT 0,
          keterangan TEXT, sumber_data TEXT,
          FOREIGN KEY(nik) REFERENCES employees(nik)
        );
        CREATE TABLE IF NOT EXISTS warnings(
          id INTEGER PRIMARY KEY, nik TEXT NOT NULL, tanggal TEXT,
          jenis_sp TEXT, keterangan TEXT,
          FOREIGN KEY(nik) REFERENCES employees(nik)
        );
        CREATE TABLE IF NOT EXISTS evaluations(
          id INTEGER PRIMARY KEY, nik TEXT NOT NULL, periode TEXT,
          bulan_ke INTEGER, sakit INTEGER DEFAULT 0, izin INTEGER DEFAULT 0,
          alpa INTEGER DEFAULT 0, sp1 INTEGER DEFAULT 0, sp2 INTEGER DEFAULT 0,
          sp3 INTEGER DEFAULT 0, nilai INTEGER, catatan TEXT,
          FOREIGN KEY(nik) REFERENCES employees(nik)
        );
        CREATE TABLE IF NOT EXISTS nonrenew_requests(
          id INTEGER PRIMARY KEY, nik TEXT NOT NULL, tanggal TEXT,
          alasan TEXT, status TEXT DEFAULT 'Menunggu',
          FOREIGN KEY(nik) REFERENCES employees(nik)
        );
        CREATE TABLE IF NOT EXISTS calls(
          id INTEGER PRIMARY KEY, nik TEXT, tanggal TEXT, tujuan TEXT,
          hasil TEXT, catatan TEXT
        );
        CREATE TABLE IF NOT EXISTS import_log(
          id INTEGER PRIMARY KEY, filename TEXT, jenis TEXT,
          jumlah INTEGER, imported_at TEXT
        );
        """)
        # Buat akun awal tanpa password; Super Admin wajib menetapkan password.
        for username, role in [
            ("niko","Super Admin"),("agung","Admin HRD"),("iis","Admin HRD"),
            ("nurhayat","Tally"),("23010202","Tally"),
            ("26090328","Tally"),("26092377","Tally")
        ]:
            c.execute("INSERT OR IGNORE INTO users(username,role,active) VALUES(?,?,1)", (username,role))
        for row in c.execute("SELECT username FROM users"):
            for menu in MENUS:
                c.execute("INSERT OR IGNORE INTO menu_permissions(username,menu,allowed) VALUES(?,?,?)",
                          (row["username"],menu,1))

class TableParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.tables=[]; self.table=None; self.row=None; self.cell=None
    def handle_starttag(self, tag, attrs):
        t=tag.lower()
        if t=="table": self.table=[]
        elif t=="tr" and self.table is not None: self.row=[]
        elif t in ("td","th") and self.row is not None: self.cell=""
    def handle_data(self, data):
        if self.cell is not None: self.cell += data
    def handle_endtag(self, tag):
        t=tag.lower()
        if t in ("td","th") and self.cell is not None:
            self.row.append(" ".join(self.cell.split())); self.cell=None
        elif t=="tr" and self.row is not None:
            if self.row: self.table.append(self.row)
            self.row=None
        elif t=="table" and self.table is not None:
            if self.table: self.tables.append(self.table)
            self.table=None

def read_any_excel(path, sheet=None):
    raw=Path(path).read_bytes()
    if raw.startswith(b"PK"):
        from openpyxl import load_workbook
        w=load_workbook(path,read_only=True,data_only=True)
        s=w[sheet] if sheet and sheet in w.sheetnames else w.active
        rows=list(s.iter_rows(values_only=True)); w.close()
        return rows
    if raw.startswith(b"\xd0\xcf\x11\xe0"):
        # CFB container: XLSB atau XLS lama; coba XLSB dahulu.
        try:
            from pyxlsb import open_workbook
            with open_workbook(str(path)) as w:
                sn=sheet if sheet in w.sheets else w.sheets[0]
                with w.get_sheet(sn) as s: return [[x.v for x in r] for r in s.rows()]
        except Exception:
            try:
                import xlrd
                w=xlrd.open_workbook(file_contents=raw)
                s=w.sheet_by_name(sheet) if sheet and sheet in w.sheet_names() else w.sheet_by_index(0)
                return [s.row_values(i) for i in range(s.nrows)]
            except Exception as e: raise ValueError(f"Format XLS/XLSB tidak terbaca: {e}")
    head=raw[:1000].lower().lstrip()
    if b"<html" in head or b"<table" in head or head.startswith(b"<!doctype"):
        text=None
        for enc in ("utf-8-sig","utf-16","cp1252","latin-1"):
            try: text=raw.decode(enc); break
            except UnicodeDecodeError: pass
        p=TableParser(); p.feed(text or "")
        if not p.tables: raise ValueError("Tidak ditemukan tabel HTML.")
        return max(p.tables,key=len)
    raise ValueError("Isi file tidak dikenali sebagai Excel atau HTML-export.")

def norm(v):
    if v is None: return ""
    if isinstance(v,float) and v.is_integer(): return str(int(v))
    return str(v).strip()

def header_index(headers, aliases):
    h={norm(x).lower():i for i,x in enumerate(headers)}
    for a in aliases:
        if a.lower() in h: return h[a.lower()]
    return None

def score_employee(sakit, izin, alpa, sp1, sp2, sp3):
    excess=max(0, int(sakit or 0)+int(izin or 0)-5)
    deduction=excess*3+int(alpa or 0)*10+int(sp1 or 0)*10+int(sp2 or 0)*20+int(sp3 or 0)*30
    return max(0,100-deduction)

class HRDApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME); self.geometry("1180x720"); self.minsize(980,600)
        self.user=None; self.role=None
        self.configure(bg="#f3f5f8")
        self.login_screen()

    def clear(self):
        for w in self.winfo_children(): w.destroy()

    def login_screen(self):
        self.clear()
        box=ttk.Frame(self,padding=32); box.place(relx=.5,rely=.5,anchor="center")
        ttk.Label(box,text=APP_NAME,font=("Segoe UI",18,"bold")).pack(pady=(0,8))
        ttk.Label(box,text="Aplikasi Administrasi HRD - Lokal").pack(pady=(0,20))
        ttk.Label(box,text="Username").pack(anchor="w")
        self.username=ttk.Entry(box,width=36); self.username.pack(pady=(4,12))
        ttk.Label(box,text="Password (kosongkan jika akun belum memiliki password)").pack(anchor="w")
        self.password=ttk.Entry(box,width=36,show="*"); self.password.pack(pady=4)
        ttk.Button(box,text="MASUK",command=self.login).pack(fill="x",pady=16)
        ttk.Label(box,text="Akun awal: niko, agung, iis, nurhayat, 23010202, 26090328, 26092377",
                  wraplength=400).pack()

    def login(self):
        u=self.username.get().strip(); p=self.password.get()
        with db() as c: row=c.execute("SELECT * FROM users WHERE username=? AND active=1",(u,)).fetchone()
        if not row: messagebox.showerror("Login gagal","Akun tidak ditemukan atau tidak aktif."); return
        if row["password_hash"]:
            if not verify_password(p,row["salt"],row["password_hash"]):
                messagebox.showerror("Login gagal","Password salah."); return
        elif p:
            messagebox.showerror("Login gagal","Akun ini belum memiliki password. Kosongkan password untuk masuk pertama kali."); return
        self.user=u; self.role=row["role"]; self.main_screen()

    def allowed(self, menu):
        if self.role=="Super Admin": return True
        with db() as c:
            r=c.execute("SELECT allowed FROM menu_permissions WHERE username=? AND menu=?",
                        (self.user,menu)).fetchone()
        return bool(r and r["allowed"])

    def main_screen(self):
        self.clear()
        shell=ttk.Frame(self); shell.pack(fill="both",expand=True)
        side=ttk.Frame(shell,padding=12); side.pack(side="left",fill="y")
        ttk.Label(side,text="HRD TOOLS",font=("Segoe UI",17,"bold")).pack(anchor="w",pady=(4,2))
        ttk.Label(side,text=f"{self.user} • {self.role}").pack(anchor="w",pady=(0,16))
        self.content=ttk.Frame(shell,padding=20); self.content.pack(side="left",fill="both",expand=True)
        for menu in MENUS:
            if self.allowed(menu):
                ttk.Button(side,text=menu,width=29,command=lambda m=menu:self.show_page(m)).pack(fill="x",pady=3)
        ttk.Separator(side).pack(fill="x",pady=12)
        ttk.Button(side,text="Keluar",command=self.login_screen).pack(fill="x")
        self.show_page("Dashboard")

    def show_page(self, menu):
        for w in self.content.winfo_children(): w.destroy()
        ttk.Label(self.content,text=menu,font=("Segoe UI",20,"bold")).pack(anchor="w",pady=(0,16))
        if menu=="Dashboard": self.dashboard()
        elif menu=="Master Data Karyawan": self.employee_page()
        elif menu=="Pengaturan Pengguna": self.user_page()
        else:
            ttk.Label(self.content,text="Modul ini sudah disiapkan pada navigasi dan akan dilengkapi pada tahap berikutnya.",
                      wraplength=700).pack(anchor="w")

    def dashboard(self):
        with db() as c:
            employees=c.execute("SELECT COUNT(*) n FROM employees").fetchone()["n"]
            active=c.execute("SELECT COUNT(*) n FROM employees WHERE status IN ('S3','S4')").fetchone()["n"]
            warnings=c.execute("SELECT COUNT(*) n FROM warnings").fetchone()["n"]
        for label,value in [("Total Karyawan",employees),("Karyawan Status S3/S4",active),("Catatan SP",warnings)]:
            card=ttk.LabelFrame(self.content,text=label,padding=18); card.pack(side="left",fill="x",expand=True,padx=6)
            ttk.Label(card,text=str(value),font=("Segoe UI",24,"bold")).pack()

    def employee_page(self):
        bar=ttk.Frame(self.content); bar.pack(fill="x",pady=(0,10))
        ttk.Button(bar,text="Impor Excel",command=self.import_employees).pack(side="left")
        ttk.Button(bar,text="Muat Ulang",command=self.refresh_employees).pack(side="left",padx=6)
        ttk.Button(bar,text="Ekspor XLSX",command=self.export_employees).pack(side="left")
        cols=("nik","nama","status","departemen","jabatan","tanggal_masuk")
        self.tree=ttk.Treeview(self.content,columns=cols,show="headings")
        labels=("NIK","Nama","Status","Departemen","Jabatan","Tanggal Masuk")
        for col,label in zip(cols,labels):
            self.tree.heading(col,text=label); self.tree.column(col,width=150)
        self.tree.pack(fill="both",expand=True)
        self.refresh_employees()

    def refresh_employees(self):
        if not hasattr(self,"tree") or not self.tree.winfo_exists(): return
        self.tree.delete(*self.tree.get_children())
        with db() as c:
            for r in c.execute("SELECT nik,nama,status,departemen,jabatan,tanggal_masuk FROM employees ORDER BY nama"):
                self.tree.insert("","end",values=tuple(r))

    def import_employees(self):
        path=filedialog.askopenfilename(title="Pilih Employee Tracker",
            filetypes=[("File Excel","*.xlsx *.xlsm *.xls *.xlsb"),("Semua file","*.*")])
        if not path: return
        try:
            rows=read_any_excel(path)
            if len(rows)<2: raise ValueError("Tidak ada baris data.")
            headers=rows[0]
            idx={
              "nik":header_index(headers,["NIK","No NIK","Employee ID","ID Karyawan"]),
              "nama":header_index(headers,["Nama","Nama Karyawan","Employee Name","Name"]),
              "status":header_index(headers,["Status","Status Karyawan","Employee Status"]),
              "departemen":header_index(headers,["Departemen","Department"]),
              "jabatan":header_index(headers,["Jabatan","Position"]),
              "tanggal_masuk":header_index(headers,["Tanggal Masuk","Tanggal Bergabung","Join Date","Hire Date"])
            }
            if idx["nik"] is None: raise ValueError("Kolom NIK tidak ditemukan. Periksa judul kolom file.")
            count=0
            with db() as c:
                for row in rows[1:]:
                    def val(key):
                        i=idx[key]
                        return norm(row[i]) if i is not None and i<len(row) else ""
                    nik=val("nik")
                    if not nik: continue
                    status=val("status")
                    if status and status.upper() not in ("S3","S4"): continue
                    c.execute("""INSERT INTO employees(nik,nama,status,departemen,jabatan,tanggal_masuk,sumber_data,updated_at)
                      VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(nik) DO UPDATE SET
                      nama=excluded.nama,status=excluded.status,departemen=excluded.departemen,
                      jabatan=excluded.jabatan,tanggal_masuk=excluded.tanggal_masuk,
                      sumber_data=excluded.sumber_data,updated_at=excluded.updated_at""",
                      (nik,val("nama"),status,val("departemen"),val("jabatan"),val("tanggal_masuk"),
                       Path(path).name,datetime.now().isoformat(timespec="seconds")))
                    count+=1
                c.execute("INSERT INTO import_log(filename,jenis,jumlah,imported_at) VALUES(?,?,?,?)",
                          (Path(path).name,"Master Karyawan",count,datetime.now().isoformat(timespec="seconds")))
            self.refresh_employees()
            messagebox.showinfo("Impor selesai",f"{count} data karyawan berhasil diproses.")
        except Exception as e: messagebox.showerror("Impor gagal",str(e))

    def export_employees(self):
        path=filedialog.asksaveasfilename(defaultextension=".xlsx",filetypes=[("Excel Workbook","*.xlsx")])
        if not path: return
        from openpyxl import Workbook
        with db() as c: rows=c.execute("SELECT nik,nama,status,departemen,jabatan,tanggal_masuk,tanggal_keluar FROM employees ORDER BY nama").fetchall()
        w=Workbook(); s=w.active; s.title="Master Karyawan"
        s.append(["NIK","Nama","Status","Departemen","Jabatan","Tanggal Masuk","Tanggal Keluar"])
        for r in rows: s.append(list(r))
        w.save(path); messagebox.showinfo("Ekspor selesai",f"File disimpan:\n{path}")

    def user_page(self):
        ttk.Label(self.content,text="Manajemen akun dan hak akses").pack(anchor="w")
        cols=("username","role","active")
        tree=ttk.Treeview(self.content,columns=cols,show="headings",height=10)
        for x in cols: tree.heading(x,text=x.title()); tree.column(x,width=180)
        tree.pack(fill="x",pady=10)
        with db() as c:
            for r in c.execute("SELECT username,role,active FROM users ORDER BY username"):
                tree.insert("","end",values=(r["username"],r["role"],"Aktif" if r["active"] else "Nonaktif"))
        ttk.Label(self.content,text="Fitur ubah password, peran, dan izin menu akan ditambahkan pada penyelesaian modul administrasi.",
                  wraplength=700).pack(anchor="w")

def main():
    # Pastikan aplikasi dijalankan dari folder file ini, bukan folder kerja terminal.
    os.chdir(BASE_DIR)
    init_db()
    app = HRDApp()
    app.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        error_text = traceback.format_exc()
        log_path = BASE_DIR / "hrd_tools_error.log"
        try:
            log_path.write_text(error_text, encoding="utf-8")
        except Exception:
            pass
        print(error_text, file=sys.stderr)
        try:
            messagebox.showerror(
                "HRD Tools - Terjadi Kesalahan",
                f"Aplikasi tidak dapat dijalankan.\n\n{exc}\n\n"
                f"Detail kesalahan tersimpan di:\n{log_path}"
            )
        except Exception:
            pass
        input("Tekan Enter untuk keluar...")
