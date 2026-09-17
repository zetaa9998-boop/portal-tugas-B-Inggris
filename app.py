import sys
import asyncio
import io
import streamlit as st
import pandas as pd

# Fix untuk bug asyncio di Python pada Windows (opsional)
if sys.platform == 'win32':
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

# 1. Konfigurasi Halaman
st.set_page_config(page_title="Aplikasi Pengumpul Tugas SMK", layout="wide")

# 2. Inisialisasi Data & Sandi Guru
PASSWORD_GURU = "Guru123!"

# Fungsi Bantuan untuk Mengekstrak Tingkat Kelas dari Nama Kelas
def dapatkan_tingkat_kelas(nama_kelas: str) -> str:
    """Mengembalikan 'Kelas X', 'Kelas XI', atau 'Kelas XII' berdasarkan string kelas."""
    kelas_upper = str(nama_kelas).upper().strip()
    if "XII" in kelas_upper or "12" in kelas_upper:
        return "Kelas XII"
    elif "XI" in kelas_upper or "11" in kelas_upper:
        return "Kelas XI"
    elif "X" in kelas_upper or "10" in kelas_upper:
        return "Kelas X"
    return "Lainnya"

# Inisialisasi Data Siswa Awal
if "data_siswa" not in st.session_state:
    st.session_state.data_siswa = pd.DataFrame({
        "NIS": ["101", "102", "103", "104"],
        "Nama Siswa": ["Budi Santoso", "Siti Aminah", "Rudi Hermawan", "Dewi Lestari"],
        "Kelas": ["X TM 1", "X TM 2", "XI TM 1", "XII TM 1"]
    })

# Inisialisasi Data Tugas Berdasarkan Tingkat Kelas
# Format: {"Nama Tugas": {"Tingkat": "Kelas X" / "Kelas XI" / "Kelas XII"}}
if "data_tugas" not in st.session_state:
    st.session_state.data_tugas = {
        "Tugas 1 (K3L)": {"Tingkat": "Kelas X"},
        "Tugas Elemen Mesin": {"Tingkat": "Kelas XI"},
        "Tugas Proyek Akhir / PKL": {"Tingkat": "Kelas XII"}
    }

# Inisialisasi Pengumpulan & Nilai (Kunci: (NIS, Nama_Tugas))
if "data_pengumpulan" not in st.session_state:
    st.session_state.data_pengumpulan = {
        ("101", "Tugas 1 (K3L)"): {"status": "Sudah Mengumpulkan", "nilai": 85.0},
        ("102", "Tugas 1 (K3L)"): {"status": "Belum Mengumpulkan", "nilai": 0.0},
    }

# 3. Navigasi Sidebar
st.sidebar.title("📌 Navigasi Portal")
role = st.sidebar.selectbox("Login Sebagai:", ["Siswa", "Guru"], key="main_role_select")


# ===================================================================
# PORTAL SISWA
# ===================================================================
if role == "Siswa":
    st.title("👨‍🎓 Portal Siswa - Pengumpulan Tugas")
    st.caption("Pilih kelas dan namamu untuk melihat daftar tugas sesuai tingkat kelasmu.")

    list_kelas = sorted(list(st.session_state.data_siswa["Kelas"].unique()))
    if not list_kelas:
        st.warning("Data kelas belum tersedia.")
    else:
        kelas_siswa = st.selectbox("Pilih Kelas Anda:", list_kelas, key="siswa_pilih_kelas")
        tingkat_siswa = dapatkan_tingkat_kelas(kelas_siswa)

        st.info(f"Tingkat Kelas Terdeteksi: **{tingkat_siswa}**")

        # Filter Siswa Berdasarkan Kelas
        df_siswa_kelas = st.session_state.data_siswa[st.session_state.data_siswa["Kelas"] == kelas_siswa]
        list_siswa = df_siswa_kelas["Nama Siswa"].tolist()

        if list_siswa:
            siswa_terpilih = st.selectbox("Pilih Nama Anda:", list_siswa, key="siswa_pilih_nama")
            nis_siswa = str(df_siswa_kelas[df_siswa_kelas["Nama Siswa"] == siswa_terpilih]["NIS"].values[0])

            # Cari tugas KHUSUS untuk TINGKAT KELAS siswa tersebut
            tugas_tingkat = [tugas for tugas, info in st.session_state.data_tugas.items() if info["Tingkat"] == tingkat_siswa]

            st.markdown("---")
            if not tugas_tingkat:
                st.info(f"Belum ada tugas yang diberikan untuk **{tingkat_siswa}**.")
            else:
                tugas_terpilih = st.selectbox("Pilih Tugas yang Ingin Dikumpulkan:", tugas_tingkat, key="siswa_pilih_tugas")
                
                # Status Pengumpulan
                key_pengumpulan = (nis_siswa, tugas_terpilih)
                info_pengumpulan = st.session_state.data_pengumpulan.get(key_pengumpulan, {"status": "Belum Mengumpulkan", "nilai": 0.0})
                
                status_saat_ini = info_pengumpulan["status"]

                if status_saat_ini == "Sudah Mengumpulkan":
                    st.success(f"✅ Status: **{status_saat_ini}** | Nilai: **{info_pengumpulan['nilai']}**")
                else:
                    st.warning(f"⏳ Status: **{status_saat_ini}**")

                with st.form("form_upload_siswa"):
                    file_tugas = st.file_uploader("Pilih Berkas Tugas (PDF/Gambar/Docx):", type=["pdf", "png", "jpg", "docx"])
                    submit_button = st.form_submit_button("Kirim Tugas")

                    if submit_button:
                        if file_tugas is not None:
                            st.session_state.data_pengumpulan[key_pengumpulan] = {
                                "status": "Sudah Mengumpulkan",
                                "nilai": info_pengumpulan.get("nilai", 0.0)
                            }
                            st.success(f"Berkas **'{file_tugas.name}'** berhasil dikirim!")
                            st.rerun()
                        else:
                            st.error("Silakan pilih berkas terlebih dahulu sebelum mengirim.")


# ===================================================================
# PORTAL GURU
# ===================================================================
elif role == "Guru":
    st.title("👨‍🏫 Portal Guru - Pengelolaan & Penilaian")
    
    password_input = st.sidebar.text_input("Masukkan Kata Sandi Guru:", type="password", key="input_password_guru")

    if password_input != PASSWORD_GURU:
        if password_input != "":
            st.error("❌ Kata sandi salah! Akses ditolak.")
        else:
            st.info("🔒 Silakan masukkan kata sandi Guru di bilah samping (sidebar) untuk mengakses halaman ini.")
    else:
        st.success("🔓 Akses Diterima. Selamat datang, Guru!")

        menu_guru = st.sidebar.radio("Pilih Menu Guru:", [
            "📊 Rekapitulasi & Penilaian", 
            "⚙️ Kelola Tugas Per Tingkat", 
            "👤 Kelola Data Siswa"
        ], key="radio_menu_guru")

        # --- MENU 1: REKAPITULASI & PENILAIAN ---
        if menu_guru == "📊 Rekapitulasi & Penilaian":
            st.header("📊 Rekapitulasi & Penilaian Tugas")

            tingkat_pilihan = st.selectbox("Pilih Tingkat Kelas:", ["Kelas X", "Kelas XI", "Kelas XII"], key="guru_select_tingkat_rekap")

            # Filter Tugas berdasarkan Tingkat Kelas
            tugas_tersedia = [t for t, i in st.session_state.data_tugas.items() if i["Tingkat"] == tingkat_pilihan]

            if not tugas_tersedia:
                st.warning(f"Belum ada tugas yang dibuat untuk **{tingkat_pilihan}**.")
            else:
                col_tugas, col_kelas = st.columns(2)
                with col_tugas:
                    tugas_pilihan = st.selectbox("Pilih Tugas:", tugas_tersedia, key="guru_pilih_tugas_rekap")
                with col_kelas:
                    # Filter Rombel/Kelas yang termasuk dalam Tingkat Kelas yang dipilih
                    semua_kelas = st.session_state.data_siswa["Kelas"].unique()
                    kelas_in_tingkat = [k for k in semua_kelas if dapatkan_tingkat_kelas(k) == tingkat_pilihan]
                    filter_kelas = st.selectbox("Filter Spesifik Rombel/Kelas:", ["Semua Rombel"] + sorted(kelas_in_tingkat), key="guru_filter_rombel_rekap")

                # Ambil Data Siswa yang Sesuai
                df_siswa_tingkat = st.session_state.data_siswa.copy()
                df_siswa_tingkat["Tingkat"] = df_siswa_tingkat["Kelas"].apply(dapatkan_tingkat_kelas)
                df_siswa_tingkat = df_siswa_tingkat[df_siswa_tingkat["Tingkat"] == tingkat_pilihan]

                if filter_kelas != "Semua Rombel":
                    df_siswa_tingkat = df_siswa_tingkat[df_siswa_tingkat["Kelas"] == filter_kelas]

                # Susun Status dan Nilai
                status_list = []
                nilai_list = []
                for _, row in df_siswa_tingkat.iterrows():
                    key = (str(row["NIS"]), tugas_pilihan)
                    data_p = st.session_state.data_pengumpulan.get(key, {"status": "Belum Mengumpulkan", "nilai": 0.0})
                    status_list.append(data_p["status"])
                    nilai_list.append(data_p["nilai"])

                df_siswa_tingkat["Status Pengumpulan"] = status_list
                df_siswa_tingkat["Nilai"] = nilai_list

                st.dataframe(df_siswa_tingkat[["NIS", "Nama Siswa", "Kelas", "Status Pengumpulan", "Nilai"]], use_container_width=True)

                st.markdown("---")
                st.subheader("📝 Input Skor Nilai Siswa")

                list_nama_siswa = df_siswa_tingkat["Nama Siswa"].tolist()
                if list_nama_siswa:
                    siswa_pilihan = st.selectbox("Pilih Siswa:", list_nama_siswa, key="guru_pilih_siswa_nilai")
                    nis_pilihan = str(df_siswa_tingkat[df_siswa_tingkat["Nama Siswa"] == siswa_pilihan]["NIS"].values[0])

                    key_target = (nis_pilihan, tugas_pilihan)
                    nilai_saat_ini = st.session_state.data_pengumpulan.get(key_target, {}).get("nilai", 0.0)

                    with st.form("form_input_nilai"):
                        skor = st.number_input(f"Berikan Nilai untuk {siswa_pilihan}:", min_value=0.0, max_value=100.0, value=float(nilai_saat_ini))
                        simpan = st.form_submit_button("Simpan Nilai")

                        if simpan:
                            status_existing = st.session_state.data_pengumpulan.get(key_target, {}).get("status", "Belum Mengumpulkan")
                            st.session_state.data_pengumpulan[key_target] = {
                                "status": status_existing,
                                "nilai": skor
                            }
                            st.success(f"Nilai {skor} berhasil disimpan untuk {siswa_pilihan}!")
                            st.rerun()

        # --- MENU 2: KELOLA TUGAS PER TINGKAT ---
        elif menu_guru == "⚙️ Kelola Tugas Per Tingkat":
            st.header("⚙️ Buat & Kelola Tugas Berdasarkan Tingkat Kelas")

            tab_buat, tab_edit = st.tabs(["➕ Buat Tugas Baru", "✏️ Edit / Hapus Tugas"])

            with tab_buat:
                with st.form("form_buat_tugas_tingkat"):
                    target_tingkat = st.selectbox("Pilih Target Tingkat Kelas:", ["Kelas X", "Kelas XI", "Kelas XII"], key="buat_target_tingkat")
                    nama_tugas_baru = st.text_input("Nama Tugas (contoh: Tugas 1 - Dasar Keahlian / PKL):")
                    submit_tugas = st.form_submit_button("Buat Tugas")

                    if submit_tugas:
                        if nama_tugas_baru:
                            if nama_tugas_baru in st.session_state.data_tugas:
                                st.warning("Nama tugas sudah ada, gunakan nama lain.")
                            else:
                                st.session_state.data_tugas[nama_tugas_baru] = {"Tingkat": target_tingkat}
                                st.success(f"Tugas **'{nama_tugas_baru}'** berhasil dibuat untuk **{target_tingkat}**!")
                                st.rerun()
                        else:
                            st.error("Nama tugas tidak boleh kosong.")

            with tab_edit:
                if st.session_state.data_tugas:
                    tugas_edit = st.selectbox("Pilih Tugas yang Ingin Diubah/Dihapus:", list(st.session_state.data_tugas.keys()), key="select_tugas_edit_tingkat")
                    tingkat_sekarang = st.session_state.data_tugas[tugas_edit]["Tingkat"]

                    st.info(f"Tugas ini terdaftar untuk: **{tingkat_sekarang}**")
                    nama_baru = st.text_input("Nama Baru Tugas:", value=tugas_edit, key="input_rename_tugas_tingkat")

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("💾 Simpan Perubahan Nama", key="btn_rename_tugas_tingkat"):
                            if nama_baru and nama_baru != tugas_edit:
                                st.session_state.data_tugas[nama_baru] = st.session_state.data_tugas.pop(tugas_edit)
                                st.success("Nama tugas berhasil diubah!")
                                st.rerun()
                    with col2:
                        if st.button("🗑️ Hapus Tugas Ini", key="btn_hapus_tugas_tingkat", type="primary"):
                            del st.session_state.data_tugas[tugas_edit]
                            st.success(f"Tugas **'{tugas_edit}'** berhasil dihapus!")
                            st.rerun()
                else:
                    st.info("Belum ada tugas yang dibuat.")

        # --- MENU 3: KELOLA DATA SISWA ---
        elif menu_guru == "👤 Kelola Data Siswa":
            st.header("👤 Kelola Data Siswa")

            tab1, tab2, tab3 = st.tabs(["✍️ Edit / Hapus Siswa", "📤 Upload Excel Siswa", "➕ Tambah Manual"])

            with tab1:
                list_siswa = st.session_state.data_siswa["Nama Siswa"].tolist()
                if list_siswa:
                    siswa_pilihan = st.selectbox("Pilih Siswa:", list_siswa, key="edit_siswa_select_main")
                    idx = st.session_state.data_siswa[st.session_state.data_siswa["Nama Siswa"] == siswa_pilihan].index[0]
                    row_siswa = st.session_state.data_siswa.loc[idx]

                    with st.form("form_edit_siswa_detail"):
                        edit_nis = st.text_input("NIS:", value=str(row_siswa["NIS"]))
                        edit_nama = st.text_input("Nama Lengkap:", value=str(row_siswa["Nama Siswa"]))
                        edit_kelas = st.text_input("Kelas (contoh: X TM 1 / XI TKR 2):", value=str(row_siswa["Kelas"]))
                        
                        if st.form_submit_button("💾 Simpan Perubahan Siswa"):
                            st.session_state.data_siswa.at[idx, "NIS"] = edit_nis
                            st.session_state.data_siswa.at[idx, "Nama Siswa"] = edit_nama
                            st.session_state.data_siswa.at[idx, "Kelas"] = edit_kelas
                            st.success("Data siswa berhasil diperbarui!")
                            st.rerun()

                    if st.button(f"🗑️ Hapus Siswa ({siswa_pilihan})", key="btn_hapus_siswa_del_main", type="primary"):
                        st.session_state.data_siswa.drop(index=idx, inplace=True)
                        st.session_state.data_siswa.reset_index(drop=True, inplace=True)
                        st.success(f"Siswa **{siswa_pilihan}** berhasil dihapus!")
                        st.rerun()

            with tab2:
                buffer = io.BytesIO()
                try:
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        pd.DataFrame({
                            "NIS": ["105", "106", "107"],
                            "Nama Siswa": ["Ahmad Fauzi", "Siti Nurhaliza", "Doni Prasetyo"],
                            "Kelas": ["X TM 1", "XI TKR 1", "XII TP 2"]
                        }).to_excel(writer, index=False, sheet_name='Data Siswa')

                    st.download_button("📥 Unduh Template Excel", buffer.getvalue(), "template_siswa.xlsx", key="dl_template_excel_tingkat")
                except Exception:
                    st.warning("Pustaka `openpyxl` belum terpasang di server.")

                uploaded_excel = st.file_uploader("Unggah File Excel:", type=["xlsx", "xls"], key="excel_uploader_tingkat")
                if uploaded_excel and st.button("🚀 Impor Data Excel", key="btn_impor_excel_tingkat"):
                    try:
                        df_excel = pd.read_excel(uploaded_excel)
                        st.session_state.data_siswa = pd.concat([st.session_state.data_siswa, df_excel[["NIS", "Nama Siswa", "Kelas"]]], ignore_index=True)
                        st.success("Data siswa berhasil ditambahkan!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal membaca file: {e}")

            with tab3:
                with st.form("form_tambah_manual_siswa_tingkat"):
                    m_nis = st.text_input("NIS:")
                    m_nama = st.text_input("Nama Lengkap:")
                    m_kelas = st.text_input("Kelas (contoh: X TM 1 / XI TKR 1 / XII TP 2):")

                    if st.form_submit_button("Tambah Siswa"):
                        if m_nis and m_nama and m_kelas:
                            new_row = pd.DataFrame([{"NIS": m_nis, "Nama Siswa": m_nama, "Kelas": m_kelas}])
                            st.session_state.data_siswa = pd.concat([st.session_state.data_siswa, new_row], ignore_index=True)
                            st.success(f"Siswa **{m_nama}** berhasil ditambahkan!")
                            st.rerun()