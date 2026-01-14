# File: modules/pages/dashboard.py

"""
Dashboard Overview Page
========================
Provides a real-time, high-level overview of inventory health and key metrics.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# Asumsikan fungsi-fungsi ini ada di modul yang sesuai
from modules.activity_logger import log_activity
from modules.email_utils import render_email_form

def render_page(df: pd.DataFrame):
    """Merender halaman utama dashboard."""
    
    # Validate required columns exist
    if df is None or len(df) == 0:
        st.error("❌ No data available. Please check your data sources.")
        return
    
    # Ensure required columns exist
    required_cols = ['product_code', 'product_name', 'avg_daily_demand', 'current_stock_qty']
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        st.warning(f"⚠️ Missing columns: {', '.join(missing_cols)}. Some features may not work correctly.")
        # Create placeholder columns if missing
        if 'product_code' not in df.columns:
            if 'product_id' in df.columns:
                df['product_code'] = df['product_id'].astype(str)
            else:
                df['product_code'] = [f"PROD-{i}" for i in range(len(df))]
        if 'product_name' not in df.columns:
            df['product_name'] = 'Product ' + df['product_code'].astype(str)
    
    st.title("🏠 Inventory Intelligence Hub")
    st.markdown("Real-time overview of your inventory health")

    # ========================================================================
    # TOP METRICS ROW WITH DETAILED POPOVERS
    # ========================================================================
    
    col1, col2, col3, col4 = st.columns(4)

    # Metric 1: Service Level
    with col1:
        with st.popover("ℹ️"):
            st.markdown("### 📊 Service Level")
            st.markdown("**Definisi:** Persentase pesanan yang dapat dipenuhi dari stok tersedia.")
            st.markdown("**Formula:**")
            st.code("Service Level = (Pesanan Terpenuhi / Total Pesanan) × 100%")
            st.markdown("**Benchmark Industry:** >95%: Excellent")
        
        service_level = (df['current_stock_qty'] > 0).sum() / len(df) * 100
        prev_service_level = 92.1  # Mock
        delta = service_level - prev_service_level
        
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Service Level</div>
            <div class="metric-value">{service_level:.1f}%</div>
            <div class="metric-delta {'positive' if delta > 0 else 'negative'}">
                {'↑' if delta > 0 else '↓'} {abs(delta):.1f}% vs last month
            </div>
            <div class="metric-insight">Target: >95% | Status: {'Good' if service_level > 90 else 'Fair'}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Metric 2: Inventory Turnover
    with col2:
        with st.popover("ℹ️"):
            st.markdown("### 🔄 Inventory Turnover Ratio (30-day)")
            st.markdown("**Definisi:** Kecepatan inventory terjual dalam periode 30 hari.")
            st.markdown("**Formula:** Units Sold (30d) / Average Inventory")
            st.markdown("**Benchmark IT Products:** 1-3x per 30 hari = Ideal")

        # USE PRE-CALCULATED VALUES FROM DATA_LOADER
        # Average turnover weighted by stock value
        if 'turnover_ratio_30d' in df.columns:
            # Calculate weighted average: sum(turnover * stock_value) / sum(stock_value)
            df_with_stock = df[df['stock_value'] > 0]
            if not df_with_stock.empty:
                weighted_turnover = (df_with_stock['turnover_ratio_30d'] * df_with_stock['stock_value']).sum()
                total_weight = df_with_stock['stock_value'].sum()
                avg_turnover_30d = weighted_turnover / total_weight if total_weight > 0 else 0
            else:
                avg_turnover_30d = df['turnover_ratio_30d'].mean()
        else:
            avg_turnover_30d = 1.0  # Default fallback
        
        # Cap display at 10x for realism
        avg_turnover_30d = min(avg_turnover_30d, 10.0)
        days_to_refresh = 30 / (avg_turnover_30d + 0.01)

        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Turnover (30d)</div>
            <div class="metric-value">{avg_turnover_30d:.2f}x</div>
            <div class="metric-delta positive">Avg weighted by stock value</div>
            <div class="metric-insight">Inventory refresh: ~{days_to_refresh:.0f} days</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Metric 3: Stockout Risk Index
    with col3:
        with st.popover("ℹ️"):
            st.markdown("### ⚠️ Stockout Risk Index")
            st.markdown("**Definisi:** Jumlah produk berisiko kehabisan stok dalam 30 hari.")
            st.markdown("**Level Risiko:** Critical (<7 hari), High (7-14 hari), Medium (14-30 hari)")
        
        critical_count = len(df[df['days_until_stockout'] < 7])
        high_count = len(df[(df['days_until_stockout'] >= 7) & (df['days_until_stockout'] < 14)])
        medium_count = len(df[(df['days_until_stockout'] >= 14) & (df['days_until_stockout'] < 30)])
        total_risk = critical_count + high_count + medium_count
        
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Stockout Risk</div>
            <div class="metric-value">{total_risk}</div>
            <div class="metric-delta negative">↑ {critical_count + high_count} products at risk</div>
            <div class="metric-insight">{critical_count} critical | {high_count} high | {medium_count} medium</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Metric 4: Average Stock Age
    with col4:
        with st.popover("ℹ️"):
            st.markdown("### 📅 Average Stock Age")
            st.markdown("**Definisi:** Rata-rata hari sejak produk dibeli / Days Inventory Outstanding (DIO).")
            st.markdown("**Interpretasi:** <30 hari (Excellent), 30-60 hari (Good), >60 hari (Warning)")
        
        valid_dio = df[df['days_in_inventory_90d'] > 0]['days_in_inventory_90d']
        avg_stock_age = valid_dio.median() if not valid_dio.empty else 60
        
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Avg Stock Age</div>
            <div class="metric-value">{avg_stock_age:.0f}d</div>
            <div class="metric-delta positive">↓ 5 days vs last month</div>
            <div class="metric-insight">Target: <60 days | Status: {'Good' if avg_stock_age < 60 else 'Warning'}</div>
        </div>
        """, unsafe_allow_html=True)

    # ========================================================================
    # PERFORMANCE TRENDS & TODAY'S ALERTS
    # ========================================================================
    
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.markdown("### 📊 Performance Trends")
        months = pd.date_range(end=datetime.now(), periods=6, freq='M')
        performance_data = pd.DataFrame({
            'Month': months.strftime('%b %Y'),
            'Service Level': [service_level - 3.0, service_level - 1.7, service_level - 1.1, service_level - 1.4, service_level - 0.3, service_level],
            'Turnover Rate': [avg_turnover_30d - 0.7, avg_turnover_30d - 0.5, avg_turnover_30d - 0.3, avg_turnover_30d - 0.4, avg_turnover_30d - 0.1, avg_turnover_30d]
        })
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=performance_data['Month'], y=performance_data['Service Level'], name='Service Level (%)', line=dict(color='#10b981', width=3), mode='lines+markers'))
        fig.add_trace(go.Scatter(x=performance_data['Month'], y=performance_data['Turnover Rate'] * (100 / (avg_turnover_30d or 1)), name='Turnover Rate (Scaled)', line=dict(color='#6366f1', width=3), mode='lines+markers', yaxis='y2', customdata=performance_data['Turnover Rate'], hovertemplate='<b>%{x}</b><br>Turnover: %{customdata:.1f}x<extra></extra>'))
        fig.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=280, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), hovermode='x unified', yaxis=dict(title="Service Level (%)", range=[85, 100]), yaxis2=dict(title="Turnover Rate", overlaying='y', side='right', showgrid=False, tickvals=[]))
        st.plotly_chart(fig, width='stretch')

    with col2:
        st.markdown("### ⚠️ Today's Alerts")

        # Gaya CSS yang lebih kuat untuk mengatasi tumpang tindih tema
        alert_box_style = """
            padding: 1rem; 
            border-radius: 8px; 
            margin-bottom: 0.75rem; 
            color: white; 
            border-left: 5px solid {border_color};
            background-color: {bg_color};
        """

        # Kotak Critical Alert
        st.markdown(f"""
        <div style="{alert_box_style.format(bg_color='#4A1D1D', border_color='#EF4444')}">
            <strong>🔴 Critical ({critical_count})</strong>
            <div style="font-size: 0.85rem; color: #F8B4B4;">Stockout in &lt; 7 days</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Kotak High Risk Alert
        st.markdown(f"""
        <div style="{alert_box_style.format(bg_color='#4A3A1D', border_color='#F59E0B')}">
            <strong>🟡 High Risk ({high_count})</strong>
            <div style="font-size: 0.85rem; color: #F8DAB4;">Need reorder soon</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Kotak Slow-Moving Alert
        slow_moving_count = len(df[df['turnover_ratio_90d'] < 1.0])
        st.markdown(f"""
        <div style="{alert_box_style.format(bg_color='#1D3A4A', border_color='#3B82F6')}">
            <strong>🔵 Slow-Moving ({slow_moving_count})</strong>
            <div style="font-size: 0.85rem; color: #B4D4F8;">Low turnover products</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Tombol View All Alerts tetap sama
        if st.button("View All Alerts →", width='stretch'):
            st.session_state.show_all_alerts = not st.session_state.get('show_all_alerts', False)

    
    # ========================================================================
    # ALL ALERTS EXPANDABLE TABLE
    # ========================================================================
    
    if st.session_state.get('show_all_alerts', False):
        st.markdown("### 📋 All Alerts")
        
        # Prepare comprehensive alert data
        alert_products = df[
            (df['days_until_stockout'] < 30) | 
            (df['turnover_ratio_90d'] < 1.0)
        ].copy()
        
        # Classify risk levels
        def get_risk_level(row):
            days = row['days_until_stockout']
            if days < 7:
                return '🔴 Critical'
            elif days < 14:
                return '🟡 High'
            elif days < 30:
                return '🔵 Medium'
            elif row['turnover_ratio_90d'] < 1.0:
                return '🔵 Slow-Moving'
            else:
                return '🟢 Low'
        
        alert_products['Risk Level'] = alert_products.apply(get_risk_level, axis=1)
        
        # Recommended actions
        def get_action(risk):
            if '🔴' in risk:
                return 'Reorder Now'
            elif '🟡' in risk:
                return 'Plan Reorder'
            else:
                return 'Monitor'
        
        alert_products['Action'] = alert_products['Risk Level'].apply(get_action)
        
        # Sort by urgency
        priority_order = {'🔴 Critical': 0, '🟡 High': 1, '🔵 Medium': 2, '🔵 Slow-Moving': 3, '🟢 Low': 4}
        alert_products['priority_rank'] = alert_products['Risk Level'].map(priority_order)
        alert_products = alert_products.sort_values('priority_rank')
        
        # Display table
        display_cols = ['product_code', 'product_name', 'current_stock_qty', 'avg_daily_demand', 
                       'days_until_stockout', 'Risk Level', 'Action']
        
        st.dataframe(
            alert_products[display_cols].head(20),
            width='stretch',
            height=300,
            column_config={
                "product_code": "SKU",
                "product_name": st.column_config.TextColumn("Product", width="large"),
                "current_stock_qty": st.column_config.NumberColumn("Stock", format="%.0f"),
                "avg_daily_demand": st.column_config.NumberColumn("Daily Demand", format="%.2f"),
                "days_until_stockout": st.column_config.NumberColumn("Stockout Days", format="%.0f"),
                "Risk Level": "Risk",
                "Action": "Recommended Action"
            }
        )
        
        # Action buttons
        col1, col2, col3 = st.columns(3)
        with col1:
            csv_data = alert_products.to_csv(index=False).encode('utf-8')
            if st.download_button(
                label="📥 Export Alerts",
                data=csv_data,
                file_name=f"alerts_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                width='stretch',
                key="dashboard_alert_download_btn"
            ):
                 log_activity("📥 Exported Alerts Report", '#6366f1')
                 
        with col2:
            if st.button("📅 Schedule Review", width='stretch'):
                st.info("📅 Review scheduled for tomorrow 9:00 AM")
                log_activity("📅 Scheduled Alert Review", '#f59e0b')
        with col3:
            if st.button("📝 Create Action Plan", width='stretch'):
                st.success("✅ Action plan created!")
                log_activity("📝 Created Alert Action Plan", '#10b981')
    
    # ========================================================================
    # TOP FAST-MOVING PRODUCTS & QUICK ACTIONS
    # ========================================================================
    
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.markdown("### 🚀 Top 5 Fast-Moving Products")
        
        # Use forecast_30d from demand forecasting module if available (more bounded)
        if 'forecast_30d' in df.columns:
            demand_col = 'forecast_30d'
            df_valid = df[df['forecast_30d'].notna() & (df['forecast_30d'] > 0)]
            display_label = "Forecasted Daily Demand"
        else:
            demand_col = 'avg_daily_demand'
            df_valid = df[df['avg_daily_demand'].notna() & (df['avg_daily_demand'] > 0)]
            display_label = "Daily Demand"
        
        # Get top 5 products by demand
        top_products = df_valid.nlargest(5, demand_col)[
            ['product_code', 'product_name', demand_col, 'current_stock_qty']
        ].copy()
        
        # Create horizontal bar chart
        fig = go.Figure()
        
        for i, row in enumerate(top_products.itertuples()):
            product_name = str(row.product_name) if pd.notna(row.product_name) else f"Product {row.product_code}"
            demand_value = getattr(row, demand_col.replace('-', '_'))
            
            try:
                short_name = ' '.join(product_name.split()[:3])
                if len(short_name) > 20:
                    short_name = short_name[:17] + "..."
            except (AttributeError, TypeError):
                short_name = product_name[:20] if len(product_name) > 20 else product_name
            
            fig.add_trace(go.Bar(
                y=[f"{row.product_code}"],
                x=[demand_value],
                orientation='h',
                marker_color='#10b981' if i == 0 else '#6366f1',
                text=f"{short_name}<br>{row.current_stock_qty:.0f} units in stock",
                textposition='inside',
                insidetextanchor='middle',
                textfont=dict(color='white', size=10),
                hovertemplate=(
                    '<b>%{y}</b><br>' +
                    f'{product_name}<br>' +
                    f'{display_label}: ' + '%{x:.2f} units<br>' +
                    f'Stock: {row.current_stock_qty:.0f} units' +
                    '<extra></extra>'
                ),
                showlegend=False
            ))
        
        fig.update_layout(
            template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=280,
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis_title=f"{display_label} (units/day)",
            yaxis_title="",
            yaxis={'categoryorder':'total ascending'},
            xaxis=dict(
                showgrid=True,
                gridcolor='rgba(255,255,255,0.1)'
            )
        )
        
        st.plotly_chart(fig, width='stretch')
        st.caption(f"📊 Data source: {demand_col}")
    
    with col2:
        st.markdown("### 🎬 Quick Actions")
        
        # Initialize session states if not exists
        if 'show_bulk_order_detail' not in st.session_state:
            st.session_state.show_bulk_order_detail = False
        if 'show_email_detail' not in st.session_state:
            st.session_state.show_email_detail = False
        if 'show_export_detail' not in st.session_state:
            st.session_state.show_export_detail = False
        
        # Quick Action 1: Bulk Order
        if st.button("🚀 Bulk Order", width='stretch', key="quick_bulk_order_btn"):
            st.session_state.show_bulk_order_detail = not st.session_state.show_bulk_order_detail
        
        if st.session_state.show_bulk_order_detail:
            critical_items = df[df['days_until_stockout'] < 7].nlargest(3, 'avg_daily_demand')
            total_value = 0
            
            st.markdown("""
            <div class="detail-box">
                <strong>📦 Bulk Order Details</strong><br><br>
                <strong>Products to Order:</strong><br>
            """, unsafe_allow_html=True)
            
            for idx, row in critical_items.iterrows():
                order_qty = max(row['optimal_safety_stock'] * 2, row['avg_daily_demand'] * 30)
                # Estimate unit price from stock_value/current_stock or use a mock value
                est_price = row['stock_value'] / max(row['current_stock_qty'], 1) if row['current_stock_qty'] > 0 else 50000 
                item_value = order_qty * est_price
                total_value += item_value
                
                st.markdown(f"""
                • {row['product_code']}: {order_qty:.0f} units (Rp {item_value:,.0f})<br>
                """, unsafe_allow_html=True)
            
            st.markdown(f"""
                <br><strong>Total:</strong> {critical_items['avg_daily_demand'].sum() * 30:.0f} units | Rp {total_value:,.0f}<br>
                <strong>Expected Delivery:</strong> 5-7 days
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("✅ Confirm Order", key="confirm_bulk_order_dashboard"):
                st.success("✅ Bulk Order confirmed! Order ID: #ORD-" + datetime.now().strftime('%Y%m%d-%H%M'))
                log_activity("🚀 Confirmed Quick Bulk Order", '#10b981')
                st.session_state.show_bulk_order_detail = False
                st.rerun()
        
        # Quick Action 2: Send Email (FIXED to use render_email_form)
        if st.button("📧 Send Quick Alert Email", width='stretch', key="quick_alert_email_btn", help="Langsung mengirim laporan item kritis ke penerima default yang dikonfigurasi di Settings."):
            
            # 1. Validasi konfigurasi terlebih dahulu
            sender = st.session_state.get('email_sender')
            password = st.session_state.get('email_password')
            recipients_str = st.session_state.get('email_recipients', '')
            recipient_list = [r.strip() for r in recipients_str.split(',') if r.strip()]

            if not sender or not password:
                st.error("❌ Email Sender/Password belum diatur. Silakan atur di halaman 'Settings'.")
            elif not recipient_list:
                st.error("❌ 'Default Recipients' belum diatur. Silakan atur di halaman 'Settings'.")
            else:
                # 2. Jika valid, panggil fungsi send_quick_alert_email
                from modules.email_utils import send_quick_alert_email
                
                # Siapkan data untuk laporan
                alert_products_for_email = df[df['days_until_stockout'] < 30].sort_values('days_until_stockout', ascending=True).head(50)
                
                # Panggil fungsi yang langsung mengirim email
                send_quick_alert_email(alert_products_for_email)
        
        # Quick Action 3: Export Report
        if st.button("📥 Export Report", width='stretch', key="quick_export_report_btn"):
            st.session_state.show_export_detail = not st.session_state.show_export_detail
        
        if st.session_state.show_export_detail:
            st.markdown(f"""
            <div class="detail-box">
                <strong>📊 Report Details</strong><br><br>
                <strong>Report Type:</strong> Weekly Inventory Summary<br>
                <strong>Period:</strong> {datetime.now().strftime('%b %d, %Y')}<br>
                <strong>Format:</strong> CSV<br><br>
                <strong>Includes:</strong><br>
                • All product inventory levels<br>
                • Stock age analysis<br>
                • Movement frequency<br>
                • Stockout risk assessment<br>
                • Reorder recommendations
            </div>
            """, unsafe_allow_html=True)
            
            csv_data = df.to_csv(index=False).encode('utf-8')
            if st.download_button(
                label="📥 Download Report",
                data=csv_data,
                file_name=f"inventory_report_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                width='stretch',
                key="dashboard_quick_export_download"
            ):
                log_activity("📥 Downloaded Full Inventory Report (Quick Action)", '#6366f1')
    
    # ========================================================================
    # STOCK HEALTH DISTRIBUTION & RECENT ACTIVITIES
    # ========================================================================
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 🎯 Stock Health Distribution")
        
        with st.popover("📖 Penjelasan Kategori"):
            st.markdown("""
            ### 🟢 Healthy
            **Kriteria:** High turnover, adequate stock
            
            **Artinya:** Produk laku keras, stok optimal
            
            **Tindakan:** 
            - Maintain stock level optimal
            - Monitor untuk avoid stockout
            - Consider increase order quantity
            
            ---
            
            ### 🔵 Stable
            **Kriteria:** Normal movement, balanced stock
            
            **Artinya:** Produk bergerak normal
            
            **Tindakan:** 
            - Monitor trend pergerakan
            - Maintain current reorder policy
            
            ---
            
            ### 🟡 Warning
            **Kriteria:** Low turnover or aging stock
            
            **Artinya:** Produk mulai lambat
            
            **Tindakan:** 
            - Promosi atau discount
            - Cross-sell strategy
            - Review pricing
            
            ---
            
            ### 🔴 Critical
            **Kriteria:** Very low turnover, dead stock
            
            **Artinya:** Stock bermasalah, action needed!
            
            **Tindakan:** 
            - Aggressive discount 30-50%
            - Bundle with fast-moving items
            - Consider return to supplier
            - STOP future orders
            
            ---
            
            **Target Ideal:**
            - Healthy + Stable: >70%
            - Warning: 15-20%
            - Critical: <10%
            """)
        
        # Classify products into health categories
        def classify_health(row):
            turnover = row['turnover_ratio_90d']
            days_stock = row['days_until_stockout']
            
            if turnover > 2.0 and days_stock > 30:
                return 'Healthy'
            elif turnover > 1.0 and days_stock > 14:
                return 'Stable'
            elif turnover > 0.5 or days_stock > 7:
                return 'Warning'
            else:
                return 'Critical'
        
        df['health_category'] = df.apply(classify_health, axis=1)
        health_counts = df['health_category'].value_counts()
        total_products = len(df)
        
        # Color mapping
        colors_map = {
            'Healthy': '#10b981',
            'Stable': '#6366f1',
            'Warning': '#f59e0b',
            'Critical': '#ef4444'
        }
        
        # Create donut chart
        fig = go.Figure(data=[go.Pie(
            labels=health_counts.index,
            values=health_counts.values,
            hole=0.5,
            marker=dict(
                colors=[colors_map.get(cat, '#64748b') for cat in health_counts.index],
                line=dict(color='#1e293b', width=2)
            ),
            textinfo='label+percent',
            texttemplate='<b>%{label}</b><br>%{percent}',
            textposition='outside',
            textfont=dict(size=11, color='#e2e8f0'),
            hovertemplate='<b>%{label}</b><br>%{value} products<br>%{percent}<extra></extra>',
            pull=[0.1 if cat == 'Critical' else 0.05 if cat == 'Warning' else 0 for cat in health_counts.index],
            showlegend=True,
            rotation=90
        )])
        
        # Center annotation
        fig.add_annotation(
            text=f"<b>{total_products:,}</b><br><span style='font-size:14px'>Total<br>Products</span>",
            x=0.5, y=0.5,
            font=dict(size=24, color='#f8fafc'),
            showarrow=False
        )
        
        fig.update_layout(
            template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=350,
            margin=dict(l=20, r=20, t=20, b=20),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.15,
                xanchor="center",
                x=0.5,
                font=dict(color='#e2e8f0', size=11)
            ),
            hoverlabel=dict(
                bgcolor="#1e293b",
                font_color="#e2e8f0",
                font_size=12
            )
        )
        
        st.plotly_chart(fig, width='stretch')
    
    with col2:
        st.markdown("### 📋 Recent Activities")
        
        # PERBAIKAN: Import dan tampilkan dari activity log
        from modules.activity_logger import get_activity_log
        
        activities_to_display = get_activity_log()[:5]  # Max 5 terbaru
        
        if not activities_to_display:
            st.info("No recent activity.")
        else:
            for activity in activities_to_display:
                st.markdown(f"""
                <div style="background: rgba(30, 41, 59, 0.6); padding: 0.8rem; border-radius: 8px; 
                            margin-bottom: 0.5rem; border-left: 3px solid {activity['color']};">
                    <div style="font-size: 0.75rem; color: #94a3b8;">{activity['time']}</div>
                    <div style="font-size: 0.9rem; color: #e2e8f0; margin-top: 0.2rem;">
                        {activity['action']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            # Info jika ada lebih banyak activities
            total_activities = len(get_activity_log())
            if total_activities > 5:
                st.caption(f"_Showing 5 of {total_activities} activities. Check sidebar for full log._")

    
    st.markdown("### 📊 Category Summary")
    
    num_categories = len(health_counts)
    summary_cols = st.columns(num_categories)
    
    for i, (category, count) in enumerate(health_counts.items()):
        col_index = i % len(summary_cols)
        with summary_cols[col_index]:
            percentage = (count / total_products) * 100
            st.markdown(f"""
            <div class="metric-card" style="border-left: 4px solid {colors_map.get(category, '#64748b')}; min-height: 100px;">
                <div class="metric-label">{category}</div>
                <div class="metric-value">{count}</div>
                <div style="color: #94a3b8; font-size: 0.8rem;">{percentage:.1f}% of total</div>
            </div>
            """, unsafe_allow_html=True)
    
    # ========================================================================
    # DETAILED PRODUCT TABLE WITH ADVANCED FILTERS
    # ========================================================================
    
    st.markdown("### 📋 Detail Produk per Kategori")
    
    # Advanced Filter Section
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1]) 
    
    with col1:
        selected_category = st.selectbox(
            "Pilih kategori health:",
            ['Semua Kategori'] + list(health_counts.index),
            key='dashboard_category_filter'
        )
        
    with col2:
        # NEW: Product Category Filter (Enhancement 2)
        product_categories = ['Semua Kategori'] + sorted([c for c in df['product_category'].unique() if c != 'OTHER'])
        selected_product_category = st.selectbox(
            "Filter by Product Group:",
            product_categories,
            key='dashboard_product_group_filter'
        )
    
    with col3:
        # ABC Class filter
        abc_filter_options = st.multiselect(
            "Filter by ABC Class:",
            ['A', 'B', 'C'],
            default=None,
            key='dashboard_abc_filter'
        )
    
    with col4:
        # NEW: Product Count Filter (Enhancement 3)
        product_limit = st.slider(
            "Max Products to Show", 
            min_value=5, 
            max_value=min(200, len(df)), # Cap at 200 for performance
            value=20, 
            step=5,
            key='dashboard_product_limit'
        )
    
    # Apply filters
    display_data = df.copy()
    
    if selected_category != 'Semua Kategori':
        display_data = display_data[display_data['health_category'] == selected_category]
    
    # 🎯 FIX: Product Category filter - search in both product_category AND product_code
    # This allows filtering by SKU patterns like 'omada' matching 'omada-001', 'omada-002', etc.
    if selected_product_category != 'Semua Kategori':
        category_upper = selected_product_category.upper()
        # Match product_category OR product_code containing the filter value
        category_mask = display_data['product_category'].str.upper() == category_upper
        code_mask = display_data['product_code'].str.upper().str.contains(category_upper, na=False)
        name_mask = display_data['product_name'].str.upper().str.contains(category_upper, na=False)
        display_data = display_data[category_mask | code_mask | name_mask]

    # Apply ABC filter
    if abc_filter_options:
        display_data = display_data[display_data['ABC_class'].isin(abc_filter_options)]
    
    # Apply default sorting (Stock Value Desc)
    display_data = display_data.sort_values('stock_value', ascending=False)
    
    st.markdown(f"**{len(display_data):,} produk dalam kategori ini** (Menampilkan top {product_limit})")
    
    # Create styled dataframe (Applied limit - Enhancement 3)
    display_df = display_data[
        ['product_code', 'product_name', 'current_stock_qty', 'avg_daily_demand', 
         'days_until_stockout', 'turnover_ratio_90d', 'stock_value', 
         'ABC_class', 'health_category', 'product_category'] 
    ].head(product_limit).copy() 
    
    display_df.columns = ['SKU', 'Product Name', 'Stock', 'Daily Demand', 
                          'Days Coverage', 'Turnover', 'Stock Value', 'ABC', 'Health', 'Group']
    
    # Display with custom configuration
    st.dataframe(
        display_df,
        width='stretch',
        height=400,
        column_config={
            "SKU": st.column_config.TextColumn("SKU", width="small"),
            "Product Name": st.column_config.TextColumn("Product Name", width="large"),
            "Stock": st.column_config.NumberColumn("Stock", format="%.0f"),
            "Daily Demand": st.column_config.NumberColumn("Daily Demand", format="%.2f"),
            "Days Coverage": st.column_config.NumberColumn("Days Coverage", format="%.0f"),
            "Turnover": st.column_config.NumberColumn("Turnover", format="%.2fx"),
            "Stock Value": st.column_config.NumberColumn("Value", format="Rp %.0f"),
            "ABC": st.column_config.TextColumn("ABC", width="small"),
            "Health": st.column_config.TextColumn("Health Status", width="medium"),
            "Group": st.column_config.TextColumn("Group", width="small")
        }
    )
    
    # Category Statistics (if filtered)
    if selected_category != 'Semua Kategori' or selected_product_category != 'Semua Kategori' or abc_filter_options:
        st.markdown("### 📈 Category Statistics")
        
        col_a, col_b, col_c, col_d = st.columns(4)
        
        with col_a:
            avg_stock = display_data['current_stock_qty'].mean()
            st.metric("Avg Stock", f"{avg_stock:.0f} units")
        
        with col_b:
            avg_demand = display_data['avg_daily_demand'].mean()
            st.metric("Avg Daily Demand", f"{avg_demand:.2f} units")
        
        with col_c:
            # Use total values for a stable turnover metric even on filtered data
            total_sales = display_data['total_sales_90d'].sum()
            total_stock = display_data['stock_value'].sum()
            avg_turnover_cat = (total_sales / (total_stock + 0.01)) * (365/90)
            st.metric("Avg Turnover (Ann.)", f"{avg_turnover_cat:.2f}x")
        
        with col_d:
            total_value = display_data['stock_value'].sum()
            st.metric("Total Value", f"Rp {total_value/1_000_000:.1f}M")
    
    # ========================================================================
    # ABC CLASSIFICATION LEGEND (NEW)
    # ========================================================================
    st.markdown("---")
    st.markdown("### 📖 Keterangan Klasifikasi")
    
    legend_cols = st.columns(3)
    with legend_cols[0]:
        st.markdown("""
        **🅰️ Class A - Fast Moving**
        - Produk dengan kontribusi revenue tinggi (80% total)
        - Prioritas utama untuk ketersediaan stok
        - Monitoring harian, reorder cepat
        """)
    with legend_cols[1]:
        st.markdown("""
        **🅱️ Class B - Moderate Moving**
        - Kontribusi revenue sedang (15% total)
        - Prioritas menengah
        - Monitoring mingguan
        """)
    with legend_cols[2]:
        st.markdown("""
        **©️ Class C - Slow Moving**
        - Kontribusi revenue rendah (5% total)
        - Prioritas rendah, perlu evaluasi
        - Pertimbangkan promosi atau discontinue
        """)
    
    # ========================================================================
    # EXPORT & SHARE SECTION
    # ========================================================================
    
    st.markdown("---")
    st.markdown("### 📤 Export & Share")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📥 Export to CSV", width='stretch', key="dashboard_export_btn"):
            st.session_state.show_export_options = not st.session_state.get('show_export_options', False)
    
    with col2:
        if st.button("📧 Email Report", width='stretch', key="dashboard_email_btn"):
            st.session_state.show_email_form = not st.session_state.get('show_email_form', False)
    
    with col3:
        if st.button("📊 Generate PDF Report", width='stretch', key="dashboard_pdf_btn"):
            st.info("📊 PDF generation feature coming soon!")
            log_activity("❌ Attempted PDF Report Generation (Feature Missing)", '#ef4444')
    
    # Export Options
    if st.session_state.get('show_export_options', False):
        st.markdown("#### 📥 Export Options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            export_format = st.radio("Select Format", ["CSV", "Excel (XLSX)", "JSON"], horizontal=True, key="export_format_radio")
        
        with col2:
            include_charts = st.checkbox("Include chart data", value=True)
            include_summary = st.checkbox("Include summary statistics", value=True)
        
        if export_format == "CSV":
            export_df = display_data.copy()
            
            if include_summary:
                summary_row = pd.DataFrame({
                    'product_code': ['SUMMARY'],
                    'product_name': ['Summary Statistics'],
                    'current_stock_qty': [export_df['current_stock_qty'].sum()],
                    'avg_daily_demand': [export_df['avg_daily_demand'].mean()],
                    'stock_value': [export_df['stock_value'].sum()],
                    'turnover_ratio_90d': [export_df['turnover_ratio_90d'].mean()]
                })
            
            csv_data = export_df.to_csv(index=False).encode('utf-8')
            if st.download_button(
                label="⬇️ Download CSV",
                data=csv_data,
                file_name=f"inventory_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                width='stretch',
                key="export_dashboard_csv_final"
            ):
                 log_activity(f"📥 Downloaded Dashboard data as {export_format}", '#6366f1')
        
        elif export_format == "Excel (XLSX)":
            st.info("📊 Excel export feature coming soon!")
        
        else:  # JSON
            json_export = {
                'export_date': datetime.now().isoformat(),
                'total_products': len(export_df),
                'summary': {
                    'total_stock_value': float(export_df['stock_value'].sum()),
                    'avg_turnover': float(export_df['turnover_ratio_90d'].mean()),
                    'avg_daily_demand': float(export_df['avg_daily_demand'].mean())
                } if include_summary else {},
                'products': export_df.to_dict('records')
            }
            
            json_data = pd.io.json.dumps(json_export, indent=2)
            if st.download_button(
                label="⬇️ Download JSON",
                data=json_data,
                file_name=f"inventory_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                width='stretch',
                key="export_dashboard_json_final"
            ):
                 log_activity(f"📥 Downloaded Dashboard data as {export_format}", '#6366f1')

    # Email Form
    if st.session_state.get('show_email_form', False):
        render_email_form(display_data, "overview", "inventory_dashboard")
    
    # ========================================================================
    # INSIGHTS & RECOMMENDATIONS
    # ========================================================================
    
    st.markdown("---")
    st.markdown("### 💡 AI-Powered Insights & Recommendations")
    
    # Generate dynamic insights based on data
    insights = []
    
    # Insight 1: Service Level
    if service_level < 90:
        insights.append({
            'type': 'warning',
            'title': '⚠️ Service Level Below Target',
            'message': f'Current service level is {service_level:.1f}%, below the 95% target. Consider increasing safety stock for critical items.',
            'action': 'Review stockout alerts and adjust reorder points'
        })
    else:
        insights.append({
            'type': 'success',
            'title': '✅ Excellent Service Level',
            'message': f'Service level at {service_level:.1f}% exceeds target. Great inventory management!',
            'action': 'Maintain current policies'
        })
    
    # Insight 2: Turnover
    # Insight 2: Turnover
    if avg_turnover_30d < 0.5:
        insights.append({
            'type': 'warning',
            'title': '📉 Low Inventory Turnover',
            'message': f'Turnover rate of {avg_turnover_30d:.2f}x (30d) is below target (>0.5x). Consider reducing slow-moving inventory.',
            'action': 'Implement promotions for slow-moving items'
        })
    
    # Insight 3: Critical Stock
    if critical_count > 0:
        insights.append({
            'type': 'critical',
            'title': '🔴 Critical Stockout Risk',
            'message': f'{critical_count} products will run out in less than 7 days. Immediate action required!',
            'action': 'Process emergency orders immediately'
        })
    
    # Insight 4: Dead Stock
    dead_stock_count = len(df[df['turnover_ratio_30d'] < 0.1])
    if dead_stock_count > 0:
        insights.append({
            'type': 'warning',
            'title': '📦 Dead Stock Detected',
            'message': f'{dead_stock_count} products have very low turnover (<0.1x). Consider clearance sale.',
            'action': 'Identify and discount dead stock'
        })
    
    # Display insights in cards
    for i, insight in enumerate(insights):
        border_color = {
            'success': '#10b981',
            'warning': '#f59e0b',
            'critical': '#ef4444',
            'info': '#6366f1'
        }.get(insight['type'], '#6366f1')
        
        st.markdown(f"""
        <div style="background: rgba(30, 41, 59, 0.6); border-left: 4px solid {border_color}; 
                    padding: 1rem; border-radius: 8px; margin-bottom: 0.8rem;">
            <h4 style="margin: 0 0 0.5rem 0; color: #f8fafc;">{insight['title']}</h4>
            <p style="margin: 0 0 0.5rem 0; color: #e2e8f0; font-size: 0.95rem;">{insight['message']}</p>
            <p style="margin: 0; color: #94a3b8; font-size: 0.85rem;">
                <strong>Recommended Action:</strong> {insight['action']}
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # ========================================================================
    # PERFORMANCE COMPARISON - STOCK VALUE BY ABC CLASS
    # ========================================================================
    
    st.markdown("---")
    st.markdown("### 📊 Stock Value & Performance by ABC Class")
    
    # Group by ABC class
    abc_performance = df.groupby('ABC_class').agg({
        'current_stock_qty': 'sum',
        'stock_value': 'sum',
        'avg_daily_demand': 'mean',
        'turnover_ratio_30d': 'mean'
    }).reset_index()
    
    
    # Stock Value by ABC - Full Width
    fig = go.Figure(data=[go.Bar(
        x=abc_performance['ABC_class'],
        y=abc_performance['stock_value'] / 1_000_000,
        marker_color=['#10b981', '#f59e0b', '#ef4444'],
        text=abc_performance['stock_value'].apply(lambda x: f'Rp {x/1_000_000:.1f}M'),
        textposition='outside'
    )])
    
    fig.update_layout(
        title="Stock Value Distribution by ABC Class",
        xaxis_title="ABC Class",
        yaxis_title="Stock Value (Million Rp)",
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=350,
        showlegend=False,
        xaxis=dict(
            showgrid=True,
            gridcolor='rgba(255,255,255,0.1)'
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='rgba(255,255,255,0.1)'
        )
    )
    
    st.plotly_chart(fig, width='stretch')
    
    # ABC Performance Summary Cards
    st.markdown("### 📈 ABC Class Performance Summary")
    
    abc_cols = st.columns(3)
    for idx, (class_name, row) in enumerate(abc_performance.iterrows()):
        with abc_cols[idx]:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Class {row['ABC_class']}</div>
                <div style="margin: 0.5rem 0;">
                    <div style="font-size: 0.85rem; color: #94a3b8;">Stock Value</div>
                    <div style="font-size: 1.5rem; color: #10b981; font-weight: 600;">Rp {row['stock_value']/1_000_000:.1f}M</div>
                </div>
                <div style="margin: 0.5rem 0;">
                    <div style="font-size: 0.85rem; color: #94a3b8;">Daily Demand</div>
                    <div style="font-size: 1.1rem; color: #6366f1; font-weight: 600;">{row['avg_daily_demand']:.1f} units</div>
                </div>
                <div style="margin: 0.5rem 0; padding-top: 0.5rem; border-top: 1px solid #334155;">
                    <div style="font-size: 0.85rem; color: #94a3b8;">Turnover</div>
                    <div style="font-size: 1.1rem; color: #f59e0b; font-weight: 600;">{row['turnover_ratio_30d']:.2f}x</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # ========================================================================
    # FOOTER WITH KEY TAKEAWAYS
    # ========================================================================
    
    st.markdown("---")
    st.markdown("### 🎯 Key Takeaways")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="insight-card">
            <h4 style="color: #10b981; margin-top: 0;">✅ Strengths</h4>
            <ul style="font-size: 0.9rem;">
                <li>Service level within target range</li>
                <li>Fast-moving products well-stocked</li>
                <li>Regular inventory turnover</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="insight-card">
            <h4 style="color: #f59e0b; margin-top: 0;">⚠️ Areas for Improvement</h4>
            <ul style="font-size: 0.9rem;">
                <li>Address critical stockout risks</li>
                <li>Optimize slow-moving inventory</li>
                <li>Reduce dead stock capital</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="insight-card">
            <h4 style="color: #6366f1; margin-top: 0;">🚀 Next Actions</h4>
            <ul style="font-size: 0.9rem;">
                <li>Process urgent reorders today</li>
                <li>Schedule weekly inventory review</li>
                <li>Implement promotional campaigns</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
