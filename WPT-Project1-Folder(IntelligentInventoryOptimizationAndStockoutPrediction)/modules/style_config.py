
"""
Style Configuration Module
==========================
Defines global CSS styles for Neomorphism (Soft UI) theme.
Characterized by soft shadows, minimal contrast, and "embossed" look.
"""

def get_glassmorphism_css():
    """
    Returns the CSS string for Neomorphism theme.
    (Function name kept as 'get_glassmorphism_css' to avoid breaking imports in other files,
     but the content is now Neomorphism)
    """
    return """
    <style>
        /* IMPORT FONT */
        @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700&display=swap');

        /* GLOBAL APP STYLE */
        .stApp {
            background-color: #e0e5ec;
            font-family: 'Nunito', sans-serif;
            color: #4a5568;
        }
        
        /* REMOVE DEFAULT PADDING */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 100% !important;
        }

        /* NEOMORPHISM CARD CONTAINER */
        /* Replaces the previous glass-card class */
        .glass-card {
            background-color: #e0e5ec;
            border-radius: 20px;
            padding: 24px;
            margin-bottom: 24px;
            border: none;
            /* The Neumorphic Shadow: Light Top-Left, Dark Bottom-Right */
            box-shadow: 9px 9px 16px rgb(163,177,198,0.6), -9px -9px 16px rgba(255,255,255, 0.5);
            transition: all 0.3s ease;
        }

        .glass-card:hover {
            transform: translateY(-2px);
            box-shadow: 12px 12px 20px rgb(163,177,198,0.7), -12px -12px 20px rgba(255,255,255, 0.6);
        }
        
        /* INSET EFFECT FOR METRICS (Optional variance) */
        .metric-card-inset {
            background-color: #e0e5ec;
            border-radius: 15px;
            padding: 15px;
            box-shadow: inset 6px 6px 10px 0 rgba(163,177,198, 0.7), 
                        inset -6px -6px 10px 0 rgba(255,255,255, 0.8);
        }

        /* METRIC STYLING */
        .metric-label {
            font-size: 0.85rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #718096; /* Slate 500 */
            margin-bottom: 8px;
        }

        .metric-value {
            font-size: 2.2rem;
            font-weight: 800;
            color: #2d3748; /* Slate 800 */
            margin-bottom: 4px;
            /* Soft text shadow */
            text-shadow: 1px 1px 1px rgba(255,255,255,0.8);
        }

        .metric-sub {
            font-size: 0.9rem;
            color: #718096;
            display: flex;
            align-items: center;
            gap: 6px;
            font-weight: 600;
        }
        
        /* SPECIFIC METRIC CARD CLASS (Used in reorder.py) */
        .metric-card {
            background-color: #e0e5ec;
            border-radius: 20px;
            padding: 20px;
            margin-bottom: 15px;
            box-shadow: 9px 9px 16px rgb(163,177,198,0.6), -9px -9px 16px rgba(255,255,255, 0.5);
            text-align: center;
        }
        
        .metric-delta {
            font-size: 0.8rem;
            font-weight: 700;
            margin-top: 5px;
            padding: 2px 8px;
            border-radius: 10px;
            display: inline-block;
        }
        .metric-delta.positive { color: #48bb78; background: #e0e5ec; box-shadow: inset 3px 3px 6px #bccaea, inset -3px -3px 6px #ffffff; }
        .metric-delta.negative { color: #f56565; background: #e0e5ec; box-shadow: inset 3px 3px 6px #bccaea, inset -3px -3px 6px #ffffff; }


        /* CUSTOM ALERT BADGES - Neumorphic Style */
        .badge {
            padding: 5px 15px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 700;
            display: inline-block;
            /* Convex button look */
            background: #e0e5ec;
            box-shadow: 3px 3px 6px #bccaea, -3px -3px 6px #ffffff;
        }
        .badge-critical { color: #e53e3e; }
        .badge-warning { color: #d69e2e; }
        .badge-success { color: #38a169; }
        .badge-neutral { color: #718096; }

        /* CLEANER TABLE STYLE - Light Mode */
        [data-testid="stDataFrame"] {
            background: transparent;
        }
        
        /* TABLE HEADER */
        [data-testid="stDataFrame"] thead th {
            background-color: #e0e5ec !important;
            color: #4a5568 !important;
            font-weight: 700;
            border-bottom: 2px solid #cbd5e0 !important;
        }
        
        /* TABLE ROWS */
        [data-testid="stDataFrame"] tbody td {
            color: #4a5568 !important;
        }

        /* SIDEBAR STYLING - Simulating a raised panel */
        [data-testid="stSidebar"] {
            background-color: #e0e5ec;
            box-shadow: 5px 0 15px rgba(0,0,0,0.05);
            border-right: none;
        }

        /* CUSTOM PROGRESS BAR */
        .stProgress > div > div > div > div {
            background-image: linear-gradient(90deg, #667eea, #764ba2);
            border-radius: 10px;
        }
        
        /* TITLES */
        h1, h2, h3 {
            color: #2d3748 !important; /* Dark Slate */
            font-weight: 800 !important;
            letter-spacing: -0.5px;
            text-shadow: 1px 1px 0 #fff;
        }
        
        /* BUTTONS (Download, etc) */
        .stButton > button {
            background-color: #e0e5ec;
            color: #4a5568;
            font-weight: 700;
            border: none;
            border-radius: 12px;
            box-shadow: 6px 6px 10px #b8b9be, -6px -6px 10px #ffffff;
            transition: all 0.2s ease;
        }
        .stButton > button:hover {
            box-shadow: 2px 2px 5px #b8b9be, -2px -2px 5px #ffffff;
            transform: translateY(2px);
            color: #2b6cb0;
        }
        .stButton > button:active {
            box-shadow: inset 4px 4px 8px #b8b9be, inset -4px -4px 8px #ffffff;
        }
        
        /* SCROLLBAR */
        ::-webkit-scrollbar {
            width: 10px;
            height: 10px;
        }
        ::-webkit-scrollbar-track {
            background: #e0e5ec; 
        }
        ::-webkit-scrollbar-thumb {
            background: #cbd5e0; 
            border-radius: 5px;
            border: 2px solid #e0e5ec;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #a0aec0; 
        }
        
        /* POPOVER / EXPANDER */
        .streamlit-expanderHeader {
            background-color: #e0e5ec !important;
            color: #4a5568 !important;
            font-weight: 600;
            border-radius: 10px;
            box-shadow: 3px 3px 6px #bccaea, -3px -3px 6px #ffffff;
            margin-bottom: 10px;
        }
    </style>
    """

def render_glass_metric(label, value, sub_value="", sub_color="neutral", icon="📊"):
    """
    Renders a unified Neomorphism metric card.
    Note: Function name kept as 'render_glass_metric' for compatibility.
    """
    color_map = {
        "positive": "#38a169",    # Green
        "negative": "#e53e3e",    # Red
        "warning": "#d69e2e",     # Mustard
        "neutral": "#718096",     # Slate
        "blue": "#3182ce"         # Blue
    }
    
    sub_style = f"color: {color_map.get(sub_color, '#718096')};"
    icon_style = f"color: {color_map.get(sub_color, '#718096')}; filter: drop-shadow(1px 1px 0 #fff);"
    
    html = f"""
    <div class="glass-card">
        <div style="display: flex; justify-content: space-between; align-items: start;">
            <div>
                <div class="metric-label">{label}</div>
                <div class="metric-value">{value}</div>
                <div class="metric-sub">
                    <span style="{sub_style}">{sub_value}</span>
                </div>
            </div>
            <div style="font-size: 1.8rem; opacity: 0.8; {icon_style}">{icon}</div>
        </div>
    </div>
    """
    return html

def render_section_header(title, subtitle=""):
    return f"""
    <div style="margin-bottom: 25px; margin-top: 25px; border-left: 5px solid #667eea; padding-left: 15px;">
        <h3 style="margin: 0; font-size: 1.4rem; color: #2d3748;">{title}</h3>
        <div style="color: #718096; font-size: 0.9rem; font-weight: 500;">{subtitle}</div>
    </div>
    """
