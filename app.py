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

# 1. Konfigurasi Halaman (Harus di paling atas)
st.set_page_config(page_title="Aplikasi Pengumpul Tugas SMK", layout="wide")

# 2. Inisialisasi Data & Sandi
PASSWORD_GURU = "Guru123!"

if "data_siswa" not in st.session_state:
    st.session_state.data_siswa = pd.DataFrame({
        "NIS": ["101", "102", "103", "104"],
        "Nama Siswa": ["Budi Santoso", "Siti Aminah", "Rudi Hermawan", "Dewi Lestari"],
        "Kelas": ["X TM 1", "X TM 1", "X TM 2", "X TM 2"],
        "Tugas 1 (K3L)": ["Sudah Mengumpulkan", "Sudah Mengumpulkan", "Belum Mengumpulkan", "Sudah Mengumpulkan"],
        "Nilai_Tugas 1 (K3L)": [85.0, 90.0, 0.0, 88.0]
    })

# 3. Navigasi Sidebar
st.sidebar.title("📌 Navigasi Portal")
role = st.sidebar.selectbox("Login Sebagai:", ["Siswa", "Guru"], key="main_role_select")

# Filter Kelas di Sidebar
list_kelas = ["Semua Kelas"] + list(st.session_state.data_siswa["Kelas"].unique())
kelas_terpilih = st.sidebar.selectbox("Filter Kelas:", list_kelas, key="main_kelas_filter")

# Filter Dataframe berdasarkan Kelas
df_filtered = st.session_state.data_siswa.copy()
if kelas_terpilih != "Semua Kelas":
    df_filtered = df_filtered[df_filtered["Kelas"] == kelas_terpilih]


# ===================================================================
# PORTAL SISWA
# ===================================================================
if role == "Siswa":
    st.title("👨‍🎓 Portal Siswa - Pengumpulan Tugas")
    st.caption("Unggah berkas tugas dan periksa status pengumpulanmu di sini.")

    kolom_tugas = [col for col in st.session_state.data_siswa.columns if col not in ["NIS", "Nama Siswa", "Kelas"] and not col.startswith("Nilai_")]

    if not kolom_tugas:
        st.info("Belum ada tugas yang diberikan oleh Guru.")
    else:
        list_siswa = df_filtered["Nama Siswa"].tolist()
        if list_siswa:
            siswa_terpilih = st.selectbox("Pilih Nama Anda:", list_siswa, key="siswa_pilih_nama")
            idx = st.session_state.data_siswa[st.session_state.data_siswa["Nama Siswa"] == siswa_terpilih].index[0]
            data_siswa_saat_ini = st.session_state.data_siswa.loc[idx]

            st.write(f"**Kelas:** {data_siswa_saat_ini['Kelas']}")
            st.markdown("---")

            tugas_terpilih = st.selectbox("Pilih Tugas yang Ingin Dikumpulkan:", kolom_tugas, key="siswa_pilih_tugas")
            status_saat_ini = data_siswa_saat_ini[tugas_terpilih]

            if status_saat_ini == "Sudah Mengumpulkan":
                st.success(f"✅ Status Pengumpulan: **{status_saat_ini}**")
            else:
                st.warning(f"⏳ Status Pengumpulan: **{status_saat_ini}**")

            with st.form("form_upload_siswa"):
                file_tugas = st.file_uploader("Pilih Berkas Tugas (PDF/Gambar/Docx):", type=["pdf", "png", "jpg", "docx"])
                submit_button = st.form_submit_button("Kirim Tugas")

                if submit_button:
                    if file_tugas is not None:
                        st.session_state.data_siswa.at[idx, tugas_terpilih] = "Sudah Mengumpulkan"
                        st.success(f"Berkas **'{file_tugas.name}'** berhasil dikirim!")
                        st.rerun()
                    else:
                        st.error("Silakan pilih berkas terlebih dahulu sebelum mengirim.")
        else:
            st.warning("Tidak ada data siswa pada kelas ini.")


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
            "⚙️ Kelola & Edit Tugas", 
            "👤 Kelola & Edit Data Siswa"
        ], key="radio_menu_guru")

        # --- MENU 1: REKAPITULASI & PENILAIAN ---
        if menu_guru == "📊 Rekapitulasi & Penilaian":
            st.header("📊 Rekapitulasi Status & Penilaian")
            st.dataframe(df_filtered, use_container_width=True)

            st.markdown("---")
            st.subheader("📝 Input Skor Nilai Siswa")

            kolom_tugas = [col for col in st.session_state.data_siswa.columns if col not in ["NIS", "Nama Siswa", "Kelas"] and not col.startswith("Nilai_")]

            if kolom_tugas:
                col_tugas, col_siswa = st.columns(2)
                with col_tugas:
                    tugas_terpilih = st.selectbox("Pilih Tugas:", kolom_tugas, key="guru_pilih_tugas")
                with col_siswa:
                    list_siswa = df_filtered["Nama Siswa"].tolist()
                    siswa_terpilih = st.selectbox("Pilih Siswa:", list_siswa, key="guru_pilih_siswa") if list_siswa else None

                if siswa_terpilih:
                    idx = st.session_state.data_siswa[st.session_state.data_siswa["Nama Siswa"] == siswa_terpilih].index[0]
                    kolom_nilai = f"Nilai_{tugas_terpilih}"
                    nilai_sekarang = float(st.session_state.data_siswa.at[idx, kolom_nilai])

                    with st.form("form_nilai"):
                        skor = st.number_input(f"Berikan Nilai untuk {siswa_terpilih}:", min_value=0.0, max_value=100.0, value=nilai_sekarang)
                        simpan = st.form_submit_button("Simpan Nilai")

                        if simpan:
                            st.session_state.data_siswa.at[idx, kolom_nilai] = skor
                            st.success(f"Nilai {skor} berhasil disimpan untuk {siswa_terpilih}!")
                            st.rerun()

        # --- MENU 2: KELOLA & EDIT TUGAS ---
        elif menu_guru == "⚙️ Kelola & Edit Tugas":
            st.header("⚙️ Kelola & Edit Tugas")
            
            tab_tambah_tugas, tab_edit_tugas = st.tabs(["➕ Tambah Tugas Baru", "✏️ Edit / Hapus Nama Tugas"])

            with tab_tambah_tugas:
                with st.form("form_tambah_tugas"):
                    nama_tugas_baru = st.text_input("Nama Tugas Baru (contoh: Tugas 2 - Gambar Teknik):")
                    submitted = st.form_submit_button("Buat Tugas")

                    if submitted:
                        if nama_tugas_baru and nama_tugas_baru not in st.session_state.data_siswa.columns:
                            st.session_state.data_siswa[nama_tugas_baru] = "Belum Mengumpulkan"
                            st.session_state.data_siswa[f"Nilai_{nama_tugas_baru}"] = 0.0
                            st.success(f"Tugas **'{nama_tugas_baru}'** berhasil ditambahkan!")
                            st.rerun()
                        elif nama_tugas_baru in st.session_state.data_siswa.columns:
                            st.warning("Nama tugas tersebut sudah ada.")
                        else:
                            st.error("Nama tugas tidak boleh kosong.")

            with tab_edit_tugas:
                kolom_tugas = [col for col in st.session_state.data_siswa.columns if col not in ["NIS", "Nama Siswa", "Kelas"] and not col.startswith("Nilai_")]
                if kolom_tugas:
                    tugas_diedit = st.selectbox("Pilih Tugas yang Ingin Diubah/Dihapus:", kolom_tugas, key="select_tugas_edit")
                    
                    nama_baru_tugas = st.text_input("Nama Baru Tugas:", value=tugas_diedit, key="input_nama_baru_tugas")
                    
                    col_b1, col_b2 = st.columns(2)
                    with col_b1:
                        if st.button("💾 Ubah Nama Tugas", key="btn_rename_tugas"):
                            if nama_baru_tugas and nama_baru_tugas != tugas_diedit:
                                # Rename kolom tugas dan kolom nilai terkait
                                st.session_state.data_siswa.rename(columns={
                                    tugas_diedit: nama_baru_tugas,
                                    f"Nilai_{tugas_diedit}": f"Nilai_{nama_baru_tugas}"
                                }, inplace=True)
                                st.success("Nama tugas berhasil diperbarui!")
                                st.rerun()
                    with col_b2:
                        if st.button("🗑️ Hapus Tugas Ini", key="btn_delete_tugas", type="primary"):
                            st.session_state.data_siswa.drop(columns=[tugas_diedit, f"Nilai_{tugas_diedit}"], inplace=True)
                            st.success(f"Tugas **'{tugas_diedit}'** berhasil dihapus!")
                            st.rerun()
                else:
                    st.info("Belum ada tugas untuk dikelola.")

        # --- MENU 3: KELOLA & EDIT DATA SISWA ---
        elif menu_guru == "👤 Kelola & Edit Data Siswa":
            st.header("👤 Kelola & Edit Data Siswa")

            tab1, tab2, tab3 = st.tabs(["✍️ Edit / Hapus Data Siswa", "📤 Upload Banyak Data (Excel)", "➕ Tambah Manual (1 Siswa)"])

            # TAB EDIT/HAPUS SISWA
            with tab1:
                st.subheader("Edit Informasi Siswa")
                list_siswa_all = st.session_state.data_siswa["Nama Siswa"].tolist()
                
                if list_siswa_all:
                    siswa_pilihan = st.selectbox("Pilih Siswa yang Ingin Di-edit:", list_siswa_all, key="select_siswa_edit")
                    idx_edit = st.session_state.data_siswa[st.session_state.data_siswa["Nama Siswa"] == siswa_pilihan].index[0]
                    data_edit = st.session_state.data_siswa.loc[idx_edit]

                    with st.form("form_edit_siswa"):
                        edit_nis = st.text_input("NIS:", value=str(data_edit["NIS"]))
                        edit_nama = st.text_input("Nama Lengkap Siswa:", value=str(data_edit["Nama Siswa"]))
                        edit_kelas = st.text_input("Kelas:", value=str(data_edit["Kelas"]))
                        
                        btn_update_siswa = st.form_submit_button("💾 Simpan Perubahan Siswa")

                        if btn_update_siswa:
                            st.session_state.data_siswa.at[idx_edit, "NIS"] = edit_nis
                            st.session_state.data_siswa.at[idx_edit, "Nama Siswa"] = edit_nama
                            st.session_state.data_siswa.at[idx_edit, "Kelas"] = edit_kelas
                            st.success("Data siswa berhasil diperbarui!")
                            st.rerun()
                    
                    st.markdown("---")
                    if st.button(f"🗑️ Hapus Data Siswa ({siswa_pilihan})", key="btn_hapus_siswa", type="primary"):
                        st.session_state.data_siswa.drop(index=idx_edit, inplace=True)
                        st.session_state.data_siswa.reset_index(drop=True, inplace=True)
                        st.success(f"Siswa **{siswa_pilihan}** berhasil dihapus!")
                        st.rerun()
                else:
                    st.info("Belum ada data siswa.")

            # TAB UPLOAD EXCEL
            with tab2:
                st.subheader("1. Unduh Template Excel")
                template_df = pd.DataFrame({
                    "NIS": ["105", "106"],
                    "Nama Siswa": ["Ahmad Fauzi", "Siti Nurhaliza"],
                    "Kelas": ["X TM 1", "X TM 1"]
                })
                
                buffer = io.BytesIO()
                try:
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        template_df.to_excel(writer, index=False, sheet_name='Data Siswa')
                    
                    st.download_button(
                        label="📥 Unduh Template Excel (.xlsx)",
                        data=buffer.getvalue(),
                        file_name="template_data_siswa.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="btn_download_template"
                    )
                except Exception:
                    st.warning("Pustaka `openpyxl` belum terpasang.")

                st.markdown("---")
                st.subheader("2. Unggah File Excel")
                uploaded_excel = st.file_uploader("Pilih file Excel yang telah diisi:", type=["xlsx", "xls"], key="uploader_excel_siswa")

                if uploaded_excel is not None:
                    try:
                        df_excel = pd.read_excel(uploaded_excel)
                        kolom_wajib = ["NIS", "Nama Siswa", "Kelas"]
                        
                        if all(k in df_excel.columns for k in kolom_wajib):
                            st.write("🔍 **Pratinjau Data:**")
                            st.dataframe(df_excel[kolom_wajib], use_container_width=True)

                            if st.button("🚀 Impor Semua Data ke Aplikasi", key="btn_impor_excel"):
                                kolom_tugas = [col for col in st.session_state.data_siswa.columns if col not in ["NIS", "Nama Siswa", "Kelas"] and not col.startswith("Nilai_")]

                                list_data_baru = []
                                for _, row in df_excel.iterrows():
                                    data_baru = {
                                        "NIS": str(row["NIS"]),
                                        "Nama Siswa": str(row["Nama Siswa"]),
                                        "Kelas": str(row["Kelas"])
                                    }
                                    for t in kolom_tugas:
                                        data_baru[t] = "Belum Mengumpulkan"
                                        data_baru[f"Nilai_{t}"] = 0.0
                                    list_data_baru.append(data_baru)

                                st.session_state.data_siswa = pd.concat([st.session_state.data_siswa, pd.DataFrame(list_data_baru)], ignore_index=True)
                                st.success(f"Berhasil mengimpor {len(df_excel)} data siswa baru!")
                                st.rerun()
                        else:
                            st.error(f"Format kolom Excel salah. Harus berisi: {', '.join(kolom_wajib)}")
                    except Exception as e:
                        st.error(f"Terjadi kesalahan saat membaca file Excel: {e}")

            # TAB TAMBAH MANUAL
            with tab3:
                st.subheader("Input Manual")
                with st.form("form_tambah_siswa_manual"):
                    nis = st.text_input("NIS:")
                    nama = st.text_input("Nama Lengkap Siswa:")
                    kelas = st.text_input("Kelas (contoh: X TM 1):")

                    simpan_siswa = st.form_submit_button("Tambah Siswa")

                    if simpan_siswa:
                        if nis and nama and kelas:
                            siswa_baru = {"NIS": nis, "Nama Siswa": nama, "Kelas": kelas}
                            kolom_tugas = [col for col in st.session_state.data_siswa.columns if col not in ["NIS", "Nama Siswa", "Kelas"] and not col.startswith("Nilai_")]
                            for t in kolom_tugas:
                                siswa_baru[t] = "Belum Mengumpulkan"
                                siswa_baru[f"Nilai_{t}"] = 0.0

                            st.session_state.data_siswa = pd.concat([st.session_state.data_siswa, pd.DataFrame([siswa_baru])], ignore_index=True)
                            st.success(f"Siswa **{nama}** berhasil ditambahkan!")
                            st.rerun()
                        else:
                            st.error("Semua kolom harus diisi.")