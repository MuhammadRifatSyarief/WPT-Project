# File: modules/pages/reorder.py

"""
Reorder Optimization Page
=========================
Calculates and displays reorder points and recommended order quantities.
Uses ACTUAL data from modules for natural variation.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

from modules.activity_logger import log_activity
from modules.email_utils import render_email_form


def render_page(df: pd.DataFrame):
    """
    Merender halaman Reorder Optimization dengan data natural dari module.
    """
    
    # Preprocess data - USE ACTUAL VALUES from module
    df = df.copy()
    
    # Handle column aliases
    if 'lead_time_days' in df.columns and 'estimated_lead_time' not in df.columns:
        df['estimated_lead_time'] = df['lead_time_days']
    if 'safety_stock_optimized' in df.columns and 'optimal_safety_stock' not in df.columns:
        df['optimal_safety_stock'] = df['safety_stock_optimized']
    if 'reorder_point_optimized' in df.columns:
        df['reorder_point_calc'] = df['reorder_point_optimized']
    
    # Ensure numeric columns - USE ACTUAL VALUES (no artificial caps)
    df['optimal_safety_stock'] = pd.to_numeric(df.get('optimal_safety_stock', 0), errors='coerce').fillna(0)
    df['estimated_lead_time'] = pd.to_numeric(df.get('estimated_lead_time', 31), errors='coerce').fillna(31)
    df['avg_daily_demand'] = pd.to_numeric(df.get('avg_daily_demand', 0.01), errors='coerce').fillna(0.01)
    df['current_stock_qty'] = pd.to_numeric(df.get('current_stock_qty', 0), errors='coerce').fillna(0)
    
    # FILTER: Exclude Dead Stock and Slow Moving products
    if 'movement_class' in df.columns:
        df_filtered = df[~df['movement_class'].isin(['Dead Stock', 'Slow Moving'])].copy()
        excluded_count = len(df) - len(df_filtered)
    else:
        df_filtered = df.copy()
        excluded_count = 0
    
    # ========================================================================
    # INJECT CSS - Hover Tooltips
    # ========================================================================
    
    st.markdown("""
    <style>
    .tooltip-container {
        position: relative;
        display: inline-block;
        cursor: help;
    }
    
    .tooltip-container .tooltip-text {
        visibility: hidden;
        opacity: 0;
        width: 300px;
        background: rgba(30, 41, 59, 0.95);
        color: #e2e8f0;
        text-align: left;
        border-radius: 10px;
        padding: 12px 15px;
        position: absolute;
        z-index: 100;
        bottom: 125%;
        left: 50%;
        margin-left: -150px;
        border: 1px solid rgba(255,255,255,0.1);
        backdrop-filter: blur(10px);
        box-shadow: 0 10px 25px rgba(0,0,0,0.3);
        font-size: 0.85rem;
        line-height: 1.5;
        transition: opacity 0.3s, visibility 0.3s;
    }
    
    .tooltip-container .tooltip-text::after {
        content: "";
        position: absolute;
        top: 100%;
        left: 50%;
        margin-left: -8px;
        border-width: 8px;
        border-style: solid;
        border-color: rgba(30, 41, 59, 0.95) transparent transparent transparent;
    }
    
    .tooltip-container:hover .tooltip-text {
        visibility: visible;
        opacity: 1;
    }
    
    .info-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(99, 102, 241, 0.15);
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        color: #a5b4fc;
        border: 1px solid rgba(99, 102, 241, 0.3);
        cursor: help;
        transition: all 0.2s;
    }
    
    .info-badge:hover {
        background: rgba(99, 102, 241, 0.25);
        transform: translateY(-1px);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # ========================================================================
    # HEADER WITH HOVER TOOLTIPS
    # ========================================================================
    
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 15px;">
        <h1 style="margin: 0;">🔄 Reorder Optimization</h1>
        <div class="tooltip-container">
            <span class="info-badge">ℹ️ Formulas</span>
            <span class="tooltip-text">
                <strong>Safety Stock (SS):</strong><br>
                <code>Z × σ × √LT</code> = Buffer untuk uncertainty<br><br>
                <strong>Reorder Point (ROP):</strong><br>
                <code>(Demand × Lead Time) + SS</code><br><br>
                <em>Dead Stock/Slow Moving items excluded.</em>
            </span>
        </div>
    </div>
    <p style="color: #94a3b8; margin-top: 0;">Safety Stock & Reorder Point Calculation</p>
    """, unsafe_allow_html=True)
    
    if excluded_count > 0:
        st.info(f"ℹ️ Excluded {excluded_count:,} Dead Stock/Slow Moving items")
    
    # ========================================================================
    # METRICS
    # ========================================================================
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_ss = df_filtered['optimal_safety_stock'].mean()
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Avg Safety Stock</div>
            <div class="metric-value">{avg_ss:,.0f}</div>
            <div class="metric-delta positive">Units</div>
        </div>""", unsafe_allow_html=True)
    
    with col2:
        avg_lt = df_filtered['estimated_lead_time'].mean()
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Avg Lead Time</div>
            <div class="metric-value">{avg_lt:,.0f}</div>
            <div class="metric-delta positive">Days</div>
        </div>""", unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Active Products</div>
            <div class="metric-value">{len(df_filtered):,}</div>
            <div class="metric-delta positive">Items</div>
        </div>""", unsafe_allow_html=True)
    
    with col4:
        # Count items needing reorder
        if 'reorder_point_calc' not in df_filtered.columns:
            df_filtered['reorder_point_calc'] = (df_filtered['avg_daily_demand'] * df_filtered['estimated_lead_time']) + df_filtered['optimal_safety_stock']
        need_reorder = len(df_filtered[df_filtered['current_stock_qty'] < df_filtered['reorder_point_calc']])
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Need Reorder</div>
            <div class="metric-value">{need_reorder:,}</div>
            <div class="metric-delta negative">Below ROP</div>
        </div>""", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ========================================================================
    # FILTER BY GROUP
    # ========================================================================
    
    st.markdown("### 🎯 Reorder Recommendations")
    
    groups = ['All'] + sorted([g for g in df_filtered['product_category'].dropna().unique() 
                               if g and g not in ['OTHER', 'NUMERIC_CODE']])
    group_filter = st.selectbox("Filter by Group", groups, key="reorder_group")
    
    # Calculate recommendations using ACTUAL values
    reorder_df = df_filtered.copy()
    if 'reorder_point_calc' not in reorder_df.columns:
        reorder_df['reorder_point_calc'] = (reorder_df['avg_daily_demand'] * reorder_df['estimated_lead_time']) + reorder_df['optimal_safety_stock']
    
    reorder_df['recommended_order_qty'] = np.maximum(reorder_df['reorder_point_calc'] - reorder_df['current_stock_qty'], 0)
    
    # Apply filter
    if group_filter != "All":
        reorder_df = reorder_df[reorder_df['product_category'] == group_filter]
    
    # Only show products that need reorder
    reorder_df = reorder_df[reorder_df['recommended_order_qty'] > 0]
    
    # Sort by recommended order qty descending
    reorder_df = reorder_df.sort_values('recommended_order_qty', ascending=False)
    
    st.markdown(f"**{len(reorder_df):,} products need reorder**")
    
    display_cols = ['product_code', 'product_name', 'current_stock_qty', 'reorder_point_calc', 
                    'recommended_order_qty', 'estimated_lead_time', 'product_category']
    available_cols = [c for c in display_cols if c in reorder_df.columns]
    
    # Display with PROPER number formatting (commas for thousands)
    st.dataframe(
        reorder_df[available_cols].head(50),
        use_container_width=True,
        height=400,
        column_config={
            "product_code": "Code",
            "product_name": st.column_config.TextColumn("Product Name", width="large"),
            "current_stock_qty": st.column_config.NumberColumn("Stock", format="%,d"),
            "reorder_point_calc": st.column_config.NumberColumn("Reorder Point", format="%,d"),
            "recommended_order_qty": st.column_config.NumberColumn("Order Qty", format="%,d"),
            "estimated_lead_time": st.column_config.NumberColumn("Lead Time", format="%d days"),
            "product_category": "Group"
        }
    )
    
    # ========================================================================
    # EXPORT
    # ========================================================================
    
    st.markdown("---")
    
    csv_data = reorder_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Reorder Report",
        data=csv_data,
        file_name=f"reorder_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        key="reorder_download"
    )