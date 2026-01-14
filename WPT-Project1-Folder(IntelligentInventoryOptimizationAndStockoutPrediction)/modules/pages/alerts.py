# File: modules/pages/alerts.py

"""
Stockout Alerts Page
====================
Provides real-time view of products at risk of stockout.
Uses ACTUAL data from modules without artificial caps for natural variation.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

from modules.activity_logger import log_activity
from modules.email_utils import render_email_form


def render_page(df: pd.DataFrame):
    """
    Merender halaman Stockout Alerts dengan data natural dari module.
    """
    
    # Preprocess data - USE ACTUAL VALUES from module
    df = df.copy()
    
    # Ensure numeric columns
    df['avg_daily_demand'] = pd.to_numeric(df.get('avg_daily_demand', 0.01), errors='coerce').fillna(0.01)
    df['current_stock_qty'] = pd.to_numeric(df.get('current_stock_qty', 0), errors='coerce').fillna(0)
    
    # Use safety_stock from module (ACTUAL values, no cap)
    if 'optimal_safety_stock' in df.columns:
        df['safety_stock'] = pd.to_numeric(df['optimal_safety_stock'], errors='coerce').fillna(0)
    elif 'safety_stock_optimized' in df.columns:
        df['safety_stock'] = pd.to_numeric(df['safety_stock_optimized'], errors='coerce').fillna(0)
    else:
        # Calculate if not available
        demand_std = df['avg_daily_demand'] * 0.3
        lead_time = 31  # Business assumption
        df['safety_stock'] = np.ceil(1.65 * demand_std * np.sqrt(lead_time))
    
    # Calculate days until stockout
    df['days_until_stockout'] = df['current_stock_qty'] / (df['avg_daily_demand'] + 0.001)
    df['days_until_stockout'] = df['days_until_stockout'].clip(upper=365)
    
    # Categorize risk level
    df['risk_level'] = pd.cut(
        df['days_until_stockout'], 
        bins=[-np.inf, 7, 14, 30, np.inf],
        labels=['Critical', 'High', 'Medium', 'Low']
    )
    
    critical_products = df[df['risk_level'] == 'Critical']
    high_products = df[df['risk_level'] == 'High']
    medium_products = df[df['risk_level'] == 'Medium']
    
    st.title("⚠️ Stockout Alerts")
    st.markdown("Monitor and manage stockout risks")
    
    # ========================================================================
    # METRICS
    # ========================================================================
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="alert-critical">
            <h3 style="margin: 0; color: white;">🔴 Critical</h3>
            <div style="font-size: 2rem; font-weight: 700; margin: 0.5rem 0;">{len(critical_products):,}</div>
            <div style="color: #fca5a5;">&lt;7 days stock</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="alert-warning">
            <h3 style="margin: 0; color: white;">🟡 High</h3>
            <div style="font-size: 2rem; font-weight: 700; margin: 0.5rem 0;">{len(high_products):,}</div>
            <div style="color: #fcd34d;">7-14 days stock</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="alert-info">
            <h3 style="margin: 0; color: white;">🔵 Medium</h3>
            <div style="font-size: 2rem; font-weight: 700; margin: 0.5rem 0;">{len(medium_products):,}</div>
            <div style="color: #93c5fd;">15-30 days stock</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ========================================================================
    # FILTER - GROUP AND RISK LEVEL
    # ========================================================================
    
    st.markdown("### 📋 Alert Details")
    
    col1, col2 = st.columns(2)
    
    with col1:
        groups = ['All'] + sorted([g for g in df['product_category'].dropna().unique() 
                                   if g and g not in ['OTHER', 'NUMERIC_CODE']])
        group_filter = st.selectbox("Filter by Group", groups, key="alert_group")
    
    with col2:
        risk_filter = st.selectbox("Filter by Risk Level", 
                                   ["All", "Critical", "High", "Medium"], key="alert_risk")
    
    # Apply filters
    alert_df = df.copy()
    
    if group_filter != "All":
        alert_df = alert_df[alert_df['product_category'] == group_filter]
    
    if risk_filter != "All":
        alert_df = alert_df[alert_df['risk_level'] == risk_filter]
    else:
        alert_df = alert_df[alert_df['risk_level'].isin(['Critical', 'High', 'Medium'])]
    
    # Sort by safety stock descending
    alert_df = alert_df.sort_values('safety_stock', ascending=False)
    
    st.markdown(f"**Showing {len(alert_df):,} products**")
    
    # Display columns with PROPER RUPIAH FORMAT
    display_cols = ['product_code', 'product_name', 'current_stock_qty', 'avg_daily_demand', 
                    'days_until_stockout', 'safety_stock', 'risk_level', 'product_category']
    
    available_cols = [c for c in display_cols if c in alert_df.columns]
    
    st.dataframe(
        alert_df[available_cols].head(30),
        use_container_width=True,
        height=400,
        column_config={
            "product_code": "Code",
            "product_name": st.column_config.TextColumn("Product Name", width="large"),
            "current_stock_qty": st.column_config.NumberColumn("Stock", format="%,d"),
            "avg_daily_demand": st.column_config.NumberColumn("Daily Demand", format="%.2f"),
            "days_until_stockout": st.column_config.NumberColumn("Days Left", format="%.0f"),
            "safety_stock": st.column_config.NumberColumn("Safety Stock", format="%,d"),
            "risk_level": "Risk",
            "product_category": "Group"
        }
    )
    
    st.markdown("---")
    
    # ========================================================================
    # QUICK ACTIONS
    # ========================================================================
    
    st.markdown("### 🎬 Quick Actions")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🚀 Generate Bulk Order", use_container_width=True, key="alert_bulk"):
            st.session_state.show_bulk_order = not st.session_state.get('show_bulk_order', False)
        
        if st.session_state.get('show_bulk_order', False):
            st.markdown("#### 📦 Critical Items to Order")
            critical_list = critical_products.head(5)
            
            for idx, row in critical_list.iterrows():
                order_qty = max(row.get('safety_stock', 10) * 2, row.get('avg_daily_demand', 1) * 30)
                st.markdown(f"• **{row['product_code']}**: Order {order_qty:,.0f} units")
            
            if st.button("✅ Confirm Order", key="confirm_bulk"):
                st.success(f"✅ Order confirmed! ID: #ORD-{datetime.now().strftime('%Y%m%d-%H%M')}")
                log_activity("🚀 Confirmed Stockout Bulk Order", '#10b981')
    
    with col2:
        csv_data = alert_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Report",
            data=csv_data,
            file_name=f"stockout_alerts_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
            key="stockout_export"
        )