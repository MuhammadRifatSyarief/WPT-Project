# File: main.py

import streamlit as st
import sys
import os
import pandas as pd

# Tambahkan root proyek ke path agar modul bisa diimpor
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Impor modul
from modules.data_loader_v5 import DashboardDataLoaderV5, load_all_data
from modules.session_manager import initialize_session_state
from modules.ui_components import apply_page_css, render_sidebar_header, render_quick_stat_box
from modules.activity_logger import render_activity_log_sidebar, log_activity
from modules.auth import is_authenticated, is_admin, get_current_user, logout

# Impor semua modul halaman
from modules.pages import (
    dashboard,
    forecasting,
    health,
    alerts,
    reorder,
    slow_moving,
    rfm,
    mba,
    settings,
    login
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
# INITIALIZE SCHEDULER (Check for scheduled puller runs)
# ============================================================================
try:
    from modules.puller_scheduler import initialize_scheduler, check_and_run_scheduled_pullers
    # Initialize scheduler on startup
    initialize_scheduler()
    # Check if any pullers need to run (only check once per session)
    if 'scheduler_checked' not in st.session_state:
        check_and_run_scheduled_pullers()
        st.session_state.scheduler_checked = True
except Exception as e:
    # Don't fail if scheduler has issues
    pass

# ============================================================================
# AUTHENTICATION CHECK
# ============================================================================
if not is_authenticated():
    # Show login page if not authenticated
    login.render_login_page()
    st.stop()

# ============================================================================
# MEMUAT DATA MENGGUNAKAN LOADER V5 (NEW)
# ============================================================================
data_loader = DashboardDataLoaderV5()
df = data_loader.load_all_data(apply_filters=True)  # Filters out dummy/umum/jasa

if df is None or df.empty:
    st.error("Gagal memuat data. Mohon periksa konsol atau log untuk detail error.")
    st.info("Pastikan file `master_features.csv` ada di dalam direktori `data/features/`.")
    st.stop()

# --- FUNGSI UNTUK QUICK STATS ---
def get_quick_stats_from_df(dataf: pd.DataFrame) -> dict:
    if dataf.empty:
        return {'active_alerts': 0, 'total_products': 0, 'last_updated': 'N/A'}
    
    # Use risk_class from predictions if available
    if 'risk_class' in dataf.columns:
        active_alerts = len(dataf[dataf['risk_class'].isin(['critical', 'high'])])
    elif 'days_until_stockout' in dataf.columns:
        active_alerts = len(dataf[dataf['days_until_stockout'] < 14])
    else:
        active_alerts = 0
    
    return {
        'active_alerts': active_alerts,
        'total_products': len(dataf),
        'last_updated': pd.Timestamp.now().strftime('%H:%M:%S')
    }

quick_stats = get_quick_stats_from_df(df)

# ============================================================================
# GROUP FILTER (NEW: Item Group from no prefix)
# ============================================================================
# Get available groups from the loaded data
available_groups = sorted(df['item_group_normalized'].dropna().unique().tolist()) if 'item_group_normalized' in df.columns else []

# Store selected groups in session state
if 'selected_groups' not in st.session_state:
    st.session_state.selected_groups = []


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
    "👥 RFM Analysis",
    "🛒 Market Basket Analysis",
    "⚙️ Settings"
]

with st.sidebar:
    render_sidebar_header("📦 Inventory Intelligence", "Data Science Team")
    
    # User info
    current_user = get_current_user()
    if current_user:
        role_badge = "🔴 Admin" if is_admin() else "🔵 User"
        st.markdown(f"### 👤 {current_user['username']}")
        st.markdown(f"**Role:** {role_badge}")
        st.markdown("---")
    
    page = st.radio("Navigasi", PAGES, label_visibility="collapsed")
    st.markdown("---")
    st.markdown("### Quick Stats")
    render_quick_stat_box("Active Alerts", str(quick_stats.get('active_alerts', 'N/A')), type_='alert')
    render_quick_stat_box("Products Monitored", f"{quick_stats.get('total_products', 0):,}", type_='products')
    render_quick_stat_box("Last Updated", quick_stats.get('last_updated', 'N/A'), type_='updated')
    st.markdown("---")
    
    # ========================================================================
    # GROUP FILTER (NEW: Item Groups)
    # ========================================================================
    st.markdown("### 🏷️ Filter by Group")
    if available_groups:
        selected_groups = st.multiselect(
            "Select item groups",
            options=available_groups,
            default=st.session_state.selected_groups,
            key="group_filter_select",
            help="Filter products by group prefix (extracted from item code before '-')"
        )
        st.session_state.selected_groups = selected_groups
        
        if selected_groups:
            st.caption(f"📌 {len(selected_groups)} group(s) selected")
    else:
        st.caption("No groups available")
    
    st.markdown("---")
    
    # ========================================================================
    # DATA REFRESH BUTTON (NEW)
    # ========================================================================
    st.markdown("### 🔄 Data Refresh")
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        if st.button("🔄 Refresh", use_container_width=True, help="Reload data from CSV"):
            st.cache_data.clear()
            log_activity("🔄 Data cache cleared", "#10b981")
            st.rerun()
    with col_r2:
        if st.button("⚡ Full Pull", use_container_width=True, help="Run full pipeline"):
            try:
                from modules.data_puller_project1 import PipelineDataPuller
                puller = PipelineDataPuller()
                if puller.is_data_stale(max_age_hours=24):
                    log_activity("⚡ Starting full pipeline...", "#f59e0b")
                    st.info("⏳ Running pipeline... This may take a while.")
                else:
                    log_activity("✅ Data is fresh, skipping pull", "#10b981")
                    st.success("✅ Data is already up-to-date!")
            except Exception as e:
                st.error(f"Pipeline error: {str(e)}")
    
    st.markdown("---")
    render_activity_log_sidebar(max_initial_entries=5)
    st.markdown("---")
    
    # Logout button
    if st.button("🚪 Logout", use_container_width=True):
        logout()
        st.rerun()
    
    st.markdown("---")
    st.markdown("### About")
    st.markdown("**Internship Program**")
    st.markdown("UNESA Data Science")
    st.markdown("**Version:** 1.0")

# ============================================================================
# APPLY GROUP FILTER (NEW)
# ============================================================================
# Create filtered dataframe based on selected groups
df_filtered = df.copy()
if st.session_state.selected_groups:
    df_filtered = df_filtered[df_filtered['item_group_normalized'].isin(st.session_state.selected_groups)]
    st.info(f"🏷️ Filtered: {len(df_filtered):,} products from {len(st.session_state.selected_groups)} group(s)")

# ============================================================================
# ROUTING HALAMAN
# ============================================================================
if "Dashboard Overview" in page:
    log_activity("Navigated to Dashboard", "#6366f1")
    dashboard.render_page(df_filtered)
elif "Demand Forecasting" in page:
    log_activity("Navigated to Forecasting", "#6366f1")
    forecasting.render_page(df_filtered)
elif "Inventory Health" in page:
    log_activity("Navigated to Health", "#6366f1")
    health.render_page(df_filtered)
elif "Stockout Alerts" in page:
    log_activity("Navigated to Alerts", "#6366f1")
    alerts.render_page(df_filtered)
elif "Reorder Optimization" in page:
    log_activity("Navigated to Reorder", "#6366f1")
    reorder.render_page(df_filtered)
elif "Slow-Moving Analysis" in page:
    log_activity("Navigated to Slow-Moving", "#6366f1")
    slow_moving.render_page(df_filtered)
elif "RFM Analysis" in page:
    log_activity("Navigated to RFM Analysis", "#6366f1")
    rfm.render_page(df_filtered)
elif "Market Basket Analysis" in page:
    log_activity("Navigated to Market Basket Analysis", "#6366f1")
    mba.render_page(df_filtered)
elif "Settings" in page:
    # Settings page requires admin access for full functionality
    log_activity("Navigated to Settings", "#6366f1")
    settings.render_page(df_filtered)
else:
    st.error("Halaman tidak ditemukan.")