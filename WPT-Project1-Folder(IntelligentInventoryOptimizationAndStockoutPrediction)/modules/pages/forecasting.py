# File: modules/pages/forecasting.py

"""
Demand Forecasting Page
========================
Allows users to predict future product demand based on historical data
and various filters.
"""

# 1. Impor library yang dibutuhkan
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# 2. Impor fungsi dari modul kustom Anda
from modules.activity_logger import log_activity
# Pastikan fungsi render_email_form ada di dalam email_utils.py atau ui_components.py
from modules.email_utils import render_email_form 

# 3. Definisikan fungsi render halaman
def render_page(df: pd.DataFrame):
    """
    Merender seluruh konten untuk halaman Demand Forecasting.
    
    Args:
        df (pd.DataFrame): DataFrame utama yang berisi semua data inventaris.
    """
    
    # Semua logika halaman dimulai dari sini, di dalam fungsi
    st.title("📈 Demand Forecasting")
    st.markdown("Predict future demand and analyze trends")
    
    with st.popover("ℹ️ Tentang Demand Forecasting"):
        st.markdown("""
        **Demand Forecasting** memprediksi permintaan produk di masa depan.
        
        **Manfaat:**
        - Mencegah stockout dengan perencanaan lebih baik
        - Mengurangi overstock dan biaya penyimpanan
        - Optimasi cash flow
        
        **Data Source:**
        - Historical sales data (90 hari)
        - Trend analysis
        - Seasonal patterns
        """)
    
    # ========================================================================
    # FILTER INPUTS
    # ========================================================================
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        search_product = st.text_input(
            "🔍 Search Product", 
            placeholder="Search by code or name..."
        )
    
    with col2:
        product_categories = ['All'] + sorted([c for c in df['product_category'].unique() if c and c != 'OTHER'])
        forecast_category_filter = st.selectbox(
            "Product Group", 
            product_categories,
            key="forecast_product_group_filter"
        )
    
    with col3:
        forecast_days = st.slider("Forecast Days", 7, 90, 30)
    
    with col4:
        abc_class_filter = st.selectbox("ABC Class", ["All", "A", "B", "C"])
    
    # ========================================================================
    # LOGIKA PEMFILTERAN DATA
    # ========================================================================
    
    forecast_df = df.copy()
    if search_product:
        mask = (
            forecast_df['product_code'].str.contains(search_product, case=False, na=False) |
            forecast_df['product_name'].str.contains(search_product, case=False, na=False)
        )
        forecast_df = forecast_df[mask]
    
    if forecast_category_filter != "All":
        forecast_df = forecast_df[forecast_df['product_category'] == forecast_category_filter]
        
    if abc_class_filter != "All":
        forecast_df = forecast_df[forecast_df['ABC_class'] == abc_class_filter]
    
    st.markdown("---")
    
    # ========================================================================
    # VISUALISASI DATA
    # ========================================================================
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 Demand Distribution")
        fig = px.histogram(forecast_df, x='avg_daily_demand', nbins=50, 
                          title="Daily Demand Distribution", 
                          template="plotly_dark")
        fig.update_layout(height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig,  width='stretch')
    
    with col2:
        st.markdown(f"### 📈 Top 10 Products Forecast ({forecast_days} Days)")
        top_products = forecast_df.nlargest(10, 'avg_daily_demand')[['product_code', 'avg_daily_demand']].copy()
        top_products['forecast'] = top_products['avg_daily_demand'] * forecast_days
        
        fig = px.bar(top_products, x='product_code', y='forecast', 
                    title=f"{forecast_days}-Day Forecast (Top 10)", 
                    template="plotly_dark",
                    labels={'product_code': 'Product Code', 'forecast': 'Forecasted Demand'})
        fig.update_layout(height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig,  width='stretch')
    
    st.markdown("---")
    
    # ========================================================================
    # TABEL DETAIL PRODUK
    # ========================================================================
    
    st.markdown(f"### Top Products by Demand (Forecast for {forecast_days} days)")
    
    top_df = forecast_df.nlargest(15, 'avg_daily_demand')[
        ['product_code', 'product_name', 'avg_daily_demand', 'ABC_class', 'segment_label', 'current_stock_qty', 'product_category']
    ].copy()
    
    top_df['forecast_demand'] = top_df['avg_daily_demand'] * forecast_days
    top_df['stock_coverage_days'] = top_df['current_stock_qty'] / (top_df['avg_daily_demand'] + 0.01)
    
    st.dataframe(
        top_df,
         width='stretch',
        height=400,
        column_config={
            "product_code": "Code",
            "product_name": st.column_config.TextColumn("Product Name", width="large"),
            "avg_daily_demand": st.column_config.NumberColumn("Daily Demand", format="%.2f"),
            "forecast_demand": st.column_config.NumberColumn(f"{forecast_days}-Day Forecast", format="%.0f"),
            "current_stock_qty": st.column_config.NumberColumn("Current Stock", format="%.0f"),
            "stock_coverage_days": st.column_config.NumberColumn("Coverage (days)", format="%.0f"),
            "ABC_class": "ABC",
            "segment_label": "Segment",
            "product_category": "Group"
        }
    )
    
    # ========================================================================
    # EKSPOR & AKSI
    # ========================================================================
    
    st.markdown("---")
    st.markdown("### 📤 Export & Share Forecast")
    
    col1, col2 = st.columns(2)
    
    with col1:
        csv_data = top_df.to_csv(index=False).encode('utf-8')
        download_button_clicked = st.download_button(
            label="📥 Download Forecast Report",
            data=csv_data,
            file_name=f"demand_forecast_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
             width='stretch',
            key="forecast_download_csv"
        )
        if download_button_clicked:
            log_activity("📥 Downloaded Demand Forecast Report", '#6366f1')
    
    with col2:
        if st.button("📧 Email Forecast",  width='stretch', key="forecast_email_button"):
            # Toggle visibilitas form email
            st.session_state.show_email_forecast = not st.session_state.get('show_email_forecast', False)
    
    # Render form email jika tombol di-klik
    if st.session_state.get('show_email_forecast', False):
        st.markdown("---")
        render_email_form(top_df, "forecast", "demand_forecast")