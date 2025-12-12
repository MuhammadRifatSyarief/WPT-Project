"""
Global Constants and Configuration
=====================================

Modul ini berisi semua konstanta global, default values, dan konfigurasi
yang digunakan di seluruh aplikasi.

Author: Data Science Team
Date: 2025-11-18
Version: 1.0
"""

# ============================================================================
# APPLICATION METADATA
# ============================================================================

APP_TITLE = "Inventory Intelligence Hub - PT Wahana Piranti Teknologi"
APP_ICON = "📦"
APP_VERSION = "1.0 PRODUCTION"
APP_COMPANY = "PT Wahana Piranti Teknologi"
AUTHOR = "Data Science Team"
LAST_MODIFIED = "2025-11-18"

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

PAGES = [
    "🏠 Dashboard Overview",
    "📈 Demand Forecasting",
    "📊 Inventory Health",
    "⚠️ Stockout Alerts",
    "🔄 Reorder Optimization",
    "📋 Slow-Moving Analysis",
    "⚙️ Settings"
]

# ============================================================================
# COLOR SCHEME & STYLING
# ============================================================================

COLORS = {
    'primary': '#6366f1',           # Indigo
    'success': '#10b981',           # Emerald
    'warning': '#f59e0b',           # Amber
    'danger': '#ef4444',            # Red
    'bg_dark': '#0f172a',           # Slate very dark
    'bg_card': '#1e293b',           # Slate dark
    'text_primary': '#f8fafc',      # Slate 50
    'text_secondary': '#94a3b8',    # Slate 400
    'border': '#334155',            # Slate 700
}

# ============================================================================
# PERFORMANCE & CACHING
# ============================================================================

CACHE_TTL = 3600  # Cache Time-To-Live in seconds (1 hour)
DATA_REFRESH_INTERVAL = 120  # Data refresh interval in seconds (2 minutes)
MAX_ROWS_DISPLAY = 100  # Maximum rows to display per page

# ============================================================================
# DEFAULT EMAIL CONFIGURATION
# ============================================================================

DEFAULT_EMAIL_SENDER = "muhammadrifat.23053@mhs.unesa.ac.id"
DEFAULT_EMAIL_RECIPIENTS = [
    "purchasing@company.com",
    "manager@company.com",
    "inventory@company.com",
    "support@company.com"
]

# SMTP Configuration for Gmail
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# ============================================================================
# DEMAND FORECASTING SETTINGS
# ============================================================================

DEFAULT_FORECAST_DAYS = 30
FORECAST_MIN_DAYS = 7
FORECAST_MAX_DAYS = 90

# ============================================================================
# INVENTORY HEALTH METRICS
# ============================================================================

# Service Level Targets
SERVICE_LEVEL_TARGET = 95  # Target service level percentage
SERVICE_LEVEL_EXCELLENT = 95
SERVICE_LEVEL_GOOD = 90
SERVICE_LEVEL_FAIR = 85

# Inventory Turnover Benchmarks (for IT Products)
TURNOVER_EXCELLENT = 12  # Annual turnover rate
TURNOVER_IDEAL = 8
TURNOVER_ACCEPTABLE = 4

# Health Score Thresholds
HEALTH_EXCELLENT = 80
HEALTH_GOOD = 60
HEALTH_FAIR = 40

# ============================================================================
# STOCKOUT ALERT THRESHOLDS
# ============================================================================

ALERT_CRITICAL_DAYS = 7    # Critical: < 7 days
ALERT_HIGH_DAYS = 14       # High: 7-14 days
ALERT_MEDIUM_DAYS = 30     # Medium: 15-30 days

# Alert Risk Levels
RISK_LEVELS = {
    'Critical': 'Critical',
    'High': 'High',
    'Medium': 'Medium',
    'Low': 'Low'
}

# ============================================================================
# REORDER OPTIMIZATION SETTINGS
# ============================================================================

# Service Level Factor (Z-score) for Safety Stock calculation
SERVICE_LEVEL_FACTOR = 1.65  # For 95% service level

# Default ordering and holding costs (if not provided in data)
DEFAULT_ORDERING_COST = 50.0   # Per order
DEFAULT_HOLDING_COST = 0.25    # Per unit per year (25% of unit cost)

# ============================================================================
# SLOW-MOVING PRODUCTS CRITERIA
# ============================================================================

SLOW_MOVING_TURNOVER_THRESHOLD = 1.0   # Turnover ratio < 1.0x per 90 days
SLOW_MOVING_STOCK_AGE_DAYS = 60        # Stock age > 60 days
SLOW_MOVING_DAILY_DEMAND_LOW = 2.0     # Low daily demand threshold

# ============================================================================
# DATA FILES & SOURCES
# ============================================================================

import os
from pathlib import Path

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# Possible locations for data file
POSSIBLE_DATA_PATHS = [
    PROJECT_ROOT / "data" / "master_features_final.csv",  # data/ folder in project root
    PROJECT_ROOT / "master_features_final.csv",            # project root
    Path("D:/ATEST/data/master_features_final.csv"),       # absolute path (Windows)
    Path("./data/master_features_final.csv"),              # relative to working directory
]

# Find the first existing path
MASTER_DATA_FILE = None
for path in POSSIBLE_DATA_PATHS:
    if path.exists():
        MASTER_DATA_FILE = str(path)
        break

# If not found, default to the most likely location and let the module handle the error
if MASTER_DATA_FILE is None:
    MASTER_DATA_FILE = str(PROJECT_ROOT / "data" / "master_features_final.csv")

DATA_DESCRIPTION = "Real data from master_features_final.csv (2,136 products)"

# ============================================================================
# ACTIVITY LOGGING
# ============================================================================

LOG_MAX_ENTRIES = 100  # Maximum entries to keep in activity log
ACTIVITY_LOG_FORMAT = "%H:%M:%S"  # Time format for activity log

# ============================================================================
# SESSION STATE DEFAULTS
# ============================================================================

DEFAULT_SESSION_STATE = {
    # Konfigurasi Email
    "email_sender": "",
    "email_password": "",
    "email_recipients": "muhammadrifat.23053@mhs.unesa.ac.id,202110098@smkyadika11.sch.id",
    "custom_recipients_list": [],  # <-- HARUS list kosong

    # Visibilitas Form Email
    "show_email_form": False,
    "show_email_forecast": False,
    "show_email_health": False,
    "show_email_reorder": False,
    "show_email_slow": False,
    "show_email_settings_test": False,
    
    # Visibilitas UI Lainnya
    "show_bulk_order": False,
    "show_export_options": False,
    "show_all_alerts": False,
    "show_email_detail": False,
    
    # State Lainnya
    "selected_products": [],
    "activities": [],
}

# ============================================================================
# ABC CLASSIFICATION
# ============================================================================

ABC_CLASSES = ["All", "A", "B", "C"]
ABC_CLASS_DESCRIPTIONS = {
    'A': 'High-value, high-frequency (70% of value, 20% of items)',
    'B': 'Medium-value (20% of value, 30% of items)',
    'C': 'Low-value, low-frequency (10% of value, 50% of items)'
}

# ============================================================================
# PRODUCT SEGMENTATION
# ============================================================================

PRODUCT_SEGMENTS = ['Fast_Movers', 'Slow_Movers', 'Core_Products']

# ============================================================================
# POPOVER DESCRIPTIONS
# ============================================================================

POPOVERS = {
    'service_level': {
        'title': 'Service Level',
        'description': 'Persentase pesanan yang dapat dipenuhi dari stok tersedia.',
        'formula': 'Service Level = (Pesanan Terpenuhi / Total Pesanan) × 100%',
        'example': '- Total pesanan: 1,000 orders\n- Pesanan terpenuhi: 942 orders\n- Service Level: 94.2%',
        'benchmarks': '- >95%: Excellent\n- 90-95%: Good\n- 85-90%: Fair\n- <85%: Poor'
    },
    'inventory_turnover': {
        'title': 'Inventory Turnover Ratio',
        'description': 'Berapa kali inventory terjual dan diganti dalam setahun.',
        'formula': 'Turnover 90d = (Sum Total Sales 90d) / (Sum Total Stock Value)',
        'benchmarks': '- 8-12x: Excellent\n- 6-8x: Ideal\n- 4-6x: Acceptable\n- <4x: Slow'
    },
    'quick_stats': {
        'title': 'Quick Stats',
        'description': 'Quick Stats memberikan snapshot real-time dari kondisi inventory Anda.',
        'items': '- Active Alerts: Produk yang memerlukan perhatian segera\n- Products Monitored: Total produk dalam sistem\n- Last Updated: Waktu sinkronisasi data terakhir'
    }
}
