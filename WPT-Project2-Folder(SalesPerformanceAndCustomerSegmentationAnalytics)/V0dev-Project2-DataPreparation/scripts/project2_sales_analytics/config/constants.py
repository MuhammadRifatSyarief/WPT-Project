"""
==========================================================================
PROJECT 2: SALES PERFORMANCE & CUSTOMER SEGMENTATION ANALYTICS
==========================================================================
File: config/constants.py
Purpose: Global constants, configuration, and settings
Author: v0
Created: 2025
==========================================================================

OVERVIEW:
---------
Centralized configuration for Sales Performance & Customer Segmentation
Analytics system. Contains all constants, thresholds, and mappings.

USAGE:
------
    from config.constants import API_CONFIG, RFM_CONFIG, MBA_CONFIG
"""

from datetime import datetime, timedelta

# ==========================================================================
# API CONFIGURATION
# ==========================================================================
API_CONFIG = {
    # Base URLs
    'BASE_URL_ACCOUNT': 'https://account.accurate.id',
    'BASE_URL_ACCURATE': '/accurate',
    
    # Rate Limiting
    'REQUESTS_PER_SECOND': 3,
    'RETRY_MAX_ATTEMPTS': 3,
    'DELAY_BETWEEN_PAGES': 0.5,
    'DELAY_BETWEEN_DETAILS': 0.5,
    
    # Pagination
    'DEFAULT_PAGE_SIZE': 100,
    'MAX_PAGES': 50,
    
    # Timeout
    'REQUEST_TIMEOUT': 30,
}

# ==========================================================================
# DATE CONFIGURATION
# ==========================================================================
DATE_CONFIG = {
    'DATE_FORMAT': '%d/%m/%Y',
    'DATE_FORMAT_ISO': '%Y-%m-%d',
    'TIMEZONE': 'Asia/Jakarta',
    'DEFAULT_PERIOD_DAYS': 365,  # 1 year for RFM analysis
}

def get_default_date_range(days: int = None) -> tuple:
    """
    Get default date range for data pulling.
    
    Args:
        days: Number of days to look back (default: DATE_CONFIG['DEFAULT_PERIOD_DAYS'])
    
    Returns:
        tuple: (start_date, end_date) in DD/MM/YYYY format
    """
    if days is None:
        days = DATE_CONFIG['DEFAULT_PERIOD_DAYS']
    
    end_date = datetime.now().strftime(DATE_CONFIG['DATE_FORMAT'])
    start_date = (datetime.now() - timedelta(days=days)).strftime(DATE_CONFIG['DATE_FORMAT'])
    
    return start_date, end_date

# ==========================================================================
# API ENDPOINTS - Sales Performance & Customer Segmentation
# ==========================================================================
API_ENDPOINTS = {
    # Master Data
    'items': {
        'list': '/api/item/list.do',
        'detail': '/api/item/detail.do',
        'fields': 'id,no,name,itemType,itemCategoryName,itemCategoryId,avgCost,unitPrice,unit1Name,minimumStock,isInventory,upcNo,description'
    },
    'customers': {
        'list': '/api/customer/list.do',
        'detail': '/api/customer/detail.do',
        'fields': 'id,name,customerNo,categoryName,email,mobilePhone,workPhone,billStreet,billCity'
    },
    'customer_categories': {
        'list': '/api/customer-category/list.do',
        'fields': 'id,name,description'
    },
    
    # Sales Data
    'sales_invoices': {
        'list': '/api/sales-invoice/list.do',
        'detail': '/api/sales-invoice/detail.do',
        'fields': 'id,number,transDate,customerId,customerName,totalAmount,description,branchId,branchName,salesmanName'
    },
    'sales_orders': {
        'list': '/api/sales-order/list.do',
        'detail': '/api/sales-order/detail.do',
        'fields': 'id,number,transDate,customerId,customerName,totalAmount,description,branchId,branchName'
    },
    'sales_receipts': {
        'list': '/api/sales-receipt/list.do',
        'detail': '/api/sales-receipt/detail.do',
        'fields': 'id,number,transDate,customerName,totalAmount,description'
    },
    
    # Salesperson & Targets
    'employees': {
        'list': '/api/employee/list.do',
        'fields': 'id,name,email,mobilePhone,departmentName'
    },
}

# ==========================================================================
# RFM ANALYSIS CONFIGURATION
# ==========================================================================
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

# ==========================================================================
# MARKET BASKET ANALYSIS CONFIGURATION
# ==========================================================================
MBA_CONFIG = {
    # Minimum support threshold
    'MIN_SUPPORT': 0.01,  # 1% of transactions
    
    # Minimum confidence threshold
    'MIN_CONFIDENCE': 0.3,  # 30%
    
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

# ==========================================================================
# CUSTOMER VALUE METRICS
# ==========================================================================
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

# ==========================================================================
# CURRENCY CONFIGURATION (Indonesian Rupiah)
# ==========================================================================
CURRENCY_CONFIG = {
    'USD_TO_IDR_RATE': 16615.20,
    'CURRENCY_SYMBOL': 'Rp',
    'THOUSAND_SEPARATOR': '.',
    'DECIMAL_SEPARATOR': ',',
    'MIN_VALID_IDR_PRICE': 1000,  # Prices below this are likely USD
}

# ==========================================================================
# FILE PATHS
# ==========================================================================
FILE_PATHS = {
    'CHECKPOINT_FILE': 'sales_analytics_checkpoint.pkl',
    'OUTPUT_EXCEL': 'sales_performance_analytics.xlsx',
    'OUTPUT_CSV_FOLDER': 'output_csv',
    'MASTER_FEATURES_FILE': 'sales_master_features.csv',
}

# ==========================================================================
# EXPORT CONFIGURATION
# ==========================================================================
EXPORT_CONFIG = {
    # Excel sheet names
    'SHEETS': {
        'rfm_analysis': '1_RFM_Analysis',
        'customer_segments': '2_Customer_Segments',
        'market_basket': '3_Market_Basket',
        'product_associations': '4_Product_Associations',
        'sales_details': '5_Sales_Details',
        'sales_by_customer': '6_Sales_By_Customer',
        'sales_by_product': '7_Sales_By_Product',
        'customer_master': '8_Customer_Master',
        'item_master': '9_Item_Master',
        'summary_stats': '10_Summary_Stats',
    },
    
    # Columns to include in exports
    'RFM_EXPORT_COLUMNS': [
        'customer_id', 'customer_name', 'customer_no', 'category',
        'recency_days', 'frequency', 'monetary',
        'r_score', 'f_score', 'm_score', 'rfm_score',
        'segment', 'recommended_action',
        'last_purchase_date', 'first_purchase_date',
        'avg_order_value', 'total_orders', 'total_items_purchased'
    ],
}

# ==========================================================================
# LOGGING CONFIGURATION
# ==========================================================================
LOG_CONFIG = {
    'SHOW_PROGRESS': True,
    'SHOW_WARNINGS': True,
    'SHOW_ERRORS': True,
    'LOG_FILE': 'sales_analytics.log',
}

# ==========================================================================
# VISUALIZATION CONFIGURATION
# ==========================================================================
VIZ_CONFIG = {
    # Color palette
    'PRIMARY_COLOR': '#1976D2',
    'SECONDARY_COLOR': '#424242',
    'SUCCESS_COLOR': '#4CAF50',
    'WARNING_COLOR': '#FF9800',
    'ERROR_COLOR': '#F44336',
    
    # Chart defaults
    'CHART_HEIGHT': 400,
    'CHART_WIDTH': 800,
    
    # Font sizes
    'TITLE_FONT_SIZE': 16,
    'LABEL_FONT_SIZE': 12,
    'TICK_FONT_SIZE': 10,
}
