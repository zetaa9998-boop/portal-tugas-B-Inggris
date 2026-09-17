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

st.set_page_config(page_title="Debug Portal SMK", layout="wide")
st.title("🔍 Menu Diagnostik Data Google Sheets")

SHEET_ID = "1BTUS3nbirH2sU_j6u2YLZDTykYyULMYXNsE30mkhiAo"

# Fungsi Baca Data Langsung
@st.cache_data(ttl=1)
def muat_debug_sheet(nama_tab):
    try:
        timestamp = int(time.time())
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={nama_tab}&_t={timestamp}"
        df = pd.read_csv(url, dtype=str)
        return df.fillna("")
    except Exception as e:
        return pd.DataFrame({"Error": [str(e)]})

df_siswa_debug = muat_debug_sheet("Siswa")
df_tugas_debug = muat_debug_sheet("Tugas")
df_pengumpulan_debug = muat_debug_sheet("Pengumpulan")

if st.button("🔄 Paksa Hapus Cache & Muat Ulang"):
    st.cache_data.clear()
    st.rerun()

st.subheader("1. Data Mentah Tab 'Siswa' yang Terbaca di Streamlit:")
st.dataframe(df_siswa_debug, use_container_width=True)

st.subheader("2. Informasi Kolom Tab 'Siswa':")
st.write(list(df_siswa_debug.columns))

st.subheader("3. Data Mentah Tab 'Tugas':")
st.dataframe(df_tugas_debug, use_container_width=True)
