"""
Page Template - Use this as reference for new pages
=====================================================

Template standar untuk membuat halaman baru.
Copy file ini dan modify sesuai kebutuhan page Anda.

Author: Data Science Team
Date: 2025-11-18
"""

import streamlit as st
import pandas as pd
from modules.data_loader import load_master_data, get_filtered_data, get_quick_stats
from modules.activity_logger import log_activity
from modules.ui_components import (
    render_page_header,
    render_metric_card,
    render_alert_box,
    render_filter_row,
    render_data_table
)
from modules.session_manager import toggle_visibility, get_session_value
from utils.formatters import format_percentage, format_currency, format_number
from utils.helpers import (
    safe_divide,
    calculate_percentage,
    get_risk_color,
    truncate_text
)
from config.constants import COLORS


# ============================================================================
# SECTION 1: HELPER FUNCTIONS (Business Logic)
# ============================================================================

def helper_calculate_metrics(df: pd.DataFrame) -> dict:
    """
    Calculate metrics spesifik untuk halaman ini.
    
    Fungsi internal - jangan dipanggil dari luar module.
    
    Args:
        df (pd.DataFrame): Master data
        
    Returns:
        dict: Calculated metrics
    """
    
    metrics = {
        'total': len(df),
        'active': len(df[df['current_stock_qty'] > 0]),
        'inactive': len(df[df['current_stock_qty'] == 0]),
    }
    
    return metrics


def helper_process_data(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """
    Process dan filter data berdasarkan user selections.
    
    Args:
        df (pd.DataFrame): Master data
        filters (dict): Filter criteria dari UI
        
    Returns:
        pd.DataFrame: Processed data
    """
    
    processed = get_filtered_data(
        df,
        search_term=filters.get('search', ''),
        category_filter=filters.get('category', 'All'),
        abc_class_filter=filters.get('abc_class', 'All')
    )
    
    return processed


# ============================================================================
# SECTION 2: RENDER COMPONENTS (UI Building Blocks)
# ============================================================================

def render_header_section():
    """Render halaman header dengan title dan description."""
    
    render_page_header(
        title="Page Title",
        description="Deskripsi halaman singkat",
        icon="🎯"
    )


def render_filter_section() -> dict:
    """
    Render filter controls dan return filter selections.
    
    Returns:
        dict: Selected filter values
    """
    
    st.markdown("### Filters")
    
    filters = render_filter_row([
        {
            'type': 'text_input',
            'label': 'Search',
            'key': 'search',
            'placeholder': 'Search by code or name...'
        },
        {
            'type': 'selectbox',
            'label': 'Category',
            'key': 'category',
            'options': ['All', 'Category A', 'Category B']
        },
        {
            'type': 'selectbox',
            'label': 'ABC Class',
            'key': 'abc_class',
            'options': ['All', 'A', 'B', 'C']
        }
    ])
    
    return filters


def render_metrics_section(metrics: dict):
    """Render key metrics sebagai cards."""
    
    st.markdown("### Key Metrics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        render_metric_card(
            label="Total Items",
            value=f"{metrics['total']:,}",
            insight="Total monitored items"
        )
    
    with col2:
        render_metric_card(
            label="Active",
            value=f"{metrics['active']:,}",
            delta=f"{calculate_percentage(metrics['active'], metrics['total']):.0f}%",
            delta_positive=True
        )
    
    with col3:
        render_metric_card(
            label="Inactive",
            value=f"{metrics['inactive']:,}",
            delta=f"{calculate_percentage(metrics['inactive'], metrics['total']):.0f}%",
            delta_positive=False
        )


def render_data_section(df: pd.DataFrame):
    """Render data table dengan search dan sorting."""
    
    st.markdown("### Data Table")
    
    if len(df) == 0:
        st.info("No data available")
        return
    
    render_data_table(
        df,
        title="",
        max_rows=100,
        searchable=True
    )


def render_details_section(df: pd.DataFrame):
    """Render detailed view untuk selected item (expandable)."""
    
    st.markdown("### Details")
    
    if len(df) == 0:
        return
    
    # Option 1: Using expander
    with st.expander("Show Details"):
        st.json(df.head(1).to_dict(orient='records')[0])
    
    # Option 2: Using tabs
    if len(df) > 0:
        tab1, tab2, tab3 = st.tabs(["Overview", "Statistics", "Export"])
        
        with tab1:
            st.dataframe(df[['product_code', 'product_name', 'current_stock_qty']])
        
        with tab2:
            st.write("Statistical summary would go here")
        
        with tab3:
            if st.button("Download as CSV"):
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download",
                    data=csv,
                    file_name="export.csv",
                    mime="text/csv"
                )


def render_action_section():
    """Render action buttons."""
    
    st.markdown("### Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Refresh", width='stretch'):
            st.cache_data.clear()
            log_activity("Refreshed data", "#10b981")
            st.rerun()
    
    with col2:
        if st.button("📊 Export", width='stretch'):
            log_activity("Initiated export", "#3b82f6")
            st.info("Export functionality would be implemented here")
    
    with col3:
        if st.button("⚙️ Settings", width='stretch'):
            log_activity("Opened settings", "#f59e0b")
            st.info("Settings functionality would be implemented here")


# ============================================================================
# SECTION 3: MAIN PAGE RENDER FUNCTION
# ============================================================================

def render_page():
    """
    Main function untuk render halaman.
    
    Dipanggil dari main.py:
        from modules.pages.page_template import render_page
        render_page()
    
    Structure:
        1. Setup halaman
        2. Load data
        3. Render sections
        4. Log activity
    """
    
    # 1. SETUP HALAMAN
    render_header_section()
    log_activity("Viewed Page Template", "#6366f1")
    
    # 2. LOAD DATA
    df = load_master_data()
    
    if df.empty:
        st.error("Failed to load data")
        return
    
    # 3. RENDER MAIN SECTIONS
    
    # Filter section
    st.divider()
    filters = render_filter_section()
    
    # Process data
    filtered_df = helper_process_data(df, filters)
    
    # Metrics section
    st.divider()
    metrics = helper_calculate_metrics(filtered_df)
    render_metrics_section(metrics)
    
    # Data section
    st.divider()
    render_data_section(filtered_df)
    
    # Details section
    st.divider()
    render_details_section(filtered_df.head(10))
    
    # Actions section
    st.divider()
    render_action_section()
    
    # Info message
    st.info("Template page - customize this as needed")
