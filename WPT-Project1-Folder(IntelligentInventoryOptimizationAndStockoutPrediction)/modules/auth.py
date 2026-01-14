"""
Authentication Module
=====================
Handles user authentication, authorization, and session management.
"""

import streamlit as st
from typing import Optional, Dict, Tuple
from modules.database import authenticate_user, create_user, get_user_by_username
import logging

logger = logging.getLogger(__name__)


def is_authenticated() -> bool:
    """Check if user is authenticated."""
    return st.session_state.get('authenticated', False)


def get_current_user() -> Optional[Dict]:
    """Get current authenticated user information."""
    if is_authenticated():
        return {
            'username': st.session_state.get('username'),
            'role': st.session_state.get('role'),
            'user_id': st.session_state.get('user_id')
        }
    return None


def is_admin() -> bool:
    """Check if current user is an admin."""
    return is_authenticated() and st.session_state.get('role') == 'admin'


def is_user() -> bool:
    """Check if current user is a regular user."""
    return is_authenticated() and st.session_state.get('role') == 'user'


def login(username: str, password: str) -> Tuple[bool, str]:
    """
    Authenticate user and set session state.
    
    Args:
        username: Username
        password: Password
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    user = authenticate_user(username, password)
    
    if user:
        st.session_state['authenticated'] = True
        st.session_state['username'] = user['username']
        st.session_state['role'] = user['role']
        st.session_state['user_id'] = user['id']
        logger.info(f"User logged in: {username} ({user['role']})")
        return True, "Login successful"
    else:
        return False, "Invalid username or password"


def logout():
    """Logout current user and clear session state."""
    username = st.session_state.get('username', 'Unknown')
    role = st.session_state.get('role', 'Unknown')
    
    st.session_state['authenticated'] = False
    st.session_state['username'] = None
    st.session_state['role'] = None
    st.session_state['user_id'] = None
    
    logger.info(f"User logged out: {username} ({role})")


def signup(username: str, password: str, role: str) -> Tuple[bool, str]:
    """
    Register a new user.
    
    Args:
        username: Username
        password: Password
        role: User role ('admin' or 'user')
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    # Validate username format (admin/user followed by number)
    if not (username.startswith('admin') or username.startswith('user')):
        return False, "Username must start with 'admin' or 'user'"
    
    # Validate password format
    if not password.endswith('!wahana25'):
        return False, "Password must end with '!wahana25'"
    
    # Extract number from username
    try:
        if username.startswith('admin'):
            num = username.replace('admin', '')
        else:
            num = username.replace('user', '')
        
        if not num.isdigit():
            return False, "Username must be in format: admin1, admin2, user1, user2, etc."
        
        # Validate password matches username pattern
        expected_password = f"{username}!wahana25"
        if password != expected_password:
            return False, f"Password must be: {expected_password}"
        
    except Exception as e:
        return False, f"Invalid username format: {str(e)}"
    
    # Create user in database
    success, message = create_user(username, password, role)
    
    if success:
        logger.info(f"New user registered: {username} ({role})")
    
    return success, message


def require_auth():
    """Decorator-like function to require authentication."""
    if not is_authenticated():
        st.error("Please login to access this page.")
        st.stop()


def require_admin():
    """Decorator-like function to require admin role."""
    require_auth()
    if not is_admin():
        st.error("Access denied. Admin privileges required.")
        st.stop()
