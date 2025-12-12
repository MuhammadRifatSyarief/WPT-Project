    # # ========================================================================
    # # STOCK HEALTH DISTRIBUTION & RECENT ACTIVITIES
    # # ========================================================================
    
    # col1, col2 = st.columns([2, 1])
    
    # with col1:
    #     st.markdown("### 🎯 Stock Health Distribution")
        
    #     with st.popover("📖 Penjelasan Kategori"):
    #         st.markdown("""
    #         ### 🟢 Healthy
    #         **Kriteria:** High turnover, adequate stock
            
    #         **Artinya:** Produk laku keras, stok optimal
            
    #         **Tindakan:** 
    #         - Maintain stock level optimal
    #         - Monitor untuk avoid stockout
    #         - Consider increase order quantity
            
    #         ---
            
    #         ### 🔵 Stable
    #         **Kriteria:** Normal movement, balanced stock
            
    #         **Artinya:** Produk bergerak normal
            
    #         **Tindakan:** 
    #         - Monitor trend pergerakan
    #         - Maintain current reorder policy
            
    #         ---
            
    #         ### 🟡 Warning
    #         **Kriteria:** Low turnover or aging stock
            
    #         **Artinya:** Produk mulai lambat
            
    #         **Tindakan:** 
    #         - Promosi atau discount
    #         - Cross-sell strategy
    #         - Review pricing
            
    #         ---
            
    #         ### 🔴 Critical
    #         **Kriteria:** Very low turnover, dead stock
            
    #         **Artinya:** Stock bermasalah, action needed!
            
    #         **Tindakan:** 
    #         - Aggressive discount 30-50%
    #         - Bundle with fast-moving items
    #         - Consider return to supplier
    #         - STOP future orders
            
    #         ---
            
    #         **Target Ideal:**
    #         - Healthy + Stable: >70%
    #         - Warning: 15-20%
    #         - Critical: <10%
    #         """)
        
    #     # Classify products into health categories
    #     def classify_health(row):
    #         turnover = row['turnover_ratio_90d']
    #         days_stock = row['days_until_stockout']
            
    #         if turnover > 2.0 and days_stock > 30:
    #             return 'Healthy'
    #         elif turnover > 1.0 and days_stock > 14:
    #             return 'Stable'
    #         elif turnover > 0.5 or days_stock > 7:
    #             return 'Warning'
    #         else:
    #             return 'Critical'
        
    #     df['health_category'] = df.apply(classify_health, axis=1)
    #     health_counts = df['health_category'].value_counts()
    #     total_products = len(df)
        
    #     # Color mapping
    #     colors_map = {
    #         'Healthy': '#10b981',
    #         'Stable': '#6366f1',
    #         'Warning': '#f59e0b',
    #         'Critical': '#ef4444'
    #     }
        
    #     # Create donut chart
    #     fig = go.Figure(data=[go.Pie(
    #         labels=health_counts.index,
    #         values=health_counts.values,
    #         hole=0.5,
    #         marker=dict(
    #             colors=[colors_map.get(cat, '#64748b') for cat in health_counts.index],
    #             line=dict(color='#1e293b', width=2)
    #         ),
    #         textinfo='label+percent',
    #         texttemplate='<b>%{label}</b><br>%{percent}',
    #         textposition='outside',
    #         textfont=dict(size=11, color='#e2e8f0'),
    #         hovertemplate='<b>%{label}</b><br>%{value} products<br>%{percent}<extra></extra>',
    #         pull=[0.1 if cat == 'Critical' else 0.05 if cat == 'Warning' else 0 for cat in health_counts.index],
    #         showlegend=True,
    #         rotation=90
    #     )])
        
    #     # Center annotation
    #     fig.add_annotation(
    #         text=f"<b>{total_products:,}</b><br><span style='font-size:14px'>Total<br>Products</span>",
    #         x=0.5, y=0.5,
    #         font=dict(size=24, color='#f8fafc'),
    #         showarrow=False
    #     )
        
    #     fig.update_layout(
    #         template='plotly_dark',
    #         paper_bgcolor='rgba(0,0,0,0)',
    #         plot_bgcolor='rgba(0,0,0,0)',
    #         height=350,
    #         margin=dict(l=20, r=20, t=20, b=20),
    #         legend=dict(
    #             orientation="h",
    #             yanchor="bottom",
    #             y=-0.15,
    #             xanchor="center",
    #             x=0.5,
    #             font=dict(color='#e2e8f0', size=11)
    #         ),
    #         hoverlabel=dict(
    #             bgcolor="#1e293b",
    #             font_color="#e2e8f0",
    #             font_size=12
    #         )
    #     )
        
    #     st.plotly_chart(fig, width='stretch')
    
    # with col2:
    #     st.markdown("### 📋 Recent Activities")
        
    #     # PERBAIKAN: Import dan tampilkan dari activity log
    #     from modules.activity_logger import get_activity_log
        
    #     activities_to_display = get_activity_log()[:5]  # Max 5 terbaru
        
    #     if not activities_to_display:
    #         st.info("No recent activity.")
    #     else:
    #         for activity in activities_to_display:
    #             st.markdown(f"""
    #             <div style="background: rgba(30, 41, 59, 0.6); padding: 0.8rem; border-radius: 8px; 
    #                         margin-bottom: 0.5rem; border-left: 3px solid {activity['color']};">
    #                 <div style="font-size: 0.75rem; color: #94a3b8;">{activity['time']}</div>
    #                 <div style="font-size: 0.9rem; color: #e2e8f0; margin-top: 0.2rem;">
    #                     {activity['action']}
    #                 </div>
    #             </div>
    #             """, unsafe_allow_html=True)
            
    #         # Info jika ada lebih banyak activities
    #         total_activities = len(get_activity_log())
    #         if total_activities > 5:
    #             st.caption(f"_Showing 5 of {total_activities} activities. Check sidebar for full log._")

