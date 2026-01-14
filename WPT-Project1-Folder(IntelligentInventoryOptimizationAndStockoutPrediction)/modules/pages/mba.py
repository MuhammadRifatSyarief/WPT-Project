# File: modules/pages/mba.py

"""
Market Basket Analysis Page
===========================
Product association analysis and cross-selling recommendations.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import numpy as np
import networkx as nx
import matplotlib.cm as cm

from modules.data_loader import load_project2_data
from modules.market_basket_analyzer import MarketBasketAnalyzer
from modules.activity_logger import log_activity
from config.constants import MBA_CONFIG


def render_page(df: pd.DataFrame = None):
    """Render Market Basket Analysis page."""
    
    st.title("🛒 Market Basket Analysis")
    st.markdown("**Discover product associations and cross-selling opportunities**")
    
    # Load Project 2 data
    with st.spinner("Loading transaction data..."):
        project2_data = load_project2_data()
    
    # Check if required data is available
    if not project2_data or '5_Sales_Details.csv' not in project2_data:
        st.error("⚠️ Sales transaction data not found. Please ensure Project 2 data files are in the data folder.")
        st.info("""
        **Required files:**
        - `5_Sales_Details.csv` - Transaction-level sales data
        - `3_Market_Basket.csv` - Pre-computed market basket (optional)
        - `4_Product_Associations.csv` - Product associations (optional)
        """)
        return
    
    # Get sales details
    sales_details = project2_data.get('5_Sales_Details.csv')
    
    # Try to load pre-computed MBA if available
    mba_precomputed = project2_data.get('3_Market_Basket.csv')
    associations_precomputed = project2_data.get('4_Product_Associations.csv')
    
    # Initialize analyzer
    try:
        # Determine column names
        product_id_col = 'product_id' if 'product_id' in sales_details.columns else 'item_id'
        product_name_col = 'product_name' if 'product_name' in sales_details.columns else 'item_name'
        transaction_col = 'invoice_id' if 'invoice_id' in sales_details.columns else 'transaction_id'
        
        analyzer = MarketBasketAnalyzer(
            sales_details,
            product_id_col=product_id_col,
            product_name_col=product_name_col,
            transaction_col=transaction_col
        )
    except Exception as e:
        st.error(f"❌ Error initializing Market Basket Analyzer: {str(e)}")
        st.info("Please check that sales data has required columns: product_id, product_name, invoice_id")
        return
    
    # ========================================================================
    # KEY METRICS OVERVIEW
    # ========================================================================
    
    st.markdown("---")
    st.markdown("### 📊 Transaction Overview")
    
    summary = analyzer.export_summary()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Transactions", f"{summary['total_transactions']:,}")
    
    with col2:
        st.metric("Multi-Item Transactions", f"{summary['multi_item_transactions']:,}")
    
    with col3:
        st.metric("Unique Products", f"{summary['unique_products']:,}")
    
    # ========================================================================
    # CONFIGURATION PANEL
    # ========================================================================
    
    st.markdown("---")
    st.markdown("### ⚙️ Analysis Configuration")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        min_support = st.slider(
            "Minimum Support",
            min_value=0.001,
            max_value=0.1,
            value=MBA_CONFIG['MIN_SUPPORT'],
            step=0.001,
            format="%.3f",
            help="Minimum percentage of transactions containing itemset"
        )
    
    with col2:
        min_confidence = st.slider(
            "Minimum Confidence",
            min_value=0.1,
            max_value=1.0,
            value=MBA_CONFIG['MIN_CONFIDENCE'],
            step=0.05,
            format="%.2f",
            help="Minimum confidence for association rules"
        )
    
    with col3:
        min_lift = st.slider(
            "Minimum Lift",
            min_value=0.5,
            max_value=5.0,
            value=MBA_CONFIG['MIN_LIFT'],
            step=0.1,
            format="%.1f",
            help="Minimum lift value (must be > 1 for positive association)"
        )
    
    # Run analysis
    if st.button("🔍 Run Market Basket Analysis", type="primary"):
        with st.spinner("Analyzing product associations..."):
            # Find frequent itemsets
            itemsets = analyzer.find_frequent_itemsets(
                min_support=min_support,
                max_itemset_size=MBA_CONFIG['MAX_ITEMSET_SIZE']
            )
            
            # Generate association rules
            rules_df = analyzer.generate_association_rules(
                min_confidence=min_confidence,
                min_lift=min_lift
            )
            
            st.session_state['mba_rules'] = rules_df
            st.session_state['mba_itemsets'] = itemsets
            st.success("✅ Analysis complete!")
    
    # ========================================================================
    # ASSOCIATION RULES
    # ========================================================================
    
    if 'mba_rules' in st.session_state and not st.session_state['mba_rules'].empty:
        rules_df = st.session_state['mba_rules']
        
        st.markdown("---")
        st.markdown("### 🔗 Association Rules")
        
        # Filter options
        col1, col2 = st.columns(2)
        
        with col1:
            lift_category_filter = st.selectbox(
                "Filter by Lift Category:",
                options=['All'] + list(rules_df['lift_category'].unique())
            )
        
        with col2:
            top_n = st.slider("Show Top N Rules:", min_value=10, max_value=100, value=20, step=10)
        
        # Filter rules
        filtered_rules = rules_df.copy()
        if lift_category_filter != 'All':
            filtered_rules = filtered_rules[filtered_rules['lift_category'] == lift_category_filter]
        
        filtered_rules = filtered_rules.head(top_n)
        
        # Display rules
        if not filtered_rules.empty:
            # Rules table
            display_rules = filtered_rules[['antecedent_items', 'consequent_items', 'support', 'confidence', 'lift', 'lift_category']].copy()
            display_rules.columns = ['If Customer Buys', 'Recommend', 'Support', 'Confidence', 'Lift', 'Strength']
            
            st.dataframe(
                display_rules.style.format({
                    'Support': '{:.2%}',
                    'Confidence': '{:.2%}',
                    'Lift': '{:.2f}'
                }).background_gradient(subset=['Lift'], cmap='viridis'),
                use_container_width=True,
                height=400
            )
            
            # Business-Focused Visualizations
            st.markdown("#### 💼 Business Impact Analysis")
            
            # Calculate Business Impact Score (Lift × Confidence × Support × 1000)
            # This score represents the potential business value of each rule
            filtered_rules_copy = filtered_rules.copy()
            filtered_rules_copy['business_impact'] = (
                filtered_rules_copy['lift'] * 
                filtered_rules_copy['confidence'] * 
                filtered_rules_copy['support'] * 1000
            ).round(2)
            
            # Create readable rule labels with unique identifier to avoid duplicates
            def create_rule_label(row, idx):
                """Create unique rule label with index to prevent duplicates"""
                antecedent = str(row['antecedent_items'])[:25] + "..." if len(str(row['antecedent_items'])) > 25 else str(row['antecedent_items'])
                consequent = str(row['consequent_items'])[:25] + "..." if len(str(row['consequent_items'])) > 25 else str(row['consequent_items'])
                return f"#{idx+1}. {antecedent} → {consequent}"
            
            filtered_rules_copy['rule_label'] = [
                create_rule_label(row, idx) 
                for idx, (_, row) in enumerate(filtered_rules_copy.iterrows())
            ]
            
            # Business Impact Analysis - Simplified to single column
            with st.expander("ℹ️ About Business Impact Score", expanded=False):
                st.info("""
                **Business Impact Score** = Lift × Confidence × Support × 1000
                
                This score combines three key factors:
                - **Lift**: How much more likely customers are to buy both products together
                - **Confidence**: Probability that the recommendation will succeed
                - **Support**: How often this combination occurs in transactions
                
                **Higher score = Higher business value** - Focus on top rules for maximum revenue impact.
                """)
            
            top_impact = filtered_rules_copy.nlargest(10, 'business_impact').reset_index(drop=True)
            
            # Use go.Bar with product names inside chart (like dashboard overview)
            fig_impact = go.Figure()
            
            for i, (idx, row) in enumerate(top_impact.iterrows()):
                # Create short labels for inside chart (similar to dashboard)
                antecedent_short = ' '.join(str(row['antecedent_items']).split()[:2])
                if len(antecedent_short) > 18:
                    antecedent_short = antecedent_short[:15] + "..."
                
                consequent_short = ' '.join(str(row['consequent_items']).split()[:2])
                if len(consequent_short) > 18:
                    consequent_short = consequent_short[:15] + "..."
                
                # Text inside bar
                inside_text = f"{antecedent_short} → {consequent_short}<br>Score: {row['business_impact']:.1f}"
                
                fig_impact.add_trace(go.Bar(
                    y=[f"#{i+1}"],
                    x=[row['business_impact']],
                    orientation='h',
                    marker=dict(
                        color='#10b981' if i == 0 else '#6366f1',
                        line=dict(color='rgba(255,255,255,0.2)', width=0.8),
                        opacity=0.9
                    ),
                    text=inside_text,
                    textposition='inside',
                    insidetextanchor='middle',
                    textfont=dict(color='rgba(255,255,255,0.95)', size=9),
                    hovertemplate=(
                        '<b>Rule #%{y}</b><br>' +
                        f'If: {row["antecedent_items"]}<br>' +
                        f'Then: {row["consequent_items"]}<br>' +
                        'Business Impact: %{x:.1f}<br>' +
                        f'Lift: {row["lift"]:.2f} | Confidence: {row["confidence"]:.1%}' +
                        '<extra></extra>'
                    ),
                    showlegend=False
                ))
            
            fig_impact.update_layout(
                title=dict(
                    text="🎯 Top 10 Rules by Business Impact",
                    font=dict(size=16, color='rgba(255,255,255,0.95)')
                ),
                xaxis=dict(
                    title='Business Impact Score',
                    titlefont=dict(color='rgba(255,255,255,0.9)'),
                    tickfont=dict(color='rgba(255,255,255,0.8)'),
                    gridcolor='rgba(255,255,255,0.1)',
                    showgrid=True
                ),
                yaxis=dict(
                    title='',
                    tickfont=dict(color='rgba(255,255,255,0.9)', size=10),
                    categoryorder='total ascending'
                ),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                height=500,
                template='plotly_dark',
                margin=dict(l=0, r=0, t=50, b=10),
                showlegend=False
            )
            
            st.plotly_chart(fig_impact, use_container_width=True)
            
            # Business Actionable Insights
            st.markdown("**💡 Actionable Business Insights:**")
            
            strong_count = len(filtered_rules[filtered_rules['lift_category'] == 'Strong'])
            moderate_count = len(filtered_rules[filtered_rules['lift_category'] == 'Moderate'])
            weak_count = len(filtered_rules[filtered_rules['lift_category'] == 'Weak'])
            
            # Calculate potential revenue impact
            total_transactions = summary.get('total_transactions', 0)
            high_confidence_rules = len(filtered_rules[filtered_rules['confidence'] >= 0.7])
            
            insights_html = f"""
            <div style='background-color: rgba(13,8,135,0.2); padding: 15px; border-radius: 10px; margin: 10px 0;'>
                <h4 style='color: rgba(255,255,255,0.95); margin-bottom: 10px;'>📈 Key Findings:</h4>
                <ul style='color: rgba(255,255,255,0.9); line-height: 1.8;'>
                    <li><strong>{strong_count} High-Value Rules:</strong> Create product bundles for maximum cross-sell impact</li>
                    <li><strong>{high_confidence_rules} High-Confidence Rules:</strong> {high_confidence_rules/len(filtered_rules)*100:.0f}% of rules have >70% confidence - very reliable for recommendations</li>
                    <li><strong>Top Rule Impact:</strong> Score of {top_impact['business_impact'].iloc[0]:.1f} - prioritize this association</li>
                    <li><strong>Moderate Opportunities:</strong> {moderate_count} rules suitable for promotional campaigns</li>
                </ul>
            </div>
            """
            st.markdown(insights_html, unsafe_allow_html=True)
            
        else:
            st.warning("No association rules found with current filters. Try adjusting the thresholds.")
    
    # ========================================================================
    # FREQUENTLY BOUGHT TOGETHER
    # ========================================================================
    
    st.markdown("---")
    st.markdown("### 🛍️ Frequently Bought Together")
    with st.expander("ℹ️ About Product Pairs", expanded=False):
        st.info("""
        This section shows products that are frequently purchased together in the same transaction.
        
        **Support**: Percentage of all transactions where both products appear together.
        - Example: 5% support = these products appear together in 5 out of 100 transactions.
        
        **Use Cases**:
        - Create product bundles
        - Place products near each other in store/website
        - Design promotional campaigns
        - Optimize inventory placement
        """)
    
    if 'mba_itemsets' in st.session_state:
        pairs_df = analyzer.get_frequently_bought_together(top_n=20)
        
        if not pairs_df.empty:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.dataframe(
                    pairs_df.style.format({
                    'support': '{:.2%}',
                    'support_count': '{:,.0f}'
                }),
                    use_container_width=True,
                    height=400
                )
            
            with col2:
                # Top pairs visualization with product names inside chart
                top_pairs = pairs_df.head(10).copy()
                
                # Function to truncate product names intelligently
                def truncate_product_name(name, max_length=35):
                    """Truncate product name intelligently, preserving important parts"""
                    name_str = str(name)
                    if len(name_str) <= max_length:
                        return name_str
                    
                    # Try to truncate at common delimiters
                    for delimiter in [',', '.', ' ', '-']:
                        if delimiter in name_str:
                            parts = name_str.split(delimiter, 1)
                            if len(parts[0]) <= max_length - 3:
                                return parts[0] + "..."
                    
                    # If no delimiter found, truncate at max_length
                    return name_str[:max_length-3] + "..."
                
                # Create combined product pair labels with truncated names
                top_pairs['pair_label'] = top_pairs.apply(
                    lambda row: f"{truncate_product_name(row['product_1_name'])} + {truncate_product_name(row['product_2_name'])}", 
                    axis=1
                )
                
                # Store full names for hover tooltip
                top_pairs['full_pair_label'] = top_pairs.apply(
                    lambda row: f"{row['product_1_name']} + {row['product_2_name']}", 
                    axis=1
                )
                
                # Create figure using go.Bar for better text control
                fig_pairs = go.Figure()
                
                fig_pairs.add_trace(go.Bar(
                    x=top_pairs['support'],
                    y=top_pairs['pair_label'],
                    orientation='h',
                    marker=dict(
                        color=top_pairs['support'],
                        colorscale='Plasma',
                        line=dict(color='rgba(255,255,255,0.2)', width=0.8),
                        opacity=0.9
                    ),
                    text=[f"{val:.1%}" for val in top_pairs['support']],
                    textposition='inside',
                    textfont=dict(color='rgba(255,255,255,0.95)', size=11, family='Arial Black'),
                    customdata=top_pairs['full_pair_label'],
                    hovertemplate='<b>%{customdata}</b><br>Support: %{text}<extra></extra>',
                    name='Product Pairs'
                ))
                
                fig_pairs.update_layout(
                    title=dict(
                        text="🛍️ Top 10 Product Pairs",
                        font=dict(size=16, color='rgba(255,255,255,0.95)')
                    ),
                    xaxis=dict(
                        title='Support (%)',
                        titlefont=dict(color='rgba(255,255,255,0.9)'),
                        tickfont=dict(color='rgba(255,255,255,0.8)'),
                        gridcolor='rgba(255,255,255,0.1)'
                    ),
                    yaxis=dict(
                        title='',
                        tickfont=dict(color='rgba(255,255,255,0.9)', size=10),
                        autorange='reversed'
                    ),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    height=500,
                    template='plotly_dark',
                    margin=dict(l=5, r=10, t=50, b=10),
                    showlegend=False
                )
                
                st.plotly_chart(fig_pairs, use_container_width=True)
        else:
            st.info("No frequent pairs found. Try lowering the minimum support threshold.")
    
    # ========================================================================
    # PRODUCT RECOMMENDATIONS
    # ========================================================================
    
    st.markdown("---")
    st.markdown("### 💡 Product Recommendations")
    with st.expander("ℹ️ How Product Recommendations Work", expanded=False):
        st.info("""
        Select a product to see which other products you should recommend to customers who buy it.
        
        **Recommendations are based on**:
        - **Lift**: How much more likely customers are to buy the recommended product
        - **Confidence**: Probability that the recommendation will be successful
        
        **Best Practices**:
        - Focus on recommendations with Lift > 1.5 and Confidence > 70%
        - Use these for automated product suggestions on your website
        - Create targeted email campaigns for specific product combinations
        """)
    
    # Get product list
    if '9_Item_Master.csv' in project2_data:
        item_master = project2_data['9_Item_Master.csv']
        product_options = item_master['product_name'].tolist() if 'product_name' in item_master.columns else []
    else:
        product_options = sales_details[product_name_col].unique().tolist() if product_name_col in sales_details.columns else []
    
    if product_options:
        selected_product = st.selectbox(
            "Select a product to get recommendations:",
            options=product_options[:100]  # Limit for performance
        )
        
        if selected_product and 'mba_rules' in st.session_state:
            # Get product ID
            if '9_Item_Master.csv' in project2_data:
                item_master = project2_data['9_Item_Master.csv']
                product_id = item_master[item_master[product_name_col] == selected_product][product_id_col].iloc[0] if product_id_col in item_master.columns else None
            else:
                product_id = sales_details[sales_details[product_name_col] == selected_product][product_id_col].iloc[0] if product_id_col in sales_details.columns else None
            
            if product_id:
                recommendations = analyzer.get_product_recommendations(str(product_id), top_n=10)
                
                if recommendations:
                    rec_df = pd.DataFrame(recommendations)
                    
                    st.success(f"Found {len(recommendations)} recommendations for **{selected_product}**")
                    
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.dataframe(
                            rec_df[['product_name', 'confidence', 'lift', 'rule']].style.format({
                                'confidence': '{:.2%}',
                                'lift': '{:.2f}'
                            }),
                            use_container_width=True,
                            height=300
                        )
                    
                    with col2:
                        # Recommendation strength chart - Smooth gradient
                        fig_rec = px.bar(
                            rec_df,
                            x='lift',
                            y='product_name',
                            orientation='h',
                            title="Recommendation Strength",
                            labels={'lift': 'Lift', 'product_name': 'Recommended Product'},
                            color='lift',
                            color_continuous_scale='Plasma',
                            text=rec_df['lift']
                        )
                        fig_rec.update_traces(
                            texttemplate='%{text:.2f}',
                            marker=dict(
                                line=dict(color='rgba(255,255,255,0.15)', width=0.5),
                                opacity=0.85
                            )
                        )
                        fig_rec.update_layout(
                            plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)',
                            font=dict(color='rgba(255,255,255,0.9)'),
                            height=300,
                            coloraxis_showscale=False,
                            template='plotly_dark'
                        )
                        st.plotly_chart(fig_rec, use_container_width=True)
                else:
                    st.info(f"No recommendations found for {selected_product}. Try adjusting the analysis parameters.")
    
    # ========================================================================
    # CROSS-SELLING OPPORTUNITIES
    # ========================================================================
    
    st.markdown("---")
    st.markdown("### 🎯 Cross-Selling Opportunities")
    st.info("💡 **Tip**: Use the filter options in 'Association Rules' section above to view cross-selling opportunities. Filter by 'Strong' or 'Moderate' lift category to see the best opportunities.")
    
    if 'mba_rules' in st.session_state:
        opportunities = analyzer.get_cross_selling_opportunities()
        
        if not opportunities.empty:
            st.success(f"Found {len(opportunities):,} cross-selling opportunities")
            
            # Business Actionable Recommendations - Focus on actionable insights, not redundant table
            st.markdown("#### 💼 Strategic Business Recommendations")
            
            # Calculate top opportunities with business context
            top_opps = opportunities.head(20).copy()
            
            # Create business impact score
            top_opps['business_value'] = (
                top_opps['lift'] * 
                top_opps['confidence'] * 
                top_opps['transactions']
            ).round(0)
            
            # Sort by business value
            top_opps = top_opps.sort_values('business_value', ascending=False)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**🎯 Top 5 High-Value Opportunities:**")
                with st.expander("ℹ️ How to Read These Opportunities", expanded=False):
                    st.info("""
                    Each opportunity shows:
                    - **When customer buys**: The trigger product
                    - **Recommend**: The product to suggest
                    - **Strength**: Association strength (Very Strong = Lift > 3.0, Strong = 1.5-3.0, Moderate = 1.0-1.5)
                    - **Success Rate**: Probability of successful cross-sell (Confidence %)
                    - **Potential**: Number of transactions where this can be applied
                    
                    **Action**: Prioritize opportunities with "Very Strong" strength and high success rates.
                    """)
                
                # Display top 5 opportunities in a clear, actionable format with full text
                for idx, (_, opp) in enumerate(top_opps.head(5).iterrows(), 1):
                    success_rate = opp['confidence'] * 100
                    strength = "🔥 Very Strong" if opp['lift'] > 3.0 else "✅ Strong" if opp['lift'] > 1.5 else "📊 Moderate"
                    
                    # Get full product names without truncation
                    trigger_product = str(opp['if_customer_buys'])
                    recommend_product = str(opp['recommend'])
                    
                    opp_html = f"""
                    <div style='background-color: rgba(13,8,135,0.15); padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 4px solid rgba(253,174,97,0.8);'>
                        <div style='color: rgba(255,255,255,0.95); font-weight: bold; margin-bottom: 8px; font-size: 1.05em;'>
                            #{idx}. When customer buys:
                        </div>
                        <div style='color: rgba(253,174,97,0.9); font-size: 0.95em; margin-bottom: 10px; padding-left: 10px; word-wrap: break-word;'>
                            {trigger_product}
                        </div>
                        <div style='color: rgba(255,255,255,0.95); font-weight: bold; margin-bottom: 8px; font-size: 1.05em;'>
                            → Recommend:
                        </div>
                        <div style='color: rgba(255,255,255,0.9); font-size: 0.95em; margin-bottom: 10px; padding-left: 10px; word-wrap: break-word; font-weight: 500;'>
                            {recommend_product}
                        </div>
                        <div style='color: rgba(255,255,255,0.85); font-size: 0.9em; padding-top: 8px; border-top: 1px solid rgba(255,255,255,0.1);'>
                            {strength} | Success Rate: {success_rate:.0f}% | Potential: {opp['transactions']:,.0f} transactions
                        </div>
                    </div>
                    """
                    st.markdown(opp_html, unsafe_allow_html=True)
            
            with col2:
                st.markdown("**📊 Opportunity Summary:**")
                
                # Calculate summary metrics
                total_potential = top_opps['transactions'].sum()
                avg_success_rate = top_opps['confidence'].mean() * 100
                strong_opps = len(top_opps[top_opps['lift'] > 3.0])
                high_confidence_opps = len(top_opps[top_opps['confidence'] >= 0.7])
                
                # Summary metrics
                st.metric(
                    "Total Potential Transactions",
                    f"{total_potential:,.0f}",
                    help="Total number of transactions where cross-selling can be applied"
                )
                st.metric(
                    "Average Success Rate",
                    f"{avg_success_rate:.1f}%",
                    help="Average probability of successful cross-sell recommendation"
                )
                st.metric(
                    "Very Strong Opportunities",
                    f"{strong_opps}",
                    help="Number of opportunities with lift > 3.0 (highly effective)"
                )
                st.metric(
                    "High-Confidence Opportunities",
                    f"{high_confidence_opps}",
                    help="Number of opportunities with >70% success probability"
                )
                
                # Visual summary - Distribution by strength
                strength_dist = pd.DataFrame({
                    'Strength': ['Very Strong\n(Lift > 3.0)', 'Strong\n(Lift 1.5-3.0)', 'Moderate\n(Lift 1.0-1.5)'],
                    'Count': [
                        len(top_opps[top_opps['lift'] > 3.0]),
                        len(top_opps[(top_opps['lift'] > 1.5) & (top_opps['lift'] <= 3.0)]),
                        len(top_opps[(top_opps['lift'] >= 1.0) & (top_opps['lift'] <= 1.5)])
                    ]
                })
                
                
                # Actionable insights
                st.markdown("**💡 Key Insights:**")
                insights_text = f"""
                <div style='background-color: rgba(13,8,135,0.2); padding: 12px; border-radius: 8px; margin-top: 10px;'>
                    <ul style='color: rgba(255,255,255,0.9); line-height: 1.6; font-size: 0.9em; margin: 0; padding-left: 20px;'>
                        <li>Focus on top 5 opportunities for maximum impact</li>
                        <li>{strong_opps} very strong opportunities - prioritize these</li>
                        <li>Average {avg_success_rate:.0f}% success rate - highly reliable</li>
                        <li>Potential to increase sales through {total_potential:,.0f} cross-sell transactions</li>
                    </ul>
                </div>
                """
                st.markdown(insights_text, unsafe_allow_html=True)
        else:
            st.info("No cross-selling opportunities found. Try adjusting the analysis parameters.")
    
    # ========================================================================
    # INSIGHTS & SUMMARY
    # ========================================================================
    
    st.markdown("---")
    st.markdown("### 📋 Analysis Summary")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Key Insights")
        
        if 'mba_rules' in st.session_state and not st.session_state['mba_rules'].empty:
            rules_df = st.session_state['mba_rules']
            
            strong_rules = len(rules_df[rules_df['lift_category'] == 'Strong'])
            moderate_rules = len(rules_df[rules_df['lift_category'] == 'Moderate'])
            avg_lift = rules_df['lift'].mean()
            avg_confidence = rules_df['confidence'].mean()
            
            st.markdown(f"""
            - **Strong Associations:** {strong_rules} rules (lift > 3.0)
            - **Moderate Associations:** {moderate_rules} rules (lift 1.5-3.0)
            - **Average Lift:** {avg_lift:.2f}
            - **Average Confidence:** {avg_confidence:.2%}
            """)
        else:
            st.info("Run analysis to see insights")
    
    with col2:
        st.markdown("#### Business Recommendations")
        
        if 'mba_rules' in st.session_state and not st.session_state['mba_rules'].empty:
            st.markdown("""
            1. **Bundle Products:** Create product bundles based on strong associations
            2. **Cross-Sell:** Recommend products with high lift values
            3. **Promotions:** Target products with moderate associations for promotions
            4. **Inventory:** Stock related products together for better visibility
            5. **Marketing:** Use association rules for targeted marketing campaigns
            """)
        else:
            st.info("Run analysis to see recommendations")
    
    # ========================================================================
    # EXPORT OPTIONS
    # ========================================================================
    
    st.markdown("---")
    st.markdown("### 📥 Export Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if 'mba_rules' in st.session_state and not st.session_state['mba_rules'].empty:
            csv = st.session_state['mba_rules'].to_csv(index=False)
            st.download_button(
                label="📊 Download Association Rules (CSV)",
                data=csv,
                file_name=f"mba_association_rules_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    with col2:
        if 'mba_itemsets' in st.session_state:
            summary = analyzer.export_summary()
            st.json(summary)
    
    log_activity("Viewed Market Basket Analysis", "#6366f1")

