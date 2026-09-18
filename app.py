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
                if "Link File" not in df_p.columns:
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
        response = requests.post(url, data=json.dumps({"action": action, "payload": payload}), timeout=90)
        if response.status_code == 200:
            res_json = response.json()
            return res_json.get("file_url", "") if action == "simpan_pengumpulan" else True
        else:
            st.error(f"Gagal menyimpan! Response: {response.text}")
            return False
    except Exception as e:
        st.error(f"Gagal menghubungkan ke Apps Script: {e}")
        return False

# Muat data segar
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
    st.rerun()

role = st.sidebar.selectbox("Login Sebagai:", ["Siswa", "Guru"], key="main_role_select")

# ===================================================================
# PORTAL SISWA
# ===================================================================
if role == "Siswa":
    st.title("👨‍🎓 Portal Siswa - Pengumpulan Tugas & Video")
    
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

                    # Ambil data pengumpulan dari DataFrame
                    q_status = pd.DataFrame()
                    if not df_pengumpulan.empty and "NIS" in df_pengumpulan.columns and "Nama Tugas" in df_pengumpulan.columns:
                        q_status = df_pengumpulan[(df_pengumpulan["NIS"].astype(str).str.strip() == str(nis_siswa).strip()) & 
                                                  (df_pengumpulan["Nama Tugas"].astype(str).str.strip() == str(tugas_terpilih).strip())]
                    
                    if not q_status.empty:
                        status_saat_ini = str(q_status["Status"].values[0]).strip()
                        nilai_saat_ini = q_status["Nilai"].values[0] if "Nilai" in q_status.columns else 0.0
                        link_file_lama = str(q_status["Link File"].values[0]) if "Link File" in q_status.columns else ""
                    else:
                        status_saat_ini = "Belum Mengumpulkan"
                        nilai_saat_ini = 0.0
                        link_file_lama = ""

                    # Tampilkan Status & Link File
                    if status_saat_ini.lower() == "sudah mengumpulkan":
                        st.success("✅ Status Pengumpulan: **Sudah Mengumpulkan**")
                        if link_file_lama and link_file_lama.strip() != "" and link_file_lama.startswith("http"):
                            st.markdown(f"🔗 **[Buka Berkas/Video yang Telah Diunggah]({link_file_lama})**")
                    else:
                        st.warning("⏳ Status Pengumpulan: **Belum Mengumpulkan**")

                    with st.form("form_upload_siswa"):
                        file_tugas = st.file_uploader(
                            "Pilih Berkas Tugas (Dokumen, Gambar, atau Video):", 
                            type=["pdf", "png", "jpg", "jpeg", "docx", "mp4", "mov", "avi", "mkv", "webm"]
                        )
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
                                with st.spinner("Mengunggah berkas/video ke Google Drive & menyinkronkan link..."):
                                    hasil_link = kirim_data_ke_sheet("simpan_pengumpulan", payload)
                                    if hasil_link:
                                        st.success(f"Berkas **'{file_tugas.name}'** berhasil dikirim & disimpan!")
                                        time.sleep(1)
                                        st.rerun()
                                    else:
                                        st.error("Gagal mengunggah file ke Google Drive.")
                            else:
                                st.error("Silakan pilih berkas atau video terlebih dahulu.")

# ===================================================================
# PORTAL GURU (Data Siswa dan Tugas Aman 100%)
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
            "📈 Rekap Global & Rata-Rata Nilai",
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

                    st.dataframe(
                        df_rekap[["NIS", "Nama Siswa", "Kelas", "Status", "Nilai", "Link File"]],
                        use_container_width=True,
                        column_config={
                            "Link File": st.column_config.LinkColumn("Berkas / Video Tugas (Klik untuk Buka/Unduh)")
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

        elif menu_guru == "📈 Rekap Global & Rata-Rata Nilai":
            st.header("📈 Rekapitulasi Nilai Keseluruhan & Kolom Rata-Rata")
            if df_siswa.empty:
                st.warning("Belum ada data siswa.")
            else:
                list_semua_tugas = [t for t in df_tugas["Nama Tugas"].unique() if str(t).strip() != ""] if not df_tugas.empty else []

                if not df_pengumpulan.empty and "Nama Tugas" in df_pengumpulan.columns and "Nilai" in df_pengumpulan.columns:
                    df_p_copy = df_pengumpulan.copy()
                    df_p_copy["Nilai_Num"] = pd.to_numeric(df_p_copy["Nilai"], errors="coerce").fillna(0.0)
                    pivot_nilai = df_p_copy.pivot_table(index="NIS", columns="Nama Tugas", values="Nilai_Num", aggfunc="max").fillna(0.0)
                else:
                    pivot_nilai = pd.DataFrame(index=df_siswa["NIS"])

                df_rekap_global = df_siswa.copy()
                df_rekap_global = pd.merge(df_rekap_global, pivot_nilai, on="NIS", how="left").fillna(0.0)

                kolom_tugas_ada = [t for t in list_semua_tugas if t in df_rekap_global.columns]
                if kolom_tugas_ada:
                    df_rekap_global["Nilai Rata-Rata"] = df_rekap_global[kolom_tugas_ada].mean(axis=1).round(2)
                else:
                    df_rekap_global["Nilai Rata-Rata"] = 0.0

                st.dataframe(df_rekap_global, use_container_width=True)
                csv_data = df_rekap_global.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Unduh Rekap Nilai & Rata-Rata (.csv)",
                    data=csv_data,
                    file_name="Rekapitulasi_Nilai_Dan_RataRata_Siswa.csv",
                    mime="text/csv",
                )

        elif menu_guru == "⚙️ Kelola Tugas Per Tingkat":
            st.header("⚙️ Kelola Tugas Per Tingkat")
            with st.form("form_buat_tugas_tingkat"):
                target_tingkat = st.selectbox("Pilih Target Tingkat Kelas:", ["Kelas X", "Kelas XI", "Kelas XII"])
                nama_tugas_baru = st.text_input("Nama Tugas:")
                if st.form_submit_button("Buat Tugas"):
                    if nama_tugas_baru and kirim_data_ke_sheet("simpan_tugas", [nama_tugas_baru, target_tingkat]):
                        st.success(f"Tugas '{nama_tugas_baru}' berhasil disimpan!")
                        time.sleep(1)
                        st.rerun()

        elif menu_guru == "👤 Kelola Data Siswa":
            st.header("👤 Kelola Data Siswa")
            with st.form("form_tambah_manual_siswa"):
                m_nis = st.text_input("NIS:")
                m_nama = st.text_input("Nama Lengkap:")
                m_kelas = st.text_input("Kelas:")
                if st.form_submit_button("Tambah Siswa"):
                    if m_nis and m_nama and m_kelas and kirim_data_ke_sheet("simpan_siswa", [m_nis.strip(), m_nama.strip(), m_kelas.strip()]):
                        st.success(f"Siswa '{m_nama}' tersimpan!")
                        time.sleep(1)
                        st.rerun()
