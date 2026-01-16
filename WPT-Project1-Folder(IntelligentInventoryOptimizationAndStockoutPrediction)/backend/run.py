"""
Flask Application Entry Point
=============================
Jalankan dengan: python run.py
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
