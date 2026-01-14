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
    Apply global Glassmorphism CSS styling ke halaman.
    
    Harus dipanggil di awal main.py setelah st.set_page_config()
    
    Example:
        >>> apply_page_css()
    """
    
    st.markdown(f"""
    <style>
        /* ============================================================
           GLASSMORPHISM DESIGN SYSTEM
           ============================================================ */
        
        /* CSS Variables */
        :root {{
            --primary: {COLORS['primary']};
            --primary-light: {COLORS.get('primary_light', '#818cf8')};
            --success: {COLORS['success']};
            --warning: {COLORS['warning']};
            --danger: {COLORS['danger']};
            --info: {COLORS.get('info', '#3b82f6')};
            --bg-dark: {COLORS['bg_dark']};
            --bg-card: {COLORS['bg_card']};
            --bg-glass: {COLORS.get('bg_glass', 'rgba(30, 41, 59, 0.7)')};
            --bg-glass-hover: {COLORS.get('bg_glass_hover', 'rgba(30, 41, 59, 0.85)')};
            --text-primary: {COLORS['text_primary']};
            --text-secondary: {COLORS['text_secondary']};
            --border: {COLORS['border']};
            --border-glass: {COLORS.get('border_glass', 'rgba(255, 255, 255, 0.1)')};
            --glass-blur: {COLORS.get('glass_blur', '16px')};
            --glass-shadow: {COLORS.get('glass_shadow', '0 8px 32px rgba(0, 0, 0, 0.3)')};
            --glass-radius: {COLORS.get('glass_radius', '16px')};
        }}
        
        /* Hide Streamlit branding */
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        
        /* Global dark background */
        .stApp {{
            background: linear-gradient(180deg, #0a0f1a 0%, #111827 100%);
        }}
        
        /* Reduce excessive spacing */
        .block-container {{
            padding-top: 1.5rem;
            padding-bottom: 1rem;
            max-width: 1400px;
        }}
        
        div[data-testid="stVerticalBlock"] > div {{
            gap: 0.75rem;
        }}
        
        /* ============================================================
           GLASSMORPHISM CARDS
           ============================================================ */
        
        .glass-card {{
            background: var(--bg-glass);
            backdrop-filter: blur(var(--glass-blur));
            -webkit-backdrop-filter: blur(var(--glass-blur));
            border: 1px solid var(--border-glass);
            border-radius: var(--glass-radius);
            box-shadow: var(--glass-shadow);
            padding: 1.5rem;
            transition: all 0.3s ease;
        }}
        
        .glass-card:hover {{
            background: var(--bg-glass-hover);
            border-color: rgba(99, 102, 241, 0.3);
            transform: translateY(-2px);
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
        }}
        
        /* ============================================================
           METRIC CARDS (Glassmorphism)
           ============================================================ */
        
        .metric-card {{
            background: var(--bg-glass);
            backdrop-filter: blur(var(--glass-blur));
            -webkit-backdrop-filter: blur(var(--glass-blur));
            border: 1px solid var(--border-glass);
            border-radius: 12px;
            box-shadow: 0 4px 24px rgba(0, 0, 0, 0.2);
            padding: 1.25rem;
            transition: all 0.3s ease;
            margin-bottom: 0.75rem;
        }}
        
        .metric-card:hover {{
            background: var(--bg-glass-hover);
            border-color: var(--primary);
            transform: translateY(-3px);
            box-shadow: 0 8px 32px rgba(102, 126, 234, 0.15);
        }}
        
        .metric-value {{
            font-size: 2rem;
            font-weight: 700;
            color: var(--text-primary);
            margin: 0.4rem 0;
            letter-spacing: -0.5px;
        }}
        
        .metric-label {{
            font-size: 0.75rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.8px;
            font-weight: 500;
        }}
        
        .metric-delta {{
            font-size: 0.8rem;
            margin-top: 0.5rem;
            padding: 0.2rem 0.6rem;
            border-radius: 4px;
            display: inline-block;
        }}
        
        .metric-delta.positive {{
            color: var(--success);
            background: rgba(16, 185, 129, 0.1);
        }}
        
        .metric-delta.negative {{
            color: var(--danger);
            background: rgba(239, 68, 68, 0.1);
        }}
        
        .metric-insight {{
            font-size: 0.7rem;
            color: var(--text-secondary);
            margin-top: 0.5rem;
            opacity: 0.8;
        }}
        
        /* ============================================================
           ALERT CARDS (Glassmorphism)
           ============================================================ */
        
        .alert-critical {{
            background: rgba(239, 68, 68, 0.15);
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            padding: 1.25rem;
            border-radius: 12px;
            border: 1px solid rgba(239, 68, 68, 0.3);
            border-left: 4px solid var(--danger);
            transition: all 0.3s ease;
        }}
        
        .alert-critical:hover {{
            background: rgba(239, 68, 68, 0.2);
            transform: translateX(4px);
        }}
        
        .alert-warning {{
            background: rgba(245, 158, 11, 0.15);
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            padding: 1.25rem;
            border-radius: 12px;
            border: 1px solid rgba(245, 158, 11, 0.3);
            border-left: 4px solid var(--warning);
            transition: all 0.3s ease;
        }}
        
        .alert-warning:hover {{
            background: rgba(245, 158, 11, 0.2);
            transform: translateX(4px);
        }}
        
        .alert-info {{
            background: rgba(99, 102, 241, 0.15);
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            padding: 1.25rem;
            border-radius: 12px;
            border: 1px solid rgba(99, 102, 241, 0.3);
            border-left: 4px solid var(--primary);
            transition: all 0.3s ease;
        }}
        
        .alert-info:hover {{
            background: rgba(99, 102, 241, 0.2);
            transform: translateX(4px);
        }}
        
        .alert-success {{
            background: rgba(16, 185, 129, 0.15);
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            padding: 1.25rem;
            border-radius: 12px;
            border: 1px solid rgba(16, 185, 129, 0.3);
            border-left: 4px solid var(--success);
            transition: all 0.3s ease;
        }}
        
        .alert-success:hover {{
            background: rgba(16, 185, 129, 0.2);
            transform: translateX(4px);
        }}
        
        /* ============================================================
           INSIGHT CARDS
           ============================================================ */
        
        .insight-card {{
            background: var(--bg-glass);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--border-glass);
            border-radius: 12px;
            padding: 1.25rem;
            transition: all 0.3s ease;
        }}
        
        .insight-card:hover {{
            background: var(--bg-glass-hover);
            transform: translateY(-2px);
        }}
        
        /* ============================================================
           SECTION HEADERS
           ============================================================ */
        
        .section-header {{
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid var(--border-glass);
        }}
        
        /* ============================================================
           DATA TABLES (Enhanced)
           ============================================================ */
        
        .stDataFrame {{
            border-radius: 12px;
            overflow: hidden;
        }}
        
        [data-testid="stDataFrame"] > div {{
            background: var(--bg-glass);
            backdrop-filter: blur(8px);
            border: 1px solid var(--border-glass);
            border-radius: 12px;
        }}
        
        /* ============================================================
           BUTTONS (Glassmorphism)
           ============================================================ */
        
        .stButton > button {{
            background: {COLORS.get('gradient_primary', 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)')};
            border: none;
            border-radius: 8px;
            color: white;
            font-weight: 500;
            padding: 0.5rem 1rem;
            transition: all 0.3s ease;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }}
        
        .stButton > button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
        }}
        
        /* Secondary button style */
        .stButton > button[kind="secondary"] {{
            background: var(--bg-glass);
            backdrop-filter: blur(8px);
            border: 1px solid var(--border-glass);
            color: var(--text-primary);
        }}
        
        /* ============================================================
           SIDEBAR (Glassmorphism)
           ============================================================ */
        
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, rgba(17, 24, 39, 0.95) 0%, rgba(10, 15, 26, 0.98) 100%);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-right: 1px solid var(--border-glass);
        }}
        
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{
            padding: 0 0.5rem;
        }}
        
        /* ============================================================
           EXPANDERS (Glassmorphism)
           ============================================================ */
        
        .streamlit-expanderHeader {{
            background: var(--bg-glass);
            backdrop-filter: blur(8px);
            border: 1px solid var(--border-glass);
            border-radius: 10px;
            padding: 0.75rem 1rem;
            color: var(--text-primary);
            font-weight: 500;
            transition: all 0.3s ease;
        }}
        
        .streamlit-expanderHeader:hover {{
            background: var(--bg-glass-hover);
            border-color: var(--primary);
        }}
        
        .streamlit-expanderContent {{
            background: rgba(15, 23, 42, 0.5);
            border: 1px solid var(--border-glass);
            border-top: none;
            border-radius: 0 0 10px 10px;
            padding: 1rem;
        }}
        
        /* ============================================================
           TABS (Glassmorphism)
           ============================================================ */
        
        .stTabs [data-baseweb="tab-list"] {{
            gap: 0.5rem;
            background: var(--bg-glass);
            backdrop-filter: blur(8px);
            border-radius: 10px;
            padding: 0.4rem;
            border: 1px solid var(--border-glass);
        }}
        
        .stTabs [data-baseweb="tab"] {{
            border-radius: 8px;
            padding: 0.5rem 1rem;
            color: var(--text-secondary);
            background: transparent;
            transition: all 0.3s ease;
        }}
        
        .stTabs [aria-selected="true"] {{
            background: {COLORS.get('gradient_primary', 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)')};
            color: white;
        }}
        
        /* ============================================================
           POPOVER (Glassmorphism)
           ============================================================ */
        
        [data-testid="stPopover"] {{
            background: var(--bg-glass);
            backdrop-filter: blur(16px);
            border: 1px solid var(--border-glass);
            border-radius: 12px;
        }}
        
        /* ============================================================
           DIVIDERS
           ============================================================ */
        
        hr {{
            border: none;
            height: 1px;
            background: linear-gradient(90deg, transparent, var(--border-glass), transparent);
            margin: 1.5rem 0;
        }}
        
        /* ============================================================
           DETAIL BOX
           ============================================================ */
        
        .detail-box {{
            background: var(--bg-glass);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--border-glass);
            border-radius: 12px;
            padding: 1.25rem;
            margin: 0.75rem 0;
            color: var(--text-primary);
        }}
        
        /* ============================================================
           PROGRESS INDICATORS
           ============================================================ */
        
        .progress-bar {{
            height: 6px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 3px;
            overflow: hidden;
            margin-top: 0.5rem;
        }}
        
        .progress-fill {{
            height: 100%;
            border-radius: 3px;
            transition: width 0.5s ease;
        }}
        
        .progress-fill.success {{ background: var(--success); }}
        .progress-fill.warning {{ background: var(--warning); }}
        .progress-fill.danger {{ background: var(--danger); }}
        .progress-fill.primary {{ background: var(--primary); }}
        
    </style>
    """, unsafe_allow_html=True)

