# 🌐 API Endpoints Design

> **Tujuan**: Mendesain REST API endpoints untuk setiap halaman Streamlit
> 
> **Prinsip**: Setiap `render_page(df)` di Streamlit → menjadi API endpoint

---

## 📋 Overview API Structure

```
/api/v1/
├── /auth
│   ├── POST /login          # Login user
│   ├── POST /logout         # Logout user
│   ├── POST /signup         # Register new user
│   └── GET  /me             # Get current user info
│
├── /dashboard
│   ├── GET  /metrics        # Quick stats & KPIs
│   ├── GET  /alerts-summary # Alert breakdown
│   └── GET  /charts         # Chart data
│
├── /inventory
│   ├── GET  /products       # List all products (paginated)
│   ├── GET  /products/:id   # Single product detail
│   └── GET  /groups         # Available groups for filter
│
├── /forecasting
│   ├── GET  /predictions    # Demand forecast data
│   └── GET  /trends         # Trend analysis
│
├── /health
│   ├── GET  /status         # Inventory health metrics
│   └── GET  /risk-levels    # Risk classification
│
├── /alerts
│   ├── GET  /stockout       # Stockout alerts
│   ├── GET  /critical       # Critical items only
│   └── POST /acknowledge    # Mark alert as seen
│
├── /reorder
│   ├── GET  /recommendations # Reorder suggestions
│   └── POST /create-order   # Create bulk order
│
├── /analytics
│   ├── GET  /slow-moving    # Slow-moving items
│   ├── GET  /rfm            # RFM analysis
│   └── GET  /mba            # Market basket analysis
│
└── /settings
    ├── GET  /               # Get user settings
    ├── PUT  /               # Update settings
    └── POST /email/test     # Test email config
```

---

## 🔐 Authentication Endpoints

### `backend/app/api/auth.py`

```python
"""
Authentication API Blueprint
============================
Migrasi dari: modules/auth.py + modules/pages/login.py
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, 
    jwt_required, 
    get_jwt_identity,
    get_jwt
)
from app.services.auth_service import AuthService

bp = Blueprint('auth', __name__)
auth_service = AuthService()


@bp.route('/login', methods=['POST'])
def login():
    """
    Login user dan return JWT token.
    
    Streamlit equivalent:
        success, msg = login(username, password)
        st.session_state['authenticated'] = True
    
    Request Body:
        {
            "username": "admin1",
            "password": "admin1!wahana25"
        }
    
    Response:
        {
            "access_token": "eyJ...",
            "user": {
                "username": "admin1",
                "role": "admin"
            }
        }
    """
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    user = auth_service.authenticate(username, password)
    
    if user:
        # Buat JWT token (pengganti st.session_state)
        access_token = create_access_token(
            identity=username,
            additional_claims={
                'role': user['role'],
                'user_id': user['id']
            }
        )
        return jsonify({
            'access_token': access_token,
            'user': {
                'username': user['username'],
                'role': user['role']
            }
        }), 200
    else:
        return jsonify({'error': 'Invalid credentials'}), 401


@bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """
    Get current authenticated user info.
    
    Streamlit equivalent:
        get_current_user() dari modules/auth.py
    """
    claims = get_jwt()
    return jsonify({
        'username': get_jwt_identity(),
        'role': claims.get('role'),
        'user_id': claims.get('user_id')
    }), 200


@bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    Logout user (invalidate token).
    
    Streamlit equivalent:
        logout() → clears st.session_state
    
    Note: Untuk JWT, logout biasanya di-handle di frontend
    dengan menghapus token dari storage.
    """
    # Opsional: Tambahkan token ke blocklist
    return jsonify({'message': 'Logged out successfully'}), 200
```

---

## 📊 Dashboard Endpoints

### `backend/app/api/dashboard.py`

```python
"""
Dashboard API Blueprint
=======================
Migrasi dari: modules/pages/dashboard.py
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from app.services.data_loader import DataLoaderService
from app.extensions import cache

bp = Blueprint('dashboard', __name__)
data_loader = DataLoaderService()


@bp.route('/metrics', methods=['GET'])
@jwt_required()
@cache.cached(timeout=300, query_string=True)  # Cache 5 menit
def get_metrics():
    """
    Get dashboard quick stats/metrics.
    
    Streamlit equivalent:
        quick_stats = get_quick_stats_from_df(df)
        render_quick_stat_box("Active Alerts", quick_stats['active_alerts'])
    
    Query Parameters:
        - groups: comma-separated group filter (optional)
    
    Response:
        {
            "active_alerts": 25,
            "total_products": 2136,
            "critical_count": 10,
            "high_count": 15,
            "last_updated": "12:48:29"
        }
    """
    # Get filter dari query params (pengganti st.session_state.selected_groups)
    groups = request.args.get('groups', '')
    group_list = [g.strip() for g in groups.split(',') if g.strip()]
    
    # Load data dengan filter
    df = data_loader.load_all_data(groups=group_list)
    
    # Hitung metrics (sama seperti di dashboard.py)
    metrics = {
        'active_alerts': len(df[df['risk_class'].isin(['critical', 'high'])]),
        'total_products': len(df),
        'critical_count': len(df[df['risk_class'] == 'critical']),
        'high_count': len(df[df['risk_class'] == 'high']),
        'medium_count': len(df[df['risk_class'] == 'medium']),
        'low_count': len(df[df['risk_class'] == 'low']),
        'last_updated': df['last_updated'].max() if 'last_updated' in df.columns else None
    }
    
    return jsonify(metrics), 200


@bp.route('/alerts-summary', methods=['GET'])
@jwt_required()
@cache.cached(timeout=300, query_string=True)
def get_alerts_summary():
    """
    Get alert breakdown for dashboard.
    
    Streamlit equivalent:
        render_alert_box('critical', 'Critical Risk', critical_count, ...)
    
    Response:
        {
            "alerts": [
                {"type": "critical", "count": 10, "description": "Stockout < 7 days"},
                {"type": "high", "count": 15, "description": "Stockout 7-14 days"},
                ...
            ]
        }
    """
    groups = request.args.get('groups', '')
    group_list = [g.strip() for g in groups.split(',') if g.strip()]
    
    df = data_loader.load_all_data(groups=group_list)
    
    alerts = [
        {
            'type': 'critical',
            'count': len(df[df['days_until_stockout'] < 7]),
            'description': 'Stockout dalam < 7 hari',
            'color': '#ef4444'
        },
        {
            'type': 'high', 
            'count': len(df[(df['days_until_stockout'] >= 7) & (df['days_until_stockout'] < 14)]),
            'description': 'Stockout dalam 7-14 hari',
            'color': '#f97316'
        },
        {
            'type': 'medium',
            'count': len(df[(df['days_until_stockout'] >= 14) & (df['days_until_stockout'] < 30)]),
            'description': 'Stockout dalam 14-30 hari',
            'color': '#eab308'
        },
        {
            'type': 'low',
            'count': len(df[df['days_until_stockout'] >= 30]),
            'description': 'Stok aman > 30 hari',
            'color': '#22c55e'
        }
    ]
    
    return jsonify({'alerts': alerts}), 200


@bp.route('/charts/stock-distribution', methods=['GET'])
@jwt_required()
@cache.cached(timeout=300, query_string=True)
def get_stock_distribution_chart():
    """
    Get data untuk stock distribution chart.
    
    Streamlit equivalent:
        fig = px.pie(df, values='count', names='category', ...)
        st.plotly_chart(fig)
    
    Response:
        {
            "chart_type": "pie",
            "data": [
                {"name": "Critical", "value": 10, "color": "#ef4444"},
                ...
            ]
        }
    """
    groups = request.args.get('groups', '')
    group_list = [g.strip() for g in groups.split(',') if g.strip()]
    
    df = data_loader.load_all_data(groups=group_list)
    
    # Prepare chart data (frontend akan render dengan Recharts/Plotly React)
    chart_data = {
        'chart_type': 'pie',
        'title': 'Stock Distribution by Risk Level',
        'data': [
            {'name': 'Critical', 'value': len(df[df['risk_class'] == 'critical']), 'color': '#ef4444'},
            {'name': 'High', 'value': len(df[df['risk_class'] == 'high']), 'color': '#f97316'},
            {'name': 'Medium', 'value': len(df[df['risk_class'] == 'medium']), 'color': '#eab308'},
            {'name': 'Low', 'value': len(df[df['risk_class'] == 'low']), 'color': '#22c55e'},
        ]
    }
    
    return jsonify(chart_data), 200
```

---

## 📦 Inventory Endpoints

### `backend/app/api/inventory.py`

```python
"""
Inventory API Blueprint
=======================
Migrasi dari: data loading & filtering di main.py
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from app.services.data_loader import DataLoaderService
from app.extensions import cache

bp = Blueprint('inventory', __name__)
data_loader = DataLoaderService()


@bp.route('/products', methods=['GET'])
@jwt_required()
@cache.cached(timeout=300, query_string=True)
def get_products():
    """
    Get paginated product list.
    
    Streamlit equivalent:
        st.dataframe(df[displayed_columns])
    
    Query Parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 50)
        - groups: Comma-separated group filter
        - search: Search term
        - sort_by: Column to sort
        - sort_order: 'asc' or 'desc'
    
    Response:
        {
            "products": [...],
            "pagination": {
                "page": 1,
                "per_page": 50,
                "total": 2136,
                "total_pages": 43
            }
        }
    """
    # Parse query parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    groups = request.args.get('groups', '')
    search = request.args.get('search', '')
    sort_by = request.args.get('sort_by', 'item_code')
    sort_order = request.args.get('sort_order', 'asc')
    
    group_list = [g.strip() for g in groups.split(',') if g.strip()]
    
    # Load and filter data
    df = data_loader.load_all_data(groups=group_list)
    
    # Apply search filter
    if search:
        df = df[
            df['item_code'].str.contains(search, case=False, na=False) |
            df['item_name'].str.contains(search, case=False, na=False)
        ]
    
    # Apply sorting
    ascending = sort_order == 'asc'
    if sort_by in df.columns:
        df = df.sort_values(by=sort_by, ascending=ascending)
    
    # Calculate pagination
    total = len(df)
    total_pages = (total + per_page - 1) // per_page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    # Slice data
    df_page = df.iloc[start_idx:end_idx]
    
    # Convert to JSON-serializable format
    products = df_page.to_dict(orient='records')
    
    return jsonify({
        'products': products,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': total_pages
        }
    }), 200


@bp.route('/groups', methods=['GET'])
@jwt_required()
@cache.cached(timeout=3600)  # Cache 1 jam
def get_groups():
    """
    Get available groups for filtering.
    
    Streamlit equivalent:
        available_groups = sorted(df['item_group_normalized'].unique())
        st.multiselect("Select groups", options=available_groups)
    
    Response:
        {
            "groups": ["GROUP-A", "GROUP-B", ...]
        }
    """
    df = data_loader.load_all_data()
    
    if 'item_group_normalized' in df.columns:
        groups = sorted(df['item_group_normalized'].dropna().unique().tolist())
    else:
        groups = []
    
    return jsonify({'groups': groups}), 200
```

---

## 📨 Request/Response Examples

### Login Request
```http
POST /api/auth/login
Content-Type: application/json

{
    "username": "admin1",
    "password": "admin1!wahana25"
}
```

### Login Response
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
        "username": "admin1",
        "role": "admin"
    }
}
```

### Authenticated Request
```http
GET /api/dashboard/metrics?groups=GROUP-A,GROUP-B
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Metrics Response
```json
{
    "active_alerts": 25,
    "total_products": 2136,
    "critical_count": 10,
    "high_count": 15,
    "medium_count": 45,
    "low_count": 2066,
    "last_updated": "2026-01-16T12:48:29"
}
```

---

## 🔗 API Client untuk Frontend

```typescript
// frontend/lib/api.ts

const API_BASE = 'http://localhost:5000/api';

class ApiClient {
    private token: string | null = null;

    setToken(token: string) {
        this.token = token;
    }

    private async request(endpoint: string, options: RequestInit = {}) {
        const headers: Record<string, string> = {
            'Content-Type': 'application/json',
            ...options.headers as Record<string, string>,
        };

        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        const response = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            headers,
        });

        if (!response.ok) {
            throw new Error(`API Error: ${response.status}`);
        }

        return response.json();
    }

    // Auth
    async login(username: string, password: string) {
        return this.request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ username, password }),
        });
    }

    // Dashboard
    async getDashboardMetrics(groups?: string[]) {
        const params = groups?.length ? `?groups=${groups.join(',')}` : '';
        return this.request(`/dashboard/metrics${params}`);
    }

    async getAlertsSummary(groups?: string[]) {
        const params = groups?.length ? `?groups=${groups.join(',')}` : '';
        return this.request(`/dashboard/alerts-summary${params}`);
    }

    // Products
    async getProducts(params: {
        page?: number;
        perPage?: number;
        groups?: string[];
        search?: string;
    }) {
        const query = new URLSearchParams();
        if (params.page) query.set('page', params.page.toString());
        if (params.perPage) query.set('per_page', params.perPage.toString());
        if (params.groups?.length) query.set('groups', params.groups.join(','));
        if (params.search) query.set('search', params.search);
        
        return this.request(`/inventory/products?${query}`);
    }
}

export const api = new ApiClient();
```

---

## ⏭️ Langkah Selanjutnya

Lanjut ke **[04_AUTH_MIGRATION.md](./04_AUTH_MIGRATION.md)** untuk detail migrasi sistem autentikasi.
