# File: modules/pages/settings.py (Versi Final dengan Grup Penerima)

"""
Settings Page
=============
Allows users to configure application settings, including display, data,
and a comprehensive email integration with custom recipient groups.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from modules.activity_logger import log_activity
from modules.email_utils import render_email_form

def render_page(df: pd.DataFrame):
    """
    Merender seluruh konten untuk halaman Settings yang canggih.
    
    Args:
        df (pd.DataFrame): DataFrame utama, digunakan untuk info dan metrik.
    """
    
    st.title("⚙️ Settings")
    st.markdown("Application settings and configuration")

    # ========================================================================
    # DATA SETTINGS
    # ========================================================================
    
    with st.expander("📁 Data Settings", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**Products Loaded:** {len(df):,}")
            st.info(f"**Data Source:** `master_features_final.csv` & others")
        with col2:
            if st.button("🔄 Refresh Data Cache", width='stretch', help="Clears the server cache to reload all data from source files on the next interaction."):
                st.cache_data.clear()
                log_activity("🔄 Data Cache Cleared", '#10b981')
                st.success("✅ Cache cleared! Data will be reloaded.")
                st.rerun()

    # ========================================================================
    # EMAIL CONFIGURATION FORM
    # ========================================================================
    
    st.markdown("### 📧 Email Configuration")
    st.info("💡 Konfigurasikan kredensial SMTP Anda di sini. Pengaturan ini akan disimpan dalam session ini.")
    
    with st.form("email_settings_form"):
        st.markdown("#### 🔐 Sender Configuration")
        col1, col2 = st.columns(2)
        with col1:
            sender_email = st.text_input("Default Sender Email", value=st.session_state.get('email_sender', ''), key="form_sender_email")
        with col2:
            app_password = st.text_input("App Password", type="password", value=st.session_state.get('email_password', ''), key="form_app_password", help="Gunakan 16-digit App Password dari akun Google Anda.")
        
        st.markdown("#### 📮 Default Recipient Configuration")
        default_recipients = st.text_area("Default Recipients (comma-separated)", value=st.session_state.get('email_recipients', ''), key="form_recipients", height=100)
        
        col1, col2 = st.columns(2)
        with col1:
            save_button = st.form_submit_button("💾 Save Email Settings", width='stretch', type="primary")
        with col2:
            reset_button = st.form_submit_button("🔄 Reset to Defaults", width='stretch')

    if save_button:
        if "@" not in sender_email or len(app_password) < 16:
            st.error("⚠️ Please provide a valid Sender Email and a 16-character App Password.")
        else:
            st.session_state.email_sender = sender_email
            st.session_state.email_password = app_password
            st.session_state.email_recipients = default_recipients
            log_activity("💾 Email Settings Saved", '#6366f1')
            st.success("✅ Email settings saved successfully for this session!")

    if reset_button:
        st.session_state.email_sender = ""
        st.session_state.email_password = ""
        st.session_state.email_recipients = ""
        st.session_state.custom_recipients_list = []
        log_activity("🔄 Reset Email Settings", '#f59e0b')
        st.info("Settings have been reset. Rerunning page...")
        st.rerun()

    # ========================================================================
    # CUSTOM RECIPIENT GROUPS (LOGIKA YANG HILANG)
    # ========================================================================

    st.markdown("---")
    st.markdown("### 👥 Custom Recipient Groups")
    st.info("Atur daftar alamat email yang dapat dipilih dengan mudah di form email pada halaman lain.")

    with st.expander("📝 Edit Custom Recipient List"):
        # Ambil daftar yang ada dari session state, atau list kosong jika belum ada
        current_list_str = "\n".join(st.session_state.get('custom_recipients_list', []))
        
        new_list_str = st.text_area(
            "Daftar Email (satu email per baris):", 
            value=current_list_str, 
            height=150,
            key="settings_custom_list_input"
        )
        
        if st.button("💾 Save Recipient List", key="save_custom_list_button"):
            # Bersihkan dan simpan daftar baru
            new_list = [email.strip() for email in new_list_str.split('\n') if email.strip()]
            valid_list = [e for e in new_list if "@" in e]
            invalid_count = len(new_list) - len(valid_list)
            
            st.session_state.custom_recipients_list = valid_list
            
            if invalid_count > 0:
                st.warning(f"⚠️ {invalid_count} email tidak valid diabaikan. Daftar tersimpan: {len(valid_list)} email.")
            else:
                st.success(f"✅ Daftar Penerima Kustom berhasil disimpan! ({len(valid_list)} email)")
            
            log_activity("💾 Saved Custom Recipient List", '#6366f1')
            st.rerun() # Rerun untuk memperbarui ringkasan di bawah

    # ========================================================================
    # TEST EMAIL CONFIGURATION
    # ========================================================================
    
    st.markdown("---")
    st.markdown("### 🧪 Test Email Configuration")
    test_email_address = st.text_input("Test Email Address", placeholder="Enter an email to send a test to", key="settings_test_email_input")
    
    if st.button("📧 Send Test Email", width='stretch', key="send_test_email_btn"):
        # Ambil kredensial dari session state
        sender = st.session_state.get('email_sender')
        password = st.session_state.get('email_password')
        
        if not all([sender, password, test_email_address]):
            st.error("⚠️ Please save your Sender Email & App Password first, and provide a test email address.")
        else:
            with st.spinner("Sending test email..."):
                try:
                    msg = MIMEMultipart()
                    msg['From'] = sender
                    msg['To'] = test_email_address
                    msg['Subject'] = "Test Email - Inventory Intelligence System v4.3"
                    body = f"""Hello,\n\nThis is a test email from the Inventory Intelligence System.\nIf you received this, your configuration is working correctly!\n\n- Sender: {sender}\n- Sent at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
                    msg.attach(MIMEText(body, 'plain'))
                    
                    with smtplib.SMTP('smtp.gmail.com', 587, timeout=20) as server:
                        server.starttls()
                        server.login(sender, password)
                        server.send_message(msg)
                    
                    st.success(f"✅ Test email sent successfully to {test_email_address}!")
                    log_activity(f"📧 Sent Test Email to {test_email_address}", '#10b981')
                except smtplib.SMTPAuthenticationError:
                    st.error("❌ Authentication failed. Please double-check your email and 16-digit App Password.")
                    log_activity("❌ Test Email Failed (Auth Error)", '#ef4444')
                except Exception as e:
                    st.error(f"❌ An error occurred: {e}")
                    log_activity("❌ Test Email Failed (General Error)", '#ef4444')
    
    st.markdown("---")
    
    # ========================================================================
    # SYSTEM INFORMATION
    # ========================================================================
    
    st.markdown("### ℹ️ Application & Data Info")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**System Information**")
        st.json({
            "Version": "4.3 PRODUCTION",
            "Streamlit Version": st.__version__,
            "Cache Status": "Active (TTL: 3600s)",
            "Last Page Load": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    with col2:
        st.markdown("**Data Quality Metrics**")
        total_stock_value = df['stock_value'].sum()
        service_level = (df['current_stock_qty'] > 0).sum() / len(df) * 100
        st.json({
            "Products Monitored": f"{len(df):,}",
            "Total Stock Value": f"Rp {total_stock_value/1_000_000_000:.2f}B",
            "Overall Service Level": f"{service_level:.1f}%",
            "Products with Stock": f"{(df['current_stock_qty'] > 0).sum():,}"
        })

    # ========================================================================
    # CURRENT CONFIGURATION SUMMARY
    # ========================================================================

    st.markdown("---")
    st.markdown("### 📋 Current Session Configuration")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        sender_email = st.session_state.get('email_sender', 'Not Configured')
        st.metric("Sender Email", sender_email if len(sender_email) < 20 else sender_email[:17] + "...")
    with col2:
        password_status = "✅ Configured" if st.session_state.get('email_password') else "❌ Not Set"
        st.metric("App Password Status", password_status)
    with col3:
        recipients = st.session_state.get('email_recipients', '')
        recipient_count = len([r.strip() for r in recipients.split(',') if r.strip()])
        st.metric("Default Recipients", f"{recipient_count} address(es)")

    if recipients:
        with st.expander("View Default Recipients"):
            st.code(recipients.replace(",", "\n"))
    
    # ========================================================================
    # CURRENT CONFIGURATION SUMMARY (DENGAN PENAMBAHAN GRUP KUSTOM)
    # ========================================================================

    st.markdown("---")
    st.markdown("### 📋 Current Session Configuration")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        sender_email_summary = st.session_state.get('email_sender', 'Not Set')
        st.metric("Sender Email", sender_email_summary if len(sender_email_summary) < 18 else sender_email_summary[:15] + "...")
    with col2:
        password_status = "✅ Configured" if st.session_state.get('email_password') else "❌ Not Set"
        st.metric("App Password", password_status)
    with col3:
        recipients = st.session_state.get('email_recipients', '')
        recipient_count = len([r.strip() for r in recipients.split(',') if r.strip()])
        st.metric("Default Recipients", f"{recipient_count}")
    with col4:
        custom_list = st.session_state.get('custom_recipients_list', [])
        st.metric("Custom Groups", f"{len(custom_list)}")