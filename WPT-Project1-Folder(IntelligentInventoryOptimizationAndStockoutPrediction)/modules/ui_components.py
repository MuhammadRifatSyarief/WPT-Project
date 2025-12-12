"""
Reusable UI Components Module
==============================

Modul ini berisi reusable UI components yang digunakan di berbagai pages.
Setiap component mendukung customization dan styling konsisten.

Author: Data Science Team
Date: 2025-11-18
Version: 1.0
"""

import streamlit as st
import pandas as pd
from config.constants import COLORS, POPOVERS


def render_metric_card(label: str,
                      value: str,
                      delta: str = '',
                      delta_positive: bool = True,
                      insight: str = '',
                      popover_info: str = '') -> None:
    """
    Render metric card dengan styling konsisten.
    
    Args:
        label (str): Label metrik
        value (str): Nilai metrik utama
        delta (str): Delta/perubahan value (optional)
        delta_positive (bool): Apakah delta positif atau negatif
        insight (str): Insight text di bawah (optional)
        popover_info (str): Info untuk popover (optional)
        
    Example:
        >>> render_metric_card(
        ...     'Service Level',
        ...     '94.2%',
        ...     delta='↑ 2.1% vs last month',
        ...     delta_positive=True,
        ...     insight='Target: >95% | Status: Good'
        ... )
    """
    
    if popover_info:
        col1, col2 = st.columns([0.9, 0.1])
        with col1:
            st.markdown("")
        with col2:
            with st.popover("ℹ️"):
                st.markdown(popover_info)
    
    delta_class = 'positive' if delta_positive else 'negative'
    delta_html = f'<div class="metric-delta {delta_class}">{delta}</div>' if delta else ''
    insight_html = f'<div class="metric-insight">{insight}</div>' if insight else ''
    
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        {delta_html}
        {insight_html}
    </div>
    """, unsafe_allow_html=True)


def render_alert_box(alert_type: str,
                     title: str,
                     count: int,
                     description: str = '') -> None:
    """
    Render alert box dengan color coding berdasarkan severity.
    
    Args:
        alert_type (str): Tipe alert ('critical', 'warning', 'info', 'success')
        title (str): Alert title
        count (int): Alert count/number
        description (str): Deskripsi tambahan (optional)
        
    Example:
        >>> render_alert_box('critical', 'Critical Risk', 45, 'Stockout in <7 days')
    """
    
    color_map = {
        'critical': {'bg': 'rgba(239, 68, 68, 0.1)', 'border': '#ef4444', 'text': '#ef4444'},
        'warning': {'bg': 'rgba(245, 158, 11, 0.1)', 'border': '#f59e0b', 'text': '#f59e0b'},
        'info': {'bg': 'rgba(99, 102, 241, 0.1)', 'border': '#6366f1', 'text': '#6366f1'},
        'success': {'bg': 'rgba(16, 185, 129, 0.1)', 'border': '#10b981', 'text': '#10b981'},
    }
    
    style = color_map.get(alert_type, color_map['info'])
    
    st.markdown(f"""
    <div style="
        background: {style['bg']};
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid {style['border']};
    ">
        <h3 style="margin: 0; color: white;">{title}</h3>
        <div style="font-size: 2rem; font-weight: 700; margin: 0.5rem 0; color: {style['text']};">
            {count:,}
        </div>
        {f'<div style="color: #94a3b8; font-size: 0.9rem;">{description}</div>' if description else ''}
    </div>
    """, unsafe_allow_html=True)


def render_info_popover(title: str, info_dict: dict):
    """
    Render info popover dengan title dan info items.
    
    Args:
        title (str): Judul popover
        info_dict (dict): Dictionary berisi {label: description}
        
    Example:
        >>> info = {
        ...     'Service Level': 'Persentase pesanan terpenuhi',
        ...     'Benchmark': '>95% = Excellent'
        ... }
        >>> render_info_popover('About Service Level', info)
    """
    
    with st.popover(f"ℹ️ {title}"):
        for key, value in info_dict.items():
            st.markdown(f"**{key}:** {value}")


def render_filter_row(columns: list[dict]) -> dict:
    """
    Render filter row dengan multiple columns dan widgets.
    
    Args:
        columns (list[dict]): List of column configs:
            {
                'type': 'text_input'|'selectbox'|'slider'|'multiselect',
                'label': 'Label teks',
                'key': 'session state key',
                'options': [...] (untuk selectbox, multiselect),
                'min_value': ... (untuk slider),
                'max_value': ... (untuk slider),
                'value': ... (default value)
            }
        
    Returns:
        dict: Dictionary hasil filter dengan key: value
        
    Example:
        >>> filters = render_filter_row([
        ...     {'type': 'text_input', 'label': 'Search', 'key': 'search'},
        ...     {'type': 'selectbox', 'label': 'Category', 'key': 'category', 'options': ['All', 'A', 'B']}
        ... ])
    """
    
    cols = st.columns(len(columns))
    results = {}
    
    for i, col_config in enumerate(columns):
        with cols[i]:
            widget_type = col_config.get('type', 'text_input')
            label = col_config.get('label', 'Input')
            key = col_config.get('key', f'filter_{i}')
            
            if widget_type == 'text_input':
                results[key] = st.text_input(
                    label,
                    placeholder=col_config.get('placeholder', ''),
                    key=f"{key}_widget"
                )
            
            elif widget_type == 'selectbox':
                results[key] = st.selectbox(
                    label,
                    options=col_config.get('options', []),
                    key=f"{key}_widget"
                )
            
            elif widget_type == 'slider':
                results[key] = st.slider(
                    label,
                    min_value=col_config.get('min_value', 0),
                    max_value=col_config.get('max_value', 100),
                    value=col_config.get('value', 50),
                    key=f"{key}_widget"
                )
            
            elif widget_type == 'multiselect':
                results[key] = st.multiselect(
                    label,
                    options=col_config.get('options', []),
                    key=f"{key}_widget"
                )
    
    return results


def render_data_table(df: pd.DataFrame,
                     title: str = '',
                     max_rows: int = 100,
                     searchable: bool = True) -> pd.DataFrame:
    """
    Render data table dengan search & sorting.
    
    Args:
        df (pd.DataFrame): Data to display
        title (str): Table title (optional)
        max_rows (int): Maximum rows to display
        searchable (bool): Enable search functionality
        
    Returns:
        pd.DataFrame: Displayed data (for potential further filtering)
        
    Example:
        >>> display_df = render_data_table(df, title='Products', max_rows=50)
    """
    
    if title:
        st.markdown(f"### {title}")
    
    display_df = df.copy()
    
    if searchable and len(df) > 0:
        search_term = st.text_input("Search table...", key=f"search_{title}")
        if search_term:
            mask = display_df.astype(str).apply(
                lambda x: x.str.contains(search_term, case=False)
            ).any(axis=1)
            display_df = display_df[mask]
    
    # Limit rows
    display_df = display_df.head(max_rows)
    
    # Display table
    st.dataframe(
        display_df,
        use_container_width=True,
        height=400
    )
    
    return display_df


def render_sidebar_header(title: str, subtitle: str = ''):
    """
    Render sidebar header dengan styling.
    
    Args:
        title (str): Main title
        subtitle (str): Subtitle (optional)
        
    Example:
        >>> render_sidebar_header('Inventory Intelligence', 'PT Wahana Piranti Teknologi')
    """
    
    subtitle_html = f'<div style="font-size: 0.9rem; color: #94a3b8; font-weight: 500;">{subtitle}</div>' if subtitle else ''
    
    st.markdown(f"""
    <div style="
        text-align: center;
        padding: 1rem 0;
        border-bottom: 2px solid #334155;
        margin-bottom: 1rem;
    ">
        <div style="font-size: 1.5rem; font-weight: 700; color: #f8fafc; margin-bottom: 0.3rem;">
            {title}
        </div>
        {subtitle_html}
    </div>
    """, unsafe_allow_html=True)


def render_quick_stat_box(label: str, value: str, type_: str = 'default'):
    """
    Render quick stat box (untuk sidebar quick stats).
    
    Args:
        label (str): Stat label
        value (str): Stat value
        type_ (str): 'alert', 'products', 'updated', 'default'
        
    Example:
        >>> render_quick_stat_box('Active Alerts', '25', type_='alert')
    """
    
    color_map = {
        'alert': {'bg': 'rgba(239, 68, 68, 0.1)', 'border': '#ef4444', 'text': '#ef4444'},
        'products': {'bg': 'rgba(99, 102, 241, 0.1)', 'border': '#6366f1', 'text': '#6366f1'},
        'updated': {'bg': 'rgba(16, 185, 129, 0.1)', 'border': '#10b981', 'text': '#10b981'},
        'default': {'bg': 'rgba(99, 102, 241, 0.1)', 'border': '#6366f1', 'text': '#6366f1'},
    }
    
    style = color_map.get(type_, color_map['default'])
    
    st.markdown(f"""
    <div style="
        background: {style['bg']};
        padding: 0.8rem;
        border-radius: 8px;
        border-left: 3px solid {style['border']};
        margin-bottom: 0.5rem;
    ">
        <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase;">
            {label}
        </div>
        <div style="font-size: 1.8rem; font-weight: 700; color: {style['text']};">
            {value}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_page_header(title: str, description: str = '', icon: str = ''):
    """
    Render page header dengan title dan description.
    
    Args:
        title (str): Page title
        description (str): Page description (optional)
        icon (str): Icon untuk title (optional)
        
    Example:
        >>> render_page_header('Dashboard Overview', 'Real-time inventory metrics', '🏠')
    """
    
    full_title = f"{icon} {title}" if icon else title
    st.title(full_title)
    
    if description:
        st.markdown(description)


def apply_page_css():
    """
    Apply global CSS styling ke halaman.
    
    Harus dipanggil di awal main.py setelah st.set_page_config()
    
    Example:
        >>> apply_page_css()
    """
    
    st.markdown(f"""
    <style>
        /* Main theme colors */
        :root {{
            --primary-color: {COLORS['primary']};
            --success-color: {COLORS['success']};
            --warning-color: {COLORS['warning']};
            --danger-color: {COLORS['danger']};
            --bg-dark: {COLORS['bg_dark']};
            --bg-card: {COLORS['bg_card']};
        }}
        
        /* Hide Streamlit branding */
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        
        /* Reduce excessive spacing */
        .block-container {{
            padding-top: 2rem;
            padding-bottom: 1rem;
        }}
        
        div[data-testid="stVerticalBlock"] > div {{
            gap: 0.5rem;
        }}
        
        /* Metric card styling */
        .metric-card {{
            background: linear-gradient(135deg, {COLORS['bg_card']} 0%, #334155 100%);
            padding: 1.2rem;
            border-radius: 10px;
            border: 1px solid {COLORS['border']};
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: transform 0.2s;
            margin-bottom: 0.5rem;
        }}
        
        .metric-card:hover {{
            transform: translateY(-2px);
            border-color: {COLORS['primary']};
        }}
        
        .metric-value {{
            font-size: 2.2rem;
            font-weight: 700;
            color: {COLORS['text_primary']};
            margin: 0.3rem 0;
        }}
        
        .metric-label {{
            font-size: 0.8rem;
            color: {COLORS['text_secondary']};
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .metric-delta {{
            font-size: 0.85rem;
            margin-top: 0.5rem;
        }}
        
        .metric-delta.positive {{
            color: {COLORS['success']};
        }}
        
        .metric-delta.negative {{
            color: {COLORS['danger']};
        }}
        
        .metric-insight {{
            font-size: 0.75rem;
            color: {COLORS['text_secondary']};
            margin-top: 0.5rem;
            font-style: italic;
        }}
        
        /* Alert styling */
        .alert-critical {{
            background: rgba(239, 68, 68, 0.1);
            padding: 1rem;
            border-radius: 8px;
            border-left: 4px solid {COLORS['danger']};
        }}
        
        .alert-warning {{
            background: rgba(245, 158, 11, 0.1);
            padding: 1rem;
            border-radius: 8px;
            border-left: 4px solid {COLORS['warning']};
        }}
        
        .alert-info {{
            background: rgba(99, 102, 241, 0.1);
            padding: 1rem;
            border-radius: 8px;
            border-left: 4px solid {COLORS['primary']};
        }}
        
        .alert-success {{
            background: rgba(16, 185, 129, 0.1);
            padding: 1rem;
            border-radius: 8px;
            border-left: 4px solid {COLORS['success']};
        }}
    </style>
    """, unsafe_allow_html=True)
