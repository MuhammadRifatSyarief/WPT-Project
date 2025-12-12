# Implementation Guide - Modular Inventory System

Panduan lengkap untuk mengimplementasikan pages dan fitur tambahan.

---

## Quick Start

### Setup Aplikasi

\`\`\`bash
# 1. Clone/setup project
cd inventory-intelligence

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Verify master data file
# master_features_final.csv harus ada di root directory

# 5. Run aplikasi
streamlit run main.py
\`\`\`

---

## Implementing Dashboard Page

Sebagai contoh, dashboard sudah diimplementasikan di `modules/pages/dashboard.py`.

### Structure Template untuk Page Baru

\`\`\`python
"""
Page Title
===========

Deskripsi page dan functionality.
"""

import streamlit as st
from modules.data_loader import load_master_data, get_quick_stats
from modules.activity_logger import log_activity
from modules.ui_components import render_page_header

def helper_function_for_page():
    """Helper functions spesifik untuk page ini."""
    pass

def render_page():
    """Main function untuk render page."""
    
    # 1. Setup page
    render_page_header("Title", "Description", "🎯")
    log_activity("Viewed Page", "#6366f1")
    
    # 2. Load data
    df = load_master_data()
    
    # 3. Process data
    processed_data = df[...].copy()
    
    # 4. Render components
    st.markdown("### Section Title")
    st.dataframe(processed_data)
    
    # 5. Optional: Actions
    if st.button("Action Button"):
        log_activity("Action performed", "#10b981")
\`\`\`

---

## Implementing Forecasting Page

### Requirements Analysis

**Input:**
- Product selection / search
- Forecast days (7-90)
- Category filter
- ABC class filter

**Output:**
- Forecast chart (Plotly)
- Statistical metrics
- Trend analysis
- Export options

### Implementation Steps

#### Step 1: Create Page File

\`\`\`bash
touch modules/pages/forecasting.py
\`\`\`

#### Step 2: Implement Core Logic

\`\`\`python
"""
Demand Forecasting Page
========================

Memprediksi permintaan produk di masa depan.
"""

import streamlit as st
import plotly.graph_objects as go
from modules.data_loader import load_master_data, get_filtered_data
from modules.ui_components import (
    render_page_header,
    render_filter_row,
    render_metric_card
)
from modules.activity_logger import log_activity
from utils.formatters import format_number

def calculate_forecast(sales_history, forecast_days):
    """
    Simple forecast menggunakan moving average.
    Bisa diganti dengan algoritma yang lebih sophisticated.
    """
    # Implementation
    pass

def render_page():
    render_page_header("Demand Forecasting", "Predict future demand", "📈")
    log_activity("Viewed Forecasting Page", "#6366f1")
    
    df = load_master_data()
    
    # Filters
    filters = render_filter_row([
        {'type': 'text_input', 'label': 'Search Product', 'key': 'search'},
        {'type': 'slider', 'label': 'Forecast Days', 'key': 'days', 
         'min_value': 7, 'max_value': 90, 'value': 30}
    ])
    
    # Filter data
    filtered_df = get_filtered_data(df, search_term=filters.get('search', ''))
    
    if len(filtered_df) == 0:
        st.info("No products found")
        return
    
    # Display forecast
    for idx, row in filtered_df.head(5).iterrows():
        forecast = calculate_forecast(row['sales_history'], filters['days'])
        st.write(f"Product: {row['product_name']}")
\`\`\`

#### Step 3: Register Page in main.py

\`\`\`python
from modules.pages import forecasting

# Add to routing:
elif "Demand Forecasting" in page:
    log_activity("Navigated to Forecasting", "#6366f1")
    forecasting.render_page()
\`\`\`

---

## Implementing Inventory Health Page

### Key Metrics

1. **Overall Health Score** (0-100%)
2. **Stock Coverage** (days)
3. **Turnover Rate** (annual)
4. **ABC Distribution**

### Template Implementation

\`\`\`python
def render_health_metrics(df):
    """Calculate health metrics."""
    
    # Health score
    service_level = (df['current_stock_qty'] > 0).sum() / len(df) * 100
    health_score = service_level * 0.9
    
    # Stock coverage
    avg_coverage = (df['current_stock_qty'] / df['avg_daily_demand']).mean()
    
    # Turnover
    turnover = (df['total_sales_90d'].sum() / df['stock_value'].sum()) * (365/90)
    
    return {
        'health_score': health_score,
        'avg_coverage': avg_coverage,
        'turnover': turnover
    }
\`\`\`

---

## Implementing Stockout Alerts Page

### Alert Levels

\`\`\`python
ALERT_LEVELS = {
    'Critical': (0, 7, '#ef4444'),        # < 7 days
    'High': (7, 14, '#f59e0b'),          # 7-14 days
    'Medium': (14, 30, '#3b82f6'),       # 14-30 days
    'Low': (30, float('inf'), '#10b981') # > 30 days
}
\`\`\`

### Template Implementation

\`\`\`python
def get_alert_level(days_until_stockout):
    """Determine alert level based on days."""
    
    for level, (min_days, max_days, color) in ALERT_LEVELS.items():
        if min_days <= days_until_stockout < max_days:
            return level, color
    
    return 'Unknown', '#666666'

def render_alerts():
    """Render alert categories."""
    
    df = load_master_data()
    
    # Group by alert level
    critical = df[df['days_until_stockout'] < 7]
    high = df[(df['days_until_stockout'] >= 7) & (df['days_until_stockout'] < 14)]
    
    # Render
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Critical", len(critical))
    with col2:
        st.metric("High", len(high))
\`\`\`

---

## Implementing Reorder Optimization Page

### Formulas

\`\`\`
Safety Stock = Z × σ × √LT
ROP = (Avg Demand × Lead Time) + Safety Stock
EOQ = √((2 × D × S) / H)
\`\`\`

### Template Implementation

\`\`\`python
import math

def calculate_safety_stock(std_dev, lead_time, z_score=1.65):
    """Calculate safety stock."""
    return z_score * std_dev * math.sqrt(lead_time)

def calculate_reorder_point(avg_demand, lead_time, safety_stock):
    """Calculate reorder point."""
    return (avg_demand * lead_time) + safety_stock

def calculate_eoq(annual_demand, ordering_cost, holding_cost):
    """Calculate Economic Order Quantity."""
    return math.sqrt((2 * annual_demand * ordering_cost) / holding_cost)
\`\`\`

---

## Implementing Slow-Moving Analysis Page

### Criteria

\`\`\`python
SLOW_MOVING_CRITERIA = {
    'turnover_threshold': 1.0,      # < 1.0x per 90 days
    'stock_age_days': 60,           # > 60 days
    'daily_demand_low': 2.0         # < 2 units/day
}
\`\`\`

### Template Implementation

\`\`\`python
def identify_slow_movers(df):
    """Identify slow-moving products."""
    
    slow_movers = df[
        (df['turnover_ratio_90d'] < SLOW_MOVING_CRITERIA['turnover_threshold']) &
        (df['stock_age_days'] > SLOW_MOVING_CRITERIA['stock_age_days'])
    ]
    
    return slow_movers

def recommend_actions(slow_movers_df):
    """Recommend actions for slow-movers."""
    
    actions = []
    
    for idx, row in slow_movers_df.iterrows():
        tied_capital = row['stock_value']
        
        if tied_capital > 10_000_000:
            actions.append(f"Promote {row['product_name']} - High tied capital")
        else:
            actions.append(f"Consider discontinuing {row['product_name']}")
    
    return actions
\`\`\`

---

## Implementing Settings Page

### Email Configuration

\`\`\`python
def render_email_settings():
    """Render email configuration form."""
    
    st.markdown("### Email Configuration")
    
    with st.form("email_config"):
        sender = st.text_input("Sender Email")
        password = st.text_input("App Password", type="password")
        recipients = st.text_area("Recipients (comma-separated)")
        
        if st.form_submit_button("Save Settings"):
            # Validate
            if validate_email(sender):
                st.session_state.email_sender = sender
                st.session_state.email_password = password
                st.session_state.email_recipients = recipients
                log_activity("Email settings updated", "#10b981")
                st.success("Settings saved!")
            else:
                st.error("Invalid email format")
\`\`\`

---

## Adding New Features

### Feature: Export to Excel

\`\`\`python
# utils/exporters.py

import openpyxl
from datetime import datetime

def export_to_excel(data_dict, filename_prefix="report"):
    """Export multiple dataframes ke Excel dengan multiple sheets."""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.xlsx"
    
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        for sheet_name, df in data_dict.items():
            df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
    
    return filename
\`\`\`

### Feature: Advanced Forecasting

\`\`\`python
# modules/forecasting_advanced.py

from scipy import stats

def forecast_with_trend(data, forecast_days):
    """Forecast menggunakan linear regression."""
    
    x = np.arange(len(data))
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, data)
    
    future_x = np.arange(len(data), len(data) + forecast_days)
    forecast = slope * future_x + intercept
    
    return forecast
\`\`\`

---

## Common Patterns

### Pattern 1: Filter dan Display Data

\`\`\`python
def render_filtered_table():
    # Filters
    search = st.text_input("Search")
    category = st.selectbox("Category", categories)
    
    # Filter
    filtered_df = get_filtered_data(df, search_term=search, category_filter=category)
    
    # Display
    st.dataframe(filtered_df)
\`\`\`

### Pattern 2: Metric Cards dengan Popovers

\`\`\`python
def render_metric_with_help():
    col1, col2 = st.columns([0.9, 0.1])
    
    with col1:
        render_metric_card("Label", "Value")
    
    with col2:
        with st.popover("ℹ️"):
            st.markdown("Help text here")
\`\`\`

### Pattern 3: Tab Organization

\`\`\`python
tab1, tab2, tab3 = st.tabs(["Overview", "Details", "Export"])

with tab1:
    # Content 1
    pass

with tab2:
    # Content 2
    pass

with tab3:
    # Content 3
    pass
\`\`\`

---

## Best Practices Checklist

- [ ] Use constants from `config/constants.py`
- [ ] Use formatters from `utils/formatters.py`
- [ ] Log important actions with `log_activity()`
- [ ] Add docstrings ke semua functions
- [ ] Validate user input sebelum processing
- [ ] Handle exceptions dengan try-except
- [ ] Cache expensive operations
- [ ] Make components reusable
- [ ] Test halaman secara manual
- [ ] Update documentation

---

## Troubleshooting Common Issues

### Issue: Import Error

\`\`\`
ModuleNotFoundError: No module named 'config'
\`\`\`

**Solution:** Run dari root directory:
\`\`\`bash
streamlit run main.py
\`\`\`

### Issue: Data Not Loading

**Solution:** Check if CSV file exists dan path correct di `data_loader.py`

### Issue: Email Sending Fails

**Checklist:**
1. Use Gmail app password (16-character)
2. Verify recipient email format
3. Check SMTP settings di constants.py
4. Enable "Less secure apps" in Gmail

### Issue: Performance is Slow

**Solutions:**
1. Clear Streamlit cache: `streamlit cache clear`
2. Filter data earlier in pipeline
3. Reduce row display limit
4. Enable data caching TTL

---

## Next Steps

1. Implement remaining pages following templates
2. Add advanced forecasting algorithms
3. Integrate with external APIs if needed
4. Add unit tests
5. Performance optimization
6. User testing
7. Production deployment

---

**Last Updated:** 2025-11-18  
**Author:** Data Science Team
