# File: modules/pages/alerts.py

"""
Stockout Alerts Page
====================
Provides a real-time view of products at risk of stockout, with filtering,
sorting, and quick actions for reordering.
"""

import streamlit as st
import pandas as pd
import numpy as np  # Import NumPy
from datetime import datetime

# Impor modul kustom
from modules.activity_logger import log_activity
from modules.email_utils import render_email_form

def render_page(df: pd.DataFrame):
    """
    Merender seluruh konten untuk halaman Stockout Alerts.
    
    Args:
        df (pd.DataFrame): DataFrame utama yang berisi semua data inventaris.
    """
    
    # Semua logika halaman dimulai dari sini, di dalam fungsi
    st.title("⚠️ Stockout Alerts")
    st.markdown("Monitor and manage stockout risks")
    
    with st.popover("ℹ️ Tentang Stockout Alert"):
        st.markdown("""
        **Stockout Alert System** mencegah kehabisan stok dengan peringatan dini.
        
        **Cara Kerja:**
        Current Stock ÷ Daily Demand = Days Until Stockout
        
        **Level Risk:**
        - 🔴 Critical: <7 hari (ORDER NOW!)
        - 🟡 High: 7-14 hari (PLAN ORDER)
        - 🔵 Medium: 15-30 hari (MONITOR)
        
        **Immediate Actions:**
        - Prioritas ordering
        - Supplier notification
        - Alternative product suggestions
        """)
    
    # ========================================================================
    # PERHITUNGAN RISIKO STOCKOUT
    # ========================================================================
    
    # Hindari ZeroDivisionError dan NaN values
    df['days_until_stockout'] = df['current_stock_qty'] / (df['avg_daily_demand'] + 0.01)
    
    # Kategorikan level risiko
    df['risk_level'] = pd.cut(df['days_until_stockout'], 
                               bins=[-np.inf, 7, 14, 30, np.inf],
                               labels=['Critical', 'High', 'Medium', 'Low'])
    
    critical_products = df[df['risk_level'] == 'Critical']
    high_products = df[df['risk_level'] == 'High']
    medium_products = df[df['risk_level'] == 'Medium']
    
    # ========================================================================
    # TAMPILAN METRIK UTAMA
    # ========================================================================
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="alert-critical">
            <h3 style="margin: 0; color: white;">🔴 Critical Risk</h3>
            <div style="font-size: 2rem; font-weight: 700; margin: 0.5rem 0;">{len(critical_products)}</div>
            <div style="color: #fca5a5;">Stockout in <7 days</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="alert-warning">
            <h3 style="margin: 0; color: white;">🟡 High Risk</h3>
            <div style="font-size: 2rem; font-weight: 700; margin: 0.5rem 0;">{len(high_products)}</div>
            <div style="color: #fcd34d;">Stockout in 7-14 days</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="alert-info">
            <h3 style="margin: 0; color: white;">🔵 Medium Risk</h3>
            <div style="font-size: 2rem; font-weight: 700; margin: 0.5rem 0;">{len(medium_products)}</div>
            <div style="color: #93c5fd;">Stockout in 15-30 days</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ========================================================================
    # TABEL DETAIL ALERT
    # ========================================================================
    
    st.markdown("### 📋 Alert Details")
    
    # Pilihan filter
    col1, col2, col3 = st.columns(3)
    
    with col1:
        risk_filter = st.selectbox("Filter by Risk Level", 
                                   ["All", "Critical", "High", "Medium", "Low"])
    
    with col2:
        abc_filter_alert = st.selectbox("Filter by ABC Class", ["All", "A", "B", "C"])
    
    with col3:
        sort_option = st.selectbox("Sort By", 
                                   ["Days Until Stockout", "Daily Demand", "Stock Value"])
    
    # Terapkan filter
    alert_df = df.copy()  # Create a copy to avoid modifying original DataFrame
    
    if risk_filter != "All":
        alert_df = alert_df[alert_df['risk_level'] == risk_filter]
    
    if abc_filter_alert != "All":
        alert_df = alert_df[alert_df['ABC_class'] == abc_filter_alert]
    
    # Terapkan pengurutan
    sort_mapping = {
        "Days Until Stockout": "days_until_stockout",
        "Daily Demand": "avg_daily_demand",
        "Stock Value": "stock_value"
    }
    if sort_option in sort_mapping:
        alert_df = alert_df.sort_values(by=sort_mapping[sort_option], ascending=True)
    
    st.markdown(f"**Showing {len(alert_df):,} products**")
    
    # Tampilkan alert
    display_cols = ['product_code', 'product_name', 'current_stock_qty', 'avg_daily_demand', 
                    'days_until_stockout', 'optimal_safety_stock', 'risk_level', 'ABC_class']
    
    st.dataframe(
        alert_df[display_cols].head(20),
        width='stretch',
        height=400,
        column_config={
            "product_code": "Code",
            "product_name": "Product Name",
            "current_stock_qty": st.column_config.NumberColumn("Current Stock", format="%.0f"),
            "avg_daily_demand": st.column_config.NumberColumn("Daily Demand", format="%.2f"),
            "days_until_stockout": st.column_config.NumberColumn("Days Until Stockout", format="%.0f"),
            "optimal_safety_stock": st.column_config.NumberColumn("Safety Stock", format="%.0f"),
            "risk_level": "Risk Level",
            "ABC_class": "ABC"
        }
    )
    
    st.markdown("---")
    
    # ========================================================================
    # AKSI CEPAT
    # ========================================================================
    
    st.markdown("### 🎬 Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🚀 Bulk Order", width='stretch', key="stockout_bulk_order"):
            st.session_state.show_bulk_order = not st.session_state.show_bulk_order
        
        if st.session_state.show_bulk_order:
            st.markdown("#### 📦 Bulk Order - Critical Items")
            
            critical_list = critical_products.head(5)
            total_value = 0
            
            for idx, row in critical_list.iterrows():
                recommended_qty = max(row['optimal_safety_stock'] * 2, row['avg_daily_demand'] * 30)
                estimated_cost = recommended_qty * (row['stock_value'] / max(row['current_stock_qty'], 1)) if row['current_stock_qty'] > 0 else recommended_qty * 50000
                total_value += estimated_cost
                
                st.markdown(f"""
                **{row['product_code']}** - {row['product_name'][:50]}...
                - Current: {row['current_stock_qty']:.0f} units
                - Daily Demand: {row['avg_daily_demand']:.2f} units
                - Recommended Order: {recommended_qty:.0f} units
                - Est. Cost: Rp {estimated_cost:,.0f}
                """)
            
            st.info(f"**Total Order Value: Rp {total_value:,.0f}**")
            
            if st.button("✅ Confirm Order", key="confirm_bulk"):
                st.success("✅ Order confirmed! Order ID: #ORD-" + datetime.now().strftime('%Y%m%d-%H%M'))
                log_activity("🚀 Confirmed Stockout Bulk Order", '#10b981')
                st.session_state.show_bulk_order = False
                st.rerun()

    with col2:
        if st.button("📧 Send Alert Email", width='stretch', key="stockout_email"):
            st.session_state.show_email_form = not st.session_state.show_email_form
        
        if st.session_state.show_email_form:
            render_email_form(alert_df, "stockout_alerts", "stockout_alerts")
    
    with col3:
        csv_data = alert_df.to_csv(index=False).encode('utf-8')
        if st.download_button(
            label="📥 Export Report",
            data=csv_data,
            file_name=f"stockout_alerts_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            width='stretch',
            key="stockout_export"
        ):
            log_activity("📥 Downloaded Stockout Alerts Report", '#ef4444')