# File: modules/pages/slow_moving.py

"""
Slow-Moving Analysis Page
=========================
Identifies slow-moving products and provides metrics and recommended actions.
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
    Merender seluruh konten untuk halaman Slow-Moving Analysis.
    
    Args:
        df (pd.DataFrame): DataFrame utama yang berisi semua data inventaris.
    """
    
    st.title("📋 Slow-Moving Stock Identification")
    st.markdown("Identify and manage slow-moving products")
    
    with st.popover("ℹ️ Tentang Slow-Moving Analysis"):
        st.markdown("""
        **Slow-Moving Analysis** mengidentifikasi produk dengan pergerakan lambat yang mengikat modal dan meningkatkan biaya penyimpanan.
        
        **Kriteria Umum:**
        - **Turnover Ratio**: Rendah (misal, < 1.0x per 90 hari)
        - **Stock Age**: Tinggi (misal, > 60 hari)
        - **Daily Demand**: Rendah
        
        **Tindakan yang Disarankan:**
        - Promosi atau diskon
        - Bundling dengan produk fast-moving
        - Pertimbangkan untuk menghentikan pemesanan ulang
        """)
    
    # ========================================================================
    # PERSIAPAN DATA & METRIK UTAMA
    # ========================================================================
    
    # Asumsikan kolom 'segment_label' sudah ada dari data_loader.py
    # Jika tidak, Anda bisa mendefinisikannya di sini:
    # df['segment_label'] = np.where(df['turnover_ratio_90d'] < 1.0, 'Slow_Movers', 'Normal')
    slow_movers = df[df['segment_label'] == 'Slow_Movers'].copy()
    
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
        avg_turnover_slow = slow_movers['turnover_ratio_90d'].mean()
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Avg Turnover (90d)</div>
            <div class="metric-value">{avg_turnover_slow:.2f}x</div>
            <div class="metric-delta negative">Low</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        tied_capital = slow_movers['stock_value'].sum()
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Tied-Up Capital</div>
            <div class="metric-value">Rp {tied_capital/1_000_000:.1f}M</div>
            <div class="metric-delta negative">High</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-label">Optimization Potential</div>
            <div class="metric-value">~25%</div>
            <div class="metric-delta positive">Capital Recovery</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ========================================================================
    # VISUALISASI DATA
    # ========================================================================
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 Demand Distribution (Slow Movers)")
        fig = px.histogram(slow_movers, x='avg_daily_demand', nbins=30, 
                          title="Distribution of Daily Demand for Slow Movers", 
                          template="plotly_dark")
        fig.update_layout(height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, width='stretch')
    
    with col2:
        st.markdown("### 📈 Stock vs Turnover (Slow Movers)")
        fig = px.scatter(slow_movers.head(100), # Visualisasikan 100 sampel
                        x='current_stock_qty', 
                        y='turnover_ratio_90d',
                        size='stock_value',
                        color='ABC_class',
                        hover_data=['product_code'],
                        title="Stock Quantity vs. Turnover Ratio", 
                        template="plotly_dark",
                        color_discrete_map={'A': '#10b981', 'B': '#f59e0b', 'C': '#ef4444'})
        fig.update_layout(height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, width='stretch')
    
    st.markdown("---")
    
    # ========================================================================
    # TABEL DETAIL PRODUK DENGAN FILTER
    # ========================================================================
    
    st.markdown("### 📋 Slow-Moving Products List")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        abc_slow_filter = st.selectbox("Filter by ABC Class", ["All", "A", "B", "C"], key="slow_abc")
    with col2:
        max_turnover = st.number_input("Max Turnover (90d)", min_value=0.0, max_value=2.0, value=1.0, step=0.1)
    with col3:
        sort_slow = st.selectbox("Sort By", ["Stock Value", "Turnover", "Current Stock"])
    
    # Terapkan filter
    slow_filtered = slow_movers.copy()
    if abc_slow_filter != "All":
        slow_filtered = slow_filtered[slow_filtered['ABC_class'] == abc_slow_filter]
    slow_filtered = slow_filtered[slow_filtered['turnover_ratio_90d'] <= max_turnover]
    
    # Terapkan pengurutan
    sort_slow_map = {
        "Stock Value": "stock_value",
        "Turnover": "turnover_ratio_90d",
        "Current Stock": "current_stock_qty"
    }
    ascending_sort = sort_slow == "Turnover" # Urutkan turnover dari terendah
    slow_filtered = slow_filtered.sort_values(by=sort_slow_map[sort_slow], ascending=ascending_sort)
    
    st.markdown(f"**Menemukan {len(slow_filtered):,} produk slow-moving berdasarkan filter Anda**")
    
    display_cols = ['product_code', 'product_name', 'current_stock_qty', 'avg_daily_demand', 'turnover_ratio_90d', 'stock_value', 'ABC_class']
    st.dataframe(
        slow_filtered[display_cols].head(50),
        width='stretch',
        height=400,
        column_config={
            "product_code": "Code",
            "product_name": "Product Name",
            "current_stock_qty": st.column_config.NumberColumn("Stock", format="%d"),
            "avg_daily_demand": st.column_config.NumberColumn("Daily Demand", format="%.2f"),
            "turnover_ratio_90d": st.column_config.NumberColumn("Turnover (90d)", format="%.2fx"),
            "stock_value": st.column_config.NumberColumn("Value", format="Rp %d"),
            "ABC_class": "ABC"
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
            <p>Untuk produk dengan nilai stok tinggi dan perputaran sangat rendah.</p>
            <ul>
                <li>Clearance sale (30-50% off)</li>
                <li>Bundle dengan produk fast-moving</li>
                <li>Hentikan pemesanan ulang (Stop future orders)</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="insight-card" style="border-left: 4px solid #f59e0b;">
            <h4 style="color: #f59e0b; margin-top: 0;">🟡 Medium Priority</h4>
            <p>Untuk produk dengan pergerakan lambat namun masih ada permintaan.</p>
            <ul>
                <li>Kampanye promosi</li>
                <li>Strategi cross-selling</li>
                <li>Tinjau ulang harga (Review pricing)</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="insight-card" style="border-left: 4px solid #6366f1;">
            <h4 style="color: #6366f1; margin-top: 0;">🔵 Monitoring</h4>
            <p>Untuk produk di ambang batas slow-moving.</p>
            <ul>
                <li>Lacak tren permintaan</li>
                <li>Pantau harga kompetitor</li>
                <li>Sesuaikan kuantitas pesanan berikutnya</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # ========================================================================
    # EKSPOR & AKSI
    # ========================================================================
    
    st.markdown("---")
    st.markdown("### 📤 Export & Share Slow-Moving Report")
    
    col1, col2 = st.columns(2)
    with col1:
        csv_data = slow_filtered.to_csv(index=False).encode('utf-8')
        if st.download_button(
            label="📥 Download Slow-Moving Report",
            data=csv_data,
            file_name=f"slow_moving_analysis_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            width='stretch',
            key="slow_moving_download"
        ):
            log_activity("📥 Downloaded Slow-Moving Analysis Report", '#f59e0b')
    with col2:
        if st.button("📧 Email Report", width='stretch', key="slow_moving_email"):
            st.session_state.show_email_slow = not st.session_state.get('show_email_slow', False)
    
    if st.session_state.get('show_email_slow', False):
        render_email_form(slow_filtered, "slow_moving", "slow_moving_analysis")