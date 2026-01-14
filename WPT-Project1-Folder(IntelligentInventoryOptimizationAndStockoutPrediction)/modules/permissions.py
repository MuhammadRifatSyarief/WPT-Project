"""
Permission Module
=================
Helper functions for role-based access control.
"""

import streamlit as st
from modules.auth import is_admin, is_user, is_authenticated


def can_edit() -> bool:
    """Check if current user can edit data (admin only)."""
    return is_authenticated() and is_admin()


def can_delete() -> bool:
    """Check if current user can delete data (admin only)."""
    return is_authenticated() and is_admin()


def can_view() -> bool:
    """Check if current user can view data (all authenticated users)."""
    return is_authenticated()


def require_edit_permission():
    """Show error and stop execution if user doesn't have edit permission."""
    if not can_edit():
        st.error("❌ Access Denied: Only administrators can modify data.")
        st.info("💡 Contact your administrator if you need edit access.")
        st.stop()


def require_delete_permission():
    """Show error and stop execution if user doesn't have delete permission."""
    if not can_delete():
        st.error("❌ Access Denied: Only administrators can delete data.")
        st.info("💡 Contact your administrator if you need delete access.")
        st.stop()


def show_permission_badge():
    """Display a badge showing current user's permissions."""
    if is_admin():
        st.success("🔴 **Admin Access**: You can view, edit, and delete data.")
    elif is_user():
        st.info("🔵 **User Access**: You can view data only.")
    else:
        st.warning("⚠️ **No Access**: Please login to continue.")


def get_action_buttons():
    """
    Return a dictionary of action button states based on user role.
    
    Returns:
        dict with keys: 'can_edit', 'can_delete', 'can_export'
    """
    return {
        'can_edit': can_edit(),
        'can_delete': can_delete(),
        'can_export': can_view(),  # All users can export
        'can_view': can_view()
    }
