# File: modules/pages/health.py

"""
Inventory Health Page
======================
Provides a detailed analysis of inventory health, including key metrics,
visualizations, and category-based filtering.
"""

# 1. Impor library yang dibutuhkan
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# 2. Impor fungsi dari modul kustom Anda
from modules.activity_logger import log_activity
from modules.email_utils import render_email_form

# 3. Definisikan fungsi render halaman
def render_page(df: pd.DataFrame):
    """
    Merender seluruh konten untuk halaman Inventory Health.
    
    Args:
        df (pd.DataFrame): DataFrame utama yang berisi semua data inventaris.
    """
    
    # Preprocess data - fill NaN values
    df = df.copy()
    df['avg_daily_demand'] = pd.to_numeric(df['avg_daily_demand'], errors='coerce').fillna(0.01)
    df['current_stock_qty'] = pd.to_numeric(df['current_stock_qty'], errors='coerce').fillna(0)
    df['turnover_ratio_90d'] = pd.to_numeric(df['turnover_ratio_90d'], errors='coerce').fillna(1.0)
    
    # Semua logika halaman dimulai dari sini, di dalam fungsi
    st.title("📊 Inventory Health")
    st.markdown("Monitor inventory status and health indicators")
    
    with st.popover("ℹ️ Panduan Inventory Health"):
        st.markdown("""
        **Inventory Health Monitor** menampilkan kesehatan inventory secara real-time.
        
        **Metrik Utama:**
        - **Overall Health**: Skor kesehatan inventaris (0-100%)
        - **Stock Coverage**: Berapa hari stok dapat bertahan
        - **Turnover Rate**: Kecepatan perputaran inventaris
        
        **Status:**
        - 80-100%: Excellent ✅
        - 60-80%: Good 
        - 40-60%: Fair ⚠️
        - <40%: Poor 🔴
        """)
    
    # ========================================================================
    # METRIK UTAMA
    # ========================================================================
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        service_level = (df['current_stock_qty'] > 0).sum() / len(df) * 100
        health_score = service_level * 0.9  # Perhitungan sederhana
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Overall Health</div>
            <div class="metric-value">{health_score:.0f}%</div>
            <div class="metric-delta positive">✓ Good</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        avg_coverage = (df['current_stock_qty'] / (df['avg_daily_demand'] + 0.01)).mean()
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Stock Coverage</div>
            <div class="metric-value">{avg_coverage:.0f}</div>
            <div class="metric-delta positive">Days</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        # Calculate turnover more accurately
        if 'turnover_ratio_90d' in df.columns:
            # Use individual turnover values, cap at 12x for realism
            df_for_turnover = df[df['turnover_ratio_90d'].notna() & (df['turnover_ratio_90d'] < 100)]
            avg_turnover = df_for_turnover['turnover_ratio_90d'].mean() if len(df_for_turnover) > 0 else 1.0
            # Convert 90-day to annual
            annualized_turnover = min(avg_turnover * (365 / 90), 12.0)  # Cap at 12x
        else:
            # Fallback calculation
            if 'total_sales_90d' in df.columns and 'stock_value' in df.columns:
                total_sales = df['total_sales_90d'].sum()
                total_stock = df['stock_value'].sum()
                annualized_turnover = min((total_sales / total_stock * (365/90)) if total_stock > 0 else 0, 12.0)
            else:
                annualized_turnover = 2.0  # Default
        
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Turnover Rate (Annual)</div>
            <div class="metric-value">{annualized_turnover:.1f}x</div>
            <div class="metric-delta positive">Avg across products</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ========================================================================
    # ANALISIS VISUAL: STOCK VS DEMAND
    # ========================================================================
    
    st.markdown("### 📈 Stock Level vs Daily Demand Analysis")
    
    # Ambil sampel produk teratas untuk visualisasi agar tidak terlalu padat
    sample_df = df.nlargest(100, 'avg_daily_demand')
    
    fig = px.scatter(sample_df, 
                    x='current_stock_qty', 
                    y='avg_daily_demand', 
                    color='ABC_class',
                    size='stock_value',
                    hover_data=['product_code', 'product_name'],
                    title="Stock vs Demand for Top 100 Products by Demand",
                    template="plotly_dark",
                    color_discrete_map={'A': '#10b981', 'B': '#f59e0b', 'C': '#ef4444'})
    
    fig.update_layout(
        height=500, 
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis_title="Current Stock Quantity (Units)",
        yaxis_title="Average Daily Demand (Units)"
    )
    st.plotly_chart(fig, width='stretch')
    
    st.markdown("---")
    
    # ========================================================================
    # KATEGORI KESEHATAN INVENTARIS
    # ========================================================================
    
    st.markdown("### 🏥 Health Categories")
    
    # Fungsi helper untuk mengklasifikasikan kesehatan produk
    def classify_health(row):
        if row['current_stock_qty'] == 0:
            return 'Out of Stock'
        coverage = row['current_stock_qty'] / (row['avg_daily_demand'] + 0.01)
        if coverage < 7:
            return 'Critical'
        elif coverage < 30:
            return 'Warning'
        elif coverage < 90:
            return 'Healthy'
        else:
            return 'Overstock'
    
    # Buat salinan untuk menghindari modifikasi DataFrame asli secara langsung di dalam modul
    df_health = df.copy()
    df_health['health_status'] = df_health.apply(classify_health, axis=1)
    
    health_counts = df_health['health_status'].value_counts()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        count = health_counts.get('Critical', 0)
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid #ef4444;">
            <div class="metric-label">🔴 Critical</div>
            <div class="metric-value">{count}</div>
            <div style="color: #94a3b8; font-size: 0.8rem;">&lt; 7 days stock</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        count = health_counts.get('Warning', 0)
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid #f59e0b;">
            <div class="metric-label">🟡 Warning</div>
            <div class="metric-value">{count}</div>
            <div style="color: #94a3b8; font-size: 0.8rem;">7-30 days stock</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        count = health_counts.get('Healthy', 0)
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid #10b981;">
            <div class="metric-label">🟢 Healthy</div>
            <div class="metric-value">{count}</div>
            <div style="color: #94a3b8; font-size: 0.8rem;">30-90 days stock</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        count = health_counts.get('Overstock', 0)
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid #6366f1;">
            <div class="metric-label">🔵 Overstock</div>
            <div class="metric-value">{count}</div>
            <div style="color: #94a3b8; font-size: 0.8rem;">&gt; 90 days stock</div>
        </div>
        """, unsafe_allow_html=True)
    
    # ========================================================================
    # TABEL DETAIL PRODUK DENGAN FILTER
    # ========================================================================

    selected_health = st.selectbox(
        "Filter by Health Status", 
        ["All", "Critical", "Warning", "Healthy", "Overstock", "Out of Stock"]
    )
    
    if selected_health != "All":
        filtered_df = df_health[df_health['health_status'] == selected_health]
    else:
        filtered_df = df_health
    
    st.markdown(f"**Menampilkan {len(filtered_df):,} produk**")
    
    display_cols = ['product_code', 'product_name', 'current_stock_qty', 'avg_daily_demand', 
                    'turnover_ratio_90d', 'health_status', 'ABC_class']
    
    st.dataframe(
        filtered_df[display_cols].head(50), # Tampilkan hingga 50 baris
        width='stretch',
        height=400,
        column_config={
            "product_code": "Code",
            "product_name": "Product Name",
            "current_stock_qty": st.column_config.NumberColumn("Stock", format="%d"),
            "avg_daily_demand": st.column_config.NumberColumn("Daily Demand", format="%.2f"),
            "turnover_ratio_90d": st.column_config.NumberColumn("Turnover (90d)", format="%.2fx"),
            "health_status": "Health Status",
            "ABC_class": "ABC"
        }
    )

    # ========================================================================
    # EKSPOR & AKSI
    # ========================================================================
    
    st.markdown("---")
    st.markdown("### 📤 Export & Share Health Report")
    
    col1, col2 = st.columns(2)
    
    with col1:
        csv_data = filtered_df.to_csv(index=False).encode('utf-8')
        download_clicked = st.download_button(
            label="📥 Download Health Report",
            data=csv_data,
            file_name=f"inventory_health_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            width='stretch',
            key="inventory_health_csv"
        )
        if download_clicked:
            log_activity("📥 Downloaded Inventory Health Report", '#6366f1')
    
    with col2:
        if st.button("📧 Email Health Report", width='stretch', key="inventory_health_email_button"):
            st.session_state.show_email_health = not st.session_state.get('show_email_health', False)
    
    if st.session_state.get('show_email_health', False):
        st.markdown("---")
        render_email_form(filtered_df, "health", "inventory_health")