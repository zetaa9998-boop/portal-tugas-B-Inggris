import sys
import asyncio
import requests
import json
import time
import streamlit as st
import pandas as pd

# Konfigurasi Event Loop untuk Windows
if sys.platform == 'win32':
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

st.set_page_config(page_title="Aplikasi Pengumpul Tugas SMK", layout="wide")

PASSWORD_GURU = "Guru123!"

# ID Google Sheet milikmu
SHEET_ID = "1BTUS3nbirH2sU_j6u2YLZDTykYyULMYXNsE30mkhiAo"

# ===================================================================
# FUNGSI MEMBACA DATA DARI GOOGLE SHEETS (REAL-TIME & AMAN TIPE DATA)
# ===================================================================
def muat_data_sheet(nama_tab):
    try:
        timestamp = int(time.time())
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={nama_tab}&_t={timestamp}"
        df = pd.read_csv(url, dtype=str) # Paksa baca sebagai String agar NIS/Angka tidak corrupt
        return df
    except Exception:
        return pd.DataFrame()

def muat_semua_data():
    df_siswa = muat_data_sheet("Siswa")
    df_tugas = muat_data_sheet("Tugas")
    df_pengumpulan = muat_data_sheet("Pengumpulan")
    return df_siswa, df_tugas, df_pengumpulan

df_siswa, df_tugas, df_pengumpulan = muat_semua_data()

# Bersihkan data jika ada kolom bernilai kosong/NaN
if not df_siswa.empty:
    df_siswa = df_siswa.fillna("")
if not df_tugas.empty:
    df_tugas = df_tugas.fillna("")
if not df_pengumpulan.empty:
    df_pengumpulan = df_pengumpulan.fillna("")

# ===================================================================
# FUNGSI KIRIM DATA KE GOOGLE APPS SCRIPT
# ===================================================================
def kirim_data_ke_sheet(action, payload):
    try:
        url = st.secrets["WEBAPP_URL"]
        response = requests.post(url, data=json.dumps({"action": action, "payload": payload}))
        if response.status_code == 200:
            return True
        else:
            st.error(f"Gagal menyimpan! Response: {response.text}")
            return False
    except Exception as e:
        st.error(f"Gagal menghubungkan ke Apps Script: {e}")
        return False

def dapatkan_tingkat_kelas(nama_kelas: str) -> str:
    kelas_upper = str(nama_kelas).upper().strip()
    if "XII" in kelas_upper or "12" in kelas_upper:
        return "Kelas XII"
    elif "XI" in kelas_upper or "11" in kelas_upper:
        return "Kelas XI"
    elif "X" in kelas_upper or "10" in kelas_upper:
        return "Kelas X"
    return "Lainnya"

# ===================================================================
# NAVIGASI SIDEBAR
# ===================================================================
st.sidebar.title("📌 Navigasi Portal")
role = st.sidebar.selectbox("Login Sebagai:", ["Siswa", "Guru"], key="main_role_select")

# ===================================================================
# PORTAL SISWA
# ===================================================================
if role == "Siswa":
    st.title("👨‍🎓 Portal Siswa - Pengumpulan Tugas")
    
    if df_siswa.empty or "Kelas" not in df_siswa.columns:
        st.warning("Data siswa belum tersedia atau Google Sheets belum diisi header (NIS, Nama Siswa, Kelas).")
    else:
        list_kelas = sorted(list(set(df_siswa["Kelas"].astype(str).str.strip().tolist())))
        list_kelas = [k for k in list_kelas if k != ""]
        
        if not list_kelas:
            st.warning("Belum ada data kelas yang terdaftar.")
        else:
            kelas_siswa = st.selectbox("Pilih Kelas Anda:", list_kelas, key="siswa_pilih_kelas")
            tingkat_siswa = dapatkan_tingkat_kelas(kelas_siswa)

            st.info(f"Tingkat Kelas Terdeteksi: **{tingkat_siswa}**")

            df_siswa_kelas = df_siswa[df_siswa["Kelas"].astype(str).str.strip() == str(kelas_siswa)]
            list_siswa = [s for s in df_siswa_kelas["Nama Siswa"].astype(str).tolist() if s != ""]

            if list_siswa:
                siswa_terpilih = st.selectbox("Pilih Nama Anda:", list_siswa, key="siswa_pilih_nama")
                nis_siswa = str(df_siswa_kelas[df_siswa_kelas["Nama Siswa"] == siswa_terpilih]["NIS"].values[0])

                tugas_tingkat = []
                if not df_tugas.empty and "Tingkat" in df_tugas.columns:
                    tugas_tingkat = df_tugas[df_tugas["Tingkat"] == tingkat_siswa]["Nama Tugas"].dropna().tolist()

                st.markdown("---")
                if not tugas_tingkat:
                    st.info(f"Belum ada tugas yang diberikan untuk **{tingkat_siswa}**.")
                else:
                    tugas_terpilih = st.selectbox("Pilih Tugas yang Ingin Dikumpulkan:", tugas_tingkat, key="siswa_pilih_tugas")

                    # Cek Status Pengumpulan
                    q_status = pd.DataFrame()
                    if not df_pengumpulan.empty and "NIS" in df_pengumpulan.columns:
                        q_status = df_pengumpulan[(df_pengumpulan["NIS"].astype(str) == nis_siswa) & (df_pengumpulan["Nama Tugas"] == tugas_terpilih)]
                    
                    if not q_status.empty:
                        status_saat_ini = str(q_status["Status"].values[0])
                        nilai_saat_ini = q_status["Nilai"].values[0]
                    else:
                        status_saat_ini = "Belum Mengumpulkan"
                        nilai_saat_ini = 0.0

                    if status_saat_ini == "Sudah Mengumpulkan":
                        st.success(f"✅ Status: **{status_saat_ini}** | Nilai: **{nilai_saat_ini}**")
                    else:
                        st.warning(f"⏳ Status: **{status_saat_ini}**")

                    with st.form("form_upload_siswa"):
                        file_tugas = st.file_uploader("Pilih Berkas Tugas (PDF/Gambar/Docx):", type=["pdf", "png", "jpg", "docx"])
                        submit_button = st.form_submit_button("Kirim Tugas")

                        if submit_button:
                            if file_tugas is not None:
                                payload = {
                                    "nis": nis_siswa,
                                    "tugas": tugas_terpilih,
                                    "status": "Sudah Mengumpulkan",
                                    "nilai": nilai_saat_ini
                                }
                                if kirim_data_ke_sheet("simpan_pengumpulan", payload):
                                    st.success(f"Berkas **'{file_tugas.name}'** berhasil dikirim!")
                                    st.rerun()
                            else:
                                st.error("Silakan pilih berkas terlebih dahulu.")

# ===================================================================
# PORTAL GURU
# ===================================================================
elif role == "Guru":
    st.title("👨‍🏫 Portal Guru - Pengelolaan & Penilaian")
    
    password_input = st.sidebar.text_input("Masukkan Kata Sandi Guru:", type="password", key="input_password_guru")

    if password_input != PASSWORD_GURU:
        if password_input != "":
            st.error("❌ Kata sandi salah!")
        else:
            st.info("🔒 Silakan masukkan kata sandi Guru.")
    else:
        st.success("🔓 Akses Diterima.")

        menu_guru = st.sidebar.radio("Pilih Menu Guru:", [
            "📊 Rekapitulasi & Penilaian", 
            "⚙️ Kelola Tugas Per Tingkat", 
            "👤 Kelola Data Siswa"
        ], key="radio_menu_guru")

        # ---------------------------------------------------------------
        # MENU 1: REKAPITULASI & PENILAIAN
        # ---------------------------------------------------------------
        if menu_guru == "📊 Rekapitulasi & Penilaian":
            st.header("📊 Rekapitulasi & Penilaian Tugas")

            tingkat_pilihan = st.selectbox("Pilih Tingkat Kelas:", ["Kelas X", "Kelas XI", "Kelas XII"], key="guru_select_tingkat_rekap")

            tugas_tersedia = []
            if not df_tugas.empty and "Tingkat" in df_tugas.columns:
                tugas_tersedia = df_tugas[df_tugas["Tingkat"] == tingkat_pilihan]["Nama Tugas"].dropna().tolist()

            if not tugas_tersedia:
                st.warning(f"Belum ada tugas yang dibuat untuk **{tingkat_pilihan}**.")
            else:
                col_tugas, col_kelas = st.columns(2)
                with col_tugas:
                    tugas_pilihan = st.selectbox("Pilih Tugas:", tugas_tersedia, key="guru_pilih_tugas_rekap")
                with col_kelas:
                    semua_kelas = df_siswa["Kelas"].dropna().astype(str).unique() if not df_siswa.empty else []
                    kelas_in_tingkat = [k for k in semua_kelas if dapatkan_tingkat_kelas(k) == tingkat_pilihan]
                    filter_kelas = st.selectbox("Filter Rombel/Kelas:", ["Semua Rombel"] + sorted(kelas_in_tingkat), key="guru_filter_rombel_rekap")

                df_siswa_tingkat = df_siswa.copy()
                if not df_siswa_tingkat.empty and "Kelas" in df_siswa_tingkat.columns:
                    df_siswa_tingkat["NIS"] = df_siswa_tingkat["NIS"].astype(str)
                    df_siswa_tingkat["Tingkat"] = df_siswa_tingkat["Kelas"].apply(dapatkan_tingkat_kelas)
                    df_siswa_tingkat = df_siswa_tingkat[df_siswa_tingkat["Tingkat"] == tingkat_pilihan]

                    if filter_kelas != "Semua Rombel":
                        df_siswa_tingkat = df_siswa_tingkat[df_siswa_tingkat["Kelas"].astype(str) == str(filter_kelas)]

                    df_p_sub = pd.DataFrame(columns=["NIS", "Nama Tugas", "Status", "Nilai"])
                    if not df_pengumpulan.empty and "Nama Tugas" in df_pengumpulan.columns:
                        df_p_sub = df_pengumpulan[df_pengumpulan["Nama Tugas"] == tugas_pilihan].copy()
                        if not df_p_sub.empty:
                            df_p_sub["NIS"] = df_p_sub["NIS"].astype(str)

                    df_rekap = pd.merge(df_siswa_tingkat, df_p_sub, on="NIS", how="left")
                    df_rekap["Status"] = df_rekap["Status"].fillna("Belum Mengumpulkan")
                    df_rekap["Nilai"] = df_rekap["Nilai"].fillna(0.0)

                    st.dataframe(df_rekap[["NIS", "Nama Siswa", "Kelas", "Status", "Nilai"]], use_container_width=True)

                    st.markdown("---")
                    st.subheader("📝 Input Skor Nilai Siswa")

                    list_nama_siswa = df_rekap["Nama Siswa"].tolist()
                    if list_nama_siswa:
                        siswa_pilihan = st.selectbox("Pilih Siswa:", list_nama_siswa, key="guru_pilih_siswa_nilai")
                        nis_pilihan = str(df_rekap[df_rekap["Nama Siswa"] == siswa_pilihan]["NIS"].values[0])

                        nilai_saat_ini = df_rekap[df_rekap["Nama Siswa"] == siswa_pilihan]["Nilai"].values[0]
                        status_saat_ini = df_rekap[df_rekap["Nama Siswa"] == siswa_pilihan]["Status"].values[0]

                        with st.form("form_input_nilai"):
                            skor = st.number_input(f"Berikan Nilai untuk {siswa_pilihan}:", min_value=0.0, max_value=100.0, value=float(nilai_saat_ini) if str(nilai_saat_ini).replace('.', '', 1).isdigit() else 0.0)
                            simpan = st.form_submit_button("Simpan Nilai")

                            if simpan:
                                payload = {
                                    "nis": nis_pilihan,
                                    "tugas": tugas_pilihan,
                                    "status": status_saat_ini,
                                    "nilai": skor
                                }
                                if kirim_data_ke_sheet("simpan_pengumpulan", payload):
                                    st.success(f"Nilai {skor} disimpan!")
                                    st.rerun()

        # ---------------------------------------------------------------
        # MENU 2: KELOLA TUGAS PER TINGKAT (TAMBAH, EDIT, HAPUS)
        # ---------------------------------------------------------------
        elif menu_guru == "⚙️ Kelola Tugas Per Tingkat":
            st.header("⚙️ Buat & Kelola Tugas Berdasarkan Tingkat Kelas")

            tab1, tab2, tab3 = st.tabs(["➕ Buat Tugas", "✏️ Edit Tugas", "🗑️ Hapus Tugas"])

            with tab1:
                with st.form("form_buat_tugas_tingkat"):
                    target_tingkat = st.selectbox("Pilih Target Tingkat Kelas:", ["Kelas X", "Kelas XI", "Kelas XII"], key="buat_target_tingkat")
                    nama_tugas_baru = st.text_input("Nama Tugas:")
                    submit_tugas = st.form_submit_button("Buat Tugas")

                    if submit_tugas:
                        if nama_tugas_baru:
                            if kirim_data_ke_sheet("simpan_tugas", [nama_tugas_baru, target_tingkat]):
                                st.success(f"Tugas **'{nama_tugas_baru}'** berhasil disimpan!")
                                st.rerun()

            with tab2:
                if not df_tugas.empty and "Nama Tugas" in df_tugas.columns:
                    list_tugas = [t for t in df_tugas["Nama Tugas"].astype(str).tolist() if t != ""]
                    if list_tugas:
                        tugas_diedit = st.selectbox("Pilih Tugas yang Akan Diedit:", list_tugas, key="select_edit_tugas")
                        
                        df_t_sub = df_tugas[df_tugas["Nama Tugas"] == tugas_diedit]
                        tingkat_asal = df_t_sub["Tingkat"].values[0] if not df_t_sub.empty else "Kelas X"

                        with st.form("form_edit_tugas"):
                            e_nama_tugas = st.text_input("Nama Tugas Baru:", value=str(tugas_diedit))
                            e_tingkat = st.selectbox("Target Tingkat:", ["Kelas X", "Kelas XI", "Kelas XII"], index=["Kelas X", "Kelas XI", "Kelas XII"].index(tingkat_asal) if tingkat_asal in ["Kelas X", "Kelas XI", "Kelas XII"] else 0)
                            
                            if st.form_submit_button("Simpan Perubahan"):
                                payload = {
                                    "tugas_lama": tugas_diedit,
                                    "tugas_baru": e_nama_tugas,
                                    "tingkat": e_tingkat
                                }
                                if kirim_data_ke_sheet("edit_tugas", payload):
                                    st.success("Data tugas berhasil diperbarui!")
                                    st.rerun()
                    else:
                        st.info("Belum ada data tugas untuk diedit.")
                else:
                    st.info("Belum ada data tugas untuk diedit.")

            with tab3:
                if not df_tugas.empty and "Nama Tugas" in df_tugas.columns:
                    list_tugas = [t for t in df_tugas["Nama Tugas"].astype(str).tolist() if t != ""]
                    if list_tugas:
                        tugas_dihapus = st.selectbox("Pilih Tugas yang Akan Dihapus:", list_tugas, key="select_hapus_tugas")
                        
                        if st.button("🔴 Hapus Tugas Ini", type="primary"):
                            payload = {"nama_tugas": tugas_dihapus}
                            if kirim_data_ke_sheet("hapus_tugas", payload):
                                st.success(f"Tugas '{tugas_dihapus}' berhasil dihapus!")
                                st.rerun()
                    else:
                        st.info("Belum ada data tugas untuk dihapus.")
                else:
                    st.info("Belum ada data tugas untuk dihapus.")

        # ---------------------------------------------------------------
        # MENU 3: KELOLA DATA SISWA (UPLOAD, TAMBAH, EDIT, HAPUS)
        # ---------------------------------------------------------------
        elif menu_guru == "👤 Kelola Data Siswa":
            st.header("👤 Kelola Data Siswa")

            tab1, tab2, tab3, tab4 = st.tabs(["📤 Upload Excel", "➕ Tambah Manual", "✏️ Edit Siswa", "🗑️ Hapus Siswa"])

            with tab1:
                uploaded_excel = st.file_uploader("Unggah File Excel Siswa:", type=["xlsx", "xls"], key="excel_uploader_tingkat")
                if uploaded_excel and st.button("🚀 Impor Data ke Google Sheets"):
                    try:
                        df_excel = pd.read_excel(uploaded_excel, dtype=str)
                        berhasil = 0
                        for _, row in df_excel.iterrows():
                            if kirim_data_ke_sheet("simpan_siswa", [str(row["NIS"]), str(row["Nama Siswa"]), str(row["Kelas"])]):
                                berhasil += 1
                        st.success(f"Berhasil mengimpor {berhasil} data siswa!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal membaca file: {e}")

            with tab2:
                with st.form("form_tambah_manual_siswa"):
                    m_nis = st.text_input("NIS:")
                    m_nama = st.text_input("Nama Lengkap:")
                    m_kelas = st.text_input("Kelas (contoh: X TM 1):")

                    if st.form_submit_button("Tambah Siswa"):
                        if m_nis and m_nama and m_kelas:
                            if kirim_data_ke_sheet("simpan_siswa", [str(m_nis), str(m_nama), str(m_kelas)]):
                                st.success(f"Siswa **{m_nama}** tersimpan!")
                                st.rerun()

            # --- TAB 3: EDIT SISWA ---
            with tab3:
                if not df_siswa.empty and "NIS" in df_siswa.columns and "Nama Siswa" in df_siswa.columns:
                    # Filter baris yang NIS dan Nama-nya tidak kosong
                    df_siswa_valid = df_siswa[(df_siswa["NIS"].astype(str).str.strip() != "") & (df_siswa["Nama Siswa"].astype(str).str.strip() != "")]
                    
                    if not df_siswa_valid.empty:
                        list_siswa_label = [f"{row['NIS']} - {row['Nama Siswa']} ({row['Kelas']})" for _, row in df_siswa_valid.iterrows()]
                        siswa_pilihan_label = st.selectbox("Pilih Siswa yang Akan Diedit:", list_siswa_label, key="select_edit_siswa")
                        
                        nis_pilihan = siswa_pilihan_label.split(" - ")[0].strip()
                        df_s_sub = df_siswa[df_siswa["NIS"].astype(str).str.strip() == nis_pilihan]
                        
                        nama_asal = df_s_sub["Nama Siswa"].values[0] if not df_s_sub.empty else ""
                        kelas_asal = df_s_sub["Kelas"].values[0] if not df_s_sub.empty else ""

                        with st.form("form_edit_siswa"):
                            st.text_input("NIS (Tidak dapat diubah):", value=str(nis_pilihan), disabled=True)
                            e_nama = st.text_input("Nama Siswa:", value=str(nama_asal))
                            e_kelas = st.text_input("Kelas:", value=str(kelas_asal))
                            
                            if st.form_submit_button("Simpan Perubahan Siswa"):
                                payload = {
                                    "nis": nis_pilihan,
                                    "nama": e_nama,
                                    "kelas": e_kelas
                                }
                                if kirim_data_ke_sheet("edit_siswa", payload):
                                    st.success("Data siswa berhasil diperbarui!")
                                    st.rerun()
                    else:
                        st.info("Belum ada data siswa untuk diedit.")
                else:
                    st.info("Belum ada data siswa untuk diedit.")

            # --- TAB 4: HAPUS SISWA ---
            with tab4:
                if not df_siswa.empty and "NIS" in df_siswa.columns and "Nama Siswa" in df_siswa.columns:
                    df_siswa_valid = df_siswa[(df_siswa["NIS"].astype(str).str.strip() != "") & (df_siswa["Nama Siswa"].astype(str).str.strip() != "")]
                    
                    if not df_siswa_valid.empty:
                        list_siswa_label = [f"{row['NIS']} - {row['Nama Siswa']} ({row['Kelas']})" for _, row in df_siswa_valid.iterrows()]
                        siswa_pilihan_label = st.selectbox("Pilih Siswa yang Akan Dihapus:", list_siswa_label, key="select_hapus_siswa")
                        
                        nis_pilihan = siswa_pilihan_label.split(" - ")[0].strip()
                        
                        if st.button("🔴 Hapus Siswa Ini", type="primary"):
                            payload = {"nis": nis_pilihan}
                            if kirim_data_ke_sheet("hapus_siswa", payload):
                                st.success(f"Siswa dengan NIS '{nis_pilihan}' berhasil dihapus!")
                                st.rerun()
                    else:
                        st.info("Belum ada data siswa untuk dihapus.")
                else:
                    st.info("Belum ada data siswa untuk dihapus.")
