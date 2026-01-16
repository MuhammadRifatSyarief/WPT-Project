"""
Flask Extensions
================
Inisialisasi extensions yang dipakai di seluruh app.
"""

from flask_caching import Cache
from flask_sqlalchemy import SQLAlchemy

# Cache - pengganti @st.cache_data
cache = Cache()

# Database ORM
db = SQLAlchemy()
