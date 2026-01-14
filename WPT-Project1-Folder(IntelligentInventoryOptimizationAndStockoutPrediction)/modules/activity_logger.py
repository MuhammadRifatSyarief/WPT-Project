# File: modules/activity_logger.py
"""
Activity Logging Module
========================
Handles real-time activity logging for tracking user actions and system events.
"""

import streamlit as st
from datetime import datetime

# Impor session manager untuk mengakses state dengan aman
from modules.session_manager import get_session_value, set_session_value

# Konstanta
ACTIVITY_LOG_FORMAT = '%H:%M:%S'
LOG_MAX_ENTRIES = 100

def log_activity(action: str, color: str = '#6366f1'):
    """
    Adds a new entry to the activity log in the session state.
    The log is stored in reverse chronological order (newest first).
    """
    activities = get_session_value('activities', [])
    new_activity = {
        'time': datetime.now().strftime(ACTIVITY_LOG_FORMAT),
        'action': action,
        'color': color
    }
    activities.insert(0, new_activity)
    set_session_value('activities', activities[:LOG_MAX_ENTRIES])

def get_activity_log() -> list:
    """Retrieves all activity log entries."""
    return get_session_value('activities', [])

def clear_activity_log():
    """Clears all activity log entries."""
    set_session_value('activities', [])

def _render_single_activity(activity: dict):
    """Helper function to render a single activity item."""
    st.markdown(f"""
    <div style="background: rgba(45, 55, 72, 0.5); padding: 0.6rem; border-radius: 8px; 
                margin-bottom: 0.5rem; border-left: 4px solid {activity['color']}; font-size: 0.85rem;">
        <div style="font-size: 0.7rem; color: #a0aec0;">{activity.get('time', 'N/A')}</div>
        <div style="color: #e2e8f0; margin-top: 0.2rem;">{activity.get('action', 'Unknown')}</div>
    </div>
    """, unsafe_allow_html=True)

def render_activity_log_sidebar(max_initial_entries: int = 5):
    """
    PENDEKATAN BARU: Renders the activity log with strict limit control.
    
    Args:
        max_initial_entries: Number of recent activities to show (default: 5)
    """
    st.markdown("### 📋 Activity Log")
    
    activities = get_activity_log()
    total_activities = len(activities)
    
    # Empty state
    if total_activities == 0:
        st.info("No recent activity.")
        return
    
    # Enforce strict slicing
    recent_activities = activities[:max_initial_entries] if total_activities > max_initial_entries else activities
    older_activities = activities[max_initial_entries:] if total_activities > max_initial_entries else []
    
    # Container untuk recent activities
    recent_container = st.container()
    with recent_container:
        # Render ONLY recent activities
        for idx, activity in enumerate(recent_activities):
            _render_single_activity(activity)
            # Pastikan tidak ada yang lolos
            if idx >= max_initial_entries - 1:
                break
    
    # Expander untuk older activities (jika ada)
    if len(older_activities) > 0:
        with st.expander(f"📜 View {len(older_activities)} older activities"):
            # CSS for scroll container
            st.markdown("""
            <style>
            .activity-scroll {
                max-height: 250px;
                overflow-y: auto;
                padding-right: 5px;
                margin-top: 10px;
            }
            /* Custom Scrollbar */
            .activity-scroll::-webkit-scrollbar {
                width: 4px;
            }
            .activity-scroll::-webkit-scrollbar-track {
                background: rgba(255, 255, 255, 0.02);
            }
            .activity-scroll::-webkit-scrollbar-thumb {
                background: rgba(255, 255, 255, 0.15);
                border-radius: 4px;
            }
            .activity-scroll::-webkit-scrollbar-thumb:hover {
                background: rgba(255, 255, 255, 0.25);
            }
            </style>
            """, unsafe_allow_html=True)

            # Build HTML content
            # Note: We must avoid indentation in the HTML string to prevent Markdown from interpreting it as code blocks
            html_content = '<div class="activity-scroll">'
            for activity in older_activities:
                html_content += f"""<div style="background: rgba(45, 55, 72, 0.5); padding: 0.6rem; border-radius: 8px; margin-bottom: 0.5rem; border-left: 4px solid {activity['color']}; font-size: 0.85rem;"><div style="font-size: 0.7rem; color: #a0aec0;">{activity.get('time', 'N/A')}</div><div style="color: #e2e8f0; margin-top: 0.2rem;">{activity.get('action', 'Unknown')}</div></div>"""
            html_content += '</div>'
            
            st.markdown(html_content, unsafe_allow_html=True)
                    
def export_activity_log() -> str:
    """Exports the activity log as a formatted string."""
    activities = get_activity_log()
    if not activities:
        return "No activities to export."
    
    lines = ["=== Activity Log Export ==="]
    for activity in reversed(activities):
        lines.append(f"[{activity.get('time', 'N/A')}] {activity.get('action', 'Unknown')}")
    
    return "\n".join(lines)