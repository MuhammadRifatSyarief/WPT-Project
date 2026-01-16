# 🧠 Business Logic Migration

> **Tujuan**: Migrasi ML pipeline dan analytics services
> 
> **File Source**: `modules/ml_pipeline.py`, `modules/demand_forecasting.py`, `modules/stockout_prediction.py`, dll

---

## 📊 Overview Business Logic Modules

| Module | Size | Function | API Endpoint |
|--------|------|----------|--------------|
| `ml_pipeline.py` | 86KB | ML model training & prediction | `/api/ml/*` |
| `demand_forecasting.py` | 26KB | Demand forecasting | `/api/forecasting/*` |
| `stockout_prediction.py` | 21KB | Stockout risk prediction | `/api/alerts/*` |
| `reorder_optimization.py` | 32KB | Reorder recommendations | `/api/reorder/*` |
| `slow_moving_analysis.py` | 20KB | Slow-moving detection | `/api/analytics/slow-moving` |
| `rfm_analyzer.py` | 13KB | RFM analysis | `/api/analytics/rfm` |
| `market_basket_analyzer.py` | 16KB | MBA analysis | `/api/analytics/mba` |

---

## 🏗️ Struktur Services

```
backend/app/services/
├── ml/
│   ├── __init__.py
│   ├── pipeline.py          # ML Pipeline orchestration
│   ├── forecasting.py       # Demand forecasting
│   └── stockout.py          # Stockout prediction
├── analytics/
│   ├── __init__.py
│   ├── slow_moving.py       # Slow-moving analysis
│   ├── rfm.py               # RFM analysis
│   └── mba.py               # Market basket analysis
└── optimization/
    ├── __init__.py
    └── reorder.py           # Reorder optimization
```

---

## 📄 Forecasting Service

```python
"""
Demand Forecasting Service
==========================
Migrasi dari: modules/demand_forecasting.py
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from app.services.data_loader import data_loader_service
from app.extensions import cache


class ForecastingService:
    """
    Service untuk demand forecasting.
    
    Streamlit equivalent: Functions in demand_forecasting.py
    yang dipanggil dari forecasting.py page
    """
    
    def __init__(self):
        self.forecast_horizon = 30  # days
    
    @cache.memoize(timeout=3600)
    def get_forecast_data(
        self, 
        groups: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get forecast data untuk display.
        
        Streamlit equivalent:
            Data yang di-render di forecasting.render_page(df)
        
        Returns:
            {
                "products": [...],
                "summary": {...},
                "accuracy_metrics": {...}
            }
        """
        df = data_loader_service.load_all_data(groups=groups)
        
        # Generate forecasts
        forecasts = self._generate_forecasts(df)
        
        # Calculate summary
        summary = self._calculate_summary(forecasts)
        
        return {
            'products': forecasts.to_dict(orient='records'),
            'summary': summary,
            'generated_at': datetime.now().isoformat()
        }
    
    def _generate_forecasts(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate demand forecasts for each product."""
        
        forecast_cols = [
            'item_code', 'item_name', 'current_stock_qty',
            'avg_daily_demand', 'forecast_7d', 'forecast_14d', 'forecast_30d',
            'trend', 'seasonality', 'confidence'
        ]
        
        results = []
        
        for _, row in df.iterrows():
            avg_demand = row.get('avg_daily_demand', 0)
            
            # Simple forecast (in real impl, use trained models)
            forecast_7d = avg_demand * 7
            forecast_14d = avg_demand * 14  
            forecast_30d = avg_demand * 30
            
            # Trend detection
            trend = self._detect_trend(row)
            
            results.append({
                'item_code': row.get('item_code'),
                'item_name': row.get('item_name'),
                'current_stock_qty': row.get('current_stock_qty', 0),
                'avg_daily_demand': avg_demand,
                'forecast_7d': round(forecast_7d, 2),
                'forecast_14d': round(forecast_14d, 2),
                'forecast_30d': round(forecast_30d, 2),
                'trend': trend,
                'seasonality': 'none',
                'confidence': 0.85
            })
        
        return pd.DataFrame(results)
    
    def _detect_trend(self, row: pd.Series) -> str:
        """Detect demand trend."""
        # Simplified - in real impl, analyze historical data
        return 'stable'
    
    def _calculate_summary(self, forecasts: pd.DataFrame) -> Dict[str, Any]:
        """Calculate forecast summary metrics."""
        return {
            'total_products': len(forecasts),
            'avg_7d_forecast': round(forecasts['forecast_7d'].mean(), 2),
            'avg_30d_forecast': round(forecasts['forecast_30d'].mean(), 2),
            'high_demand_count': len(forecasts[forecasts['avg_daily_demand'] > 10]),
            'low_demand_count': len(forecasts[forecasts['avg_daily_demand'] < 1])
        }
    
    def get_product_forecast(self, item_code: str) -> Optional[Dict[str, Any]]:
        """Get detailed forecast for single product."""
        df = data_loader_service.load_all_data()
        product = df[df['item_code'] == item_code]
        
        if len(product) == 0:
            return None
        
        row = product.iloc[0]
        avg_demand = row.get('avg_daily_demand', 0)
        
        # Generate daily forecasts for next 30 days
        daily_forecasts = []
        for i in range(30):
            date = datetime.now() + timedelta(days=i)
            daily_forecasts.append({
                'date': date.strftime('%Y-%m-%d'),
                'predicted_demand': round(avg_demand * (1 + np.random.uniform(-0.1, 0.1)), 2),
                'lower_bound': round(avg_demand * 0.8, 2),
                'upper_bound': round(avg_demand * 1.2, 2)
            })
        
        return {
            'item_code': item_code,
            'item_name': row.get('item_name'),
            'daily_forecasts': daily_forecasts,
            'summary': {
                'avg_daily_demand': avg_demand,
                'total_30d_forecast': round(avg_demand * 30, 2)
            }
        }


forecasting_service = ForecastingService()
```

---

## 📄 Stockout Prediction Service

```python
"""
Stockout Prediction Service
===========================
Migrasi dari: modules/stockout_prediction.py
"""

import pandas as pd
from typing import Dict, List, Any, Optional
from app.services.data_loader import data_loader_service
from app.extensions import cache


class StockoutService:
    """
    Service untuk stockout prediction dan alerts.
    
    Streamlit equivalent: 
        - alerts.render_page(df)
        - health.render_page(df)
    """
    
    @cache.memoize(timeout=300)  # Cache 5 menit untuk alerts
    def get_alerts(
        self, 
        groups: Optional[List[str]] = None,
        severity: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get stockout alerts.
        
        Args:
            groups: Filter by groups
            severity: 'critical', 'high', 'medium', 'low', or None for all
        
        Returns:
            {
                "alerts": [...],
                "summary": {...}
            }
        """
        df = data_loader_service.load_all_data(groups=groups)
        
        # Filter by severity if specified
        if severity:
            df = df[df['risk_class'] == severity]
        
        # Sort by days_until_stockout (most urgent first)
        df = df.sort_values('days_until_stockout', ascending=True)
        
        alerts = []
        for _, row in df.iterrows():
            alerts.append({
                'item_code': row.get('item_code'),
                'item_name': row.get('item_name'),
                'current_stock': row.get('current_stock_qty', 0),
                'days_until_stockout': round(row.get('days_until_stockout', 0), 1),
                'risk_class': row.get('risk_class', 'unknown'),
                'avg_daily_demand': row.get('avg_daily_demand', 0),
                'recommended_action': self._get_recommended_action(row)
            })
        
        summary = {
            'total_alerts': len(alerts),
            'critical': len([a for a in alerts if a['risk_class'] == 'critical']),
            'high': len([a for a in alerts if a['risk_class'] == 'high']),
            'medium': len([a for a in alerts if a['risk_class'] == 'medium']),
            'low': len([a for a in alerts if a['risk_class'] == 'low'])
        }
        
        return {
            'alerts': alerts,
            'summary': summary
        }
    
    def _get_recommended_action(self, row: pd.Series) -> str:
        """Get recommended action based on risk level."""
        risk = row.get('risk_class', 'low')
        days = row.get('days_until_stockout', 999)
        
        if risk == 'critical':
            return f"URGENT: Order immediately! Stockout in {days:.0f} days"
        elif risk == 'high':
            return f"Order within 3 days. Stockout in {days:.0f} days"
        elif risk == 'medium':
            return "Monitor closely and plan reorder"
        else:
            return "Stock level healthy"
    
    def get_health_metrics(
        self, 
        groups: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get inventory health metrics.
        
        Streamlit equivalent: health.render_page(df)
        """
        df = data_loader_service.load_all_data(groups=groups)
        
        total = len(df)
        
        return {
            'total_products': total,
            'healthy_count': len(df[df['risk_class'] == 'low']),
            'healthy_pct': round(len(df[df['risk_class'] == 'low']) / total * 100, 1) if total > 0 else 0,
            'at_risk_count': len(df[df['risk_class'].isin(['critical', 'high'])]),
            'at_risk_pct': round(len(df[df['risk_class'].isin(['critical', 'high'])]) / total * 100, 1) if total > 0 else 0,
            'distribution': {
                'critical': len(df[df['risk_class'] == 'critical']),
                'high': len(df[df['risk_class'] == 'high']),
                'medium': len(df[df['risk_class'] == 'medium']),
                'low': len(df[df['risk_class'] == 'low'])
            }
        }


stockout_service = StockoutService()
```

---

## 🌐 API Endpoints

```python
# backend/app/api/forecasting.py

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from app.services.ml.forecasting import forecasting_service

bp = Blueprint('forecasting', __name__)


@bp.route('/predictions', methods=['GET'])
@jwt_required()
def get_predictions():
    """Get demand forecast predictions."""
    groups = request.args.get('groups', '')
    group_list = [g.strip() for g in groups.split(',') if g.strip()] or None
    
    data = forecasting_service.get_forecast_data(groups=group_list)
    return jsonify(data), 200


@bp.route('/product/<item_code>', methods=['GET'])
@jwt_required()
def get_product_forecast(item_code: str):
    """Get detailed forecast for single product."""
    data = forecasting_service.get_product_forecast(item_code)
    
    if data is None:
        return jsonify({'error': 'Product not found'}), 404
    
    return jsonify(data), 200
```

```python
# backend/app/api/alerts.py

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from app.services.ml.stockout import stockout_service

bp = Blueprint('alerts', __name__)


@bp.route('/stockout', methods=['GET'])
@jwt_required()
def get_stockout_alerts():
    """Get stockout alerts."""
    groups = request.args.get('groups', '')
    severity = request.args.get('severity')
    
    group_list = [g.strip() for g in groups.split(',') if g.strip()] or None
    
    data = stockout_service.get_alerts(groups=group_list, severity=severity)
    return jsonify(data), 200


@bp.route('/health', methods=['GET'])
@jwt_required()
def get_health_metrics():
    """Get inventory health metrics."""
    groups = request.args.get('groups', '')
    group_list = [g.strip() for g in groups.split(',') if g.strip()] or None
    
    data = stockout_service.get_health_metrics(groups=group_list)
    return jsonify(data), 200
```

---

## ⚙️ Background Tasks dengan Celery (Optional)

Untuk ML pipeline yang berat, gunakan Celery:

```python
# backend/app/tasks/ml_tasks.py

from celery import Celery
from app.services.ml.pipeline import MLPipeline

celery = Celery('tasks', broker='redis://localhost:6379/0')


@celery.task
def run_ml_pipeline():
    """Run full ML pipeline in background."""
    pipeline = MLPipeline()
    result = pipeline.run()
    return result


@celery.task
def update_forecasts():
    """Update all forecasts."""
    from app.services.ml.forecasting import forecasting_service
    forecasting_service.update_all_forecasts()
    return {'status': 'completed'}
```

---

## ⏭️ Langkah Selanjutnya

Lanjut ke **[07_FRONTEND_SETUP.md](./07_FRONTEND_SETUP.md)** untuk setup Next.js frontend.
