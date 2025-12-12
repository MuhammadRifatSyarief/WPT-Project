# File: main.py

import streamlit as st
import sys
import os
import pandas as pd

# Tambahkan root proyek ke path agar modul bisa diimpor
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Impor modul
from modules.data_loader import load_all_data 
from modules.session_manager import initialize_session_state
from modules.ui_components import apply_page_css, render_sidebar_header, render_quick_stat_box
from modules.activity_logger import render_activity_log_sidebar, log_activity

# Impor semua modul halaman
from modules.pages import (
    dashboard,
    forecasting,
    health,
    alerts,
    reorder,
    slow_moving,
    settings
)

# ============================================================================
# KONFIGURASI HALAMAN
# ============================================================================
st.set_page_config(
    page_title="Inventory Intelligence",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# INISIALISASI SESSION STATE & GAYA (STYLING)
# ============================================================================
initialize_session_state() 
apply_page_css()

# ============================================================================
# MEMUAT DATA MENGGUNAKAN LOADER ANDA
# ============================================================================
# Panggil fungsi `load_all_data` yang akan mengelola semuanya
df = load_all_data()

if df is None or df.empty:
    st.error("Gagal memuat data. Mohon periksa konsol atau log untuk detail error.")
    # Coba berikan pesan yang lebih membantu jika memungkinkan
    st.info("Pastikan file `master_features_final.csv` ada di dalam direktori `data/`.")
    st.stop()

# --- FUNGSI UNTUK QUICK STATS ---
def get_quick_stats_from_df(dataf: pd.DataFrame) -> dict:
    if dataf.empty:
        return {'active_alerts': 0, 'total_products': 0, 'last_updated': 'N/A'}
    
    # Hitung ulang 'days_until_stockout' jika belum ada, untuk keamanan
    if 'days_until_stockout' not in dataf.columns:
        dataf['days_until_stockout'] = dataf['current_stock_qty'] / (dataf['avg_daily_demand'] + 0.001)

    active_alerts = len(dataf[dataf['days_until_stockout'] < 14])
    return {
        'active_alerts': active_alerts,
        'total_products': len(dataf),
        'last_updated': pd.Timestamp.now().strftime('%H:%M:%S')
    }

quick_stats = get_quick_stats_from_df(df)

# ============================================================================
# SIDEBAR & NAVIGASI
# ============================================================================
PAGES = [
    "🏠 Dashboard Overview",
    "📈 Demand Forecasting",
    "📊 Inventory Health",
    "⚠️ Stockout Alerts",
    "🔄 Reorder Optimization",
    "📋 Slow-Moving Analysis",
    "⚙️ Settings"
]

with st.sidebar:
    render_sidebar_header("📦 Inventory Intelligence", "Data Science Team")
    page = st.radio("Navigasi", PAGES, label_visibility="collapsed")
    st.markdown("---")
    st.markdown("### Quick Stats")
    render_quick_stat_box("Active Alerts", str(quick_stats.get('active_alerts', 'N/A')), type_='alert')
    render_quick_stat_box("Products Monitored", f"{quick_stats.get('total_products', 0):,}", type_='products')
    render_quick_stat_box("Last Updated", quick_stats.get('last_updated', 'N/A'), type_='updated')
    st.markdown("---")
    render_activity_log_sidebar(max_initial_entries=5)
    st.markdown("---")
    st.markdown("### About")
    st.markdown("### 👤 User")
    st.markdown("**Internship Program**")
    st.markdown("UNESA Data Science")
    st.markdown("**Version:** 1.0")

# ============================================================================
# ROUTING HALAMAN
# ============================================================================
if "Dashboard Overview" in page:
    log_activity("Navigated to Dashboard", "#6366f1")
    dashboard.render_page(df)
elif "Demand Forecasting" in page:
    log_activity("Navigated to Forecasting", "#6366f1")
    forecasting.render_page(df)
elif "Inventory Health" in page:
    log_activity("Navigated to Health", "#6366f1")
    health.render_page(df)
elif "Stockout Alerts" in page:
    log_activity("Navigated to Alerts", "#6366f1")
    alerts.render_page(df)
elif "Reorder Optimization" in page:
    log_activity("Navigated to Reorder", "#6366f1")
    reorder.render_page(df)
elif "Slow-Moving Analysis" in page:
    log_activity("Navigated to Slow-Moving", "#6366f1")
    slow_moving.render_page(df)
elif "Settings" in page:
    log_activity("Navigated to Settings", "#6366f1")
    settings.render_page(df)
else:
    st.error("Halaman tidak ditemukan.")