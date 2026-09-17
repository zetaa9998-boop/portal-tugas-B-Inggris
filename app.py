import time
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Diagnosis Data", layout="wide")
st.title("🔍 Diagnosis Data Google Sheets")

SHEET_ID = "1BTUS3nbirH2sU_j6u2YLZDTykYyULMYXNsE30mkhiAo"

timestamp = int(time.time())
url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Siswa&_t={timestamp}"

try:
    df_siswa = pd.read_csv(url, dtype=str)
    st.success("✅ Berhasil terhubung ke Google Sheets!")
    
    st.subheader("1. Nama Kolom (Header) yang Terbaca:")
    st.write(list(df_siswa.columns))
    
    st.subheader("2. Isi Tabel Siswa:")
    st.dataframe(df_siswa)
    
    st.subheader("3. Jumlah Baris Data:")
    st.write(f"Total baris: {len(df_siswa)}")

except Exception as e:
    st.error(f"❌ Gagal membaca Google Sheets: {e}")
