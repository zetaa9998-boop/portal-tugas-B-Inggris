import sys
import asyncio
import requests
import json
import base64
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

# ===================================================================
# FUNGSI MEMBACA DATA DARI GOOGLE APPS SCRIPT
# ===================================================================
@st.cache_data(ttl=2)
def muat_semua_data_gas():
    try:
        url = st.secrets["WEBAPP_URL"] + "?action=baca_semua"
        resp = requests.get(url, timeout=20)
        if resp.status_code == 200:
            data_json = resp.json()
            
            raw_siswa = data_json.get("siswa", [])
            df_siswa = pd.DataFrame(raw_siswa[1:], columns=raw_siswa[0]).astype(str) if len(raw_siswa) > 1 else pd.DataFrame(columns=["NIS", "Nama Siswa", "Kelas"])
                
            raw_tugas = data_json.get("tugas", [])
            df_tugas = pd.DataFrame(raw_tugas[1:], columns=raw_tugas[0]).astype(str) if len(raw_tugas) > 1 else pd.DataFrame(columns=["Nama Tugas", "Tingkat"])
                
            raw_pengumpulan = data_json.get("pengumpulan", [])
            if len(raw_pengumpulan) > 1:
                cols = raw_pengumpulan[0]
                df_p = pd.DataFrame(raw_pengumpulan[1:], columns=cols).astype(str)
                if len(cols) < 5:
                    df_p["Link File"] = ""
            else:
                df_p = pd.DataFrame(columns=["NIS", "Nama Tugas", "Status", "Nilai", "Link File"])
                
            return df_siswa.fillna(""), df_tugas.fillna(""), df_p.fillna("")
        else:
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    except Exception:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def kirim_data_ke_sheet(action, payload):
    try:
        url = st.secrets["WEBAPP_URL"]
        response = requests.post(url, data=json.dumps({"action": action, "payload": payload}), timeout=30)
        if response.status_code == 200:
            st.cache_data.clear()
            return True
        else:
            st.error(f"Gagal menyimpan! Response: {response.text}")
            return False
    except Exception as e:
        st.error(f"Gagal menghubungkan ke Apps Script: {e}")
        return False

df_siswa, df_tugas, df_pengumpulan = muat_semua_data_gas()

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

if st.sidebar.button("🔄 Segarkan Data", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

role = st.sidebar.selectbox("Login Sebagai:", ["Siswa", "Guru"], key="main_role_select")

# ===================================================================
# PORTAL SISWA (Nilai Disembunyikan)
# ===================================================================
if role == "Siswa":
    st.title("👨‍🎓 Portal Siswa - Pengumpulan Tugas")
    
    if df_siswa.empty:
        st.warning("Data siswa belum tersedia di Google Sheets.")
    else:
        list_kelas = sorted([k for k in df_siswa["Kelas"].unique() if str(k).strip() != ""])
        
        if not list_kelas:
            st.warning("Belum ada data kelas yang terdaftar.")
        else:
            kelas_siswa = st.selectbox("Pilih Kelas Anda:", list_kelas, key="siswa_pilih_kelas")
            tingkat_siswa = dapatkan_tingkat_kelas(kelas_siswa)

            st.info(f"Tingkat Kelas Terdeteksi: **{tingkat_siswa}**")

            df_siswa_kelas = df_siswa[df_siswa["Kelas"] == str(kelas_siswa)]
            list_siswa = [s for s in df_siswa_kelas["Nama Siswa"].tolist() if str(s).strip() != ""]

            if list_siswa:
                siswa_terpilih = st.selectbox("Pilih Nama Anda:", list_siswa, key="siswa_pilih_nama")
                nis_siswa = str(df_siswa_kelas[df_siswa_kelas["Nama Siswa"] == siswa_terpilih]["NIS"].values[0])

                tugas_tingkat = []
                if not df_tugas.empty:
                    tugas_tingkat = [t for t in df_tugas[df_tugas["Tingkat"] == tingkat_siswa]["Nama Tugas"].tolist() if str(t).strip() != ""]

                st.markdown("---")
                if not tugas_tingkat:
                    st.info(f"Belum ada tugas yang diberikan untuk **{tingkat_siswa}**.")
                else:
                    tugas_terpilih = st.selectbox("Pilih Tugas yang Ingin Dikumpulkan:", tugas_tingkat, key="siswa_pilih_tugas")

                    q_status = pd.DataFrame()
                    if not df_pengumpulan.empty and len(df_pengumpulan.columns) >= 2:
                        q_status = df_pengumpulan[(df_pengumpulan["NIS"] == nis_siswa) & (df_pengumpulan["Nama Tugas"] == tugas_terpilih)]
                    
                    if not q_status.empty:
                        status_saat_ini = str(q_status["Status"].values[0]) if "Status" in q_status.columns else "Belum Mengumpulkan"
                        nilai_saat_ini = q_status["Nilai"].values[0] if "Nilai" in q_status.columns else 0.0
                    else:
                        status_saat_ini = "Belum Mengumpulkan"
                        nilai_saat_ini = 0.0

                    if status_saat_ini == "Sudah Mengumpulkan":
                        st.success(f"✅ Status Pengumpulan: **{status_saat_ini}**")
                    else:
                        st.warning(f"⏳ Status Pengumpulan: **{status_saat_ini}**")

                    with st.form("form_upload_siswa"):
                        file_tugas = st.file_uploader("Pilih Berkas Tugas (PDF/Gambar/Docx):", type=["pdf", "png", "jpg", "docx"])
                        submit_button = st.form_submit_button("Kirim Tugas")

                        if submit_button:
                            if file_tugas is not None:
                                file_bytes = file_tugas.read()
                                file_base64 = base64.b64encode(file_bytes).decode('utf-8')
                                
                                payload = {
                                    "nis": nis_siswa,
                                    "tugas": tugas_terpilih,
                                    "status": "Sudah Mengumpulkan",
                                    "nilai": nilai_saat_ini,
                                    "file_data": file_base64,
                                    "file_name": file_tugas.name,
                                    "file_mime": file_tugas.type
                                }
                                with st.spinner("Mengunggah berkas ke Google Drive..."):
                                    if kirim_data_ke_sheet("simpan_pengumpulan", payload):
                                        st.success(f"Berkas **'{file_tugas.name}'** berhasil dikirim & disimpan!")
                                        time.sleep(1)
                                        st.rerun()
                            else:
                                st.error("Silakan pilih berkas terlebih dahulu.")

# ===================================================================
# PORTAL GURU (Nilai Tetap Terlihat & Dapat Dikelola)
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
            if not df_tugas.empty:
                tugas_tersedia = [t for t in df_tugas[df_tugas["Tingkat"] == tingkat_pilihan]["Nama Tugas"].tolist() if str(t).strip() != ""]

            if not tugas_tersedia:
                st.warning(f"Belum ada tugas yang dibuat untuk **{tingkat_pilihan}**.")
            else:
                col_tugas, col_kelas_col = st.columns(2)
                with col_tugas:
                    tugas_pilihan = st.selectbox("Pilih Tugas:", tugas_tersedia, key="guru_pilih_tugas_rekap")
                with col_kelas_col:
                    semua_kelas = [k for k in df_siswa["Kelas"].unique() if str(k).strip() != ""] if not df_siswa.empty else []
                    kelas_in_tingkat = [k for k in semua_kelas if dapatkan_tingkat_kelas(k) == tingkat_pilihan]
                    filter_kelas = st.selectbox("Filter Rombel/Kelas:", ["Semua Rombel"] + sorted(kelas_in_tingkat), key="guru_filter_rombel_rekap")

                df_siswa_tingkat = df_siswa.copy()
                if not df_siswa_tingkat.empty:
                    df_siswa_tingkat["Tingkat"] = df_siswa_tingkat["Kelas"].apply(dapatkan_tingkat_kelas)
                    df_siswa_tingkat = df_siswa_tingkat[df_siswa_tingkat["Tingkat"] == tingkat_pilihan]

                    if filter_kelas != "Semua Rombel":
                        df_siswa_tingkat = df_siswa_tingkat[df_siswa_tingkat["Kelas"] == str(filter_kelas)]

                    df_p_sub = pd.DataFrame()
                    if not df_pengumpulan.empty and "Nama Tugas" in df_pengumpulan.columns:
                        df_p_sub = df_pengumpulan[df_pengumpulan["Nama Tugas"] == tugas_pilihan].copy()

                    if not df_p_sub.empty:
                        df_rekap = pd.merge(df_siswa_tingkat, df_p_sub, on="NIS", how="left")
                    else:
                        df_rekap = df_siswa_tingkat.copy()
                        df_rekap["Status"] = "Belum Mengumpulkan"
                        df_rekap["Nilai"] = "0.0"
                        df_rekap["Link File"] = ""

                    df_rekap["Status"] = df_rekap["Status"].fillna("Belum Mengumpulkan")
                    df_rekap["Nilai"] = df_rekap["Nilai"].fillna("0.0")
                    if "Link File" not in df_rekap.columns:
                        df_rekap["Link File"] = ""

                    # Guru tetap melihat nilai dan link file secara lengkap
                    st.dataframe(
                        df_rekap[["NIS", "Nama Siswa", "Kelas", "Status", "Nilai", "Link File"]],
                        use_container_width=True,
                        column_config={
                            "Link File": st.column_config.LinkColumn("Berkas Tugas (Klik untuk Buka/Unduh)")
                        }
                    )

                    st.markdown("---")
                    st.subheader("📝 Input Skor Nilai Siswa")

                    list_nama_siswa = [s for s in df_rekap["Nama Siswa"].tolist() if str(s).strip() != ""]
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
                list_tugas = [t for t in df_tugas["Nama Tugas"].tolist() if str(t).strip() != ""] if not df_tugas.empty else []
                if list_tugas:
                    tugas_diedit = st.selectbox("Pilih Tugas yang Akan Diedit:", list_tugas, key="select_edit_tugas_v8")
                    
                    df_t_sub = df_tugas[df_tugas["Nama Tugas"] == tugas_diedit]
                    tingkat_asal = df_t_sub["Tingkat"].values[0] if not df_t_sub.empty else "Kelas X"

                    with st.form("form_edit_tugas_v8"):
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
                list_tugas = [t for t in df_tugas["Nama Tugas"].tolist() if str(t).strip() != ""] if not df_tugas.empty else []
                if list_tugas:
                    tugas_dihapus = st.selectbox("Pilih Tugas yang Akan Dihapus:", list_tugas, key="select_hapus_tugas_v8")
                    
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
                        nis_val = str(row.get("NIS", "")).strip()
                        nama_val = str(row.get("Nama Siswa", "")).strip()
                        kelas_val = str(row.get("Kelas", "")).strip()
                        if nis_val and nama_val:
                            list_siswa_label.append(f"{nis_val} - {nama_val} ({kelas_val})")

                    if list_siswa_label:
                        siswa_pilihan_label = st.selectbox("Pilih Siswa yang Akan Diedit:", list_siswa_label, key="select_edit_siswa_v8")
                        
                        nis_pilihan = siswa_pilihan_label.split(" - ")[0].strip()
                        df_s_sub = df_siswa[df_siswa["NIS"] == nis_pilihan]
                        
                        nama_asal = df_s_sub["Nama Siswa"].values[0] if not df_s_sub.empty else ""
                        kelas_asal = df_s_sub["Kelas"].values[0] if not df_s_sub.empty else ""

                        with st.form("form_edit_siswa_v8"):
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
                        nis_val = str(row.get("NIS", "")).strip()
                        nama_val = str(row.get("Nama Siswa", "")).strip()
                        kelas_val = str(row.get("Kelas", "")).strip()
                        if nis_val and nama_val:
                            list_siswa_label.append(f"{nis_val} - {nama_val} ({kelas_val})")

                    if list_siswa_label:
                        siswa_pilihan_label = st.selectbox("Pilih Siswa yang Akan Dihapus:", list_siswa_label, key="select_hapus_siswa_v8")
                        
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
