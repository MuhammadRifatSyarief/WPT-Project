# File: modules/email_utils.py (Versi Final dengan Quick Alert)

import streamlit as st
import pandas as pd
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from modules.activity_logger import log_activity

# Fungsi `send_email` tetap tidak berubah
def send_email(sender_email, app_password, recipients, subject, body, attachment_df=None, attachment_filename="report.csv"):
    """Mengirim email menggunakan SMTP Gmail dengan lampiran CSV opsional."""
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = ", ".join(recipients)
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))

        if attachment_df is not None and not attachment_df.empty:
            part = MIMEBase('application', 'octet-stream')
            csv_data = attachment_df.to_csv(index=False).encode('utf-8')
            part.set_payload(csv_data)
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="{attachment_filename}"')
            msg.attach(part)
        
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, app_password)
            server.send_message(msg)
        
        return True, "Email sent successfully!"
    
    except smtplib.SMTPAuthenticationError:
        return False, "Authentication failed. Check your email/app password in Settings."
    except Exception as e:
        return False, f"An error occurred: {str(e)}"

# ============================================================================
# --- PERUBAHAN UTAMA DI SINI ---
# Fungsi `render_email_form` sekarang menjadi lebih umum
# ============================================================================
def render_email_form(df_report: pd.DataFrame, report_type: str, default_filename: str):
    """
    Merender form email yang canggih dengan pilihan grup penerima kustom.
    """
    st.markdown("---")
    st.markdown(f"#### 📧 Email {report_type.replace('_', ' ').title()} Report")
    
    custom_recipients = st.session_state.get('custom_recipients_list', [])
    selected_from_group = []

    if custom_recipients:
        selected_from_group = st.multiselect(
            "Select from Custom Groups",
            options=custom_recipients,
            help="Pilih penerima dari grup yang telah Anda simpan di halaman Settings."
        )

    default_set = {r.strip() for r in st.session_state.get('email_recipients', '').split(',') if r.strip()}
    selected_set = set(selected_from_group)
    combined_set = default_set.union(selected_set)
    initial_recipients_str = ", ".join(sorted(list(combined_set)))

    with st.form(key=f"email_form_{report_type}"):
        recipients_str = st.text_area(
            "Recipients (comma-separated)", 
            value=initial_recipients_str,
            placeholder="contoh@perusahaan.com, manajer@perusahaan.com"
        )
        
        subject = st.text_input(
            "Subject", 
            value=f"Inventory Report: {report_type.replace('_', ' ').title()} - {datetime.now().strftime('%Y-%m-%d')}"
        )
        
        body_template = f"""<p>Dear Team,</p><p>Attached is the <b>{report_type.replace('_', ' ').title()} Report</b> generated on {datetime.now().strftime('%B %d, %Y at %H:%M')}.</p><p>This report contains {len(df_report)} items.</p><p>Best regards,<br>Inventory Intelligence System</p>"""
        body = st.text_area("Body (HTML is supported)", value=body_template, height=200)
        
        submitted = st.form_submit_button("Send Email")

        if submitted:
            sender = st.session_state.get('email_sender')
            password = st.session_state.get('email_password')
            
            if not sender or not password:
                st.error("❌ Sender email or app password not configured. Please set them in the 'Settings' page.")
                return

            recipient_list = [r.strip() for r in recipients_str.split(',') if r.strip()]
            if not recipient_list:
                st.error("❌ Please provide at least one recipient.")
                return

            with st.spinner("Sending email..."):
                success, message = send_email(
                    sender, 
                    password, 
                    recipient_list, 
                    subject, 
                    body, 
                    attachment_df=df_report, 
                    attachment_filename=f"{default_filename}_{datetime.now().strftime('%Y%m%d')}.csv"
                )
            
            if success:
                st.success(f"✅ {message}")
                log_activity(f"📧 Sent {report_type} report to {len(recipient_list)} recipients", '#10b981')
            else:
                st.error(f"❌ {message}")
                log_activity(f"❌ Failed to send {report_type} report", '#ef4444')

# ============================================================================
# --- FUNGSI BARU UNTUK QUICK ALERT ---
# Fungsi ini tidak merender form, tetapi langsung mengirim email.
# ============================================================================
def send_quick_alert_email(df_report: pd.DataFrame, report_type: str = "Quick Alert", default_filename: str = "critical_stock_alert"):
    """
    Langsung mengirim email alert ke penerima default tanpa menampilkan form input.
    """
    sender = st.session_state.get('email_sender')
    password = st.session_state.get('email_password')
    recipients_str = st.session_state.get('email_recipients', '')

    # Validasi
    if not sender or not password:
        st.error("❌ Email settings are not configured. Please go to the 'Settings' page.")
        return
        
    recipient_list = [r.strip() for r in recipients_str.split(',') if r.strip()]
    if not recipient_list:
        st.error("❌ Default Recipients are not configured. Please add them in the 'Settings' page.")
        return

    # Siapkan konten email
    subject = f"🔴 IMMEDIATE ACTION: Critical Stock Alert - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    body = f"""
    <p><b>URGENT: Critical Stock Alert</b></p>
    <p>This is an automated alert from the Inventory Intelligence System.</p>
    <p>The attached report contains a list of <b>{len(df_report)} products</b> that are at critical risk of stocking out (less than 30 days of stock).</p>
    <p>Please review and take immediate action.</p>
    <p>Best regards,<br>Inventory Intelligence System</p>
    """
    
    with st.spinner(f"Sending quick alert to {len(recipient_list)} recipient(s)..."):
        success, message = send_email(
            sender, 
            password, 
            recipient_list, 
            subject, 
            body, 
            attachment_df=df_report, 
            attachment_filename=f"{default_filename}_{datetime.now().strftime('%Y%m%d')}.csv"
        )
    
    if success:
        st.success(f"✅ Quick alert sent successfully to default recipients!")
        log_activity(f"📧 Sent Quick Alert to {len(recipient_list)} recipients", '#ef4444') # Warna merah untuk alert
    else:
        st.error(f"❌ Failed to send quick alert: {message}")
        log_activity("❌ Quick Alert send failed", '#ef4444')