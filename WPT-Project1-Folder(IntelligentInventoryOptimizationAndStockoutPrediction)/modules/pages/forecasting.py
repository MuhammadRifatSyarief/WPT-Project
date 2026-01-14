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
        product_categories = ['All'] + sorted([c for c in df['product_category'].unique() 
                                               if c and c not in ['OTHER', 'NUMERIC_CODE']])
        forecast_category_filter = st.selectbox(
            "Product Group", 
            product_categories,
            key="forecast_product_group_filter"
        )
    
    with col3:
        forecast_days = st.slider("Forecast Days", 7, 30, 14)  # Changed: max 30 days for realistic short-term forecasting
    
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
        # Use forecast_30d if available, otherwise fallback to avg_daily_demand
        demand_col = 'forecast_30d' if 'forecast_30d' in forecast_df.columns else 'avg_daily_demand'
        valid_demand_df = forecast_df[forecast_df[demand_col].notna() & (forecast_df[demand_col] > 0)]
        
        fig = px.histogram(valid_demand_df, x=demand_col, nbins=50, 
                          title=f"Daily Demand Distribution (from {demand_col})", 
                          template="plotly_dark")
        fig.update_layout(height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig,  width='stretch')
        
        # Show stats
        if not valid_demand_df.empty:
            st.caption(f"Max: {valid_demand_df[demand_col].max():.2f} | Mean: {valid_demand_df[demand_col].mean():.2f} units/day")
    
    with col2:
        # 🎯 NEW: Add slider to control number of top products shown
        top_n_products = st.slider("Top N Products", 5, 50, 10, key="forecast_top_n")
        st.markdown(f"### 📈 Top {top_n_products} Products Forecast ({forecast_days} Days)")
        
        # Use forecast_30d if available (from demand forecasting module)
        if 'forecast_30d' in forecast_df.columns:
            # Use the bounded forecast from the module
            valid_df = forecast_df[forecast_df['forecast_30d'].notna()].copy()
            top_products = valid_df.nlargest(top_n_products, 'forecast_30d')[['product_code', 'forecast_30d', 'forecast_model']].copy()
            top_products['forecast'] = top_products['forecast_30d'] * forecast_days
            chart_title = f"{forecast_days}-Day Forecast (from Prophet/Statistical Model)"
        else:
            # Fallback to avg_daily_demand
            top_products = forecast_df.nlargest(top_n_products, 'avg_daily_demand')[['product_code', 'avg_daily_demand']].copy()
            top_products['forecast'] = top_products['avg_daily_demand'] * forecast_days
            chart_title = f"{forecast_days}-Day Forecast (from Historical Average)"
        
        fig = px.bar(top_products, x='product_code', y='forecast', 
                    title=chart_title, 
                    template="plotly_dark",
                    labels={'product_code': 'Product Code', 'forecast': 'Forecasted Demand'})
        fig.update_layout(height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig,  width='stretch')
    
    st.markdown("---")
    
    # ========================================================================
    # TABEL DETAIL PRODUK
    # ========================================================================
    
    st.markdown(f"### Top Products by Forecast (for {forecast_days} days)")
    
    # Use forecast_30d if available from the demand forecasting module
    if 'forecast_30d' in forecast_df.columns:
        valid_df = forecast_df[forecast_df['forecast_30d'].notna()].copy()
        
        # Define columns to include
        base_cols = ['product_code', 'product_name', 'forecast_30d', 'ABC_class', 'current_stock_qty', 'product_category']
        if 'forecast_model' in valid_df.columns:
            base_cols.insert(3, 'forecast_model')
        
        available_cols = [c for c in base_cols if c in valid_df.columns]
        top_df = valid_df.nlargest(15, 'forecast_30d')[available_cols].copy()
        
        top_df['forecast_demand'] = top_df['forecast_30d'] * forecast_days
        top_df['stock_coverage_days'] = top_df['current_stock_qty'] / (top_df['forecast_30d'] + 0.01)
        demand_col_name = "Forecast/Day"
    else:
        # Fallback to avg_daily_demand
        top_df = forecast_df.nlargest(15, 'avg_daily_demand')[
            ['product_code', 'product_name', 'avg_daily_demand', 'ABC_class', 'current_stock_qty', 'product_category']
        ].copy()
        
        top_df['forecast_demand'] = top_df['avg_daily_demand'] * forecast_days
        top_df['stock_coverage_days'] = top_df['current_stock_qty'] / (top_df['avg_daily_demand'] + 0.01)
        top_df['forecast_30d'] = top_df['avg_daily_demand']  # Alias for display
        demand_col_name = "Daily Demand"
    
    st.dataframe(
        top_df,
         width='stretch',
        height=400,
        column_config={
            "product_code": "Code",
            "product_name": st.column_config.TextColumn("Product Name", width="large"),
            "forecast_30d": st.column_config.NumberColumn(demand_col_name, format="%.2f"),
            "forecast_model": "Model",
            "forecast_demand": st.column_config.NumberColumn(f"{forecast_days}-Day Forecast", format="%.0f"),
            "current_stock_qty": st.column_config.NumberColumn("Current Stock", format="%.0f"),
            "stock_coverage_days": st.column_config.NumberColumn("Coverage (days)", format="%.0f"),
            "ABC_class": "ABC",
            "product_category": "Group"
        }
    )
    
    # ========================================================================
    # ABC & SEGMENT CLASSIFICATION LEGENDS (NEW)
    # ========================================================================
    st.markdown("---")
    st.markdown("### 📖 Keterangan Klasifikasi")
    
    with st.expander("📊 Penjelasan ABC Class", expanded=False):
        st.markdown("""
        | Class | Kontribusi Revenue | Prioritas | Aksi |
        |-------|-------------------|-----------|------|
        | **A** | ~80% total | Tinggi | Monitoring ketat, stock optimal |
        | **B** | ~15% total | Sedang | Monitoring reguler |
        | **C** | ~5% total | Rendah | Review kebutuhan |
        """)
    
    with st.expander("🔤 Penjelasan Segment (ABC-XYZ)", expanded=False):
        st.markdown("""
        | Segment | Artinya | Rekomendasi |
        |---------|---------|-------------|
        | **AX, BX** | Revenue tinggi/sedang, demand stabil | Fokus utama, forecast akurat |
        | **AY, BY** | Revenue tinggi/sedang, demand fluktuatif | Butuh safety stock lebih |
        | **AZ, BZ** | Revenue tinggi/sedang, demand tidak stabil | Perlu monitoring intensif |
        | **CX, CY, CZ** | Revenue rendah | Evaluasi untuk discontinue |
        """)
    
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