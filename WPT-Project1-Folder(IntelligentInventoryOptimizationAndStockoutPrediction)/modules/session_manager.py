# File: modules/session_manager.py
"""
Session State Management
=========================
Manages the initialization and access of Streamlit's session state
in a safe and centralized manner. This module has NO external module dependencies.
"""

import streamlit as st

# Impor nilai default dari file konfigurasi pusat
# Pastikan file ini ada: config/constants.py
from config.constants import DEFAULT_SESSION_STATE

def initialize_session_state():
    """
    Initializes all required session state keys using a loop,
    preventing state from being reset on page navigation.
    """
    for key, default_value in DEFAULT_SESSION_STATE.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

def get_session_value(key: str, default=None):
    """Safely retrieves a value from the session state."""
    return st.session_state.get(key, default)

def set_session_value(key: str, value):
    """Sets a value in the session state."""
    st.session_state[key] = value

def reset_session_state_to_defaults():
    """
    Resets all session state keys back to their default values.
    The logging of this action should be handled by the caller, not this function.
    """
    for key, default_value in DEFAULT_SESSION_STATE.items():
        st.session_state[key] = default_value
    
    # !!! PEMANGGILAN log_activity() DIHAPUS DARI SINI UNTUK MEMUTUSKAN LINGKARAN IMPOR !!!
    # st.success("Session has been reset to defaults.")

def toggle_visibility(key: str):
    """Toggles a boolean visibility state (True/False)."""
    st.session_state[key] = not st.session_state.get(key, False)

def get_email_config() -> dict:
    """Retrieves all email-related configurations from the session state."""
    return {
        'email_sender': st.session_state.get('email_sender', ''),
        'email_password': st.session_state.get('email_password', ''),
        'email_recipients': st.session_state.get('email_recipients', ''),
        'custom_recipients_list': st.session_state.get('custom_recipients_list', [])
    }

def get_activities_log() -> list:
    """Retrieves the activity log from the session state."""
    return st.session_state.get('activities', [])