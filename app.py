import sys
import asyncio
import requests
import json
import time
import streamlit as st
import pandas as pd

if sys.platform == 'win32':
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

st.set_page_config(page_title="Aplikasi Pengumpul Tugas SMK", layout="wide")

PASSWORD_GURU = "Guru123!"
SHEET_ID = "1BTUS3nbirH2sU_j6u2YLZDTykYyULMYXNsE30mkhiAo"

# ===================================================================
# FUNGSI MEMBACA DATA DARI GOOGLE SHEETS
# ===================================================================
@st.cache_data(ttl=2)
def muat_data_sheet(nama_tab):
    try:
        # Panggilan cepat via ekspor CSV gviz
        timestamp = int(time.time())
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={nama_tab}&_t={timestamp}"
        df = pd.read_csv(url, dtype=str)
        df = df.fillna("")
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()
        return df
    except Exception:
        # Fallback jika CSV gagal: panggil via Web App Apps Script
        try:
            url_gas = st.secrets["WEBAPP_URL"] + "?action=baca_semua"
            resp = requests.get(url_gas, timeout=15)
            if resp.status_code == 200:
                data_json = resp.json()
                key = nama_tab.lower()
                raw_data = data_json.get(key, [])
                if len(raw_data) > 1:
                    return pd.DataFrame(raw_data[1:], columns=raw_data[0]).astype(str).fillna("")
        except Exception:
            pass
        return pd.DataFrame()

def muat_semua_data():
    df_siswa = muat_data_sheet("Siswa")
    df_tugas = muat_data_sheet("Tugas")
    df_pengumpulan = muat_data_sheet("Pengumpulan")
    return df_siswa, df_tugas, df_pengumpulan

def kirim_data_ke_sheet(action, payload):
    try:
        url = st.secrets["WEBAPP_URL"]
        response = requests.post(url, data=json.dumps({"action": action, "payload": payload}))
        if response.status_code == 200:
            st.cache_data.clear()
            return True
        else:
            st.error(f"Gagal menyimpan! Response: {response.text}")
            return False
    except Exception as e:
        st.error(f"Gagal menghubungkan ke Apps Script: {e}")
        return False

df_siswa, df_tugas, df_pengumpulan = muat_semua_data()

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

if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

role = st.sidebar.selectbox("Login Sebagai:", ["Siswa", "Guru"], key="main_role_select")

# ===================================================================
# PORTAL SISWA
# ===================================================================
if role == "Siswa":
    st.title("👨‍🎓 Portal Siswa - Pengumpulan Tugas")
    
    if df_siswa.empty:
        st.warning("Data siswa belum tersedia di Google Sheets.")
    else:
        col_kelas = df_siswa.columns[2] if len(df_siswa.columns) >= 3 else df_siswa.columns[0]
        list_kelas = sorted([k for k in df_siswa[col_kelas].unique() if str(k).strip() != ""])
        
        if not list_kelas:
            st.warning("Belum ada data kelas yang terdaftar.")
        else:
            kelas_siswa = st.selectbox("Pilih Kelas Anda:", list_kelas, key="siswa_pilih_kelas")
            tingkat_siswa = dapatkan_tingkat_kelas(kelas_siswa)

            st.info(f"Tingkat Kelas Terdeteksi: **{tingkat_siswa}**")

            col_nama = df_siswa.columns[1] if len(df_siswa.columns) >= 2 else df_siswa.columns[0]
            col_nis = df_siswa.columns[0]

            df_siswa_kelas = df_siswa[df_siswa[col_kelas] == str(kelas_siswa)]
            list_siswa = [s for s in df_siswa_kelas[col_nama].tolist() if str(s).strip() != ""]

            if list_siswa:
                siswa_terpilih = st.selectbox("Pilih Nama Anda:", list_siswa, key="siswa_pilih_nama")
                nis_siswa = str(df_siswa_kelas[df_siswa_kelas[col_nama] == siswa_terpilih][col_nis].values[0])

                tugas_tingkat = []
                if not df_tugas.empty and len(df_tugas.columns) >= 2:
                    col_t_nama = df_tugas.columns[0]
                    col_t_tingkat = df_tugas.columns[1]
                    tugas_tingkat = [t for t in df_tugas[df_tugas[col_t_tingkat] == tingkat_siswa][col_t_nama].tolist() if str(t).strip() != ""]

                st.markdown("---")
                if not tugas_tingkat:
                    st.info(f"Belum ada tugas yang diberikan untuk **{tingkat_siswa}**.")
                else:
                    tugas_terpilih = st.selectbox("Pilih Tugas yang Ingin Dikumpulkan:", tugas_tingkat, key="siswa_pilih_tugas")

                    q_status = pd.DataFrame()
                    if not df_pengumpulan.empty and len(df_pengumpulan.columns) >= 2:
                        col_p_nis = df_pengumpulan.columns[0]
                        col_p_tugas = df_pengumpulan.columns[1]
                        q_status = df_pengumpulan[(df_pengumpulan[col_p_nis] == nis_siswa) & (df_pengumpulan[col_p_tugas] == tugas_terpilih)]
                    
                    if not q_status.empty:
                        col_p_status = df_pengumpulan.columns[2] if len(df_pengumpulan.columns) >= 3 else ""
                        col_p_nilai = df_pengumpulan.columns[3] if len(df_pengumpulan.columns) >= 4 else ""
                        status_saat_ini = str(q_status[col_p_status].values[0]) if col_p_status else "Belum Mengumpulkan"
                        nilai_saat_ini = q_status[col_p_nilai].values[0] if col_p_nilai else 0.0
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
                                    time.sleep(1)
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

        if menu_guru == "📊 Rekapitulasi & Penilaian":
            st.header("📊 Rekapitulasi & Penilaian Tugas")

            tingkat_pilihan = st.selectbox("Pilih Tingkat Kelas:", ["Kelas X", "Kelas XI", "Kelas XII"], key="guru_select_tingkat_rekap")

            tugas_tersedia = []
            if not df_tugas.empty and len(df_tugas.columns) >= 2:
                col_t_nama = df_tugas.columns[0]
                col_t_tingkat = df_tugas.columns[1]
                tugas_tersedia = [t for t in df_tugas[df_tugas[col_t_tingkat] == tingkat_pilihan][col_t_nama].tolist() if str(t).strip() != ""]

            if not tugas_tersedia:
                st.warning(f"Belum ada tugas yang dibuat untuk **{tingkat_pilihan}**.")
            else:
                col_tugas, col_kelas_col = st.columns(2)
                with col_tugas:
                    tugas_pilihan = st.selectbox("Pilih Tugas:", tugas_tersedia, key="guru_pilih_tugas_rekap")
                with col_kelas_col:
                    col_s_kelas = df_siswa.columns[2] if len(df_siswa.columns) >= 3 else df_siswa.columns[0]
                    semua_kelas = [k for k in df_siswa[col_s_kelas].unique() if str(k).strip() != ""] if not df_siswa.empty else []
                    kelas_in_tingkat = [k for k in semua_kelas if dapatkan_tingkat_kelas(k) == tingkat_pilihan]
                    filter_kelas = st.selectbox("Filter Rombel/Kelas:", ["Semua Rombel"] + sorted(kelas_in_tingkat), key="guru_filter_rombel_rekap")

                df_siswa_tingkat = df_siswa.copy()
                if not df_siswa_tingkat.empty and len(df_siswa_tingkat.columns) >= 3:
                    col_nis = df_siswa_tingkat.columns[0]
                    col_nama = df_siswa_tingkat.columns[1]
                    col_kelas = df_siswa_tingkat.columns[2]

                    df_siswa_tingkat["Tingkat"] = df_siswa_tingkat[col_kelas].apply(dapatkan_tingkat_kelas)
                    df_siswa_tingkat = df_siswa_tingkat[df_siswa_tingkat["Tingkat"] == tingkat_pilihan]

                    if filter_kelas != "Semua Rombel":
                        df_siswa_tingkat = df_siswa_tingkat[df_siswa_tingkat[col_kelas] == str(filter_kelas)]

                    df_p_sub = pd.DataFrame()
                    if not df_pengumpulan.empty and len(df_pengumpulan.columns) >= 2:
                        col_p_tugas = df_pengumpulan.columns[1]
                        df_p_sub = df_pengumpulan[df_pengumpulan[col_p_tugas] == tugas_pilihan].copy()

                    if not df_p_sub.empty:
                        df_rekap = pd.merge(df_siswa_tingkat, df_p_sub, left_on=col_nis, right_on=df_p_sub.columns[0], how="left")
                    else:
                        df_rekap = df_siswa_tingkat.copy()
                        df_rekap["Status"] = "Belum Mengumpulkan"
                        df_rekap["Nilai"] = "0.0"

                    df_rekap["Status"] = df_rekap["Status"].fillna("Belum Mengumpulkan")
                    df_rekap["Nilai"] = df_rekap["Nilai"].fillna("0.0")

                    st.dataframe(df_rekap[[col_nis, col_nama, col_kelas, "Status", "Nilai"]], use_container_width=True)

                    st.markdown("---")
                    st.subheader("📝 Input Skor Nilai Siswa")

                    list_nama_siswa = [s for s in df_rekap[col_nama].tolist() if str(s).strip() != ""]
                    if list_nama_siswa:
                        siswa_pilihan = st.selectbox("Pilih Siswa:", list_nama_siswa, key="guru_pilih_siswa_nilai")
                        nis_pilihan = str(df_rekap[df_rekap[col_nama] == siswa_pilihan][col_nis].values[0])

                        nilai_saat_ini = df_rekap[df_rekap[col_nama] == siswa_pilihan]["Nilai"].values[0]
                        status_saat_ini = df_rekap[df_rekap[col_nama] == siswa_pilihan]["Status"].values[0]

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
                                    time.sleep(1)
                                    st.rerun()

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
                                time.sleep(1)
                                st.rerun()

            with tab2:
                list_tugas = [t for t in df_tugas.iloc[:, 0].tolist() if str(t).strip() != ""] if not df_tugas.empty else []
                if list_tugas:
                    tugas_diedit = st.selectbox("Pilih Tugas yang Akan Diedit:", list_tugas, key="select_edit_tugas_v6")
                    
                    df_t_sub = df_tugas[df_tugas.iloc[:, 0] == tugas_diedit]
                    tingkat_asal = df_t_sub.iloc[0, 1] if not df_t_sub.empty and len(df_t_sub.columns) > 1 else "Kelas X"

                    with st.form("form_edit_tugas_v6"):
                        e_nama_tugas = st.text_input("Nama Tugas Baru:", value=str(tugas_diedit))
                        idx_tingkat = ["Kelas X", "Kelas XI", "Kelas XII"].index(tingkat_asal) if tingkat_asal in ["Kelas X", "Kelas XI", "Kelas XII"] else 0
                        e_tingkat = st.selectbox("Target Tingkat:", ["Kelas X", "Kelas XI", "Kelas XII"], index=idx_tingkat)
                        
                        if st.form_submit_button("Simpan Perubahan"):
                            payload = {
                                "tugas_lama": tugas_diedit,
                                "tugas_baru": e_nama_tugas,
                                "tingkat": e_tingkat
                            }
                            if kirim_data_ke_sheet("edit_tugas", payload):
                                st.success("Data tugas berhasil diperbarui!")
                                time.sleep(1)
                                st.rerun()
                else:
                    st.info("Belum ada data tugas untuk diedit.")

            with tab3:
                list_tugas = [t for t in df_tugas.iloc[:, 0].tolist() if str(t).strip() != ""] if not df_tugas.empty else []
                if list_tugas:
                    tugas_dihapus = st.selectbox("Pilih Tugas yang Akan Dihapus:", list_tugas, key="select_hapus_tugas_v6")
                    
                    if st.button("🔴 Hapus Tugas Ini", type="primary"):
                        payload = {"nama_tugas": tugas_dihapus}
                        if kirim_data_ke_sheet("hapus_tugas", payload):
                            st.success(f"Tugas '{tugas_dihapus}' berhasil dihapus!")
                            time.sleep(1)
                            st.rerun()
                else:
                    st.info("Belum ada data tugas untuk dihapus.")

        elif menu_guru == "👤 Kelola Data Siswa":
            st.header("👤 Kelola Data Siswa")

            tab1, tab2, tab3, tab4 = st.tabs(["📤 Upload Excel", "➕ Tambah Manual", "✏️ Edit Siswa", "🗑️ Hapus Siswa"])

            with tab1:
                uploaded_excel = st.file_uploader("Unggah File Excel Siswa:", type=["xlsx", "xls"], key="excel_uploader_tingkat")
                if uploaded_excel and st.button("🚀 Impor Data ke Google Sheets"):
                    try:
                        df_excel = pd.read_excel(uploaded_excel, dtype=str).fillna("")
                        berhasil = 0
                        for _, row in df_excel.iterrows():
                            nis_val = str(row.iloc[0]).strip() if len(row) > 0 else ""
                            nama_val = str(row.iloc[1]).strip() if len(row) > 1 else ""
                            kelas_val = str(row.iloc[2]).strip() if len(row) > 2 else ""
                            if nis_val and nama_val:
                                if kirim_data_ke_sheet("simpan_siswa", [nis_val, nama_val, kelas_val]):
                                    berhasil += 1
                        st.success(f"Berhasil mengimpor {berhasil} data siswa!")
                        time.sleep(1)
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
                            if kirim_data_ke_sheet("simpan_siswa", [m_nis.strip(), m_nama.strip(), m_kelas.strip()]):
                                st.success(f"Siswa **{m_nama}** tersimpan!")
                                time.sleep(1)
                                st.rerun()

            with tab3:
                if not df_siswa.empty:
                    list_siswa_label = []
                    for _, row in df_siswa.iterrows():
                        nis_val = str(row.iloc[0]).strip() if len(row) > 0 else ""
                        nama_val = str(row.iloc[1]).strip() if len(row) > 1 else ""
                        kelas_val = str(row.iloc[2]).strip() if len(row) > 2 else ""
                        if nis_val and nama_val:
                            list_siswa_label.append(f"{nis_val} - {nama_val} ({kelas_val})")

                    if list_siswa_label:
                        siswa_pilihan_label = st.selectbox("Pilih Siswa yang Akan Diedit:", list_siswa_label, key="select_edit_siswa_v6")
                        
                        nis_pilihan = siswa_pilihan_label.split(" - ")[0].strip()
                        df_s_sub = df_siswa[df_siswa.iloc[:, 0].astype(str).str.strip() == nis_pilihan]
                        
                        nama_asal = df_s_sub.iloc[0, 1] if not df_s_sub.empty and len(df_s_sub.columns) > 1 else ""
                        kelas_asal = df_s_sub.iloc[0, 2] if not df_s_sub.empty and len(df_s_sub.columns) > 2 else ""

                        with st.form("form_edit_siswa_v6"):
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
                                    time.sleep(1)
                                    st.rerun()
                    else:
                        st.info("Belum ada data siswa untuk diedit.")
                else:
                    st.info("Belum ada data siswa untuk diedit.")

            with tab4:
                if not df_siswa.empty:
                    list_siswa_label = []
                    for _, row in df_siswa.iterrows():
                        nis_val = str(row.iloc[0]).strip() if len(row) > 0 else ""
                        nama_val = str(row.iloc[1]).strip() if len(row) > 1 else ""
                        kelas_val = str(row.iloc[2]).strip() if len(row) > 2 else ""
                        if nis_val and nama_val:
                            list_siswa_label.append(f"{nis_val} - {nama_val} ({kelas_val})")

                    if list_siswa_label:
                        siswa_pilihan_label = st.selectbox("Pilih Siswa yang Akan Dihapus:", list_siswa_label, key="select_hapus_siswa_v6")
                        
                        nis_pilihan = siswa_pilihan_label.split(" - ")[0].strip()
                        
                        if st.button("🔴 Hapus Siswa Ini", type="primary"):
                            payload = {"nis": nis_pilihan}
                            if kirim_data_ke_sheet("hapus_siswa", payload):
                                st.success(f"Siswa dengan NIS '{nis_pilihan}' berhasil dihapus!")
                                time.sleep(1)
                                st.rerun()
                    else:
                        st.info("Belum ada data siswa untuk dihapus.")
                else:
                    st.info("Belum ada data siswa untuk dihapus.")
