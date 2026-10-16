from datetime import datetime
from io import BytesIO
import os
import sys

# --- PENGECEKAN MODUL PENDUKUNG ---
try:
  import pandas as pd
  import streamlit as st
  import openpyxl
except ImportError as e:
  print("==================================================")
  print("KESALAHAN: Modul Python belum terinstal dengan lengkap.")
  print(f"Detail Error: {e}")
  print("Silakan buka CMD, lalu ketik: pip install streamlit pandas openpyxl")
  print("==================================================")
  input("Tekan Enter untuk keluar...")
  sys.exit(1)

# Konfigurasi Halaman (Wide Layout)
st.set_page_config(
    page_title="hrd_tools - Panggilan Karyawan", page_icon="📊", layout="wide"
)

# File Database Lokal
DB_TRANSAKSI = "database_panggilan.csv"
DB_MASTER = "master_karyawan.csv"

# --- BUAT DEFAULT MASTER KARYAWAN JIKA BELUM ADA ---
if not os.path.exists(DB_MASTER):
  default_master = pd.DataFrame([
      {
          "NIK": "agung",
          "Nama": "Agung",
          "Bagian": "Manager HRD",
          "Shift": "Universal",
      },
      {
          "NIK": "niko",
          "Nama": "Niko",
          "Bagian": "Admin HRD 1",
          "Shift": "Universal",
      },
      {
          "NIK": "iis",
          "Nama": "Iis",
          "Bagian": "Admin HRD 2",
          "Shift": "Universal",
      },
      {
          "NIK": "nurhayat",
          "Nama": "Nurhayat",
          "Bagian": "Admin HRD 3",
          "Shift": "Universal",
      },
      {
          "NIK": "23010202",
          "Nama": "Tally 1",
          "Bagian": "Tally Lapangan",
          "Shift": "E",
      },
      {
          "NIK": "26090328",
          "Nama": "Tally 2",
          "Bagian": "Tally Lapangan",
          "Shift": "F",
      },
      {
          "NIK": "26092377",
          "Nama": "Tally 3",
          "Bagian": "Tally Lapangan",
          "Shift": "G",
      },
      {
          "NIK": "P001",
          "Nama": "Siti Rahma",
          "Bagian": "Produksi Plywood",
          "Shift": "E",
      },
      {
          "NIK": "P002",
          "Nama": "Budi Santoso",
          "Bagian": "Produksi Plywood",
          "Shift": "F",
      },
      {
          "NIK": "P003",
          "Nama": "Ahmad Fauzi",
          "Bagian": "Maintenance / Mesin",
          "Shift": "G",
      },
      {
          "NIK": "P004",
          "Nama": "Dewi Lestari",
          "Bagian": "Gudang / Logistik",
          "Shift": "M",
      },
  ])
  default_master.to_csv(DB_MASTER, index=False)


def load_master():
  return pd.read_csv(DB_MASTER, dtype=str)


def load_transaksi():
  if os.path.exists(DB_TRANSAKSI):
    df = pd.read_csv(DB_TRANSAKSI)
    if "Status" not in df.columns:
      df["Status"] = "Menghadap"
    return df
  else:
    return pd.DataFrame(columns=[
        "Waktu Input",
        "Login User",
        "NIK Karyawan",
        "Nama Karyawan",
        "Departemen",
        "Shift",
        "Keperluan",
        "Status",
    ])


df_master = load_master()
df_panggilan = load_transaksi()

if "logged_in" not in st.session_state:
  st.session_state.logged_in = False
  st.session_state.user_role = None
  st.session_state.username = None
  st.session_state.allowed_shifts = []

# --- HALAMAN LOGIN ---
if not st.session_state.logged_in:
  col1, col2, col3 = st.columns([1, 2, 1])
  with col2:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.title("🔐 Login Portal - hrd_tools")
    st.write("Silakan masukkan Username Admin atau NIK Karyawan.")

    with st.form("login_form"):
      identifier = st.text_input("Username / NIK Karyawan")
      btn_login = st.form_submit_button(
          "Masuk ke Dashboard", use_container_width=True
      )

      if btn_login:
        clean_id = identifier.strip().lower()

        if clean_id == "23010202":
          st.session_state.logged_in = True
          st.session_state.user_role = "tally"
          st.session_state.username = "Tally 1 (23010202)"
          st.session_state.allowed_shifts = ["E", "M", "N", "O", "P", "J"]
          st.rerun()
        elif clean_id == "26090328":
          st.session_state.logged_in = True
          st.session_state.user_role = "tally"
          st.session_state.username = "Tally 2 (26090328)"
          st.session_state.allowed_shifts = ["F", "M", "N", "O", "P", "J"]
          st.rerun()
        elif clean_id == "26092377":
          st.session_state.logged_in = True
          st.session_state.user_role = "tally"
          st.session_state.username = "Tally 3 (26092377)"
          st.session_state.allowed_shifts = ["G", "M", "N", "O", "P", "J"]
          st.rerun()
        else:
          valid_admins = ["agung", "niko", "iis", "nurhayat"]
          if clean_id in valid_admins:
            st.session_state.logged_in = True
            st.session_state.user_role = "admin"
            st.session_state.username = clean_id
            st.session_state.allowed_shifts = [
                "E",
                "F",
                "G",
                "M",
                "N",
                "O",
                "P",
                "J",
            ]
            st.rerun()
          else:
            st.error("Username atau NIK tidak dikenali dalam sistem!")

# --- HALAMAN UTAMA (DASHBOARD) ---
else:
  with st.sidebar:
    st.markdown(f"### Halo, `{st.session_state.username}`")
    st.markdown(
        f"**Peran:** "
        f"{'Manager / Admin HRD' if st.session_state.user_role == 'admin' else 'Tally Lapangan'}"
    )
    st.markdown("---")

    # Menu khusus Admin: Download Template & Upload Master Karyawan
    if st.session_state.user_role == "admin":
      st.markdown("### 📂 Master Data Karyawan")

      # Tombol Download Template Excel
      template_df = pd.DataFrame(
          columns=["NIK", "Nama", "Bagian", "Shift"],
          data=[
              ["P001", "Contoh Nama Karyawan", "Produksi Plywood", "E"],
              ["agung", "Agung", "Manager HRD", "Universal"],
          ],
      )
      output_template = BytesIO()
      with pd.ExcelWriter(output_template, engine="openpyxl") as writer:
        template_df.to_excel(
            writer, index=False, sheet_name="Master_Template"
        )
      excel_template_data = output_template.getvalue()

      st.download_button(
          label="📥 Download Template Excel",
          data=excel_template_data,
          file_name="template_master_karyawan.xlsx",
          mime=(
              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          ),
          use_container_width=True,
      )

      st.markdown("<br>", unsafe_allow_html=True)
      st.write("Upload file master yang sudah diisi:")
      uploaded_file = st.file_uploader(
          "Pilih file (.csv / .xlsx)", type=["csv", "xlsx"]
      )
      if uploaded_file is not None:
        try:
          if uploaded_file.name.endswith(".csv"):
            new_master = pd.read_csv(uploaded_file, dtype=str)
          else:
            new_master = pd.read_excel(uploaded_file, dtype=str)

          new_master.to_csv(DB_MASTER, index=False)
          st.success("Master Karyawan berhasil di-update!")
          st.rerun()
        except Exception as e:
          st.error(f"Gagal membaca file: {e}")
      st.markdown("---")

    if st.button("🚪 Keluar Sistem", use_container_width=True):
      st.session_state.logged_in = False
      st.session_state.user_role = None
      st.session_state.username = None
      st.session_state.allowed_shifts = []
      st.rerun()

  st.title("📊 hrd_tools - Dashboard Panggilan Karyawan")
  st.markdown("Pencatatan kehadiran karyawan dan koordinasi ke bagian HRD.")
  st.markdown("---")

  total_panggilan = len(df_panggilan)
  menghadap_count = (
      len(df_panggilan[df_panggilan["Status"] == "Menghadap"])
      if not df_panggilan.empty
      else 0
  )
  selesai_count = (
      len(df_panggilan[df_panggilan["Status"] == "Selesai"])
      if not df_panggilan.empty
      else 0
  )

  col_m1, col_m2, col_m3 = st.columns(3)
  with col_m1:
    st.metric(label="📋 Total Panggilan", value=total_panggilan)
  with col_m2:
    st.metric(
        label="⏳ Status Menghadap", value=menghadap_count, delta="Belum Selesai"
    )
  with col_m3:
    st.metric(label="✅ Panggilan Selesai", value=selesai_count, delta="Closed")

  st.markdown("---")

  col_form, col_data = st.columns([1, 1.4], gap="large")

  with col_form:
    st.subheader("➕ Buat Panggilan (Auto-Fill Master)")

    selected_nik = ""
    nama_karyawan = ""
    departemen = "Produksi Plywood"

    if not df_master.empty and "NIK" in df_master.columns:
      list_nik_nama = (df_master["NIK"] + " - " + df_master["Nama"]).tolist()
      chosen_employee = st.selectbox(
          "Cari & Pilih NIK / Nama Karyawan",
          ["-- Ketik / Pilih Karyawan --"] + list_nik_nama,
      )

      if chosen_employee != "-- Ketik / Pilih Karyawan --":
        selected_nik = chosen_employee.split(" - ")[0]
        emp_data = df_master[df_master["NIK"] == selected_nik].iloc[0]
        nama_karyawan = emp_data["Nama"]
        departemen = emp_data.get("Bagian", "Produksi Plywood")
        st.success(
            f"✅ **Terdeteksi:** {nama_karyawan} | Bagian: {departemen}"
        )
      else:
        st.info("Silakan pilih karyawan dari daftar di atas.")
    else:
      st.warning("Master data kosong.")

    with st.form("form_panggilan_submit", clear_on_submit=True):
      c1, c2 = st.columns(2)
      with c1:
        input_dept = st.text_input("Bagian / Departemen", value=departemen)
      with c2:
        input_shift = st.selectbox(
            "Shift Terkait", st.session_state.allowed_shifts, index=0
        )

      keperluan = st.text_area("Keperluan Panggilan / Catatan")
      submit_btn = st.form_submit_button(
          "Kirim Panggilan", use_container_width=True
      )

      if submit_btn:
        if selected_nik and nama_karyawan:
          new_row = pd.DataFrame([{
              "Waktu Input": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
              "Login User": st.session_state.username,
              "NIK Karyawan": selected_nik,
              "Nama Karyawan": nama_karyawan,
              "Departemen": input_dept,
              "Shift": input_shift,
              "Keperluan": keperluan,
              "Status": "Menghadap",
          }])
          df_panggilan = pd.concat([df_panggilan, new_row], ignore_index=True)
          df_panggilan.to_csv(DB_TRANSAKSI, index=False)
          st.success("Panggilan berhasil dicatat!")
          st.rerun()
        else:
          st.warning("Mohon pilih karyawan terlebih dahulu.")

  with col_data:
    st.subheader("📌 Daftar Panggilan Aktif & Riwayat")

    if not df_panggilan.empty:
      search_query = st.text_input(
          "🔍 Cari berdasarkan NIK, Nama, atau Bagian", ""
      )
      filtered_df = df_panggilan
      if search_query:
        filtered_df = df_panggilan[
            df_panggilan["NIK Karyawan"].astype(str).str.contains(search_query, case=False, na=False) |
            df_panggilan["Nama Karyawan"].str.contains(search_query, case=False, na=False) |
            df_panggilan["Departemen"].str.contains(search_query, case=False, na=False)
        ]

      st.dataframe(filtered_df, use_container_width=True, height=350)

      with st.expander("🛠️ Perbarui Status Panggilan"):
        row_index = st.number_input(
            "Nomor Baris (Index) Data",
            min_value=0,
            max_value=max(0, len(df_panggilan) - 1),
            step=1,
        )
        new_status = st.selectbox("Ubah Status Menjadi", ["Menghadap", "Selesai"])
        if st.button("Update Status"):
          df_panggilan.loc[row_index, "Status"] = new_status
          df_panggilan.to_csv(DB_TRANSAKSI, index=False)
          st.success(f"Status berhasil diubah menjadi {new_status}!")
          st.rerun()

      if st.session_state.user_role == "admin":
        st.markdown("---")
        st.subheader("🛠️ Panel Kontrol Admin HRD")
        c_dl, c_rs = st.columns(2)

        with c_dl:
          output = BytesIO()
          with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df_panggilan.to_excel(
                writer, index=False, sheet_name="Rekap_Panggilan"
            )
          excel_data = output.getvalue()

          st.download_button(
              label="📥 Download Excel Rekap",
              data=excel_data,
              file_name=(
                  f"hrd_tools_rekap_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
              ),
              mime=(
                  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              ),
              use_container_width=True,
          )

        with c_rs:
          confirm_reset = st.checkbox("Konfirmasi Reset Data Transaksi")
          if st.button(
              "🗑️ Reset Database Panggilan", use_container_width=True
          ):
            if confirm_reset:
              empty_df = pd.DataFrame(columns=[
                  "Waktu Input",
                  "Login User",
                  "NIK Karyawan",
                  "Nama Karyawan",
                  "Departemen",
                  "Shift",
                  "Keperluan",
                  "Status",
              ])
              empty_df.to_csv(DB_TRANSAKSI, index=False)
              st.success("Database berhasil dikosongkan!")
              st.rerun()
            else:
              st.error("Centang kotak konfirmasi terlebih dahulu.")
    else:
      st.info("Belum ada data panggilan yang tercatat.")