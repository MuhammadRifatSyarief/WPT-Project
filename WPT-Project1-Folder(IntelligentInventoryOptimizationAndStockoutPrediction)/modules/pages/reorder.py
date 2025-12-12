# File: modules/pages/reorder.py

"""
Reorder Optimization Page
=========================
Calculates and displays reorder points and recommended order quantities.
"""

# 1. Impor library yang dibutuhkan
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# 2. Impor fungsi dari modul kustom Anda
from modules.activity_logger import log_activity
from modules.email_utils import render_email_form

# 3. Definisikan fungsi render halaman
def render_page(df: pd.DataFrame):
    """
    Merender seluruh konten untuk halaman Reorder Optimization.
    
    Args:
        df (pd.DataFrame): DataFrame utama yang berisi semua data inventaris.
    """
    
    st.title("🔄 Reorder Optimization")
    st.markdown("Safety Stock & Reorder Point Calculation")
    
    with st.popover("ℹ️ Tentang Reorder Optimization"):
        st.markdown("""
        **Reorder Optimization** menghitung kapan dan berapa banyak yang harus diorder ulang.
        
        **Formula Kunci:**
        - **Safety Stock (SS)**: `Z × σ × √LT` (Buffer untuk ketidakpastian)
        - **Reorder Point (ROP)**: `(Avg Demand × Lead Time) + SS` (Pemicu untuk memesan)
        """)
    
    # ========================================================================
    # KARTU METRIK UTAMA
    # ========================================================================
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        avg_safety_stock = df['optimal_safety_stock'].mean()
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Avg Safety Stock</div>
            <div class="metric-value">{avg_safety_stock:.0f}</div>
            <div class="metric-delta positive">Units</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        avg_lead_time = df['estimated_lead_time'].mean()
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Avg Lead Time</div>
            <div class="metric-value">{avg_lead_time:.0f}</div>
            <div class="metric-delta positive">Days</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Reorder Points</div>
            <div class="metric-value">{len(df):,}</div>
            <div class="metric-delta positive">Calculated</div>
        </div>""", unsafe_allow_html=True)
    with col4:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-label">Cost Savings</div>
            <div class="metric-value">~15%</div>
            <div class="metric-delta positive">Potential</div>
        </div>""", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ========================================================================
    # TABEL REKOMENDASI PEMESANAN ULANG
    # ========================================================================
    
    st.markdown("### 🎯 Reorder Recommendations")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        abc_reorder_filter = st.selectbox("Filter by ABC Class", ["All", "A", "B", "C"], key="reorder_abc")
    with col2:
        min_demand = st.number_input("Min Daily Demand", min_value=0.0, value=0.0, step=0.1)
    with col3:
        sort_reorder = st.selectbox("Sort By", ["Urgency", "Daily Demand", "Stock Value"])
    
    # Hitung rekomendasi
    reorder_df = df.copy()
    reorder_df['reorder_point_calc'] = (reorder_df['avg_daily_demand'] * reorder_df['estimated_lead_time']) + reorder_df['optimal_safety_stock']
    reorder_df['recommended_order_qty'] = np.maximum(reorder_df['reorder_point_calc'] - reorder_df['current_stock_qty'], 0)
    reorder_df['urgency_score'] = reorder_df['recommended_order_qty'] / (reorder_df['reorder_point_calc'] + 0.01)
    
    # Terapkan filter
    if abc_reorder_filter != "All":
        reorder_df = reorder_df[reorder_df['ABC_class'] == abc_reorder_filter]
    if min_demand > 0:
        reorder_df = reorder_df[reorder_df['avg_daily_demand'] >= min_demand]
    
    # Hanya tampilkan produk yang perlu diorder
    reorder_df = reorder_df[reorder_df['recommended_order_qty'] > 0]

    # Terapkan pengurutan
    sort_map = {
        "Urgency": "urgency_score",
        "Daily Demand": "avg_daily_demand",
        "Stock Value": "stock_value"
    }
    reorder_df = reorder_df.sort_values(by=sort_map[sort_reorder], ascending=False)
    
    st.markdown(f"**Menampilkan {len(reorder_df):,} produk yang direkomendasikan untuk diorder ulang**")
    
    display_cols = ['product_code', 'product_name', 'current_stock_qty', 'reorder_point_calc', 'recommended_order_qty', 'estimated_lead_time', 'ABC_class']
    st.dataframe(
        reorder_df[display_cols].head(50),
        width='stretch',
        height=400,
        column_config={
            "product_code": "Code",
            "product_name": "Product Name",
            "current_stock_qty": st.column_config.NumberColumn("Stock", format="%d"),
            "reorder_point_calc": st.column_config.NumberColumn("Reorder Point", format="%d"),
            "recommended_order_qty": st.column_config.NumberColumn("Order Qty", format="%d"),
            "estimated_lead_time": st.column_config.NumberColumn("Lead Time", format="%d days"),
            "ABC_class": "ABC"
        }
    )
    
    # ========================================================================
    # EKSPOR & AKSI
    # ========================================================================
    
    st.markdown("---")
    st.markdown("### 📤 Export & Share Reorder Plan")
    
    col1, col2 = st.columns(2)
    with col1:
        csv_data = reorder_df.to_csv(index=False).encode('utf-8')
        if st.download_button(
            label="📥 Download Reorder Report",
            data=csv_data,
            file_name=f"reorder_optimization_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            width='stretch',
            key="reorder_report_download"
        ):
            log_activity("📥 Downloaded Reorder Optimization Report", '#6366f1')
    
    with col2:
        if st.button("📧 Email Reorder Plan", width='stretch', key="reorder_email_button"):
            st.session_state.show_email_reorder = not st.session_state.get('show_email_reorder', False)
    
    if st.session_state.get('show_email_reorder', False):
        render_email_form(reorder_df, "reorder", "reorder_optimization")