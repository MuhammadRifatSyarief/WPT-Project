# File: modules/pages/slow_moving.py

"""
Slow-Moving Analysis Page
=========================
Identifies slow-moving products and provides metrics and recommended actions.
SIMPLIFIED VERSION with natural data values.
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from modules.activity_logger import log_activity
from modules.email_utils import render_email_form


def render_page(df: pd.DataFrame):
    """
    Merender halaman Slow-Moving Analysis dengan data natural dari module.
    """
    
    # Preprocess - use ACTUAL values from module
    df = df.copy()
    
    # Ensure numeric columns
    df['turnover_ratio_90d'] = pd.to_numeric(df.get('turnover_ratio_90d', df.get('turnover_ratio', 1)), errors='coerce').fillna(0.5)
    df['current_stock_qty'] = pd.to_numeric(df.get('current_stock_qty', 0), errors='coerce').fillna(0)
    df['avg_daily_demand'] = pd.to_numeric(df.get('avg_daily_demand', 0), errors='coerce').fillna(0.01)
    
    # Calculate stock_value if not present or zero
    if 'stock_value' not in df.columns or df['stock_value'].sum() == 0:
        avgCost = pd.to_numeric(df.get('avgCost', df.get('unit_price', 1000)), errors='coerce').fillna(1000)
        df['stock_value'] = df['current_stock_qty'] * avgCost
    else:
        df['stock_value'] = pd.to_numeric(df['stock_value'], errors='coerce').fillna(0)
    
    # Use movement_class from slow_moving module if available
    if 'movement_class' in df.columns:
        slow_movers = df[df['movement_class'].isin(['Dead Stock', 'Slow Moving'])].copy()
    else:
        # Fallback: use turnover_ratio < 2.0 as slow mover criteria
        slow_movers = df[df['turnover_ratio_90d'] < 2.0].copy()
    
    st.title("📋 Slow-Moving Stock Analysis")
    st.markdown("Identifikasi produk dengan pergerakan lambat")
    
    # ========================================================================
    # METRIK UTAMA
    # ========================================================================
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Slow-Moving Products</div>
            <div class="metric-value">{len(slow_movers):,}</div>
            <div class="metric-delta negative">{(len(slow_movers)/len(df)*100):.1f}% of total</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        avg_turnover = slow_movers['turnover_ratio_90d'].mean() if len(slow_movers) > 0 else 0
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Avg Turnover</div>
            <div class="metric-value">{avg_turnover:.2f}x</div>
            <div class="metric-delta negative">Low</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        tied_capital = slow_movers['stock_value'].sum()
        # Format Rupiah with proper comma separator
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Tied-Up Capital</div>
            <div class="metric-value">Rp {tied_capital:,.0f}</div>
            <div class="metric-delta negative">At Risk</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        dead_stock_count = len(df[df.get('movement_class', '') == 'Dead Stock']) if 'movement_class' in df.columns else 0
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Dead Stock</div>
            <div class="metric-value">{dead_stock_count:,}</div>
            <div class="metric-delta negative">No Movement</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ========================================================================
    # FILTER SEDERHANA
    # ========================================================================
    
    st.markdown("### 📋 Slow-Moving Products List")
    
    col1, col2 = st.columns(2)
    with col1:
        groups = ['All'] + sorted([g for g in df['product_category'].dropna().unique() 
                                   if g and g not in ['OTHER', 'NUMERIC_CODE']])
        group_filter = st.selectbox("Filter by Group", groups, key="slow_group_filter")
    
    with col2:
        if 'movement_class' in df.columns:
            movement_options = ['All'] + list(slow_movers['movement_class'].dropna().unique())
            movement_filter = st.selectbox("Filter by Movement Class", movement_options, key="slow_movement_filter")
        else:
            movement_filter = "All"
    
    # Apply filters
    slow_filtered = slow_movers.copy()
    
    if group_filter != "All":
        slow_filtered = slow_filtered[slow_filtered['product_category'] == group_filter]
    
    if movement_filter != "All" and 'movement_class' in slow_filtered.columns:
        slow_filtered = slow_filtered[slow_filtered['movement_class'] == movement_filter]
    
    # Sort by stock value descending
    slow_filtered = slow_filtered.sort_values('stock_value', ascending=False)
    
    st.markdown(f"**{len(slow_filtered):,} produk ditemukan**")
    
    # ========================================================================
    # TABEL DENGAN FORMAT RUPIAH YANG BENAR
    # ========================================================================
    
    # Prepare display columns - essential only
    display_df = slow_filtered[['product_code', 'product_name', 'current_stock_qty', 'stock_value']].head(50).copy()
    
    # Add movement class if available
    if 'movement_class' in slow_filtered.columns:
        display_df['movement_class'] = slow_filtered['movement_class'].head(50)
    
    st.dataframe(
        display_df,
        use_container_width=True,
        height=400,
        column_config={
            "product_code": "Code",
            "product_name": st.column_config.TextColumn("Product Name", width="large"),
            "current_stock_qty": st.column_config.NumberColumn("Stock", format="%,d"),
            "stock_value": st.column_config.NumberColumn("Value (Rp)", format="Rp %,.0f"),
            "movement_class": "Status"
        }
    )
    
    # ========================================================================
    # REKOMENDASI TINDAKAN
    # ========================================================================
    
    st.markdown("---")
    st.markdown("### 💡 Recommended Actions")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div class="insight-card" style="border-left: 4px solid #ef4444;">
            <h4 style="color: #ef4444; margin-top: 0;">🔴 High Priority</h4>
            <ul>
                <li>Clearance sale (30-50% off)</li>
                <li>Bundle dengan fast-moving products</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="insight-card" style="border-left: 4px solid #f59e0b;">
            <h4 style="color: #f59e0b; margin-top: 0;">🟡 Medium Priority</h4>
            <ul>
                <li>Kampanye promosi</li>
                <li>Cross-selling strategy</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="insight-card" style="border-left: 4px solid #6366f1;">
            <h4 style="color: #6366f1; margin-top: 0;">🔵 Monitoring</h4>
            <ul>
                <li>Track demand trend</li>
                <li>Monitor competitor pricing</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # ========================================================================
    # EXPORT
    # ========================================================================
    
    st.markdown("---")
    
    csv_data = slow_filtered.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Report",
        data=csv_data,
        file_name=f"slow_moving_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        key="slow_moving_download"
    )