"""
Pages Package Initialization

Import page modules untuk easier access.

Setiap page harus memiliki function render_page() yang dipanggil dari main.py
"""

# Import all page modules
from modules.pages import (
    dashboard,
    forecasting,
    health,
    alerts,
    reorder,
    slow_moving,
    rfm,
    mba,
    settings,
    login
)

__all__ = [
    'dashboard',
    'forecasting',
    'health',
    'alerts',
    'reorder',
    'slow_moving',
    'rfm',
    'mba',
    'settings',
    'login'
]
