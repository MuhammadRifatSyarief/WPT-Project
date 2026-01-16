# File: modules/pages/settings.py (Versi Lengkap dan Final)

"""
Settings Page
=============
Allows users to configure application settings, including display, data,
and a comprehensive email integration with validation and testing.
"""

# 1. Impor library yang dibutuhkan
import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# 2. Impor fungsi dari modul kustom Anda
from modules.activity_logger import log_activity
from modules.email_utils import render_email_form
from modules.auth import is_admin, get_current_user
from modules.database import (
    save_puller_config,
    get_puller_config,
    get_puller_execution_history
)
from modules.data_puller_service import get_puller_service
from modules.permissions import require_edit_permission

# 3. Definisikan fungsi render halaman
def render_page(df: pd.DataFrame):
    """
    Merender seluruh konten untuk halaman Settings yang canggih.
    
    Args:
        df (pd.DataFrame): DataFrame utama, digunakan untuk info dan metrik.
    """
    
    st.title("Settings")
    st.markdown("Application settings and configuration")
    
    # ========================================================================
    # DISPLAY SETTINGS (Visual Placeholder)
    # ========================================================================
    
    with st.expander("Display Settings", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.radio("Theme (Visual only)", options=['Dark', 'Light'], horizontal=True, help="This is a visual placeholder and does not change the app's theme.")
        with col2:
            st.slider("Rows per page (Visual only)", 10, 100, 20, help="This is a visual placeholder.")
    
    # ========================================================================
    # DATA SETTINGS
    # ========================================================================
    
    with st.expander("📁 Data Settings", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**Products Loaded:** {len(df):,}")
            st.info(f"**Data Source:** `master_features_final.csv` & others")
        with col2:
            if st.button("Refresh Data Cache", use_container_width=True, help="Clears the server cache to reload all data from source files on the next interaction."):
                st.cache_data.clear()
                log_activity("Data Cache Cleared", '#10b981')
                st.success("Cache cleared! Data will be reloaded.")
                st.rerun()

    # ========================================================================
    # DATA PULLER CONFIGURATION (Admin Only)
    # ========================================================================
    
    st.markdown("---")
    st.markdown("### Data Puller Configuration")
    st.info("Konfigurasikan data puller untuk menjalankan pull data secara otomatis setiap minggu. Hanya admin yang dapat mengakses fitur ini.")
    
    if not is_admin():
        st.warning("Hanya admin yang dapat mengakses konfigurasi data puller.")
    else:
        # Get current config
        current_config = get_puller_config()
        
        with st.expander("Configure Data Puller", expanded=True):
            # Project selection
            project_option = st.selectbox(
                "Select Project",
                options=['project1', 'project2', 'both'],
                index=0 if not current_config else ['project1', 'project2', 'both'].index(current_config.get('project_name', 'project1')),
                help="Pilih project yang akan dijalankan: Project 1 (Inventory), Project 2 (Sales), atau Keduanya"
            )
            
            # Date range selection
            col1, col2 = st.columns(2)
            with col1:
                # Handle date conversion - could be date object or string
                if current_config and current_config.get('start_date'):
                    start_date_value = current_config['start_date']
                    if isinstance(start_date_value, str):
                        start_date_value = datetime.strptime(start_date_value, '%Y-%m-%d').date()
                    elif isinstance(start_date_value, date):
                        start_date_value = start_date_value
                    elif hasattr(start_date_value, 'date'):
                        start_date_value = start_date_value.date()
                    else:
                        start_date_value = datetime.now().date() - timedelta(days=90)
                else:
                    start_date_value = datetime.now().date() - timedelta(days=90)
                
                start_date = st.date_input(
                    "Start Date",
                    value=start_date_value,
                    help="Tanggal mulai untuk rentang data yang akan di-pull"
                )
            with col2:
                # Handle date conversion - could be date object or string
                if current_config and current_config.get('end_date'):
                    end_date_value = current_config['end_date']
                    if isinstance(end_date_value, str):
                        end_date_value = datetime.strptime(end_date_value, '%Y-%m-%d').date()
                    elif isinstance(end_date_value, date):
                        end_date_value = end_date_value
                    elif hasattr(end_date_value, 'date'):
                        end_date_value = end_date_value.date()
                    else:
                        end_date_value = datetime.now().date()
                else:
                    end_date_value = datetime.now().date()
                
                end_date = st.date_input(
                    "End Date",
                    value=end_date_value,
                    help="Tanggal akhir untuk rentang data yang akan di-pull"
                )
            
            # Validate date range
            if end_date < start_date:
                st.error("End date must be after start date!")
            
            # Schedule type
            schedule_type = st.radio(
                "Schedule Type",
                options=['weekly', 'manual'],
                index=0 if not current_config or current_config.get('schedule_type') == 'weekly' else 1,
                horizontal=True,
                help="Weekly: Otomatis setiap minggu | Manual: Hanya dijalankan secara manual"
            )
            
            # Action buttons
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("Save Configuration", use_container_width=True, type="primary"):
                    if end_date < start_date:
                        st.error("Please fix the date range before saving.")
                    else:
                        current_user = get_current_user()
                        username = current_user['username'] if current_user else 'admin'
                        
                        success, message = save_puller_config(
                            project_option,
                            start_date.strftime('%Y-%m-%d'),
                            end_date.strftime('%Y-%m-%d'),
                            schedule_type,
                            username
                        )
                        
                        if success:
                            st.success(f"{message}")
                            log_activity("Data Puller Configuration Saved", '#6366f1')
                            st.rerun()
                        else:
                            st.error(f"{message}")
            
            with col2:
                if st.button("Run Puller Now", use_container_width=True):
                    if end_date < start_date:
                        st.error("Please fix the date range before running.")
                    else:
                        current_user = get_current_user()
                        username = current_user['username'] if current_user else 'admin'
                        
                        # Get or create config
                        config = get_puller_config(project_option)
                        config_id = config['id'] if config else None
                        
                        # Run puller
                        with st.spinner(f"Running {project_option} puller... This may take several minutes."):
                            try:
                                service = get_puller_service()
                                
                                if project_option == 'project1':
                                    success, message, exec_id = service.run_project1_puller(
                                        start_date.strftime('%Y-%m-%d'),
                                        end_date.strftime('%Y-%m-%d'),
                                        config_id,
                                        username
                                    )
                                elif project_option == 'project2':
                                    success, message, exec_id = service.run_project2_puller(
                                        start_date.strftime('%Y-%m-%d'),
                                        end_date.strftime('%Y-%m-%d'),
                                        config_id,
                                        username
                                    )
                                else:  # both
                                    success, message, exec_ids = service.run_both_pullers(
                                        start_date.strftime('%Y-%m-%d'),
                                        end_date.strftime('%Y-%m-%d'),
                                        config_id,
                                        username
                                    )
                                
                                if success:
                                    st.success(f"{message}")
                                    log_activity(f"Data Puller Executed: {project_option}", '#10b981')
                                else:
                                    st.error(f"{message}")
                                    log_activity(f"Data Puller Failed: {project_option}", '#ef4444')
                                    
                            except Exception as e:
                                st.error(f"Error running puller: {str(e)}")
                                log_activity(f"Data Puller Error: {str(e)}", '#ef4444')
            
            with col3:
                if st.button("View History", use_container_width=True):
                    st.session_state.show_puller_history = True
        
        # Show execution history
        if st.session_state.get('show_puller_history', False):
            st.markdown("---")
            st.markdown("### Puller Execution History")
            
            history = get_puller_execution_history(limit=20)
            
            if history:
                history_df = pd.DataFrame(history)
                history_df['started_at'] = pd.to_datetime(history_df['started_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
                history_df['completed_at'] = pd.to_datetime(history_df['completed_at']).dt.strftime('%Y-%m-%d %H:%M:%S') if history_df['completed_at'].notna().any() else None
                
                # Display in a nice format
                for idx, row in history_df.iterrows():
                    status_color = {
                        'completed': '[OK]',
                        'running': '[...]',
                        'failed': '[X]',
                        'cancelled': '[-]'
                    }.get(row['status'], '[-]')
                    
                    with st.expander(f"{status_color} {row['project_name']} - {row['started_at']} ({row['status']})"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Project:** {row['project_name']}")
                            st.write(f"**Date Range:** {row['start_date']} to {row['end_date']}")
                            st.write(f"**Status:** {row['status']}")
                        with col2:
                            st.write(f"**Records Pulled:** {row['records_pulled']:,}")
                            st.write(f"**Execution Time:** {row['execution_time_seconds']}s" if row['execution_time_seconds'] else "**Execution Time:** N/A")
                            st.write(f"**Executed By:** {row['executed_by'] or 'System'}")
                        
                        if row['error_message']:
                            st.error(f"**Error:** {row['error_message']}")
            else:
                st.info("No execution history found.")
            
            if st.button("Close History"):
                st.session_state.show_puller_history = False
                st.rerun()
        
        # Show current configuration
        if current_config:
            st.markdown("---")
            st.markdown("### Current Configuration")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Project", current_config.get('project_name', 'N/A').upper())
            with col2:
                st.metric("Schedule", current_config.get('schedule_type', 'N/A').title())
            with col3:
                last_run = current_config.get('last_run_at')
                if last_run:
                    st.metric("Last Run", pd.to_datetime(last_run).strftime('%Y-%m-%d %H:%M'))
                else:
                    st.metric("Last Run", "Never")
    
    # ========================================================================
    # EMAIL CONFIGURATION FORM
    # ========================================================================
    
    st.markdown("---")
    st.markdown("### Email Configuration")
    st.info("Konfigurasikan kredensial SMTP Anda di sini. Pengaturan ini akan disimpan dalam session ini dan digunakan untuk semua fitur pengiriman email.")
    
    with st.form("email_settings_form"):
        st.markdown("#### Sender Configuration")
        col1, col2 = st.columns(2)
        with col1:
            # Gunakan kunci unik untuk widget di dalam form untuk menghindari konflik
            sender_email = st.text_input("Default Sender Email", value=st.session_state.get('email_sender', ''), key="form_sender_email")
        with col2:
            app_password = st.text_input("App Password", type="password", value=st.session_state.get('email_password', ''), key="form_app_password", help="16-digit App Password from Gmail (get from: https://myaccount.google.com/apppasswords)")
        
        st.markdown("#### Default Recipient Configuration")
        default_recipients = st.text_area("Default Recipients (comma-separated)", value=st.session_state.get('email_recipients', ''), key="form_recipients", height=100)
        
        # Tombol Submit Form
        col1, col2 = st.columns(2)
        with col1:
            save_button = st.form_submit_button("Save Email Settings", use_container_width=True, type="primary")
        with col2:
            reset_button = st.form_submit_button("Reset to Defaults", use_container_width=True)

    # Logika setelah form disubmit
    if save_button:
        if "@" not in sender_email or len(app_password) < 16:
            st.error("Please provide a valid Sender Email and a 16-character App Password.")
        else:
            st.session_state.email_sender = sender_email
            st.session_state.email_password = app_password
            st.session_state.email_recipients = default_recipients
            log_activity("Email Settings Saved", '#6366f1')
            st.success("Email settings saved successfully for this session!")
            st.balloons()

    if reset_button:
        st.session_state.email_sender = ""
        st.session_state.email_password = ""
        st.session_state.email_recipients = ""
        st.session_state.custom_recipients_list = []
        log_activity("Reset Email Settings", '#f59e0b')
        st.info("Settings have been reset. Rerunning page...")
        st.rerun()

    # ========================================================================
    # TEST EMAIL CONFIGURATION
    # ========================================================================
    
    st.markdown("---")
    st.markdown("### Test Email Configuration")
    test_email_address = st.text_input("Test Email Address", placeholder="Enter an email to send a test to", key="settings_test_email_input")
    
    if st.button("Send Test Email", use_container_width=True, key="send_test_email_btn"):
        # Ambil kredensial dari session state
        sender = st.session_state.get('email_sender')
        password = st.session_state.get('email_password')
        
        if not all([sender, password, test_email_address]):
            st.error("Please save your Sender Email & App Password first, and provide a test email address.")
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
                    
                    st.success(f"Test email sent successfully to {test_email_address}!")
                    log_activity(f"Sent Test Email to {test_email_address}", '#10b981')
                except smtplib.SMTPAuthenticationError:
                    st.error("Authentication failed. Please double-check your email and 16-digit App Password.")
                    log_activity("Test Email Failed (Auth Error)", '#ef4444')
                except Exception as e:
                    st.error(f"An error occurred: {e}")
                    log_activity("Test Email Failed (General Error)", '#ef4444')
    
    st.markdown("---")
    
    # ========================================================================
    # SYSTEM INFORMATION
    # ========================================================================
    
    st.markdown("### Application & Data Info")
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
    st.markdown("### Current Session Configuration")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        sender_email = st.session_state.get('email_sender', 'Not Configured')
        st.metric("Sender Email", sender_email if len(sender_email) < 20 else sender_email[:17] + "...")
    with col2:
        password_status = "Configured" if st.session_state.get('email_password') else "Not Set"
        st.metric("App Password Status", password_status)
    with col3:
        recipients = st.session_state.get('email_recipients', '')
        recipient_count = len([r.strip() for r in recipients.split(',') if r.strip()])
        st.metric("Default Recipients", f"{recipient_count} address(es)")

    if recipients:
        with st.expander("View Default Recipients"):
            st.code(recipients.replace(",", "\n"))