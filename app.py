import streamlit as st
import pandas as pd
import os
from datetime import datetime

# ==========================================
# KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(
    page_title="HRD Tools - Manajemen Panggilan",
    page_icon="📋",
    layout="wide"
)

# File Penyimpanan
FILE_MASTER = "master_karyawan.csv"
FILE_PANGGILAN = "database_panggilan.csv"

# Daftar Hak Akses Admin / Manager
ADMIN_USERS = ["agung", "niko", "iis", "nurhayat"]

# Mapping NIK Tally ke Shift
TALLY_MAPPING = {
    "23010202": "Shift E",
    "26090328": "Shift F",
    "26092377": "Shift G"
}

# ==========================================
# FUNGSI HELPER / DATABASE LOKAL
# ==========================================
def load_master_data():
    if os.path.exists(FILE_MASTER):
        try:
            df = pd.read_csv(FILE_MASTER, dtype=str)
            return df
        except Exception:
            return pd.DataFrame(columns=["NIK", "Nama", "Bagian", "Shift"])
    return pd.DataFrame(columns=["NIK", "Nama", "Bagian", "Shift"])

def save_master_data(df):
    # Menyimpan dan menimpa (overwrite) file master lama
    df.to_csv(FILE_MASTER, index=False)

def load_panggilan_data():
    if os.path.exists(FILE_PANGGILAN):
        try:
            return pd.read_csv(FILE_PANGGILAN, dtype=str)
        except Exception:
            return pd.DataFrame(columns=["Tanggal", "Waktu", "NIK", "Nama", "Bagian", "Shift", "Alasan", "Petugas"])
    return pd.DataFrame(columns=["Tanggal", "Waktu", "NIK", "Nama", "Bagian", "Shift", "Alasan", "Petugas"])

def save_panggilan_data(df):
    df.to_csv(FILE_PANGGILAN, index=False)

# ==========================================
# SISTEM LOGIN INSTAN
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = ""
    st.session_state.is_admin = False
    st.session_state.shift = ""

if not st.session_state.logged_in:
    st.title("🔒 Login HRD Tools")
    st.caption("Masukkan Username Admin atau NIK Tally untuk masuk")
    
    input_login = st.text_input("Username / NIK", value="", placeholder="")
    
    if st.button("Login", type="primary", use_container_width=True):
        user_clean = input_login.strip().lower()
        
        if user_clean in ADMIN_USERS:
            st.session_state.logged_in = True
            st.session_state.user_id = user_clean.upper()
            st.session_state.is_admin = True
            st.session_state.shift = "All Shift (Admin)"
            st.success(f"Selamat datang, {st.session_state.user_id}!")
            st.rerun()
        elif input_login.strip() in TALLY_MAPPING:
            nik = input_login.strip()
            st.session_state.logged_in = True
            st.session_state.user_id = f"Tally ({nik})"
            st.session_state.is_admin = False
            st.session_state.shift = TALLY_MAPPING[nik]
            st.success(f"Selamat datang Tally {nik} - {TALLY_MAPPING[nik]}!")
            st.rerun()
        else:
            st.error("Username atau NIK tidak terdaftar!")
    st.stop()

# ==========================================
# SIDEBAR / MENU UTAMA DI SEBELAH KIRI
# ==========================================
st.sidebar.title("📌 Menu Utama")
st.sidebar.write(f"👤 **User:** {st.session_state.user_id}")
st.sidebar.write(f"🏷️ **Akses:** {st.session_state.shift}")

# Pilihan Menu Utama
menu_options = ["Panggilan Karyawan"]
if st.session_state.is_admin:
    # Menu Master Data hanya muncul untuk Admin/Manager
    menu_options.insert(0, "Master Data Karyawan")

menu_utama = st.sidebar.radio("Pilih Menu:", menu_options)

st.sidebar.markdown("---")
if st.sidebar.button("🚪 Logout", use_container_width=True):
    st.session_state.logged_in = False
    st.rerun()

# ==========================================
# MENU 1: MASTER DATA KARYAWAN
# ==========================================
if menu_utama == "Master Data Karyawan":
    st.title("🗂️ Master Data Karyawan")
    st.info("Menu ini digunakan untuk memperbarui database karyawan. Mengunggah data baru akan **menghapus data lama** secara otomatis.")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("📥 1. Download Template")
        template_df = pd.DataFrame({
            "NIK": ["1001", "1002"],
            "Nama": ["Budi Santoso", "Siti Aminah"],
            "Bagian": ["Produksi", "Packing"],
            "Shift": ["Shift E", "Shift F"]
        })
        csv_template = template_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Template CSV",
            data=csv_template,
            file_name="template_master_karyawan.csv",
            mime="text/csv",
            use_container_width=True
        )

    with col2:
        st.subheader("📤 2. Upload Data Baru")
        uploaded_file = st.file_uploader("Pilih file Excel atau CSV:", type=["csv", "xlsx"])
        
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith('.csv'):
                    new_df = pd.read_csv(uploaded_file, dtype=str)
                else:
                    new_df = pd.read_excel(uploaded_file, dtype=str)
                
                # Memastikan kolom sesuai
                required_cols = ["NIK", "Nama", "Bagian", "Shift"]
                if all(col in new_df.columns for col in required_cols):
                    st.write("🔍 **Pratinjau Data Baru:**")
                    st.dataframe(new_df.head(5), use_container_width=True)
                    
                    st.warning("⚠️ **Perhatian:** Mengklik tombol di bawah ini akan **MENGHAPUS SELURUH MASTER DATA LAMA** dan menggantinya dengan file ini.")
                    
                    if st.button("🔥 Hapus Data Lama & Import Data Baru", type="primary"):
                        save_master_data(new_df[required_cols])
                        st.success("✅ Master Data Karyawan berhasil diperbarui!")
                        st.rerun()
                else:
                    st.error(f"Format kolom tidak sesuai! Pastikan file memiliki kolom: {', '.join(required_cols)}")
            except Exception as e:
                st.error(f"Gagal membaca file: {e}")

    st.markdown("---")
    st.subheader("📋 Master Data Karyawan Saat Ini")
    df_current = load_master_data()
    if not df_current.empty:
        st.write(f"Total Karyawan Terdaftar: **{len(df_current)}** orang")
        st.dataframe(df_current, use_container_width=True)
    else:
        st.warning("Belum ada data karyawan terdaftar. Silakan upload data terlebih dahulu.")

# ==========================================
# MENU 2: PANGGILAN KARYAWAN
# ==========================================
elif menu_utama == "Panggilan Karyawan":
    st.title("📞 Form Panggilan Karyawan")
    
    df_master = load_master_data()
    
    if df_master.empty:
        st.warning("⚠️ Master data karyawan masih kosong. Harap Minta Admin untuk mengunggah Master Data terlebih dahulu.")
    else:
        with st.form("form_panggilan", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            
            with col_a:
                nik_input = st.selectbox("Pilih / Ketik NIK Karyawan:", [""] + list(df_master["NIK"].unique()))
                
                # Auto-fill nama, bagian, shift berdasarkan NIK yang dipilih
                nama_val, bagian_val, shift_val = "", "", ""
                if nik_input:
                    match = df_master[df_master["NIK"] == nik_input]
                    if not match.empty:
                        nama_val = match.iloc[0]["Nama"]
                        bagian_val = match.iloc[0]["Bagian"]
                        shift_val = match.iloc[0]["Shift"]
                
                st.text_input("Nama Karyawan", value=nama_val, disabled=True)
            
            with col_b:
                st.text_input("Bagian / Departemen", value=bagian_val, disabled=True)
                st.text_input("Shift", value=shift_val, disabled=True)
            
            alasan = st.text_area("Alasan Panggilan:", placeholder="Tuliskan alasan dipanggil...")
            
            submit_btn = st.form_submit_button("🚨 Kirim Panggilan", type="primary", use_container_width=True)
            
            if submit_btn:
                if not nik_input:
                    st.error("Silakan pilih NIK Karyawan terlebih dahulu!")
                elif not alasan.strip():
                    st.error("Alasan panggilan wajib diisi!")
                else:
                    df_panggilan = load_panggilan_data()
                    now = datetime.now()
                    
                    new_row = pd.DataFrame([{
                        "Tanggal": now.strftime("%Y-%m-%d"),
                        "Waktu": now.strftime("%H:%M:%S"),
                        "NIK": nik_input,
                        "Nama": nama_val,
                        "Bagian": bagian_val,
                        "Shift": shift_val,
                        "Alasan": alasan,
                        "Petugas": st.session_state.user_id
                    }])
                    
                    df_panggilan = pd.concat([df_panggilan, new_row], ignore_index=True)
                    save_panggilan_data(df_panggilan)
                    st.success(f"✅ Panggilan untuk {nama_val} ({nik_input}) berhasil dicatat!")

    # ------------------------------------------
    # TABEL REKAP PANGGILAN
    # ------------------------------------------
    st.markdown("---")
    st.subheader("📊 Rekap Riwayat Panggilan")
    
    df_rekap = load_panggilan_data()
    if not df_rekap.empty:
        # Filter berdasarkan hak akses shift jika bukan admin
        if not st.session_state.is_admin:
            df_rekap = df_rekap[df_rekap["Shift"] == st.session_state.shift]
        
        st.dataframe(df_rekap, use_container_width=True)
        
        # Fitur Download Rekap Data
        csv_rekap = df_rekap.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Rekap Data (CSV)",
            data=csv_rekap,
            file_name=f"rekap_panggilan_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.info("Belum ada riwayat panggilan yang tercatat.")
