# File: modules/pages/slow_moving.py

"""
Slow-Moving Analysis Page
=========================
Identifies slow-moving products with proper formatting and clean layout.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

from modules.activity_logger import log_activity
from modules.email_utils import render_email_form


def winsorize_column(series, percentile=0.95):
    """Compress outlier values using logarithmic winsorization."""
    if series.isna().all() or len(series) == 0:
        return series
    
    p95 = series.quantile(percentile)
    if p95 <= 0:
        return series
    
    def compress_value(x):
        if pd.isna(x) or x <= p95:
            return round(x, 2) if not pd.isna(x) else x
        else:
            excess = x - p95
            compressed = p95 + np.log1p(excess / p95) * p95 * 0.5
            return round(compressed, 2)
    
    return series.apply(compress_value)


def render_page(df: pd.DataFrame):
    """Merender halaman Slow-Moving Analysis."""
    
    # ========================================================================
    # PREPROCESS DATA
    # ========================================================================
    
    df = df.copy()
    
    # Ensure numeric columns
    df['turnover_ratio_90d'] = pd.to_numeric(df.get('turnover_ratio_90d', df.get('turnover_ratio', 1)), errors='coerce').fillna(0.5)
    df['current_stock_qty'] = pd.to_numeric(df.get('current_stock_qty', 0), errors='coerce').fillna(0).astype(int)
    df['avg_daily_demand'] = pd.to_numeric(df.get('avg_daily_demand', 0), errors='coerce').fillna(0.01)
    
    # WINSORIZE TURNOVER
    df['turnover_display'] = winsorize_column(df['turnover_ratio_90d'], 0.95)
    
    # Calculate stock_value and ROUND IT
    if 'stock_value' not in df.columns or df['stock_value'].sum() == 0:
        avgCost = pd.to_numeric(df.get('avgCost', df.get('unit_price', 1000)), errors='coerce').fillna(1000)
        df['stock_value'] = (df['current_stock_qty'] * avgCost).round(0).astype(int)
    else:
        df['stock_value'] = pd.to_numeric(df['stock_value'], errors='coerce').fillna(0).round(0).astype(int)
    
    # Filter slow movers
    if 'movement_class' in df.columns:
        slow_movers = df[df['movement_class'].isin(['Dead Stock', 'Slow Moving'])].copy()
    else:
        slow_movers = df[df['turnover_ratio_90d'] < 2.0].copy()
    
    # ========================================================================
    # HEADER
    # ========================================================================
    
    st.title("Slow-Moving Analysis")
    st.markdown("Identifikasi produk dengan pergerakan lambat")
    
    # ========================================================================
    # METRICS ROW
    # ========================================================================
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card" style="border-left: 3px solid #f59e0b;">
            <div class="metric-label">Slow-Moving</div>
            <div class="metric-value">{len(slow_movers):,}</div>
            <div class="metric-delta negative">{(len(slow_movers)/len(df)*100):.1f}% of catalog</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        avg_turnover = slow_movers['turnover_display'].mean() if len(slow_movers) > 0 else 0
        st.markdown(f"""
        <div class="metric-card" style="border-left: 3px solid #ef4444;">
            <div class="metric-label">Avg Turnover</div>
            <div class="metric-value">{avg_turnover:.2f}x</div>
            <div class="metric-delta negative">Below threshold</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        tied_capital = slow_movers['stock_value'].sum()
        st.markdown(f"""
        <div class="metric-card" style="border-left: 3px solid #ef4444;">
            <div class="metric-label">Tied Capital</div>
            <div class="metric-value">Rp {tied_capital/1_000_000:,.1f}M</div>
            <div class="metric-delta negative">At Risk</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        dead_stock_count = len(df[df.get('movement_class', '') == 'Dead Stock']) if 'movement_class' in df.columns else 0
        st.markdown(f"""
        <div class="metric-card" style="border-left: 3px solid #6366f1;">
            <div class="metric-label">Dead Stock</div>
            <div class="metric-value">{dead_stock_count:,}</div>
            <div class="metric-delta negative">Zero Movement</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ========================================================================
    # CLASSIFICATION INFO - Using Expanders (more reliable than hover)
    # ========================================================================
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Klasifikasi Movement**")
        st.markdown("""
        | Status | Kriteria |
        |--------|----------|
        | **Dead Stock** | Tidak ada penjualan 90 hari |
        | **Slow Moving** | Turnover < 2x dalam 90 hari |
        | **Normal** | Turnover 2-6x dalam 90 hari |
        | **Fast Moving** | Turnover > 6x dalam 90 hari |
        """)
    
    with col2:
        st.markdown("**ABC Class**")
        st.markdown("""
        | Class | Kontribusi | Prioritas |
        |-------|------------|-----------|
        | **A** | ~80% revenue | Tinggi - monitoring ketat |
        | **B** | ~15% revenue | Sedang - monitoring reguler |
        | **C** | ~5% revenue | Rendah - review kebutuhan |
        """)
    
    with col3:
        st.markdown("**ABC-XYZ Segment**")
        st.markdown("""
        | Segment | Artinya | Rekomendasi |
        |---------|---------|-------------|
        | **AX, BX** | Demand stabil | Fokus utama |
        | **AY, BY** | Demand fluktuatif | Safety stock lebih |
        | **AZ, BZ** | Demand tidak stabil | Monitoring intensif |
        | **CX, CY, CZ** | Revenue rendah | Evaluasi discontinue |
        """)
    
    # ========================================================================
    # FILTERS
    # ========================================================================
    
    st.markdown("### Product List")
    
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
    # TABLE WITH PROPER FORMATTING
    # ========================================================================
    
    # Prepare display columns - ENSURE VALUES ARE ROUNDED
    display_cols = ['product_code', 'product_name', 'current_stock_qty', 'stock_value', 'turnover_display']
    
    if 'movement_class' in slow_filtered.columns:
        display_cols.append('movement_class')
    
    available_cols = [c for c in display_cols if c in slow_filtered.columns]
    display_df = slow_filtered[available_cols].head(50).copy()
    
    # Ensure numeric types for proper formatting
    display_df['stock_value'] = display_df['stock_value'].round(0).astype(int)
    display_df['turnover_display'] = display_df['turnover_display'].round(2)
    
    # Rename for display
    display_df = display_df.rename(columns={'turnover_display': 'turnover_ratio'})
    
    st.dataframe(
        display_df,
        use_container_width=True,
        height=400,
        column_config={
            "product_code": "Code",
            "product_name": st.column_config.TextColumn("Product Name", width="large"),
            "current_stock_qty": st.column_config.NumberColumn("Stock", format="%,d"),
            "stock_value": st.column_config.NumberColumn("Value (Rp)", format="Rp %,d"),
            "turnover_ratio": st.column_config.NumberColumn("Turnover", format="%.2fx"),
            "movement_class": "Status"
        }
    )
    
    # ========================================================================
    # RECOMMENDED ACTIONS
    # ========================================================================
    
    st.markdown("---")
    st.markdown("### Recommended Actions")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div class="insight-card" style="border-left: 4px solid #ef4444;">
            <h4 style="color: #fca5a5; margin-top: 0; font-size: 0.95rem;">High Priority</h4>
            <ul style="margin: 0; padding-left: 1.2rem; color: #cbd5e1; font-size: 0.85rem;">
                <li>Clearance sale (30-50% off)</li>
                <li>Bundle dengan fast-moving products</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="insight-card" style="border-left: 4px solid #f59e0b;">
            <h4 style="color: #fcd34d; margin-top: 0; font-size: 0.95rem;">Medium Priority</h4>
            <ul style="margin: 0; padding-left: 1.2rem; color: #cbd5e1; font-size: 0.85rem;">
                <li>Kampanye promosi</li>
                <li>Cross-selling strategy</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="insight-card" style="border-left: 4px solid #667eea;">
            <h4 style="color: #818cf8; margin-top: 0; font-size: 0.95rem;">Monitoring</h4>
            <ul style="margin: 0; padding-left: 1.2rem; color: #cbd5e1; font-size: 0.85rem;">
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
        label="Download Report",
        data=csv_data,
        file_name=f"slow_moving_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        key="slow_moving_download"
    )