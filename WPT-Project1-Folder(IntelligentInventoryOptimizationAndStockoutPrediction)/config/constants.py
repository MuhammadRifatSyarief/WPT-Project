"""
Global Constants and Configuration
=====================================

Modul ini berisi semua konstanta global, default values, dan konfigurasi
yang digunakan di seluruh aplikasi.

"""

# ============================================================================
# APPLICATION METADATA
# ============================================================================

APP_TITLE = "Inventory Intelligence Hub - PT Wahana Piranti Teknologi"
APP_ICON = "📦"
APP_VERSION = "1.0 PRODUCTION"
APP_COMPANY = "PT Wahana Piranti Teknologi"
AUTHOR = "Muhammad Rif'at Syarief"
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
    "👥 RFM Analysis",
    "🛒 Market Basket Analysis",
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
    # Authentication
    "authenticated": False,
    "username": None,
    "role": None,
    "user_id": None,
    
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

# ============================================================================
# RFM ANALYSIS CONFIGURATION
# ============================================================================
RFM_CONFIG = {
    # Scoring ranges (1-5, where 5 is best for F/M, worst for R)
    'SCORE_RANGE': (1, 5),
    
    # RFM Segment Definitions
    # Format: (R_range, F_range, M_range) -> Segment Name
    'SEGMENTS': {
        'Champions': {'R': (4, 5), 'F': (4, 5), 'M': (4, 5)},
        'Loyal Customers': {'R': (3, 5), 'F': (3, 5), 'M': (3, 5)},
        'Potential Loyalist': {'R': (4, 5), 'F': (2, 4), 'M': (2, 4)},
        'Recent Customers': {'R': (4, 5), 'F': (1, 2), 'M': (1, 2)},
        'Promising': {'R': (3, 4), 'F': (1, 2), 'M': (1, 2)},
        'Need Attention': {'R': (2, 3), 'F': (2, 3), 'M': (2, 3)},
        'About To Sleep': {'R': (2, 3), 'F': (1, 2), 'M': (1, 2)},
        'At Risk': {'R': (1, 2), 'F': (3, 5), 'M': (3, 5)},
        'Cannot Lose Them': {'R': (1, 2), 'F': (4, 5), 'M': (4, 5)},
        'Hibernating': {'R': (1, 2), 'F': (1, 2), 'M': (1, 2)},
        'Lost': {'R': (1, 1), 'F': (1, 2), 'M': (1, 2)},
    },
    
    # Segment Colors for visualization
    'SEGMENT_COLORS': {
        'Champions': '#2E7D32',          # Green
        'Loyal Customers': '#4CAF50',    # Light Green
        'Potential Loyalist': '#8BC34A', # Lime
        'Recent Customers': '#03A9F4',   # Light Blue
        'Promising': '#00BCD4',          # Cyan
        'Need Attention': '#FF9800',     # Orange
        'About To Sleep': '#FFC107',     # Amber
        'At Risk': '#FF5722',            # Deep Orange
        'Cannot Lose Them': '#F44336',   # Red
        'Hibernating': '#9E9E9E',        # Grey
        'Lost': '#607D8B',               # Blue Grey
    },
    
    # Priority weights for segment scoring
    'SEGMENT_PRIORITY': {
        'Champions': 10,
        'Loyal Customers': 9,
        'Cannot Lose Them': 8,
        'At Risk': 7,
        'Potential Loyalist': 6,
        'Need Attention': 5,
        'Recent Customers': 4,
        'Promising': 3,
        'About To Sleep': 2,
        'Hibernating': 1,
        'Lost': 0,
    },
    
    # Recommended Actions per Segment
    'SEGMENT_ACTIONS': {
        'Champions': 'Reward them. Can be early adopters for new products.',
        'Loyal Customers': 'Upsell higher value products. Engage them.',
        'Potential Loyalist': 'Offer membership/loyalty program. Recommend other products.',
        'Recent Customers': 'Start building relationship. Provide onboarding support.',
        'Promising': 'Create brand awareness. Offer free trials.',
        'Need Attention': 'Make limited time offers. Recommend based on purchase history.',
        'About To Sleep': 'Share valuable resources. Recommend popular products.',
        'At Risk': 'Send personalized emails. Offer renewals and helpful products.',
        'Cannot Lose Them': 'Win them back via renewals/special products. Talk to them.',
        'Hibernating': 'Offer other relevant products. Special discounts.',
        'Lost': 'Revive interest with reach out campaign. Ignore otherwise.',
    },
}

# ============================================================================
# MARKET BASKET ANALYSIS CONFIGURATION
# ============================================================================
MBA_CONFIG = {
    # Minimum support threshold
    'MIN_SUPPORT': 0.005,  # 0.5% of transactions
    
    # Minimum confidence threshold
    'MIN_CONFIDENCE': 0.20,  # 20%
    
    # Minimum lift threshold
    'MIN_LIFT': 1.0,  # Must be > 1 for positive association
    
    # Maximum itemset size
    'MAX_ITEMSET_SIZE': 3,
    
    # Top N rules to display
    'TOP_N_RULES': 50,
    
    # Association strength categories
    'LIFT_CATEGORIES': {
        'Strong': (3.0, float('inf')),
        'Moderate': (1.5, 3.0),
        'Weak': (1.0, 1.5),
    },
}

# ============================================================================
# CUSTOMER VALUE METRICS
# ============================================================================
CUSTOMER_VALUE_CONFIG = {
    # CLV (Customer Lifetime Value) calculation period in months
    'CLV_PERIOD_MONTHS': 12,
    
    # Customer activity thresholds (days)
    'ACTIVE_THRESHOLD_DAYS': 90,
    'AT_RISK_THRESHOLD_DAYS': 180,
    'CHURNED_THRESHOLD_DAYS': 365,
    
    # Revenue tiers
    'REVENUE_TIERS': {
        'Platinum': 0.90,  # Top 10%
        'Gold': 0.70,      # Top 30%
        'Silver': 0.40,    # Top 60%
        'Bronze': 0.0,     # Rest
    },
}
