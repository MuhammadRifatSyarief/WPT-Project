# 🔧 Flask API Setup

> **Tujuan**: Setup project Flask backend dari awal
> 
> **Waktu**: ~30 menit

---

## 📁 Struktur Project Target

```
WPT-Project1-Folder/
├── backend/                    # 🆕 Flask Backend
│   ├── app/
│   │   ├── __init__.py        # Flask app factory
│   │   ├── config.py          # Configuration
│   │   ├── extensions.py      # Flask extensions
│   │   │
│   │   ├── api/               # API Blueprints
│   │   │   ├── __init__.py
│   │   │   ├── auth.py        # /api/auth/*
│   │   │   ├── dashboard.py   # /api/dashboard/*
│   │   │   ├── forecasting.py # /api/forecasting/*
│   │   │   ├── health.py      # /api/health/*
│   │   │   ├── alerts.py      # /api/alerts/*
│   │   │   └── ...
│   │   │
│   │   ├── services/          # Business Logic
│   │   │   ├── data_loader.py
│   │   │   ├── ml_pipeline.py
│   │   │   └── ...
│   │   │
│   │   └── models/            # Data Models
│   │       ├── user.py
│   │       └── ...
│   │
│   ├── requirements.txt       # Python dependencies
│   ├── run.py                 # Entry point
│   └── .env                   # Environment variables
│
├── frontend/                  # 🆕 Next.js Frontend (setup di 07)
├── modules/                   # ⬅️ Existing Streamlit modules
└── main.py                    # ⬅️ Current Streamlit app
```

---

## 🚀 Step 1: Buat Folder Backend

```powershell
# Di folder project Anda
cd "d:\AA-WPT-PROJECT\AA-WPT-PROJECT\WPT-Project1-Folder(IntelligentInventoryOptimizationAndStockoutPrediction)"

# Buat struktur folder
mkdir backend
mkdir backend\app
mkdir backend\app\api
mkdir backend\app\services
mkdir backend\app\models
```

---

## 📄 Step 2: Buat File-file Utama

### `backend/requirements.txt`

```txt
# Core Flask
flask==3.0.0
flask-cors==4.0.0
flask-jwt-extended==4.6.0
python-dotenv==1.0.0

# Data Processing (sama seperti Streamlit)
pandas==2.1.4
numpy==1.26.2
scikit-learn==1.3.2
plotly==5.18.0

# Database
sqlalchemy==2.0.23
flask-sqlalchemy==3.1.1

# Caching (pengganti @st.cache_data)
flask-caching==2.1.0

# Email (tetap pakai)
# - menggunakan smtplib bawaan Python

# Utilities
gunicorn==21.2.0  # Production server
```

### `backend/.env`

```env
# Flask Configuration
FLASK_APP=run.py
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your-super-secret-key-change-this-in-production

# JWT Configuration
JWT_SECRET_KEY=jwt-secret-key-change-this
JWT_ACCESS_TOKEN_EXPIRES=3600

# Database (gunakan path ke folder data existing)
DATA_PATH=../data
DATABASE_URL=sqlite:///./app.db

# CORS (izinkan frontend akses)
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### `backend/app/__init__.py` (Flask Factory Pattern)

```python
"""
Flask Application Factory
=========================
Membuat instance Flask app dengan konfigurasi dan extensions.
"""

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from .config import Config
from .extensions import cache, db


def create_app(config_class=Config):
    """
    Factory function untuk membuat Flask app.
    
    Sama seperti st.set_page_config() di Streamlit,
    ini adalah setup awal aplikasi.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize Extensions
    CORS(app, origins=app.config['CORS_ORIGINS'].split(','))
    JWTManager(app)
    cache.init_app(app)
    db.init_app(app)
    
    # Register Blueprints (seperti page routing di Streamlit)
    from .api import auth, dashboard, forecasting, health, alerts
    
    app.register_blueprint(auth.bp, url_prefix='/api/auth')
    app.register_blueprint(dashboard.bp, url_prefix='/api/dashboard')
    app.register_blueprint(forecasting.bp, url_prefix='/api/forecasting')
    app.register_blueprint(health.bp, url_prefix='/api/health')
    app.register_blueprint(alerts.bp, url_prefix='/api/alerts')
    
    # Health check endpoint
    @app.route('/api/health-check')
    def health_check():
        return {'status': 'ok', 'message': 'Flask API is running!'}
    
    return app
```

### `backend/app/config.py`

```python
"""
Configuration Module
====================
Pengganti config/constants.py dari Streamlit.
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration."""
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    
    # JWT (pengganti st.session_state untuk auth)
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-dev-secret')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        seconds=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 3600))
    )
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Data Path (ke folder data existing)
    DATA_PATH = os.getenv('DATA_PATH', '../data')
    
    # Cache (pengganti @st.cache_data)
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 3600  # 1 jam, sama seperti ttl=3600
    
    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000')
```

### `backend/app/extensions.py`

```python
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
```

### `backend/run.py` (Entry Point)

```python
"""
Flask Application Entry Point
=============================
Jalankan dengan: python run.py

Sama seperti: streamlit run main.py
"""

from app import create_app

app = create_app()

if __name__ == '__main__':
    print("🚀 Starting Flask API Server...")
    print("📍 API URL: http://localhost:5000")
    print("📍 Health Check: http://localhost:5000/api/health-check")
    print("-" * 50)
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
```

---

## 📦 Step 3: Install Dependencies

```powershell
# Masuk ke folder backend
cd backend

# Buat virtual environment
python -m venv venv

# Aktivasi virtual environment
.\venv\Scripts\Activate

# Install dependencies
pip install -r requirements.txt
```

---

## 🧪 Step 4: Test Running

```powershell
# Pastikan virtual environment aktif
cd backend

# Jalankan Flask
python run.py
```

**Expected Output:**
```
🚀 Starting Flask API Server...
📍 API URL: http://localhost:5000
📍 Health Check: http://localhost:5000/api/health-check
--------------------------------------------------
 * Running on http://0.0.0.0:5000
 * Debugger is active!
```

**Test di Browser atau Postman:**
- Buka: `http://localhost:5000/api/health-check`
- Response: `{"status": "ok", "message": "Flask API is running!"}`

---

## 📊 Perbandingan dengan Streamlit

| Aspek | Streamlit | Flask |
|-------|-----------|-------|
| Entry point | `main.py` | `run.py` |
| Config | `st.set_page_config()` | `config.py` |
| Caching | `@st.cache_data` | `@cache.cached()` |
| Session | `st.session_state` | JWT tokens |
| Routing | `st.radio()` nav | Blueprints |
| Run command | `streamlit run main.py` | `python run.py` |

---

## ⏭️ Langkah Selanjutnya

Lanjut ke **[03_API_ENDPOINTS_DESIGN.md](./03_API_ENDPOINTS_DESIGN.md)** untuk mendesain REST API endpoints.
