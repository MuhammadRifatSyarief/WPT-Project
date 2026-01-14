# File: modules/pages/rfm.py

"""
RFM Analysis Page
=================
Customer segmentation using Recency, Frequency, Monetary analysis.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import numpy as np
import matplotlib.cm as cm

from modules.data_loader import load_project2_data
from modules.rfm_analyzer import RFMAnalyzer
from modules.activity_logger import log_activity
from config.constants import RFM_CONFIG, CUSTOMER_VALUE_CONFIG


def render_page(df: pd.DataFrame = None):
    """Render RFM Analysis page."""
    
    st.title("👥 RFM Customer Segmentation Analysis")
    st.markdown("**Segment customers based on Recency, Frequency, and Monetary value**")
    
    # Load Project 2 data
    with st.spinner("Loading customer data..."):
        project2_data = load_project2_data()
    
    # Check if required data is available
    if not project2_data or '6_Sales_By_Customer.csv' not in project2_data:
        st.error("⚠️ Customer data not found. Please ensure Project 2 data files are in the data folder.")
        st.info("""
        **Required files:**
        - `6_Sales_By_Customer.csv` - Customer sales aggregations
        - `1_RFM_Analysis.csv` - Pre-computed RFM analysis (optional)
        - `2_Customer_Segments.csv` - Customer segments (optional)
        """)
        return
    
    # Get customer data
    customer_data = project2_data.get('6_Sales_By_Customer.csv')
    
    # Try to load pre-computed RFM if available
    rfm_precomputed = project2_data.get('1_RFM_Analysis.csv')
    
    if rfm_precomputed is not None and not rfm_precomputed.empty:
        st.success("✅ Using pre-computed RFM analysis")
        rfm_df = rfm_precomputed
        analyzer = None
    else:
        # Initialize analyzer and compute RFM
        try:
            analyzer = RFMAnalyzer(customer_data)
            rfm_df = analyzer.calculate_rfm_scores()
            rfm_df = analyzer.segment_customers()
        except Exception as e:
            st.error(f"❌ Error computing RFM analysis: {str(e)}")
            st.info("Please check that customer data has required columns: customer_id, recency_days, frequency, monetary")
            return
    
    # ========================================================================
    # KEY METRICS OVERVIEW
    # ========================================================================
    
    st.markdown("---")
    st.markdown("### 📊 Key Metrics Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_customers = len(rfm_df)
    total_revenue = rfm_df['monetary'].sum() if 'monetary' in rfm_df.columns else 0
    avg_recency = rfm_df['recency_days'].mean() if 'recency_days' in rfm_df.columns else 0
    champions_count = len(rfm_df[rfm_df['segment'] == 'Champions']) if 'segment' in rfm_df.columns else 0
    
    with col1:
        st.markdown(f"""
        <div class="metric-card" style="border-left: 3px solid #667eea;">
            <div class="metric-label">Total Customers</div>
            <div class="metric-value">{total_customers:,}</div>
            <div class="metric-delta positive">Active accounts</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card" style="border-left: 3px solid #10b981;">
            <div class="metric-label">Total Revenue</div>
            <div class="metric-value">Rp {total_revenue/1_000_000:.1f}M</div>
            <div class="metric-delta positive">Lifetime value</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        recency_status = "positive" if avg_recency < 30 else "negative"
        st.markdown(f"""
        <div class="metric-card" style="border-left: 3px solid {'#10b981' if avg_recency < 30 else '#f59e0b'};">
            <div class="metric-label">Avg Recency</div>
            <div class="metric-value">{avg_recency:.0f}</div>
            <div class="metric-delta {recency_status}">Days since last purchase</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card" style="border-left: 3px solid #10b981;">
            <div class="metric-label">Champions</div>
            <div class="metric-value">{champions_count:,}</div>
            <div class="metric-delta positive">Best customers</div>
        </div>
        """, unsafe_allow_html=True)
    
    # ========================================================================
    # SEGMENT DISTRIBUTION
    # ========================================================================
    
    st.markdown("---")
    st.markdown("### 📈 Customer Segment Distribution")
    
    if 'segment' in rfm_df.columns:
        segment_counts = rfm_df['segment'].value_counts()
        segment_revenue = rfm_df.groupby('segment')['monetary'].sum().sort_values(ascending=False)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Segment count chart - Smooth gradient based on values
            fig_count = px.bar(
                x=segment_counts.index,
                y=segment_counts.values,
                title="Customers by Segment",
                labels={'x': 'Segment', 'y': 'Number of Customers'},
                color=segment_counts.values,
                color_continuous_scale='Plasma',
                text=segment_counts.values
            )
            fig_count.update_traces(
                marker=dict(
                    line=dict(color='rgba(255,255,255,0.15)', width=0.5),
                    opacity=0.85
                )
            )
            fig_count.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='rgba(255,255,255,0.9)'),
                height=400,
                coloraxis_showscale=False,
                template='plotly_dark'
            )
            st.plotly_chart(fig_count, use_container_width=True)
        
        with col2:
            # Segment revenue chart - Smooth gradient colors (custom gradient sequence)
            # Create gradient colors based on revenue values (sorted)
            sorted_segments = segment_revenue.sort_values(ascending=False)
            n_segments = len(sorted_segments)
            
            # Generate smooth gradient colors using Viridis colormap
            viridis = cm.get_cmap('viridis')
            gradient_colors = []
            for i in range(n_segments):
                rgba = viridis(i / max(n_segments - 1, 1))
                gradient_colors.append(f'rgba({int(rgba[0]*255)},{int(rgba[1]*255)},{int(rgba[2]*255)},{rgba[3]*0.85})')
            
            # Map colors to segment names
            color_map = {seg: gradient_colors[i] for i, seg in enumerate(sorted_segments.index)}
            
            fig_revenue = px.pie(
                values=segment_revenue.values,
                names=segment_revenue.index,
                title="Revenue Distribution by Segment",
                color=segment_revenue.index,
                color_discrete_map=color_map
            )
            fig_revenue.update_traces(
                textposition='inside',
                textinfo='percent+label',
                marker=dict(
                    line=dict(color='rgba(255,255,255,0.15)', width=1)
                ),
                opacity=0.85
            )
            fig_revenue.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='rgba(255,255,255,0.9)'),
                height=400,
                template='plotly_dark'
            )
            st.plotly_chart(fig_revenue, use_container_width=True)
        
        # Segment metrics table
        if analyzer:
            segment_metrics = analyzer.calculate_segment_metrics()
        else:
            segment_metrics = rfm_df.groupby('segment').agg({
                'customer_id': 'count',
                'recency_days': 'mean',
                'frequency': 'mean',
                'monetary': ['sum', 'mean']
            }).round(2)
            segment_metrics.columns = ['customer_count', 'avg_recency_days', 'avg_frequency', 'total_revenue', 'avg_monetary']
            segment_metrics = segment_metrics.reset_index()
            total_customers = segment_metrics['customer_count'].sum()
            total_revenue = segment_metrics['total_revenue'].sum()
            segment_metrics['customer_pct'] = (segment_metrics['customer_count'] / total_customers * 100).round(1)
            segment_metrics['revenue_pct'] = (segment_metrics['total_revenue'] / total_revenue * 100).round(1)
        
        st.markdown("#### Segment Performance Metrics")
        st.dataframe(
            segment_metrics.style.format({
                'customer_count': '{:,.0f}',
                'avg_recency_days': '{:.1f}',
                'avg_frequency': '{:.2f}',
                'total_revenue': 'Rp {:,.0f}',
                'avg_monetary': 'Rp {:,.0f}',
                'customer_pct': '{:.1f}%',
                'revenue_pct': '{:.1f}%'
            }),
            use_container_width=True,
            height=400
        )
    
    # ========================================================================
    # RFM SCORE VISUALIZATION
    # ========================================================================
    
    st.markdown("---")
    st.markdown("### 🎯 RFM Score Analysis")
    
    if all(col in rfm_df.columns for col in ['r_score', 'f_score', 'm_score']):
        # RFM Score Distribution
        st.markdown("#### RFM Score Distribution")
        col1, col2, col3 = st.columns(3)
        
        # Define distinct colors for each score (1-5) based on Customer Value Matrix gradient
        score_colors = {
            1: 'rgba(13,8,135,0.9)',      # Deep blue (Score 1)
            2: 'rgba(75,10,125,0.9)',     # Purple (Score 2)
            3: 'rgba(125,38,205,0.9)',    # Bright purple (Score 3)
            4: 'rgba(188,55,183,0.9)',    # Pink-purple (Score 4)
            5: 'rgba(253,174,97,0.9)'     # Orange (Score 5)
        }
        
        with col1:
            # Recency Score Distribution - Different color for each score (1-5)
            r_dist = rfm_df['r_score'].value_counts().sort_index()
            # Create bar chart with distinct colors for each score
            fig_r = go.Figure()
            for score in sorted(r_dist.index):
                count = r_dist[score]
                fig_r.add_trace(go.Bar(
                    x=[score],
                    y=[count],
                    name=f'Score {score}',
                    marker=dict(
                        color=score_colors[score],
                        line=dict(color='rgba(255,255,255,0.2)', width=0.8)
                    ),
                    text=[count],
                    textposition='outside',
                    showlegend=False
                ))
            fig_r.update_layout(
                title="📅 Recency Score Distribution",
                xaxis_title="Recency Score (1=Oldest, 5=Recent)",
                yaxis_title="Number of Customers",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='rgba(255,255,255,0.95)'),
                height=350,
                template='plotly_dark',
                xaxis=dict(tickmode='linear', tick0=1, dtick=1, range=[0.5, 5.5])
            )
            st.plotly_chart(fig_r, use_container_width=True)
        
        with col2:
            # Frequency Score Distribution - Different color for each score (1-5)
            f_dist = rfm_df['f_score'].value_counts().sort_index()
            # Create bar chart with distinct colors for each score
            fig_f = go.Figure()
            for score in sorted(f_dist.index):
                count = f_dist[score]
                fig_f.add_trace(go.Bar(
                    x=[score],
                    y=[count],
                    name=f'Score {score}',
                    marker=dict(
                        color=score_colors[score],
                        line=dict(color='rgba(255,255,255,0.2)', width=0.8)
                    ),
                    text=[count],
                    textposition='outside',
                    showlegend=False
                ))
            fig_f.update_layout(
                title="🔄 Frequency Score Distribution",
                xaxis_title="Frequency Score (1=Low, 5=High)",
                yaxis_title="Number of Customers",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='rgba(255,255,255,0.95)'),
                height=350,
                template='plotly_dark',
                xaxis=dict(tickmode='linear', tick0=1, dtick=1, range=[0.5, 5.5])
            )
            st.plotly_chart(fig_f, use_container_width=True)
        
        with col3:
            # Monetary Score Distribution - Different color for each score (1-5)
            m_dist = rfm_df['m_score'].value_counts().sort_index()
            # Create bar chart with distinct colors for each score
            fig_m = go.Figure()
            for score in sorted(m_dist.index):
                count = m_dist[score]
                fig_m.add_trace(go.Bar(
                    x=[score],
                    y=[count],
                    name=f'Score {score}',
                    marker=dict(
                        color=score_colors[score],
                        line=dict(color='rgba(255,255,255,0.2)', width=0.8)
                    ),
                    text=[count],
                    textposition='outside',
                    showlegend=False
                ))
            fig_m.update_layout(
                title="💰 Monetary Score Distribution",
                xaxis_title="Monetary Score (1=Low, 5=High)",
                yaxis_title="Number of Customers",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='rgba(255,255,255,0.95)'),
                height=350,
                template='plotly_dark',
                xaxis=dict(tickmode='linear', tick0=1, dtick=1, range=[0.5, 5.5])
            )
            st.plotly_chart(fig_m, use_container_width=True)
        
        # Customer Value Matrix (2D Heatmap - more readable)
        st.markdown("#### Customer Value Matrix")
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Create RFM matrix heatmap
            rfm_matrix = rfm_df.groupby(['r_score', 'f_score']).agg({
                'customer_id': 'count',
                'monetary': 'mean'
            }).reset_index()
            rfm_matrix.columns = ['r_score', 'f_score', 'customer_count', 'avg_monetary']
            
            # Pivot for heatmap
            heatmap_data = rfm_matrix.pivot(index='f_score', columns='r_score', values='customer_count').fillna(0)
            
            # Create heatmap using go.Heatmap with eye-catching gradient
            # Custom smooth gradient colorscale (eye-catching but not too bright)
            gradient_colorscale = [
                [0, 'rgba(13,8,135,0.7)'],        # Deep blue
                [0.2, 'rgba(75,10,125,0.75)'],    # Purple
                [0.4, 'rgba(125,38,205,0.8)'],    # Bright purple
                [0.6, 'rgba(188,55,183,0.85)'],  # Pink-purple
                [0.8, 'rgba(253,174,97,0.9)'],    # Orange
                [1, 'rgba(255,255,204,0.95)']    # Light yellow
            ]
            
            fig_matrix = go.Figure(data=go.Heatmap(
                z=heatmap_data.values,
                x=[str(i) for i in heatmap_data.columns],
                y=[str(i) for i in heatmap_data.index],
                colorscale=gradient_colorscale,
                text=heatmap_data.values,
                texttemplate='%{text:.0f}',
                textfont={"size": 10, "color": "rgba(255,255,255,0.95)"},
                colorbar=dict(
                    title="Number of Customers",
                    titlefont=dict(color='rgba(255,255,255,0.9)'),
                    tickfont=dict(color='rgba(255,255,255,0.8)')
                ),
                opacity=0.9
            ))
            fig_matrix.update_layout(
                title="Customer Distribution Matrix (Frequency vs Recency)",
                xaxis_title="Recency Score (1=Oldest, 5=Recent)",
                yaxis_title="Frequency Score (1=Low, 5=High)",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                height=400,
                template='plotly_dark'
            )
            st.plotly_chart(fig_matrix, use_container_width=True)
        
        with col2:
            st.markdown("**📊 Insights:**")
            st.markdown("""
            - **Top Right (High R, High F):** Best customers - Recent & Frequent
            - **Top Left (Low R, High F):** At Risk - Frequent but not recent
            - **Bottom Right (High R, Low F):** New customers - Recent but infrequent
            - **Bottom Left (Low R, Low F):** Lost customers - Not recent & infrequent
            """)
            
            # Summary stats
            high_value = len(rfm_df[(rfm_df['r_score'] >= 4) & (rfm_df['f_score'] >= 4)])
            at_risk = len(rfm_df[(rfm_df['r_score'] <= 2) & (rfm_df['f_score'] >= 4)])
            
            st.metric("High Value Customers", f"{high_value:,}")
            st.metric("At Risk Customers", f"{at_risk:,}")
    
    # ========================================================================
    # SEGMENT INSIGHTS & RECOMMENDATIONS
    # ========================================================================
    
    st.markdown("---")
    st.markdown("### 💡 Segment Insights & Recommendations")
    
    if 'segment' in rfm_df.columns and analyzer:
        recommendations = analyzer.get_segment_recommendations()
        
        # Display insights for each segment
        segments_to_show = st.multiselect(
            "Select segments to view insights:",
            options=list(recommendations.keys()),
            default=list(recommendations.keys())[:5]  # Show top 5 by default
        )
        
        for segment in segments_to_show:
            if segment in recommendations:
                rec = recommendations[segment]
                
                with st.expander(f"📌 {segment} - {rec['customer_count']:,} customers ({rec['total_revenue']:,.0f} revenue)"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Avg Recency", f"{rec['avg_recency']:.0f} days")
                    
                    with col2:
                        st.metric("Avg Frequency", f"{rec['avg_frequency']:.2f}")
                    
                    with col3:
                        st.metric("Avg Monetary", f"Rp {rec['avg_monetary']:,.0f}")
                    
                    st.markdown(f"**Recommended Action:** {rec['action']}")
                    
                    # Color indicator
                    st.markdown(f"""
                    <div style="background-color: {rec['color']}; padding: 10px; border-radius: 5px; margin-top: 10px;">
                        <strong>Segment Priority:</strong> {rec['priority']}/10
                    </div>
                    """, unsafe_allow_html=True)
    
    # ========================================================================
    # AT-RISK CUSTOMERS
    # ========================================================================
    
    st.markdown("---")
    st.markdown("### ⚠️ At-Risk Customers")
    
    if analyzer:
        at_risk = analyzer.identify_at_risk_customers()
        
        if not at_risk.empty:
            st.warning(f"Found {len(at_risk):,} high-value customers at risk of churning")
            
            # Display top at-risk customers
            st.dataframe(
                at_risk[['customer_id', 'recency_days', 'frequency', 'monetary', 'segment']].head(20).style.format({
                    'recency_days': '{:.0f}',
                    'frequency': '{:.2f}',
                    'monetary': 'Rp {:,.0f}'
                }),
                use_container_width=True
            )
        else:
            st.info("✅ No at-risk customers identified")
    
    # ========================================================================
    # CUSTOMER SEARCH & FILTER
    # ========================================================================
    
    st.markdown("---")
    st.markdown("### 🔍 Customer Search & Analysis")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        search_query = st.text_input("Search customer by ID or name:", "")
    
    with col2:
        segment_filter = st.selectbox(
            "Filter by segment:",
            options=['All'] + (list(rfm_df['segment'].unique()) if 'segment' in rfm_df.columns else [])
        )
    
    # Filter data
    filtered_df = rfm_df.copy()
    
    if search_query:
        mask = (
            filtered_df['customer_id'].astype(str).str.contains(search_query, case=False, na=False) |
            (filtered_df['customer_name'].astype(str).str.contains(search_query, case=False, na=False) if 'customer_name' in filtered_df.columns else False)
        )
        filtered_df = filtered_df[mask]
    
    if segment_filter != 'All' and 'segment' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['segment'] == segment_filter]
    
    if not filtered_df.empty:
        st.dataframe(
            filtered_df.head(100).style.format({
                'recency_days': '{:.0f}',
                'frequency': '{:.2f}',
                'monetary': 'Rp {:,.0f}',
                'r_score': '{:.0f}',
                'f_score': '{:.0f}',
                'm_score': '{:.0f}'
            }),
            use_container_width=True,
            height=400
        )
    else:
        st.info("No customers found matching the criteria")
    
    # ========================================================================
    # EXPORT OPTIONS
    # ========================================================================
    
    st.markdown("---")
    st.markdown("### 📥 Export Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 Export RFM Analysis"):
            csv = rfm_df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"rfm_analysis_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    with col2:
        if analyzer:
            summary = analyzer.export_summary()
            st.json(summary)
    
    log_activity("Viewed RFM Analysis", "#6366f1")

