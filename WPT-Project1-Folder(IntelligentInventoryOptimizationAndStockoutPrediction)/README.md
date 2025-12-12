# Inventory Intelligence Hub - Modular Architecture

**Intelligent Inventory Optimization & Stockout Prediction System**

Production Application v4.3 | Modular Structure

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Project Structure](#project-structure)
3. [Installation & Setup](#installation--setup)
4. [Module Documentation](#module-documentation)
5. [Adding New Pages](#adding-new-pages)
6. [Extending Functionality](#extending-functionality)
7. [Troubleshooting](#troubleshooting)

---

## Overview

**Inventory Intelligence Hub** adalah sistem inventory management berbasis web yang membantu:

- Monitor kesehatan inventory secara real-time
- Prediksi demand dan stockout dengan accuracy tinggi
- Optimasi reorder points berdasarkan data analytics
- Identifikasi slow-moving products untuk action strategis
- Alert system untuk immediate action

### Key Features

✅ Real-time inventory monitoring dengan 2,136+ products  
✅ Demand forecasting dengan historical analysis  
✅ Dynamic filtering, searching, dan sorting  
✅ Email export untuk berbagai reports  
✅ Activity logging untuk audit trail  
✅ Responsive UI dengan dark mode theme  
✅ Modular architecture untuk easy maintenance  

---

## Project Structure

\`\`\`
project/
├── main.py                          # Entry point - MINIMAL CODE
├── config/
│   └── constants.py                 # Global constants & defaults
│
├── modules/
│   ├── __init__.py                  # Package init
│   ├── session_manager.py           # Session state management
│   ├── data_loader.py               # Data loading & caching
│   ├── email_utils.py               # Email functionality
│   ├── activity_logger.py           # Activity logging
│   ├── ui_components.py             # Reusable UI components
│   └── pages/
│       ├── __init__.py
│       ├── dashboard.py             # Dashboard page logic
│       ├── forecasting.py           # Demand forecasting page
│       ├── health.py                # Inventory health page
│       ├── alerts.py                # Stockout alerts page
│       ├── reorder.py               # Reorder optimization page
│       ├── slow_moving.py           # Slow-moving analysis page
│       └── settings.py              # Settings page
│
├── utils/
│   ├── __init__.py
│   ├── helpers.py                   # General helper functions
│   └── formatters.py                # Data formatting utilities
│
├── master_features_final.csv        # Master data file
├── requirements.txt                 # Dependencies
└── README.md                        # Documentation

\`\`\`

---

## Installation & Setup

### 1. Prerequisites

- Python 3.8+
- pip (Python package manager)
- Virtual environment (recommended)

### 2. Clone Repository

\`\`\`bash
git clone <repository-url>
cd inventory-intelligence
\`\`\`

### 3. Create Virtual Environment

\`\`\`bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
\`\`\`

### 4. Install Dependencies

\`\`\`bash
pip install -r requirements.txt
\`\`\`

### 5. Verify Master Data File

Pastikan file `master_features_final.csv` berada di root directory project.

### 6. Run Application

\`\`\`bash
streamlit run main.py
\`\`\`

Aplikasi akan terbuka di `http://localhost:8501`

---

## Module Documentation

### config/constants.py

Berisi semua konstanta global, default values, dan konfigurasi yang digunakan di seluruh aplikasi.

**Key Constants:**
- `APP_TITLE`, `APP_VERSION`: Metadata aplikasi
- `COLORS`: Dictionary theme colors
- `PAGES`: List halaman aplikasi
- `SMTP_SERVER`, `SMTP_PORT`: Email configuration
- `ALERT_CRITICAL_DAYS`, `ALERT_HIGH_DAYS`: Alert thresholds

**Cara Menggunakan:**
\`\`\`python
from config.constants import APP_TITLE, COLORS, DEFAULT_FORECAST_DAYS

print(f"App: {APP_TITLE}")
print(f"Primary color: {COLORS['primary']}")
\`\`\`

---

### modules/session_manager.py

Mengelola Streamlit session state dengan centralized management.

**Key Functions:**
- `initialize_session_state()`: Inisialisasi semua session state
- `get_session_value(key, default)`: Ambil session value dengan safety
- `set_session_value(key, value)`: Set session value
- `reset_session_state()`: Reset ke default values
- `toggle_visibility(key)`: Toggle boolean state
- `get_email_config()`: Retrieve email configuration

**Contoh Usage:**
\`\`\`python
from modules.session_manager import initialize_session_state, get_email_config

initialize_session_state()
email_config = get_email_config()
print(email_config['email_sender'])
\`\`\`

---

### modules/data_loader.py

Handle data loading, caching, dan preprocessing dengan optimasi performance.

**Key Functions:**
- `load_master_data()`: Load master data (cached)
- `get_filtered_data(df, search_term, category_filter, ...)`: Filter data
- `get_quick_stats(df)`: Calculate dashboard statistics
- `get_unique_categories(df)`: Get available categories
- `get_unique_abc_classes(df)`: Get ABC classes

**Contoh Usage:**
\`\`\`python
from modules.data_loader import load_master_data, get_filtered_data, get_quick_stats

df = load_master_data()
filtered_df = get_filtered_data(df, search_term="XYZ", category_filter="Electronics")
stats = get_quick_stats(df)
\`\`\`

---

### modules/email_utils.py

Handle email sending, validation, dan SMTP configuration.

**Key Functions:**
- `validate_email(email)`: Validasi format email
- `validate_email_list(emails)`: Validasi list emails
- `send_email(sender, password, recipients, subject, body_html)`: Send email via SMTP
- `create_email_body_dashboard(stats, quick_stats)`: Generate HTML email body
- `dataframe_to_html_table(df)`: Convert DataFrame ke HTML table

**Contoh Usage:**
\`\`\`python
from modules.email_utils import send_email, validate_email

if validate_email("user@example.com"):
    result = send_email(
        sender="inventory@company.com",
        sender_password="app_password",
        recipients=["recipient@example.com"],
        subject="Inventory Report",
        body_html="<h1>Report</h1>"
    )
    print(result['message'])
\`\`\`

---

### modules/activity_logger.py

Real-time activity logging untuk tracking user actions dan system events.

**Key Functions:**
- `log_activity(action, color)`: Log aktivitas dengan timestamp
- `get_activity_log()`: Retrieve semua activities
- `get_recent_activities(count)`: Get n recent activities
- `render_activity_log_sidebar(max_entries)`: Render activity log di sidebar
- `export_activity_log()`: Export log sebagai string

**Contoh Usage:**
\`\`\`python
from modules.activity_logger import log_activity, render_activity_log_sidebar

log_activity("User filtered data by category", "#10b981")
render_activity_log_sidebar(max_entries=15)
\`\`\`

---

### modules/ui_components.py

Reusable UI components dengan consistent styling dan behavior.

**Key Functions:**
- `render_metric_card(label, value, delta, ...)`: Metric card component
- `render_alert_box(alert_type, title, count, ...)`: Alert box component
- `render_filter_row(columns)`: Filter row dengan multiple columns
- `render_data_table(df, title, max_rows, ...)`: Data table dengan search
- `render_sidebar_header(title, subtitle)`: Sidebar header
- `render_quick_stat_box(label, value, type_)`: Quick stat box
- `render_page_header(title, description, icon)`: Page header
- `apply_page_css()`: Apply global CSS styling

**Contoh Usage:**
\`\`\`python
from modules.ui_components import render_metric_card, render_alert_box

render_metric_card(
    label="Service Level",
    value="94.2%",
    delta="↑ 2.1%",
    delta_positive=True,
    insight="Target: >95%"
)

render_alert_box(
    alert_type="critical",
    title="Critical Risk",
    count=25,
    description="Stockout in <7 days"
)
\`\`\`

---

### utils/helpers.py

General helper functions untuk operasi umum.

**Key Functions:**
- `safe_divide(numerator, denominator, default)`: Safe division
- `calculate_percentage(value, total, decimals)`: Calculate percentage
- `get_date_range(days)`: Get date range untuk n hari terakhir
- `is_critical_status(value, threshold)`: Check critical status
- `is_warning_status(value, low, high)`: Check warning status
- `get_risk_color(risk_level)`: Get color untuk risk level
- `truncate_text(text, max_length)`: Truncate text
- `format_quantity(value, decimals)`: Format quantity dengan separators
- `days_until_date(target_date)`: Calculate days until date
- `get_status_emoji(risk_level)`: Get emoji untuk status

---

### utils/formatters.py

Data formatting utilities untuk display values dalam berbagai format.

**Key Functions:**
- `format_currency(value, currency_symbol, decimals)`: Format sebagai currency
- `format_percentage(value, decimals)`: Format sebagai percentage
- `format_number(value, decimals, use_separators)`: Format sebagai number
- `format_date(date_input, format_str)`: Format date
- `format_time(time_input, format_str)`: Format time
- `format_duration(seconds)`: Format durasi
- `format_status_badge(status)`: Format status badge
- `format_large_number(value, decimals)`: Format large numbers (K, M, B)

**Contoh Usage:**
\`\`\`python
from utils.formatters import format_currency, format_percentage

price = format_currency(1500000)  # Output: "Rp 1,500,000"
pct = format_percentage(0.942)    # Output: "94.2%"
\`\`\`

---

## Adding New Pages

Untuk menambah halaman baru ke aplikasi, ikuti langkah berikut:

### 1. Buat Page File

Buat file baru di `modules/pages/` (e.g., `modules/pages/my_page.py`):

\`\`\`python
"""
My Custom Page
===============

Deskripsi halaman dan functionality.

Author: Your Name
Date: 2025-11-18
"""

import streamlit as st
from modules.data_loader import load_master_data
from modules.activity_logger import log_activity
from modules.ui_components import render_page_header
from utils.formatters import format_currency


def render_page():
    """
    Main function untuk render halaman.
    Dipanggil dari main.py
    """
    
    render_page_header("My Page Title", "Page description", "🎯")
    
    # Load data
    df = load_master_data()
    
    # Your page logic here
    log_activity("Viewed My Custom Page", "#6366f1")
    
    # Render content
    st.write("Hello World")
\`\`\`

### 2. Update main.py

Import page module dan add routing di main.py:

\`\`\`python
from modules.pages import my_page

# ... dalam routing section ...

elif "My Page" in page:
    log_activity("Navigated to My Page", "#6366f1")
    my_page.render_page()
\`\`\`

### 3. Update constants

Tambah page ke `PAGES` list di `config/constants.py`:

\`\`\`python
PAGES = [
    "🏠 Dashboard Overview",
    # ... existing pages ...
    "🎯 My Custom Page"
]
\`\`\`

---

## Extending Functionality

### Menambah Utility Function

Tambahkan function baru ke `utils/helpers.py` atau `utils/formatters.py`:

\`\`\`python
def my_helper_function(param1, param2):
    """
    Dokumentasi lengkap
    
    Args:
        param1: Description
        param2: Description
        
    Returns:
        Description
        
    Example:
        >>> my_helper_function(x, y)
    """
    # Implementation
    return result
\`\`\`

### Menambah Modul Baru

Jika perlu, buat modul baru di `modules/`:

\`\`\`python
"""
New Module Name
================

Dokumentasi lengkap tentang modul dan responsibility-nya.
"""

# Imports
# Functions
# Classes
\`\`\`

---

## Troubleshooting

### Issue: "File 'master_features_final.csv' tidak ditemukan"

**Solution:** Pastikan file CSV berada di root directory project, di level yang sama dengan `main.py`.

### Issue: "ModuleNotFoundError: No module named 'config'"

**Solution:** Pastikan Anda menjalankan aplikasi dari root directory:
\`\`\`bash
streamlit run main.py
\`\`\`

### Issue: Email tidak terkirim

**Checklist:**
1. Gunakan Gmail App Password (bukan password biasa)
2. Enable "Less secure app access" di Gmail account
3. Validasi email format: `validate_email(email)`
4. Check SMTP settings di `config/constants.py`

### Issue: Data loading lambat

**Solution:** Data sudah di-cache. Clear cache jika data berubah:
\`\`\`bash
streamlit cache clear
\`\`\`

---

## Best Practices

### 1. Selalu Gunakan Constants

\`\`\`python
# ✅ GOOD
from config.constants import COLORS, ALERT_CRITICAL_DAYS
color = COLORS['primary']

# ❌ AVOID
color = '#6366f1'
\`\`\`

### 2. Dokumentasi Lengkap

Setiap function harus memiliki docstring dengan:
- Deskripsi
- Args
- Returns
- Example

### 3. Error Handling

Gunakan try-except untuk operasi yang mungkin gagal:

\`\`\`python
try:
    result = send_email(...)
except Exception as e:
    st.error(f"Error: {str(e)}")
    log_activity(f"Email failed: {str(e)}", "#ef4444")
\`\`\`

### 4. Logging

Log important actions untuk audit trail:

\`\`\`python
log_activity("User exported report", "#10b981")
\`\`\`

### 5. Code Reusability

Gunakan existing modules sebelum membuat yang baru:

\`\`\`python
# ✅ GOOD - Reuse existing components
from modules.ui_components import render_metric_card

# ❌ AVOID - Duplicate code
st.markdown(f"""<div>...</div>""")
\`\`\`

---

## Performance Tips

1. **Data Caching**: `load_master_data()` sudah cached, jangan load berulang
2. **Lazy Loading**: Load data hanya saat dibutuhkan
3. **Filter Early**: Filter data sebelum processing untuk reduce memory
4. **Minimize Re-renders**: Gunakan session state untuk track state

---

## Support & Contribution

- **Issues**: Report bugs di issue tracker
- **Features**: Submit feature requests dengan detail
- **Contributing**: Fork dan submit pull requests

---

## License

Proprietary - PT Wahana Piranti Teknologi

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 4.3 | 2025-11-18 | Modular architecture refactor |
| 4.2 | 2025-11-10 | Enhanced UI/UX & export features |
| 4.1 | 2025-10-15 | Activity logging added |
| 4.0 | 2025-09-01 | Initial production release |

---

**Last Updated:** 2025-11-18  
**Maintained By:** Data Science Team  
**Status:** ✅ Production Ready
