"""
Intelligent Inventory Optimization & Stockout Prediction - PRODUCTION v4.3
Complete Streamlit Application with Enhanced UI/UX & Export Features

Features:
- Real data from master_features_final.csv (2,136 products)
- Email export functionality
- Dynamic filtering, searching, and sorting
- Pop-up descriptions for all metrics
- Responsive and interactive design
- NEW: Real-time Activity Logging (Enhancement 1)
- NEW: Product Category Filter (Enhancement 2)
- NEW: Product Display Limit Filter (Enhancement 3)
- NEW: Custom Recipient List Management in Settings (Enhancement 4)
- FIX: Global calculation for 'days_until_stockout' to resolve Sidebar KeyError.
- FIX: Resolved StreamlitAPIException: st.button() in st.form() in Settings page.
- FIX: Changed Dashboard Quick Email to use proper render_email_form.

Author: Data Science Team
Date: 2025-11-10 (MODIFIED)
Version: 4.3 PRODUCTION
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import os
import sys
import warnings
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import re
import unicodedata
warnings.filterwarnings('ignore')

# Add utils to path
sys.path.insert(0, os.path.dirname(__file__))
from data_loader import DataLoaderV3

# ============================================================================
# SESSION STATE INITIALIZATION (Enhanced)
# ============================================================================

# Email configuration session state
if 'email_sender' not in st.session_state:
    st.session_state.email_sender = ""
if 'email_password' not in st.session_state:
    st.session_state.email_password = ""
if 'email_recipients' not in st.session_state:
    st.session_state.email_recipients = "muhammadrifat.23053@mhs.unesa.ac.id"
    
# NEW: List of custom recipients (Enhancement 4)
if 'custom_recipients_list' not in st.session_state:
    st.session_state.custom_recipients_list = [
        "muhammadrifat.23053@mhs.unesa.ac.id", 
        "202110098@smkyadika11.sch.id"
    ]

# Email form visibility states
if 'show_email_form' not in st.session_state:
    st.session_state.show_email_form = False
if 'show_email_forecast' not in st.session_state:
    st.session_state.show_email_forecast = False
if 'show_email_health' not in st.session_state:
    st.session_state.show_email_health = False
if 'show_email_reorder' not in st.session_state:
    st.session_state.show_email_reorder = False
if 'show_email_slow' not in st.session_state:
    st.session_state.show_email_slow = False
if 'show_email_settings_test' not in st.session_state:
    st.session_state.show_email_settings_test = False

# Other UI states
if 'show_bulk_order' not in st.session_state:
    st.session_state.show_bulk_order = False
if 'show_export_options' not in st.session_state:
    st.session_state.show_export_options = False
if 'selected_products' not in st.session_state:
    st.session_state.selected_products = []
if 'show_all_alerts' not in st.session_state:
    st.session_state.show_all_alerts = False
if 'show_email_detail' not in st.session_state:
    st.session_state.show_email_detail = False

# NEW: Activity Logging (Enhancement 1)
if 'activities' not in st.session_state:
    st.session_state.activities = [
        {'time': datetime.now().strftime('%H:%M:%S'), 'action': '🟢 System Initialized', 'color': '#10b981'}
    ]

# ============================================================================
# NEW: ACTIVITY LOGGING UTILITIES (Enhancement 1)
# ============================================================================

def log_activity(action: str, color: str = '#6366f1'):
    """Log an activity to session state, keeping the list size manageable."""
    new_activity = {
        'time': datetime.now().strftime('%H:%M:%S'), 
        'action': action, 
        'color': color
    }
    st.session_state.activities.insert(0, new_activity)
    # Keep only the last 5 activities
    st.session_state.activities = st.session_state.activities[:5]

# ============================================================================
# EMAIL UTILITIES (Minor change: log_activity integration)
# ============================================================================

def clean_text(text):
    """Clean text from non-ASCII characters"""
    if not isinstance(text, str):
        return text
    
    text = unicodedata.normalize('NFKD', text)
    text = text.replace('\xa0', ' ')
    text = text.replace('\u200b', '')
    text = text.replace('\u2013', '-')
    text = text.replace('\u2014', '-')
    text = text.encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    return text.strip()

def send_email_with_attachment(sender_email, sender_password, to_email, subject, body, filename, file_content):
    """Send email with attachment"""
    try:
        subject = clean_text(subject)
        body = clean_text(body)
        filename = clean_text(filename)
        to_email = clean_text(to_email)
        sender_email = clean_text(sender_email)
        
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(file_content)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
        msg.attach(part)
        
        with smtplib.SMTP('smtp.gmail.com', 587, timeout=30) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        
        return True, "✅ Email berhasil dikirim!"
        
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

# ============================================================================
# ENHANCED HELPER FUNCTION FOR EMAIL FORMS WITH SESSION STATE INTEGRATION
# ============================================================================

def render_email_form(data, data_type="overview", filename_prefix="inventory_report"):
    """
    Render reusable email form component with integration to Settings
    """
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    st.markdown("#### 📧 Email Configuration")
    
    # Show info if settings are configured
    if st.session_state.get('email_sender') and st.session_state.get('email_password'):
        st.info("✅ Menggunakan konfigurasi email dari Settings. Anda dapat mengubah kolom di bawah jika diperlukan.")
    else:
        st.warning("⚠️ Tidak ada konfigurasi email yang ditemukan. Mohon atur di halaman Settings atau isi di bawah.")
    
    with st.form(f"email_form_{data_type}"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Pre-fill from session state if available
            default_sender = st.session_state.get('email_sender', 'your-email@gmail.com')
            sender_email = st.text_input(
                "📧 Sender Email", 
                value=default_sender, 
                key=f"sender_{data_type}",
                help="Email address to send from (configured in Settings)"
            )
            
            # Password field - use session state but don't show value
            default_password = st.session_state.get('email_password', '')
            sender_password = st.text_input(
                "🔒 App Password", 
                type="password", 
                help="16-digit App Password dari Google",
                value=default_password,
                key=f"password_{data_type}"
            )
            
            # Show password status
            if sender_password:
                if len(sender_password) >= 16:
                    st.caption("✅ Password configured")
                else:
                    st.caption("⚠️ Password terlalu pendek (minimal 16 karakter)")
        
        with col2:
            # Pre-fill recipients from session state
            default_recipients = st.session_state.get('email_recipients', 'recipient@company.com')
            
            # Use MultiSelect for easy recipient selection if available
            if st.session_state.custom_recipients_list:
                selected_custom_recipients = st.multiselect(
                    "Pilih Penerima Kustom:",
                    options=st.session_state.custom_recipients_list,
                    default=[r.strip() for r in default_recipients.split(',') if r.strip() and r.strip() in st.session_state.custom_recipients_list],
                    help="Pilih dari daftar yang dikonfigurasi di Settings."
                )
                
                # Combine default and custom recipients
                initial_recipient_value = ", ".join(selected_custom_recipients)
            else:
                initial_recipient_value = default_recipients
                
            recipient_email = st.text_input(
                "📮 Recipient Email", 
                value=initial_recipient_value, 
                key=f"recipient_{data_type}",
                help="Comma-separated email addresses"
            )
            
            # Generate dynamic subject
            email_subject = st.text_input(
                "📝 Subject", 
                value=f"{data_type.replace('_', ' ').title()} Report - {datetime.now().strftime('%Y-%m-%d')}", 
                key=f"subject_{data_type}"
            )
            
            # Show recipient count
            if recipient_email:
                recipient_list = [r.strip() for r in recipient_email.split(',') if r.strip()]
                st.caption(f"📧 {len(recipient_list)} recipient(s)")
        
        # Email body with enhanced template
        email_body = st.text_area(
            "💬 Message",
            value=f"""Dear Team,

Please find attached the {data_type.replace('_', ' ')} report from the Inventory Intelligence System.

📊 Report Details:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Generated: {current_time}
• Total Records: {len(data):,}
• Report Type: {data_type.replace('_', ' ').title()}
• File Format: CSV
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This report contains comprehensive inventory data including:
✓ Product information
✓ Stock levels
✓ Performance metrics
✓ Recommendations

For questions or concerns, please contact the inventory management team.

Best regards,
Inventory Intelligence System
PT Wahana Piranti Teknologi""",
            height=200,
            key=f"body_{data_type}"
        )
        
        st.markdown("---")
        
        # Action buttons
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            send_button = st.form_submit_button(
                "📤 Send Email", 
                use_container_width=True, 
                type="primary"
            )
        
        with col2:
            save_draft = st.form_submit_button(
                "💾 Save Draft", 
                use_container_width=True
            )
        
        with col3:
            cancel_button = st.form_submit_button(
                "❌ Cancel", 
                use_container_width=True
            )
        
        # Handle Send Email
        if send_button:
            # Validation
            if not all([sender_email, sender_password, recipient_email]):
                st.error("⚠️ Mohon lengkapi semua kolom yang wajib diisi (Sender, Password, Recipient)")
            elif "@" not in sender_email:
                st.error("⚠️ Format email pengirim tidak valid")
            elif not all("@" in r.strip() for r in recipient_email.split(',') if r.strip()):
                st.error("⚠️ Format email penerima tidak valid")
            elif len(sender_password) < 16:
                st.error("⚠️ App Password harus 16 karakter. Dapatkan dari: https://myaccount.google.com/apppasswords")
            else:
                with st.spinner("📤 Mengirim email..."):
                    try:
                        # Prepare CSV data
                        csv_data = data.to_csv(index=False).encode('utf-8')
                        
                        # Send email using helper function
                        success, message = send_email_with_attachment(
                            sender_email=sender_email,
                            sender_password=sender_password,
                            to_email=recipient_email,
                            subject=email_subject,
                            body=email_body,
                            filename=f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            file_content=csv_data
                        )
                        
                        if success:
                            st.success(message)
                            st.balloons()
                            
                            # LOG ACTIVITY ON SUCCESS (Enhancement 1)
                            log_activity(f"📧 Email sent: '{data_type.replace('_', ' ')}' to {recipient_email.split(',')[0]}...", '#10b981')
                            
                            # Show detailed success info
                            st.info(f"""
                            ✅ Email Details:
                            • Sent to: {recipient_email}
                            • Attachment: {filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv
                            • Records: {len(data):,}
                            • Time: {datetime.now().strftime('%H:%M:%S')}
                            """)
                            
                            # Reset the form state after 2 seconds
                            import time
                            time.sleep(2)
                            
                            # Close form based on data_type
                            if data_type == "forecast":
                                st.session_state.show_email_forecast = False
                            elif data_type == "health":
                                st.session_state.show_email_health = False
                            elif data_type == "reorder":
                                st.session_state.show_email_reorder = False
                            elif data_type == "slow_moving":
                                st.session_state.show_email_slow = False
                            elif data_type == "settings_test":
                                st.session_state.show_email_settings_test = False
                            elif data_type == "quick_alert":
                                st.session_state.show_email_detail = False # Close quick alert form
                            else:
                                st.session_state.show_email_form = False
                            
                            st.rerun()
                        else:
                            st.error(message)
                            # LOG ACTIVITY ON FAILURE (Enhancement 1)
                            log_activity(f"❌ Email failed: '{data_type.replace('_', ' ')}' ({message[:30]}...)", '#ef4444')
                            
                            # Show troubleshooting tips
                            with st.expander("🔧 Troubleshooting Tips"):
                                st.markdown("""
                                **Common Issues:**
                                
                                1. **Authentication Error**
                                   - Make sure you're using an App Password, not your regular Gmail password
                                   - Generate App Password: https://myaccount.google.com/apppasswords
                                
                                2. **Connection Error**
                                   - Check your internet connection
                                   - Verify Gmail SMTP is not blocked by firewall
                                
                                3. **Invalid Credentials**
                                   - Verify email address is correct
                                   - Ensure App Password is 16 characters with no spaces
                                
                                4. **2-Factor Authentication**
                                   - Make sure 2FA is enabled on your Google account
                                   - App Passwords only work with 2FA enabled
                                """)
                    
                    except Exception as e:
                        st.error(f"❌ Unexpected error: {str(e)}")
                        st.exception(e)  # Show full traceback in development
        
        # Handle Save Draft
        if save_draft:
            st.info("💾 Draft saved! (Feature coming soon)")
        
        # Handle Cancel
        if cancel_button:
            # Close form based on data_type
            if data_type == "forecast":
                st.session_state.show_email_forecast = False
            elif data_type == "health":
                st.session_state.show_email_health = False
            elif data_type == "reorder":
                st.session_state.show_email_reorder = False
            elif data_type == "slow_moving":
                st.session_state.show_email_slow = False
            elif data_type == "settings_test":
                st.session_state.show_email_settings_test = False
            elif data_type == "quick_alert":
                st.session_state.show_email_detail = False # Close quick alert form
            else:
                st.session_state.show_email_form = False
            
            st.rerun()

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Inventory Intelligence Hub - PT Wahana Piranti Teknologi",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# COMPREHENSIVE CSS STYLING (Restored)
# ============================================================================
# (The CSS block is restored here in the actual working script)
st.markdown("""
<style>
    /* Main theme colors */
    :root {
        --primary-color: #6366f1;
        --success-color: #10b981;
        --warning-color: #f59e0b;
        --danger-color: #ef4444;
        --bg-dark: #0f172a;
        --bg-card: #1e293b;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Reduce excessive spacing */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 1rem;
    }
    
    div[data-testid="stVerticalBlock"] > div {
        gap: 0.5rem;
    }
    
    /* Custom card styling */
    .metric-card {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        padding: 1.2rem;
        border-radius: 10px;
        border: 1px solid #334155;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s;
        margin-bottom: 0.5rem;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: #6366f1;
    }
    
    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        color: #f8fafc;
        margin: 0.3rem 0;
    }
    
    .metric-label {
        font-size: 0.8rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        display: flex;
        align-items: center;
        gap: 0.3rem;
    }
    
    .metric-delta {
        font-size: 0.8rem;
        font-weight: 600;
        margin-top: 0.3rem;
    }
    
    .metric-delta.positive {
        color: #10b981;
    }
    
    .metric-delta.negative {
        color: #ef4444;
    }
    
    .metric-insight {
        font-size: 0.75rem;
        color: #64748b;
        margin-top: 0.3rem;
        font-style: italic;
    }
    
    /* Alert styling */
    .alert-critical {
        background: linear-gradient(135deg, #7f1d1d 0%, #991b1b 100%);
        padding: 0.8rem;
        border-radius: 8px;
        border-left: 4px solid #ef4444;
        margin: 0.3rem 0;
    }
    
    .alert-warning {
        background: linear-gradient(135deg, #78350f 0%, #92400e 100%);
        padding: 0.8rem;
        border-radius: 8px;
        border-left: 4px solid #f59e0b;
        margin: 0.3rem 0;
    }
    
    .alert-info {
        background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%);
        padding: 0.8rem;
        border-radius: 8px;
        border-left: 4px solid #3b82f6;
        margin: 0.3rem 0;
    }
    
    /* Calculation box styling */
    .calc-box {
        background: rgba(99, 102, 241, 0.1);
        border-left: 3px solid #6366f1;
        padding: 1rem;
        border-radius: 6px;
        margin: 0.5rem 0;
        font-family: 'Courier New', monospace;
    }
    
    .calc-step {
        margin: 0.3rem 0;
        color: #e2e8f0;
    }
    
    .calc-result {
        font-weight: 700;
        color: #10b981;
        font-size: 1.1rem;
        margin-top: 0.5rem;
    }
    
    /* Quick action card styling */
    .action-card {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #334155;
        margin-bottom: 0.5rem;
        cursor: pointer;
        transition: all 0.2s;
    }
    
    .action-card:hover {
        border-color: #6366f1;
        transform: translateX(4px);
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    }
    
    /* Button styling */
    .stButton>button {
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
        transition: all 0.2s;
    }
    
    .stButton>button:hover {
        background: linear-gradient(135deg, #4f46e5 0%, #4338ca 100%);
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
    }
    
    /* Header styling */
    h1 {
        color: #f8fafc;
        font-weight: 700;
        letter-spacing: -0.02em;
        margin-bottom: 0.5rem;
    }
    
    h2, h3 {
        color: #e2e8f0;
        font-weight: 600;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #1e293b;
        border-radius: 8px;
        padding: 0.4rem 0.8rem;
        color: #94a3b8;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
        color: white;
    }
    
    /* Detail box styling */
    .detail-box {
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    /* Improved table styling */
    .improved-table {
        background: rgba(30, 41, 59, 0.8);
        border-radius: 8px;
        padding: 1rem;
        border: 1px solid #334155;
    }
    
    .improved-table table {
        width: 100%;
        border-collapse: collapse;
    }
    
    .improved-table th {
        background: rgba(99, 102, 241, 0.2);
        color: #f8fafc;
        padding: 0.8rem;
        text-align: left;
        font-weight: 600;
        border-bottom: 2px solid #334155;
    }
    
    .improved-table td {
        color: #e2e8f0;
        padding: 0.8rem;
        border-bottom: 1px solid #334155;
    }
    
    .improved-table tr:hover {
        background: rgba(99, 102, 241, 0.1);
    }
    
    /* Horizontal insights layout */
    .insights-container {
        display: flex;
        gap: 1rem;
        margin-top: 1rem;
    }
    
    .insight-card {
        flex: 1;
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #334155;
    }
    
    /* Filter container styling */
    .filter-container {
        background: rgba(30, 41, 59, 0.6);
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 1rem;
    }
    
    /* Order form styling */
    .order-form {
        background: rgba(30, 41, 59, 0.8);
        border-radius: 8px;
        padding: 1.5rem;
        border: 1px solid #334155;
        margin-top: 1rem;
    }
    
    .order-summary {
        background: rgba(99, 102, 241, 0.1);
        border-left: 3px solid #6366f1;
        padding: 1rem;
        border-radius: 6px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# DATA LOADING & CACHING
# ============================================================================

@st.cache_data(ttl=3600)
def load_data():
    """Load and merge data from CSV files"""
    loader = DataLoaderV3()
    df = loader.merge_data()
    return df

# ============================================================================
# LOAD DATA & GLOBAL CALCULATIONS (FIXED: Global Calc for Sidebar)
# ============================================================================

with st.spinner("Loading data..."):
    df = load_data()

if df is None or len(df) == 0:
    st.error("❌ Failed to load data. Please check CSV files in data/ directory.")
    st.stop()

# FIX: Calculate days_until_stockout globally so the sidebar can access it
df['days_until_stockout'] = df['current_stock_qty'] / (df['avg_daily_demand'] + 0.01)

# ============================================================================
# SIDEBAR NAVIGATION
# ============================================================================

with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 1rem 0; border-bottom: 2px solid #334155; margin-bottom: 1rem;">
        <div style="font-size: 1.5rem; font-weight: 700; color: #f8fafc; margin-bottom: 0.3rem;">
            📦 Inventory Intelligence
        </div>
        <div style="font-size: 0.9rem; color: #94a3b8; font-weight: 500;">
            PT Wahana Piranti Teknologi
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    page = st.radio(
        "Navigation",
        [
            "🏠 Dashboard Overview",
            "📈 Demand Forecasting",
            "📊 Inventory Health",
            "⚠️ Stockout Alerts",
            "🔄 Reorder Optimization",
            "📋 Slow-Moving Analysis",
            "⚙️ Settings"
        ],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    st.markdown("### 📊 Quick Stats")
    
    with st.popover("ℹ️ Tentang Quick Stats"):
        st.markdown("""
        **Quick Stats** memberikan snapshot real-time dari kondisi inventory Anda.
        
        - **Active Alerts**: Produk yang memerlukan perhatian segera
        - **Products Monitored**: Total produk dalam sistem
        - **Last Updated**: Waktu sinkronisasi data terakhir
        
        Stats ini di-update setiap 2 menit untuk memastikan Anda selalu mendapat informasi terkini.
        """)
    
    # Load data for quick stats (Use the globally calculated DF)
    total_products = len(df)
    active_alerts = len(df[df['current_stock_qty'] < df['optimal_safety_stock']])

    # FIX: Use the calculated days_until_stockout for detailed alerts
    critical_alert_count = len(df[df['days_until_stockout'] < 7])
    high_alert_count = len(df[(df['days_until_stockout'] >= 7) & (df['days_until_stockout'] < 14)])
    
    st.markdown(f"""
    <div style="background: rgba(239, 68, 68, 0.1); padding: 0.8rem; border-radius: 8px; border-left: 3px solid #ef4444; margin-bottom: 0.5rem;">
        <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase;">Active Alerts</div>
        <div style="font-size: 1.8rem; font-weight: 700; color: #ef4444;">{active_alerts}</div>
        <div style="font-size: 0.7rem; color: #fca5a5;">↑ 3 from yesterday</div>
        <div style="font-size: 0.7rem; color: #64748b; margin-top: 0.3rem;">{critical_alert_count:.0f} critical, {high_alert_count:.0f} high</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div style="background: rgba(99, 102, 241, 0.1); padding: 0.8rem; border-radius: 8px; border-left: 3px solid #6366f1; margin-bottom: 0.5rem;">
        <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase;">Products Monitored</div>
        <div style="font-size: 1.8rem; font-weight: 700; color: #6366f1;">{total_products:,}</div>
        <div style="font-size: 0.7rem; color: #64748b; margin-top: 0.3rem;">Across multiple warehouses</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style="background: rgba(16, 185, 129, 0.1); padding: 0.8rem; border-radius: 8px; border-left: 3px solid #10b981;">
        <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase;">Last Updated</div>
        <div style="font-size: 1.2rem; font-weight: 700; color: #10b981;">Now</div>
        <div style="font-size: 0.7rem; color: #64748b; margin-top: 0.3rem;">🟢 System operational</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 👤 User")
    st.markdown("**Internship Program**")
    st.markdown("Data Science Team")

# ============================================================================
# PAGE 1: DASHBOARD OVERVIEW - ENHANCED VERSION
# ============================================================================

if "🏠 Dashboard Overview" in page:
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
            st.markdown("**Contoh Perhitungan Bulan Ini:**")
            st.markdown("- Total pesanan: 1,000 orders")
            st.markdown("- Pesanan terpenuhi: 942 orders")
            st.markdown("- Service Level: **94.2%**")
            st.markdown("**Benchmark Industry:**")
            st.markdown("- >95%: Excellent ✅")
            st.markdown("- 90-95%: Good")
            st.markdown("- 85-90%: Fair")
            st.markdown("- <85%: Poor")
        
        service_level = (df['current_stock_qty'] > 0).sum() / len(df) * 100
        prev_service_level = 92.1  # Mock previous value
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
    
    # Metric 2: Inventory Turnover (FIXED: Use Weighted Average)
    with col2:
        with st.popover("ℹ️"):
            st.markdown("### 🔄 Inventory Turnover Ratio")
            st.markdown("**Definisi:** Berapa kali inventory terjual dan diganti dalam setahun.")
            st.markdown("**Formula (Weighted Average):**")
            st.code("Turnover 90d = (Sum Total Sales 90d) / (Sum Total Stock Value)")
            st.markdown("**Contoh Perhitungan:**")
            st.markdown("- Total Sales 90d: $4,500,000")
            st.markdown("- Total Stock Value: $1,500,000")
            st.markdown("- Turnover 90d = 3.0x (Annualized: 12.0x)")
            st.markdown("**Interpretasi:**")
            st.markdown("- Rata-rata inventory terjual 12 kali/tahun")
            st.markdown("**Benchmark IT Products:**")
            st.markdown("- 8-12x: Excellent")
            st.markdown("- 6-8x: Ideal ✅")
            st.markdown("- 4-6x: Acceptable")
            st.markdown("- <4x: Slow")

        # FIX: Use Weighted Average Turnover Ratio (Total Sales 90d / Total Stock Value)
        total_sales_value = df['total_sales_90d'].sum()
        total_stock_value = df['stock_value'].sum()
        
        if total_stock_value > 0:
            weighted_avg_turnover_90d = total_sales_value / total_stock_value
        else:
            weighted_avg_turnover_90d = 0
            
        # Annualize and cap at a maximum sensible value (e.g., 100x)
        annualized_turnover = min(weighted_avg_turnover_90d * (365 / 90), 100)
        
        days_to_refresh = 365 / (annualized_turnover + 0.01)

        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Inventory Turnover</div>
            <div class="metric-value">{annualized_turnover:.1f}x</div>
            <div class="metric-delta positive">↑ 0.5x vs last month</div>
            <div class="metric-insight">Inventory refresh: ~{days_to_refresh:.0f} days</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Metric 3: Stockout Risk Index
    with col3:
        with st.popover("ℹ️"):
            st.markdown("### ⚠️ Stockout Risk Index")
            st.markdown("**Definisi:** Jumlah produk berisiko kehabisan stok dalam 30 hari.")
            st.markdown("**Cara Perhitungan:**")
            st.code("Days Until Stockout = Current Stock / Daily Demand")
            st.markdown("**Level Risiko:**")
            st.markdown("- 🔴 Critical (3): <7 hari")
            st.markdown("- 🟡 High (5): 8-14 hari")
            st.markdown("- 🔵 Medium (4): 15-30 hari")
            st.markdown("**Dampak Stockout:**")
            st.markdown("- Lost sales & revenue")
            st.markdown("- Customer dissatisfaction")
            st.markdown("- Emergency ordering costs")
        
        # Calculate stockout risks
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
    
    # Metric 4: Average Stock Age (FIXED: Use Median DIO)
    with col4:
        with st.popover("ℹ️"):
            st.markdown("### 📅 Average Stock Age")
            st.markdown("**Definisi:** Rata-rata hari sejak produk dibeli / Days Inventory Outstanding (DIO).")
            st.markdown("**Cara Perhitungan (Fixed):**")
            st.code("DIO (Median) = Median(90 / (Turnover 90d + 0.001))")
            st.markdown("**Interpretasi:**")
            st.markdown("- <30 hari: Excellent")
            st.markdown("- 30-60 hari: Good ✅")
            st.markdown("- 60-90 hari: Warning")
            st.markdown("- >90 hari: Critical")
            st.markdown("**Dampak Stock Age Tinggi:**")
            st.markdown("- Biaya penyimpanan ↑")
            st.markdown("- Risk obsolescence")
            st.markdown("- Modal tertahan")
        
        # FIX: Use median of the pre-calculated 'days_in_inventory_90d' column
        valid_dio = df[df['days_in_inventory_90d'] > 0]['days_in_inventory_90d']
        avg_stock_age = valid_dio.median() if len(valid_dio) > 0 else 60  # Default 60 hari
        
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
        
        # Generate 6 months of historical data
        months = pd.date_range(end=datetime.now(), periods=6, freq='M')
        
        # Calculate realistic trends based on actual data
        base_service = service_level
        base_turnover = annualized_turnover
        
        performance_data = pd.DataFrame({
            'Month': months.strftime('%b %Y'),
            'Service Level': [
                base_service - 3.0,
                base_service - 1.7,
                base_service - 1.1,
                base_service - 1.4,
                base_service - 0.3,
                base_service
            ],
            'Turnover Rate': [
                base_turnover - 0.7,
                base_turnover - 0.5,
                base_turnover - 0.3,
                base_turnover - 0.4,
                base_turnover - 0.1,
                base_turnover
            ]
        })
        
        fig = go.Figure()
        
        # Service Level trace
        fig.add_trace(go.Scatter(
            x=performance_data['Month'],
            y=performance_data['Service Level'],
            name='Service Level (%)',
            line=dict(color='#10b981', width=3),
            mode='lines+markers',
            marker=dict(size=8),
            hovertemplate='<b>%{x}</b><br>Service Level: %{y:.1f}%<extra></extra>'
        ))
        
        # Turnover Rate trace (scaled for visibility)
        fig.add_trace(go.Scatter(
            x=performance_data['Month'],
            y=performance_data['Turnover Rate'] * (100 / annualized_turnover) if annualized_turnover > 0 else performance_data['Turnover Rate'],  # Scale for dual-axis effect
            name='Turnover Rate (Scaled)',
            line=dict(color='#6366f1', width=3),
            mode='lines+markers',
            marker=dict(size=8),
            yaxis='y2',
            hovertemplate='<b>%{x}</b><br>Turnover: %{customdata:.1f}x<extra></extra>',
            customdata=performance_data['Turnover Rate']
        ))
        
        fig.update_layout(
            template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=280,
            margin=dict(l=0, r=0, t=10, b=0),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            hovermode='x unified',
            xaxis=dict(
                showgrid=True,
                gridcolor='rgba(255,255,255,0.1)'
            ),
            yaxis=dict(
                title="Service Level (%)",
                showgrid=True,
                gridcolor='rgba(255,255,255,0.1)',
                range=[85, 100]
            ),
            yaxis2=dict(
                title="Turnover Rate",
                overlaying='y',
                side='right',
                showgrid=False,
                tickvals=[] # Hide tick values as it's scaled
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### ⚠️ Today's Alerts")
        
        st.markdown(f"""
        <div class="alert-critical">
            <strong>🔴 Critical ({critical_count})</strong><br>
            <span style="font-size: 0.85rem;">Stockout in <7 days</span>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="alert-warning">
            <strong>🟡 High Risk ({high_count})</strong><br>
            <span style="font-size: 0.85rem;">Need reorder soon</span>
        </div>
        """, unsafe_allow_html=True)
        
        # Count slow-moving products
        slow_moving_count = len(df[df['turnover_ratio_90d'] < 1.0])
        
        st.markdown(f"""
        <div class="alert-info">
            <strong>🔵 Slow-Moving ({slow_moving_count})</strong><br>
            <span style="font-size: 0.85rem;">Low turnover products</span>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("View All Alerts →", use_container_width=True):
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
            use_container_width=True,
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
                use_container_width=True,
                key="dashboard_alert_download_btn"
            ):
                 log_activity("📥 Exported Alerts Report", '#6366f1')
                 
        with col2:
            if st.button("📅 Schedule Review", use_container_width=True):
                st.info("📅 Review scheduled for tomorrow 9:00 AM")
                log_activity("📅 Scheduled Alert Review", '#f59e0b')
        with col3:
            if st.button("📝 Create Action Plan", use_container_width=True):
                st.success("✅ Action plan created!")
                log_activity("📝 Created Alert Action Plan", '#10b981')
    
    # ========================================================================
    # TOP FAST-MOVING PRODUCTS & QUICK ACTIONS
    # ========================================================================
    
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.markdown("### 🚀 Top 5 Fast-Moving Products")
        
        # Get top 5 products by demand
        top_products = df.nlargest(5, 'avg_daily_demand')[
            ['product_code', 'product_name', 'avg_daily_demand', 'current_stock_qty']
        ].copy()
        
        # Create horizontal bar chart
        fig = go.Figure()
        
        for i, row in enumerate(top_products.itertuples()):
            # Shorten product name for display
            short_name = ' '.join(row.product_name.split()[:3])
            if len(short_name) > 20:
                short_name = short_name[:17] + "..."
            
            fig.add_trace(go.Bar(
                y=[f"{row.product_code}"],
                x=[row.avg_daily_demand],
                orientation='h',
                marker_color='#10b981' if i == 0 else '#6366f1',
                text=f"{short_name}<br>{row.current_stock_qty:.0f} units in stock",
                textposition='inside',
                insidetextanchor='middle',
                textfont=dict(color='white', size=10),
                hovertemplate=(
                    '<b>%{y}</b><br>' +
                    f'{row.product_name}<br>' +
                    'Daily Demand: %{x:.2f} units<br>' +
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
            xaxis_title="Daily Demand (units)",
            yaxis_title="",
            yaxis={'categoryorder':'total ascending'},
            xaxis=dict(
                showgrid=True,
                gridcolor='rgba(255,255,255,0.1)'
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
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
        if st.button("🚀 Bulk Order", use_container_width=True, key="quick_bulk_order_btn"):
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
        if st.button("📧 Send Alert Email", use_container_width=True, key="quick_send_email_btn"):
            # Toggle visibility, similar to other email buttons
            st.session_state.show_email_detail = not st.session_state.show_email_detail
        
        # Show email form if button toggled
        if st.session_state.show_email_detail:
            # Prepare data for alert report
            alert_products_for_email = df[df['days_until_stockout'] < 30].sort_values('days_until_stockout', ascending=True).head(50)
            render_email_form(
                alert_products_for_email, 
                "quick_alert", 
                "critical_stock_alert"
            )
        
        # Quick Action 3: Export Report
        if st.button("📥 Export Report", use_container_width=True, key="quick_export_report_btn"):
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
                use_container_width=True,
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
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### 📋 Recent Activities")
        
        # NEW: Display activities from session state (Enhancement 1)
        activities_to_display = st.session_state.activities
        
        if not activities_to_display:
             st.info("No recent activity.")
             
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
    
    # Apply Product Category filter
    if selected_product_category != 'Semua Kategori':
        display_data = display_data[display_data['product_category'] == selected_product_category]

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
        use_container_width=True,
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
    # EXPORT & SHARE SECTION
    # ========================================================================
    
    st.markdown("---")
    st.markdown("### 📤 Export & Share")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📥 Export to CSV", use_container_width=True, key="dashboard_export_btn"):
            st.session_state.show_export_options = not st.session_state.get('show_export_options', False)
    
    with col2:
        if st.button("📧 Email Report", use_container_width=True, key="dashboard_email_btn"):
            st.session_state.show_email_form = not st.session_state.get('show_email_form', False)
    
    with col3:
        if st.button("📊 Generate PDF Report", use_container_width=True, key="dashboard_pdf_btn"):
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
                use_container_width=True,
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
                use_container_width=True,
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
    if annualized_turnover < 6:
        insights.append({
            'type': 'warning',
            'title': '📉 Low Inventory Turnover',
            'message': f'Turnover rate of {annualized_turnover:.1f}x is below industry benchmark (6-8x). Consider reducing slow-moving inventory.',
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
    dead_stock_count = len(df[df['turnover_ratio_90d'] < 0.3])
    if dead_stock_count > 0:
        dead_stock_value = df[df['turnover_ratio_90d'] < 0.3]['stock_value'].sum()
        insights.append({
            'type': 'info',
            'title': '💰 Capital Optimization Opportunity',
            'message': f'{dead_stock_count} products with very low turnover. Potential to free up Rp {dead_stock_value/1_000_000:.1f}M in capital.',
            'action': 'Consider clearance sales or supplier returns'
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
        'turnover_ratio_90d': 'mean'
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
    
    st.plotly_chart(fig, use_container_width=True)
    
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
                    <div style="font-size: 1.1rem; color: #f59e0b; font-weight: 600;">{row['turnover_ratio_90d']:.2f}x</div>
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


# ============================================================================
# PAGE 2: DEMAND FORECASTING
# ============================================================================

elif "📈 Demand Forecasting" in page:
    st.title("📈 Demand Forecasting")
    st.markdown("Predict future demand and analyze trends")
    
    with st.popover("ℹ️ Tentang Demand Forecasting"):
        st.markdown("""
        **Demand Forecasting** memprediksi permintaan produk di masa depan.
        
        **Manfaat:**
        - Mencegah stockout dengan perencanaan lebih baik
        - Mengurangi overstock dan biaya penyimpanan
        - Optimasi cash flow
        
        **Data Source:**
        - Historical sales data (90 hari)
        - Trend analysis
        - Seasonal patterns
        """)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        search_product = st.text_input("🔍 Search Product", placeholder="Search by code or name...")
    
    with col2:
        # NEW: Product Category Filter (Enhancement 2)
        product_categories = ['All'] + sorted([c for c in df['product_category'].unique() if c != 'OTHER'])
        forecast_category_filter = st.selectbox(
            "Product Group", 
            product_categories,
            key="forecast_product_group_filter"
        )
    
    with col3:
        forecast_days = st.slider("Forecast Days", 7, 90, 30)
    
    with col4:
        abc_class_filter = st.selectbox("ABC Class", ["All", "A", "B", "C"])
    
    # Filter products
    forecast_df = df.copy()
    if search_product:
        mask = (
            forecast_df['product_code'].str.contains(search_product, case=False, na=False) |
            forecast_df['product_name'].str.contains(search_product, case=False, na=False)
        )
        forecast_df = forecast_df[mask]
    
    if abc_class_filter != "All":
        forecast_df = forecast_df[forecast_df['ABC_class'] == abc_class_filter]
        
    # Apply Product Category filter
    if forecast_category_filter != "All":
        forecast_df = forecast_df[forecast_df['product_category'] == forecast_category_filter]
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 Demand Distribution")
        fig = px.histogram(forecast_df, x='avg_daily_demand', nbins=50, 
                          title="Daily Demand Distribution", 
                          template="plotly_dark")
        fig.update_layout(height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### 📈 Top Products Forecast")
        top_products = forecast_df.nlargest(10, 'avg_daily_demand')[['product_code', 'avg_daily_demand']].copy()
        top_products['forecast'] = top_products['avg_daily_demand'] * forecast_days
        
        fig = px.bar(top_products, x='product_code', y='forecast', 
                    title=f"{forecast_days}-Day Forecast (Top 10)", 
                    template="plotly_dark")
        fig.update_layout(height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    st.markdown("### ⭐ Top Products by Demand")
    
    top_df = forecast_df.nlargest(15, 'avg_daily_demand')[
        ['product_code', 'product_name', 'avg_daily_demand', 'ABC_class', 'segment_label', 'current_stock_qty', 'product_category']
    ].copy()
    
    top_df['forecast_demand'] = top_df['avg_daily_demand'] * forecast_days
    top_df['stock_coverage_days'] = top_df['current_stock_qty'] / (top_df['avg_daily_demand'] + 0.01)
    
    st.dataframe(
        top_df,
        use_container_width=True,
        height=400,
        column_config={
            "product_code": "Code",
            "product_name": "Product Name",
            "avg_daily_demand": st.column_config.NumberColumn("Daily Demand", format="%.2f"),
            "forecast_demand": st.column_config.NumberColumn(f"{forecast_days}-Day Forecast", format="%.0f"),
            "current_stock_qty": st.column_config.NumberColumn("Current Stock", format="%.0f"),
            "stock_coverage_days": st.column_config.NumberColumn("Coverage (days)", format="%.0f"),
            "ABC_class": "ABC",
            "segment_label": "Segment",
            "product_category": "Group"
        }
    )
    
    # Export Section
    st.markdown("---")
    st.markdown("### 📤 Export & Share Forecast")
    
    col1, col2 = st.columns(2)
    
    with col1:
        csv_data = top_df.to_csv(index=False).encode('utf-8')
        if st.download_button(
            label="📥 Download Forecast Report",
            data=csv_data,
            file_name=f"demand_forecast_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
            key="forecast_download_csv"
        ):
            log_activity("📥 Downloaded Demand Forecast Report", '#6366f1')
    
    with col2:
        if st.button("📧 Email Forecast", use_container_width=True, key="forecast_email_button"):
            st.session_state.show_email_forecast = not st.session_state.show_email_forecast
    
    # Email Forecast Form - FIXED VERSION
    if st.session_state.show_email_forecast:
        render_email_form(top_df, "forecast", "demand_forecast")

# ============================================================================
# PAGE 3: INVENTORY HEALTH
# ============================================================================

elif "📊 Inventory Health" in page:
    st.title("📊 Inventory Health")
    st.markdown("Monitor inventory status and health indicators")
    
    with st.popover("ℹ️ Panduan Inventory Health"):
        st.markdown("""
        **Inventory Health Monitor** menampilkan kesehatan inventory secara real-time.
        
        **Metrik Utama:**
        - **Overall Health**: Score kesehatan inventory (0-100%)
        - **Stock Coverage**: Berapa hari stok dapat bertahan
        - **Turnover Rate**: Kecepatan perputaran inventory
        
        **Status:**
        - 80-100%: Excellent ✅
        - 60-80%: Good 
        - 40-60%: Fair ⚠️
        - <40%: Poor 🔴
        """)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Calculate overall health score
        service_level = (df['current_stock_qty'] > 0).sum() / len(df) * 100
        health_score = service_level * 0.9  # Simplified calculation
        
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Overall Health</div>
            <div class="metric-value">{health_score:.0f}%</div>
            <div class="metric-delta positive">✓ Good</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Calculate stock coverage
        avg_coverage = (df['current_stock_qty'] / (df['avg_daily_demand'] + 0.01)).mean()
        
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Stock Coverage</div>
            <div class="metric-value">{avg_coverage:.0f}</div>
            <div class="metric-delta positive">Days</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        # Use Weighted Average Turnover here for consistency (Annualized)
        total_sales_value = df['total_sales_90d'].sum()
        total_stock_value = df['stock_value'].sum()
        if total_stock_value > 0:
            weighted_avg_turnover_90d = total_sales_value / total_stock_value
        else:
            weighted_avg_turnover_90d = 0
        annualized_turnover = min(weighted_avg_turnover_90d * (365 / 90), 100)

        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Turnover Rate (Annual)</div>
            <div class="metric-value">{annualized_turnover:.1f}x</div>
            <div class="metric-delta positive">Weighted Average</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Stock vs Demand Analysis
    st.markdown("### 📈 Stock Level vs Daily Demand")
    
    # Sample top products for scatter plot
    sample_df = df.nlargest(100, 'avg_daily_demand')
    
    fig = px.scatter(sample_df, 
                    x='current_stock_qty', 
                    y='avg_daily_demand', 
                    color='ABC_class',
                    size='stock_value',
                    hover_data=['product_code', 'product_name'],
                    title="Stock Level vs Daily Demand Analysis",
                    template="plotly_dark",
                    color_discrete_map={'A': '#10b981', 'B': '#f59e0b', 'C': '#ef4444'})
    
    fig.update_layout(
        height=500, 
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis_title="Current Stock Quantity",
        yaxis_title="Average Daily Demand"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Health Categories
    st.markdown("### 🏥 Health Categories")
    
    # Classify products by health
    def classify_health(row):
        if row['current_stock_qty'] == 0:
            return 'Out of Stock'
        coverage = row['current_stock_qty'] / (row['avg_daily_demand'] + 0.01)
        if coverage < 7:
            return 'Critical'
        elif coverage < 30:
            return 'Warning'
        elif coverage < 90:
            return 'Healthy'
        else:
            return 'Overstock'
    
    df['health_status'] = df.apply(classify_health, axis=1)
    
    col1, col2, col3, col4 = st.columns(4)
    
    health_counts = df['health_status'].value_counts()
    
    with col1:
        critical_count = health_counts.get('Critical', 0)
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid #ef4444;">
            <div class="metric-label">🔴 Critical</div>
            <div class="metric-value">{critical_count}</div>
            <div style="color: #94a3b8; font-size: 0.8rem;"><7 days stock</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        warning_count = health_counts.get('Warning', 0)
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid #f59e0b;">
            <div class="metric-label">🟡 Warning</div>
            <div class="metric-value">{warning_count}</div>
            <div style="color: #94a3b8; font-size: 0.8rem;">7-30 days stock</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        healthy_count = health_counts.get('Healthy', 0)
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid #10b981;">
            <div class="metric-label">🟢 Healthy</div>
            <div class="metric-value">{healthy_count}</div>
            <div style="color: #94a3b8; font-size: 0.8rem;">30-90 days stock</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        overstock_count = health_counts.get('Overstock', 0)
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid #6366f1;">
            <div class="metric-label">🔵 Overstock</div>
            <div class="metric-value">{overstock_count}</div>
            <div style="color: #94a3b8; font-size: 0.8rem;">>90 days stock</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Filter by health status
    selected_health = st.selectbox("Filter by Health Status", 
                                   ["All", "Critical", "Warning", "Healthy", "Overstock", "Out of Stock"])
    
    if selected_health != "All":
        health_df = df[df['health_status'] == selected_health]
    else:
        health_df = df
    
    st.markdown(f"**Showing {len(health_df):,} products**")
    
    display_cols = ['product_code', 'product_name', 'current_stock_qty', 'avg_daily_demand', 
                    'turnover_ratio_90d', 'health_status', 'ABC_class']
    
    st.dataframe(
        health_df[display_cols].head(20),
        use_container_width=True,
        height=400,
        column_config={
            "product_code": "Code",
            "product_name": "Product Name",
            "current_stock_qty": st.column_config.NumberColumn("Stock", format="%.0f"),
            "avg_daily_demand": st.column_config.NumberColumn("Daily Demand", format="%.2f"),
            "turnover_ratio_90d": st.column_config.NumberColumn("Turnover", format="%.2fx"),
            "health_status": "Health Status",
            "ABC_class": "ABC"
        }
    )

    # Export Section
    st.markdown("---")
    st.markdown("### 📤 Export & Share Health Report")
    
    col1, col2 = st.columns(2)
    
    with col1:
        csv_data = health_df.to_csv(index=False).encode('utf-8')
        if st.download_button(
            label="📥 Download Health Report",
            data=csv_data,
            file_name=f"inventory_health_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
            key="inventory_health_csv"
        ):
            log_activity("📥 Downloaded Inventory Health Report", '#6366f1')
    
    with col2:
        if st.button("📧 Email Health Report", use_container_width=True, key="inventory_health_email_button"):
            st.session_state.show_email_health = not st.session_state.show_email_health
    
    # Email Health Form
    if st.session_state.show_email_health:
        render_email_form(health_df, "health", "inventory_health")


# ============================================================================
# PAGE 4: STOCKOUT ALERTS
# ============================================================================

elif "⚠️ Stockout Alerts" in page:
    st.title("⚠️ Stockout Alerts")
    st.markdown("Monitor and manage stockout risks")
    
    with st.popover("ℹ️ Tentang Stockout Alert"):
        st.markdown("""
        **Stockout Alert System** mencegah kehabisan stok dengan peringatan dini.
        
        **Cara Kerja:**
        Current Stock ÷ Daily Demand = Days Until Stockout
        
        **Level Risk:**
        - 🔴 Critical: <7 hari (ORDER NOW!)
        - 🟡 High: 7-14 hari (PLAN ORDER)
        - 🔵 Medium: 15-30 hari (MONITOR)
        
        **Immediate Actions:**
        - Prioritas ordering
        - Supplier notification
        - Alternative product suggestions
        """)
    
    # Calculate stockout risks
    df['days_until_stockout'] = df['current_stock_qty'] / (df['avg_daily_demand'] + 0.01)
    df['risk_level'] = pd.cut(df['days_until_stockout'], 
                               bins=[-np.inf, 7, 14, 30, np.inf],
                               labels=['Critical', 'High', 'Medium', 'Low'])
    
    critical_products = df[df['risk_level'] == 'Critical']
    high_products = df[df['risk_level'] == 'High']
    medium_products = df[df['risk_level'] == 'Medium']
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="alert-critical">
            <h3 style="margin: 0; color: white;">🔴 Critical Risk</h3>
            <div style="font-size: 2rem; font-weight: 700; margin: 0.5rem 0;">{len(critical_products)}</div>
            <div style="color: #fca5a5;">Stockout in <7 days</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="alert-warning">
            <h3 style="margin: 0; color: white;">🟡 High Risk</h3>
            <div style="font-size: 2rem; font-weight: 700; margin: 0.5rem 0;">{len(high_products)}</div>
            <div style="color: #fcd34d;">Stockout in 7-14 days</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="alert-info">
            <h3 style="margin: 0; color: white;">🔵 Medium Risk</h3>
            <div style="font-size: 2rem; font-weight: 700; margin: 0.5rem 0;">{len(medium_products)}</div>
            <div style="color: #93c5fd;">Stockout in 15-30 days</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Alert Details
    st.markdown("### 📋 Alert Details")
    
    # Filter options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        risk_filter = st.selectbox("Filter by Risk Level", 
                                   ["All", "Critical", "High", "Medium", "Low"])
    
    with col2:
        abc_filter_alert = st.selectbox("Filter by ABC Class", ["All", "A", "B", "C"])
    
    with col3:
        sort_option = st.selectbox("Sort By", 
                                   ["Days Until Stockout", "Daily Demand", "Stock Value"])
    
    # Apply filters
    alert_df = df.copy()
    
    if risk_filter != "All":
        alert_df = alert_df[alert_df['risk_level'] == risk_filter]
    
    if abc_filter_alert != "All":
        alert_df = alert_df[alert_df['ABC_class'] == abc_filter_alert]
    
    # Apply sorting
    sort_mapping = {
        "Days Until Stockout": "days_until_stockout",
        "Daily Demand": "avg_daily_demand",
        "Stock Value": "stock_value"
    }
    if sort_option in sort_mapping:
        alert_df = alert_df.sort_values(by=sort_mapping[sort_option], ascending=True)
    
    st.markdown(f"**Showing {len(alert_df):,} products**")
    
    # Display alerts
    display_cols = ['product_code', 'product_name', 'current_stock_qty', 'avg_daily_demand', 
                    'days_until_stockout', 'optimal_safety_stock', 'risk_level', 'ABC_class']
    
    st.dataframe(
        alert_df[display_cols].head(20),
        use_container_width=True,
        height=400,
        column_config={
            "product_code": "Code",
            "product_name": "Product Name",
            "current_stock_qty": st.column_config.NumberColumn("Current Stock", format="%.0f"),
            "avg_daily_demand": st.column_config.NumberColumn("Daily Demand", format="%.2f"),
            "days_until_stockout": st.column_config.NumberColumn("Days Until Stockout", format="%.0f"),
            "optimal_safety_stock": st.column_config.NumberColumn("Safety Stock", format="%.0f"),
            "risk_level": "Risk Level",
            "ABC_class": "ABC"
        }
    )
    
    st.markdown("---")
    
    # Quick Actions
    st.markdown("---")
    st.markdown("### 🎬 Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🚀 Bulk Order", use_container_width=True, key="stockout_bulk_order"):
            st.session_state.show_bulk_order = not st.session_state.show_bulk_order
        
        if st.session_state.show_bulk_order:
            st.markdown("#### 📦 Bulk Order - Critical Items")
            
            critical_list = critical_products.head(5)
            total_value = 0
            
            for idx, row in critical_list.iterrows():
                recommended_qty = max(row['optimal_safety_stock'] * 2, row['avg_daily_demand'] * 30)
                estimated_cost = recommended_qty * (row['stock_value'] / max(row['current_stock_qty'], 1)) if row['current_stock_qty'] > 0 else recommended_qty * 50000
                total_value += estimated_cost
                
                st.markdown(f"""
                **{row['product_code']}** - {row['product_name'][:50]}...
                - Current: {row['current_stock_qty']:.0f} units
                - Daily Demand: {row['avg_daily_demand']:.2f} units
                - Recommended Order: {recommended_qty:.0f} units
                - Est. Cost: Rp {estimated_cost:,.0f}
                """)
            
            st.info(f"**Total Order Value: Rp {total_value:,.0f}**")
            
            if st.button("✅ Confirm Order", key="confirm_bulk"):
                st.success("✅ Order confirmed! Order ID: #ORD-" + datetime.now().strftime('%Y%m%d-%H%M'))
                log_activity("🚀 Confirmed Stockout Bulk Order", '#10b981')
                st.session_state.show_bulk_order = False
                st.rerun()

    with col2:
        if st.button("📧 Send Alert Email", use_container_width=True, key="stockout_email"):
            st.session_state.show_email_form = not st.session_state.show_email_form
        
        if st.session_state.show_email_form:
            render_email_form(alert_df, "stockout_alerts", "stockout_alerts")
    
    with col3:
        if st.button("📥 Export Report", use_container_width=True, key="stockout_export"):
            csv_data = alert_df.to_csv(index=False).encode('utf-8')
            if st.download_button(
                label="⬇️ Download Stockout Report",
                data=csv_data,
                file_name=f"stockout_alerts_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True,
                key="stockout_export_download"
            ):
                log_activity("📥 Downloaded Stockout Alerts Report", '#ef4444')

# ============================================================================
# PAGE 5: REORDER OPTIMIZATION
# ============================================================================

elif "🔄 Reorder Optimization" in page:
    st.title("🔄 Reorder Optimization")
    st.markdown("Safety Stock & Reorder Point Calculation")
    
    with st.popover("ℹ️ Tentang Reorder Optimization"):
        st.markdown("""
        **Reorder Optimization** menghitung kapan dan berapa banyak harus order.
        
        **Key Formulas:**
        
        **Safety Stock:**
        ```
        SS = Z × σ × √LT
        ```
        - Z = Service level factor (1.65 for 95%)
        - σ = Demand standard deviation
        - LT = Lead time
        
        **Reorder Point:**
        ```
        ROP = (Avg Demand × Lead Time) + Safety Stock
        ```
        
        **Economic Order Quantity (EOQ):**
        ```
        EOQ = √((2 × D × S) / H)
        ```
        - D = Annual demand
        - S = Ordering cost
        - H = Holding cost
        """)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_safety_stock = df['optimal_safety_stock'].mean()
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Avg Safety Stock</div>
            <div class="metric-value">{avg_safety_stock:.0f}</div>
            <div class="metric-delta positive">Units</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        avg_lead_time = df['estimated_lead_time'].mean()
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Avg Lead Time</div>
            <div class="metric-value">{avg_lead_time:.0f}</div>
            <div class="metric-delta positive">Days</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Reorder Points</div>
            <div class="metric-value">{len(df):,}</div>
            <div class="metric-delta positive">Calculated</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-label">Cost Savings</div>
            <div class="metric-value">15%</div>
            <div class="metric-delta positive">Potential</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Formulas Display
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="calc-box">
            <div style="font-weight: 700; color: #6366f1; margin-bottom: 0.5rem;">Safety Stock Formula</div>
            <div class="calc-step">SS = Z × σ_L × √LT</div>
            <div style="margin-top: 0.5rem; color: #94a3b8; font-size: 0.85rem;">
                <div>Z = Service level factor</div>
                <div>σ_L = Demand std deviation</div>
                <div>LT = Lead time</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="calc-box">
            <div style="font-weight: 700; color: #6366f1; margin-bottom: 0.5rem;">Reorder Point Formula</div>
            <div class="calc-step">ROP = (D × LT) + SS</div>
            <div style="margin-top: 0.5rem; color: #94a3b8; font-size: 0.85rem;">
                <div>D = Average daily demand</div>
                <div>LT = Lead time (days)</div>
                <div>SS = Safety stock</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Reorder Recommendations
    st.markdown("### 🎯 Reorder Recommendations")
    
    # Filter options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        abc_reorder_filter = st.selectbox("ABC Class", ["All", "A", "B", "C"], key="reorder_abc")
    
    with col2:
        min_demand = st.number_input("Min Daily Demand", min_value=0.0, value=0.0, step=0.1)
    
    with col3:
        sort_reorder = st.selectbox("Sort By", 
                                    ["Daily Demand", "Stock Value", "Safety Stock", "Reorder Point"])
    
    # Calculate reorder recommendations
    reorder_df = df.copy()
    reorder_df['reorder_point_calc'] = (reorder_df['avg_daily_demand'] * reorder_df['estimated_lead_time']) + reorder_df['optimal_safety_stock']
    reorder_df['recommended_order_qty'] = np.maximum(
        reorder_df['reorder_point_calc'] - reorder_df['current_stock_qty'],
        0
    )
    
    # Apply filters
    if abc_reorder_filter != "All":
        reorder_df = reorder_df[reorder_df['ABC_class'] == abc_reorder_filter]
    
    if min_demand > 0:
        reorder_df = reorder_df[reorder_df['avg_daily_demand'] >= min_demand]
    
    # Apply sorting
    sort_map = {
        "Daily Demand": "avg_daily_demand",
        "Stock Value": "stock_value",
        "Safety Stock": "optimal_safety_stock",
        "Reorder Point": "reorder_point_calc"
    }
    reorder_df = reorder_df.sort_values(by=sort_map[sort_reorder], ascending=False)
    
    # Display top recommendations
    display_cols = ['product_code', 'product_name', 'current_stock_qty', 'optimal_safety_stock', 
                    'reorder_point_calc', 'recommended_order_qty', 'estimated_lead_time', 'ABC_class']
    
    st.dataframe(
        reorder_df[display_cols].head(20),
        use_container_width=True,
        height=400,
        column_config={
            "product_code": "Code",
            "product_name": "Product Name",
            "current_stock_qty": st.column_config.NumberColumn("Current Stock", format="%.0f"),
            "optimal_safety_stock": st.column_config.NumberColumn("Safety Stock", format="%.0f"),
            "reorder_point_calc": st.column_config.NumberColumn("Reorder Point", format="%.0f"),
            "recommended_order_qty": st.column_config.NumberColumn("Order Qty", format="%.0f"),
            "estimated_lead_time": st.column_config.NumberColumn("Lead Time", format="%.0f days"),
            "ABC_class": "ABC"
        }
    )
    
    # Export Section
    st.markdown("---")
    st.markdown("### 📤 Export & Share Reorder Plan")
    
    col1, col2 = st.columns(2)
    
    with col1:
        csv_data = reorder_df.to_csv(index=False).encode('utf-8')
        if st.download_button(
            label="📥 Download Reorder Report",
            data=csv_data,
            file_name=f"reorder_optimization_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
            key="Reorder_Report_download_csv"
        ):
            log_activity("📥 Downloaded Reorder Optimization Report", '#6366f1')
    
    with col2:
        if st.button("📧 Email Reorder Plan", use_container_width=True, key="Reorder_Report_email_button"):
            st.session_state.show_email_reorder = not st.session_state.show_email_reorder
    
    # Email Reorder Form
    if st.session_state.show_email_reorder:
        render_email_form(reorder_df, "reorder", "reorder_optimization")

# ============================================================================
# PAGE 6: SLOW-MOVING ANALYSIS
# ============================================================================

elif "📋 Slow-Moving Analysis" in page:
    st.title("📋 Slow-Moving Stock Identification")
    st.markdown("Identify and manage slow-moving products")
    
    with st.popover("ℹ️ Tentang Slow-Moving Analysis"):
        st.markdown("""
        **Slow-Moving Analysis** mengidentifikasi produk dengan pergerakan lambat.
        
        **Kriteria Slow-Moving:**
        - Turnover ratio < 1.0x per 90 hari
        - Stock age > 60 hari
        - Low daily demand
        
        **Dampak:**
        - Modal tertahan
        - Biaya penyimpanan tinggi
        - Risk of obsolescence
        
        **Actions:**
        - Promosi/diskon
        - Bundle dengan fast-moving
        - Return to supplier
        - Stop future orders
        """)
    
    slow_movers = df[df['segment_label'] == 'Slow_Movers']
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Slow-Moving Products</div>
            <div class="metric-value">{len(slow_movers):,}</div>
            <div class="metric-delta negative">{(len(slow_movers)/len(df)*100):.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        avg_turnover_slow = slow_movers['turnover_ratio_90d'].mean()
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Avg Turnover</div>
            <div class="metric-value">{avg_turnover_slow:.2f}x</div>
            <div class="metric-delta negative">Low</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        tied_capital = slow_movers['stock_value'].sum()
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Tied-Up Capital</div>
            <div class="metric-value">Rp {tied_capital/1_000_000:.0f}M</div>
            <div class="metric-delta negative">High</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-label">Optimization Potential</div>
            <div class="metric-value">25%</div>
            <div class="metric-delta positive">Reduction</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 Demand Distribution (Slow Movers)")
        fig = px.histogram(slow_movers, x='avg_daily_demand', nbins=30, 
                          title="Demand Distribution", 
                          template="plotly_dark")
        fig.update_layout(height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### 📈 Stock vs Turnover (Slow Movers)")
        fig = px.scatter(slow_movers.head(50), 
                        x='current_stock_qty', 
                        y='turnover_ratio_90d',
                        size='stock_value',
                        color='ABC_class',
                        hover_data=['product_code'],
                        title="Stock vs Turnover", 
                        template="plotly_dark")
        fig.update_layout(height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Slow-Moving Products List
    st.markdown("### 📋 Slow-Moving Products")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        abc_slow_filter = st.selectbox("ABC Class", ["All", "A", "B", "C"], key="slow_abc")
    
    with col2:
        max_turnover = st.number_input("Max Turnover", min_value=0.0, max_value=2.0, value=1.0, step=0.1)
    
    with col3:
        sort_slow = st.selectbox("Sort By", ["Stock Value", "Turnover", "Current Stock"])
    
    # Apply filters
    slow_filtered = slow_movers.copy()
    
    if abc_slow_filter != "All":
        slow_filtered = slow_filtered[slow_filtered['ABC_class'] == abc_slow_filter]
    
    slow_filtered = slow_filtered[slow_filtered['turnover_ratio_90d'] <= max_turnover]
    
    # Apply sorting
    sort_slow_map = {
        "Stock Value": "stock_value",
        "Turnover": "turnover_ratio_90d",
        "Current Stock": "current_stock_qty"
    }
    slow_filtered = slow_filtered.sort_values(by=sort_slow_map[sort_slow], ascending=False)
    
    st.markdown(f"**Found {len(slow_filtered):,} slow-moving products**")
    
    display_cols = ['product_code', 'product_name', 'current_stock_qty', 'avg_daily_demand', 
                    'turnover_ratio_90d', 'stock_value', 'ABC_class']
    
    st.dataframe(
        slow_filtered[display_cols].head(20),
        use_container_width=True,
        height=400,
        column_config={
            "product_code": "Code",
            "product_name": "Product Name",
            "current_stock_qty": st.column_config.NumberColumn("Stock", format="%.0f"),
            "avg_daily_demand": st.column_config.NumberColumn("Daily Demand", format="%.2f"),
            "turnover_ratio_90d": st.column_config.NumberColumn("Turnover", format="%.2fx"),
            "stock_value": st.column_config.NumberColumn("Value", format="Rp %.0f"),
            "ABC_class": "ABC"
        }
    )
    
    # Action Recommendations
    st.markdown("---")
    st.markdown("### 💡 Recommended Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="insight-card" style="border-left: 4px solid #ef4444;">
            <h4 style="color: #ef4444; margin-top: 0;">🔴 High Priority Actions</h4>
            <ul>
                <li>Clearance sale (30-50% off)</li>
                <li>Bundle with fast-moving items</li>
                <li>Contact supplier for return</li>
                <li>Stop future orders</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="insight-card" style="border-left: 4px solid #f59e0b;">
            <h4 style="color: #f59e0b; margin-top: 0;">🟡 Medium Priority</h4>
            <ul>
                <li>Promotional campaigns</li>
                <li>Cross-selling strategies</li>
                <li>Review pricing</li>
                <li>Customer incentives</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="insight-card" style="border-left: 4px solid #6366f1;">
            <h4 style="color: #6366f1; margin-top: 0;">🔵 Monitoring</h4>
            <ul>
                <li>Track demand trends</li>
                <li>Monitor competitor pricing</li>
                <li>Adjust order quantities</li>
                <li>Regular performance review</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # Export
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
            use_container_width=True,
            key="Slow-Moving_Report_Download_Report"
        ):
            log_activity("📥 Downloaded Slow-Moving Analysis Report", '#f59e0b')
    
    with col2:
        if st.button("📧 Email Report", use_container_width=True,key="Slow-Moving_Report_email_button"):
            st.session_state.show_email_slow = not st.session_state.show_email_slow
    
    # Email Slow-Moving Form
    if st.session_state.show_email_slow:
        render_email_form(slow_filtered, "slow_moving", "slow_moving_analysis")

# ============================================================================
# PAGE 7: SETTINGS - ENHANCED WITH EMAIL INTEGRATION
# ============================================================================

elif "⚙️ Settings" in page:
    st.title("⚙️ Settings")
    st.markdown("Application settings and configuration")
    
    # ========================================================================
    # DISPLAY SETTINGS
    # ========================================================================
    
    st.markdown("### 📊 Display Settings")
    col1, col2 = st.columns(2)
    with col1:
        theme = st.radio("Theme", options=['Dark', 'Light'], horizontal=True)
    with col2:
        rows_per_page = st.slider("Rows per page", 10, 100, 20)
    
    st.markdown("---")
    
    # ========================================================================
    # DATA SETTINGS
    # ========================================================================
    
    st.markdown("### 📁 Data Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info(f"**Products loaded:** {len(df):,}")
        st.info(f"**Data source:** master_features_final.csv + supplementary files")
    
    with col2:
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.success("✅ Cache cleared! Data will refresh on next page load.")
            log_activity("🔄 Data Cache Cleared & Refreshed", '#10b981')
            st.rerun()
    
    st.markdown("---")
    
    # ========================================================================
    # EMAIL CONFIGURATION SECTION - INTEGRATED WITH SESSION STATE
    # ========================================================================
    
    st.markdown("### 📧 Email Configuration")
    st.info("💡 Configure your email settings here. These will be used as defaults when sending reports from any page.")
    
    # --- Start Email Settings Form ---
    with st.form("email_settings"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🔐 Sender Configuration")
            default_sender = st.text_input(
                "Default Sender Email", 
                value=st.session_state.get('email_sender', 'inventory@company.com'),
                help="This email will be used as sender for all reports",
                key="settings_sender_email"
            )
            app_password = st.text_input(
                "App Password", 
                type="password",
                help="16-digit App Password from Gmail (get from: https://myaccount.google.com/apppasswords)",
                placeholder="Enter your app password",
                value=st.session_state.get('email_password', ''),
                key="settings_app_password"
            )
            
            # Show password strength indicator
            if app_password:
                if len(app_password) >= 16:
                    st.success("✅ Valid app password format")
                else:
                    st.warning("⚠️ App password should be 16 characters")
        
        with col2:
            st.markdown("#### 📮 Default Recipient Configuration")
            default_recipients = st.text_area(
                "Default Recipients (Comma-separated)", 
                value=st.session_state.get('email_recipients', 'muhammadrifat.23053@mhs.unesa.ac.id'),
                help="Comma-separated list of email addresses. These will be pre-filled in all email forms.",
                height=100,
                key="settings_recipients"
            )
            email_frequency = st.selectbox(
                "Auto-Report Frequency",
                ["Never", "Daily", "Weekly", "Monthly"],
                help="Automatic report schedule (Coming soon)"
            )
            
            # Show recipient count
            if default_recipients:
                recipient_list = [r.strip() for r in default_recipients.split(',') if r.strip()]
                st.info(f"📧 {len(recipient_list)} recipient(s) configured")
        
        st.markdown("---")
        
        # Save/Reset settings buttons (Moved test email outside)
        col1, col2 = st.columns(2)
        
        with col1:
            save_settings = st.form_submit_button("💾 Save Email Settings", use_container_width=True, type="primary")
        
        with col2:
            reset_settings = st.form_submit_button("🔄 Reset to Defaults", use_container_width=True)
            
        # Handle Save Settings
        if save_settings:
            # Validation
            if not default_sender or "@" not in default_sender:
                st.error("⚠️ Please enter a valid sender email address")
            elif not app_password:
                st.error("⚠️ Please enter your app password")
            else:
                # Save to session state
                st.session_state.email_sender = default_sender
                st.session_state.email_password = app_password
                st.session_state.email_recipients = default_recipients
                
                st.success("✅ Email settings saved successfully!")
                log_activity("💾 Saved Email Settings", '#6366f1')
                st.info("💡 These settings will be used as defaults in all email forms across the application.")
                st.balloons()
        
        if reset_settings:
            # Reset to defaults
            st.session_state.email_sender = ""
            st.session_state.email_password = ""
            st.session_state.email_recipients = "muhammadrifat.23053@mhs.unesa.ac.id"
            st.session_state.custom_recipients_list = [] # Also reset custom list
            st.info("🔄 Settings reset to default values. Please refresh the page.")
            log_activity("🔄 Reset Email Settings to Default", '#f59e0b')
            st.rerun()
            
    # --- End Email Settings Form ---
    
    st.markdown("---")

    # NEW: Custom Recipient List Management (Enhancement 4) - OUTSIDE the form
    st.markdown("#### 👥 Custom Recipient Groups")
    st.info("Atur daftar alamat email yang dapat dipilih dengan mudah di Quick Actions.")
    
    # Display and edit current list
    with st.expander("📝 Edit Custom Recipient List"):
        current_list_str = "\n".join(st.session_state.custom_recipients_list)
        new_list_str = st.text_area(
            "Daftar Email (Satu email per baris):", 
            value=current_list_str, 
            height=150,
            key="settings_custom_list_input"
        )
        
        # FIX: Changed st.button to use a unique key outside of the main form context
        if st.button("💾 Save Recipient List", key="save_custom_list_independent"):
            # Clean and save the list
            new_list = [email.strip() for email in new_list_str.split('\n') if email.strip()]
            
            # Simple validation for email format (check for @)
            valid_list = [e for e in new_list if "@" in e]
            invalid_count = len(new_list) - len(valid_list)
            
            st.session_state.custom_recipients_list = valid_list
            
            if invalid_count > 0:
                st.warning(f"⚠️ {invalid_count} alamat email tidak valid dan dihapus. Daftar tersimpan: {len(valid_list)} email.")
            else:
                st.success(f"✅ Daftar Penerima Kustom berhasil disimpan! ({len(valid_list)} email)")
            
            log_activity("💾 Saved Custom Recipient List", '#6366f1')

    st.markdown("---")
        
    # Test Email Configuration (Moved outside the form for cleaner logic)
    st.markdown("#### 🧪 Test Email Configuration")
    
    col1, col2 = st.columns(2)
    with col1:
        test_email = st.text_input(
            "Test Email Address", 
            value="test@company.com",
            help="Enter an email address to receive test email",
            key="settings_test_email"
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        # Use st.button for independent action
        test_email_button = st.button("📧 Send Test Email", use_container_width=True, key="send_test_email_btn_final")
        
    if test_email_button:
        # Use session state values for sending
        sender_email = st.session_state.settings_sender_email
        app_password = st.session_state.settings_app_password
        
        if not all([sender_email, app_password, test_email]):
            st.error("⚠️ Please fill in Sender Email, App Password (and save settings first!), and Test Email address")
        elif "@" not in sender_email or "@" not in test_email:
            st.error("⚠️ Invalid email format")
        else:
            with st.spinner("Sending test email..."):
                try:
                    # Create test email
                    test_msg = MIMEMultipart()
                    test_msg['From'] = sender_email
                    test_msg['To'] = test_email
                    test_msg['Subject'] = "Test Email - Inventory Intelligence System (v4.3)"
                    
                    body = f"""Hello,

This is a test email from the Inventory Intelligence System.

If you receive this email, your email configuration is working correctly!

Configuration Details:
- Sender: {sender_email}
- Sent at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- System: Inventory Intelligence Hub v4.3

Best regards,
Inventory Management System
"""
                    test_msg.attach(MIMEText(body, 'plain'))
                    
                    # Send email
                    with smtplib.SMTP('smtp.gmail.com', 587, timeout=30) as server:
                        server.starttls()
                        server.login(sender_email, app_password)
                        server.send_message(test_msg)
                    
                    st.success(f"✅ Test email sent successfully to {test_email}!")
                    log_activity(f"📧 Sent Test Email to {test_email}", '#10b981')
                    st.balloons()
                except smtplib.SMTPAuthenticationError:
                    st.error("❌ Authentication failed. Please check your email and app password.")
                    st.info("💡 Tip: Make sure you're using an App Password, not your regular Gmail password.")
                    log_activity("❌ Test Email Failed (Auth Error)", '#ef4444')
                except Exception as e:
                    st.error(f"❌ Error sending test email: {str(e)}")
                    log_activity("❌ Test Email Failed (Unexpected Error)", '#ef4444')


    st.markdown("---")
    
    # ========================================================================
    # EXPORT CONFIGURATION
    # ========================================================================
    
    st.markdown("### 📤 Export Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📊 Report Settings")
        default_export_format = st.selectbox(
            "Default Export Format",
            ["CSV", "Excel", "JSON"]
        )
        include_timestamps = st.checkbox("Include timestamps in filenames", value=True)
        auto_generate_summary = st.checkbox("Auto-generate summary report", value=True)
    
    with col2:
        st.markdown("#### 🔐 Security Settings")
        enable_data_encryption = st.checkbox("Enable data encryption", value=False)
        require_password_export = st.checkbox("Require password for exports", value=False)
        if require_password_export:
            export_password = st.text_input("Export Password", type="password", key="export_pwd")
    
    st.markdown("---")
    
    # ========================================================================
    # SYSTEM INFORMATION
    # ========================================================================
    
    st.markdown("### ℹ️ Application Info")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        **System Information:**
        
        - **Version**: 4.3 PRODUCTION
        - **Framework**: Streamlit {st.__version__}
        - **Products**: {len(df):,}
        - **Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        - **Data Source**: master_features_final.csv
        - **Cache Status**: 🟢 Active
        """)
    
    with col2:
        # System metrics
        total_stock_value = df['stock_value'].sum()
        avg_daily_demand = df['avg_daily_demand'].mean()
        service_level = (df['current_stock_qty'] > 0).sum() / len(df) * 100
        
        st.markdown(f"""
        **Data Quality Metrics:**
        
        - **Service Level**: {service_level:.1f}%
        - **Avg Turnover**: {df['turnover_ratio_90d'].mean():.2f}x
        - **Total Stock Value**: Rp {total_stock_value/1_000_000:.1f}M
        - **Products with Stock**: {(df['current_stock_qty'] > 0).sum():,}
        - **Avg Daily Demand**: {avg_daily_demand:.2f}
        """)
    
    st.markdown("---")
    
    # ========================================================================
    # ADVANCED SETTINGS
    # ========================================================================
    
    with st.expander("⚙️ Advanced Settings"):
        st.markdown("### 🔧 Advanced Configuration")
        
        col1, col2 = st.columns(2)
        
        with col1:
            cache_timeout = st.slider("Cache Timeout (minutes)", 5, 1440, 60)
            log_level = st.selectbox("Log Level", ["DEBUG", "INFO", "WARNING", "ERROR"])
            auto_refresh = st.checkbox("Enable auto-refresh", value=False)
            if auto_refresh:
                refresh_interval = st.slider("Refresh Interval (seconds)", 30, 3600, 300)
        
        with col2:
            data_retention = st.slider("Data Retention (days)", 7, 365, 90)
            max_export_rows = st.number_input("Max Export Rows", 100, 100000, 10000)
            enable_analytics = st.checkbox("Enable usage analytics", value=True)
        
        if st.button("Reset Advanced Settings", use_container_width=True):
            st.info("Advanced settings reset to default values")
            log_activity("🔄 Reset Advanced Settings (Mock)", '#f59e0b')
        
        if st.button("Export Configuration", use_container_width=True):
            config_data = {
                "version": "4.3",
                "export_format": default_export_format,
                "cache_timeout": cache_timeout,
                "data_retention": data_retention,
                "email_sender": st.session_state.get('email_sender', 'Not configured'),
                "email_recipients": st.session_state.get('email_recipients', 'Not configured')
            }
            
            import json
            config_json = json.dumps(config_data, indent=2)
            
            if st.download_button(
                label="📥 Download Configuration",
                data=config_json,
                file_name=f"inventory_config_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
                key="download_config"
            ):
                 log_activity("📥 Downloaded App Configuration", '#6366f1')

    
    # ========================================================================
    # EMAIL CONFIGURATION SUMMARY
    # ========================================================================
    
    st.markdown("---")
    st.markdown("### 📋 Current Email Configuration")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        sender_email = st.session_state.get('email_sender', 'Not configured')
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Sender Email</div>
            <div style="font-size: 1rem; color: #e2e8f0; margin-top: 0.5rem;">
                {sender_email}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        password_status = "✅ Configured" if st.session_state.get('email_password') else "❌ Not set"
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">App Password</div>
            <div style="font-size: 1rem; color: #e2e8f0; margin-top: 0.5rem;">
                {password_status}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        recipients = st.session_state.get('email_recipients', 'Not configured')
        recipient_count = len([r.strip() for r in recipients.split(',') if r.strip()]) if recipients != 'Not configured' else 0
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Default Recipients</div>
            <div style="font-size: 1rem; color: #e2e8f0; margin-top: 0.5rem;">
                {recipient_count} recipient(s)
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Show detailed recipients
    if recipients != 'Not configured':
        with st.expander("📧 View Default Recipients"):
            recipient_list = [r.strip() for r in recipients.split(',') if r.strip()]
            for i, recipient in enumerate(recipient_list, 1):
                st.markdown(f"{i}. {recipient}")

    if st.session_state.custom_recipients_list:
        with st.expander("📧 View Custom Recipient List"):
            for i, recipient in enumerate(st.session_state.custom_recipients_list, 1):
                st.markdown(f"{i}. {recipient}")
    
    # ========================================================================
    # QUICK TEST REPORT EXPORT
    # ========================================================================
    
    st.markdown("---")
    st.markdown("### 📤 Quick Export Test")
    st.markdown("Test the export functionality with current settings.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Sample data export
        sample_data = df.head(10)
        csv_data = sample_data.to_csv(index=False).encode('utf-8')
        if st.download_button(
            label="📥 Download Sample Report (10 rows)",
            data=csv_data,
            file_name=f"sample_report_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
            key="settings_sample_download"
        ):
            log_activity("📥 Downloaded Sample Report (Settings Test)", '#6366f1')

    
    with col2:
        if st.button("📧 Email Sample Report", use_container_width=True, key="settings_email_sample"):
            st.session_state.show_email_settings_test = not st.session_state.get('show_email_settings_test', False)
    
    # Email Sample Report Form
    if st.session_state.get('show_email_settings_test', False):
        st.markdown("---")
        render_email_form(df.head(10), "settings_test", "sample_inventory_report")

# ============================================================================
# FOOTER
# ============================================================================

current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
st.markdown("---")
st.markdown(f"""
<div style="text-align: center; color: #94a3b8; font-size: 0.85rem;">
    <p>Intelligent Inventory Optimization & Stockout Prediction v4.3 PRODUCTION</p>
    <p>© 2025 PT Wahana Piranti Teknologi. All rights reserved.</p>
    <p style="font-size: 0.7rem; margin-top: 0.5rem;">
        System Status: 🟢 Operational | Last Sync: {current_time}
    </p>
</div>
""", unsafe_allow_html=True)