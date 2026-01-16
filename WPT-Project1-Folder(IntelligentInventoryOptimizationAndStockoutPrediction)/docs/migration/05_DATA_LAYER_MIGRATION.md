# 💾 Data Layer Migration

> **Tujuan**: Migrasi data loader dari Streamlit ke Flask service layer
> 
> **File Source**: `modules/data_loader_v5.py`, `data_loader.py`

---

## 📊 Perbandingan Data Loading

| Aspek | Streamlit | Flask API |
|-------|-----------|-----------|
| Caching | `@st.cache_data(ttl=3600)` | `@cache.cached(timeout=3600)` |
| Data Format | DataFrame langsung | JSON response |
| Loading | Saat page render | Saat API request |
| Filtering | `st.session_state.selected_groups` | Query parameters |

---

## 🏗️ Struktur Data Layer

```
backend/app/services/
├── data_loader.py     # Main data loading service
├── cache_service.py   # Cache management
└── data_utils.py      # DataFrame utilities
```

---

## 📄 Data Loader Service

```python
"""
Data Loader Service
===================
Migrasi dari: modules/data_loader_v5.py
"""

import os
import pandas as pd
from typing import List, Optional, Dict, Any
from app.extensions import cache
from app.config import Config


class DataLoaderService:
    """
    Service untuk loading dan manipulasi data.
    
    Streamlit equivalent: DashboardDataLoaderV5 class
    """
    
    def __init__(self):
        self.data_path = Config.DATA_PATH
        self.features_path = os.path.join(self.data_path, 'features')
        self.predictions_path = os.path.join(self.data_path, 'predictions')
        self.forecasts_path = os.path.join(self.data_path, 'forecasts')
    
    @cache.memoize(timeout=3600)  # Cache 1 jam
    def load_all_data(
        self, 
        groups: Optional[List[str]] = None,
        apply_filters: bool = True
    ) -> pd.DataFrame:
        """
        Load all data dengan optional filtering.
        
        Streamlit equivalent:
            df = data_loader.load_all_data(apply_filters=True)
        
        Args:
            groups: List of groups to filter
            apply_filters: Whether to filter out dummy/umum/jasa
        
        Returns:
            Filtered DataFrame
        """
        # Load master features
        master_path = os.path.join(self.features_path, 'master_features.csv')
        
        if not os.path.exists(master_path):
            raise FileNotFoundError(f"Master features not found: {master_path}")
        
        df = pd.read_csv(master_path)
        
        # Apply default filters (same as Streamlit)
        if apply_filters:
            df = self._apply_default_filters(df)
        
        # Apply group filter
        if groups and len(groups) > 0:
            if 'item_group_normalized' in df.columns:
                df = df[df['item_group_normalized'].isin(groups)]
        
        # Calculate derived columns
        df = self._calculate_derived_columns(df)
        
        return df
    
    def _apply_default_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply default filters (exclude dummy, umum, jasa).
        
        Streamlit equivalent: filtering logic in DashboardDataLoaderV5
        """
        # Filter out dummy items
        if 'item_code' in df.columns:
            df = df[~df['item_code'].str.lower().str.contains('dummy', na=False)]
        
        # Filter out umum/jasa categories if applicable
        if 'category' in df.columns:
            df = df[~df['category'].str.lower().isin(['umum', 'jasa'])]
        
        return df
    
    def _calculate_derived_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate derived columns.
        
        Streamlit equivalent: Line 742 in app.py
            df['days_until_stockout'] = df['current_stock_qty'] / (df['avg_daily_demand'] + 0.01)
        """
        # Days until stockout
        if 'current_stock_qty' in df.columns and 'avg_daily_demand' in df.columns:
            df['days_until_stockout'] = df['current_stock_qty'] / (df['avg_daily_demand'] + 0.01)
        
        # Risk classification
        if 'days_until_stockout' in df.columns:
            df['risk_class'] = df['days_until_stockout'].apply(self._classify_risk)
        
        return df
    
    def _classify_risk(self, days: float) -> str:
        """Classify risk level based on days until stockout."""
        if days < 7:
            return 'critical'
        elif days < 14:
            return 'high'
        elif days < 30:
            return 'medium'
        else:
            return 'low'
    
    def get_available_groups(self) -> List[str]:
        """
        Get available groups for filtering.
        
        Streamlit equivalent:
            available_groups = sorted(df['item_group_normalized'].unique())
        """
        df = self.load_all_data()
        
        if 'item_group_normalized' in df.columns:
            return sorted(df['item_group_normalized'].dropna().unique().tolist())
        return []
    
    def get_product_by_id(self, item_code: str) -> Optional[Dict[str, Any]]:
        """Get single product by item code."""
        df = self.load_all_data()
        
        product = df[df['item_code'] == item_code]
        
        if len(product) == 0:
            return None
        
        return product.iloc[0].to_dict()
    
    def search_products(
        self, 
        query: str, 
        groups: Optional[List[str]] = None,
        limit: int = 50
    ) -> pd.DataFrame:
        """
        Search products by name or code.
        
        Streamlit equivalent: Search input + filtering logic
        """
        df = self.load_all_data(groups=groups)
        
        if query:
            mask = (
                df['item_code'].str.contains(query, case=False, na=False) |
                df['item_name'].str.contains(query, case=False, na=False)
            )
            df = df[mask]
        
        return df.head(limit)


# Singleton instance
data_loader_service = DataLoaderService()
```

---

## 📄 DataFrame to JSON Utilities

```python
"""
Data Utilities
==============
Helper functions untuk serialisasi DataFrame ke JSON.
"""

import pandas as pd
import numpy as np
from typing import Any, List, Dict
from datetime import datetime, date


def df_to_json(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Convert DataFrame to JSON-serializable list of dicts.
    
    Handles:
    - NaN → None
    - datetime → ISO string
    - numpy types → Python types
    """
    # Replace NaN with None
    df = df.replace({np.nan: None})
    
    records = df.to_dict(orient='records')
    
    # Clean up each record
    cleaned = []
    for record in records:
        clean_record = {}
        for key, value in record.items():
            clean_record[key] = _serialize_value(value)
        cleaned.append(clean_record)
    
    return cleaned


def _serialize_value(value: Any) -> Any:
    """Serialize a single value for JSON."""
    if value is None or pd.isna(value):
        return None
    elif isinstance(value, (np.integer,)):
        return int(value)
    elif isinstance(value, (np.floating,)):
        return float(value)
    elif isinstance(value, (np.bool_,)):
        return bool(value)
    elif isinstance(value, (datetime, pd.Timestamp)):
        return value.isoformat()
    elif isinstance(value, date):
        return value.isoformat()
    elif isinstance(value, np.ndarray):
        return value.tolist()
    else:
        return value


def paginate_df(
    df: pd.DataFrame, 
    page: int = 1, 
    per_page: int = 50
) -> Dict[str, Any]:
    """
    Paginate DataFrame and return with metadata.
    
    Returns:
        {
            "data": [...],
            "pagination": {
                "page": 1,
                "per_page": 50,
                "total": 2136,
                "total_pages": 43
            }
        }
    """
    total = len(df)
    total_pages = (total + per_page - 1) // per_page
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    df_page = df.iloc[start_idx:end_idx]
    
    return {
        'data': df_to_json(df_page),
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1
        }
    }
```

---

## 🔄 Cache Management

```python
"""
Cache Service
=============
Pengganti st.cache_data.clear() dan cache management.
"""

from app.extensions import cache


class CacheService:
    """Service untuk cache management."""
    
    def clear_all(self) -> None:
        """
        Clear all cache.
        
        Streamlit equivalent:
            st.cache_data.clear()
        """
        cache.clear()
    
    def clear_data_cache(self) -> None:
        """Clear only data-related cache."""
        # Memoized functions can be cleared individually
        from app.services.data_loader import DataLoaderService
        cache.delete_memoized(DataLoaderService.load_all_data)
    
    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        return {
            'type': cache.config.get('CACHE_TYPE', 'unknown'),
            'timeout': cache.config.get('CACHE_DEFAULT_TIMEOUT', 0)
        }


cache_service = CacheService()
```

---

## 🌐 API Endpoint untuk Data

```python
# backend/app/api/data.py

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from app.services.data_loader import data_loader_service
from app.services.cache_service import cache_service
from app.services.data_utils import paginate_df

bp = Blueprint('data', __name__)


@bp.route('/refresh', methods=['POST'])
@jwt_required()
def refresh_data():
    """
    Clear cache and reload data.
    
    Streamlit equivalent:
        if st.button("🔄 Refresh"):
            st.cache_data.clear()
            st.rerun()
    """
    cache_service.clear_data_cache()
    return jsonify({'message': 'Cache cleared successfully'}), 200


@bp.route('/products', methods=['GET'])
@jwt_required()
def get_products():
    """Get paginated products with filters."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    groups = request.args.get('groups', '')
    search = request.args.get('search', '')
    
    group_list = [g.strip() for g in groups.split(',') if g.strip()] or None
    
    df = data_loader_service.load_all_data(groups=group_list)
    
    # Apply search
    if search:
        df = df[
            df['item_code'].str.contains(search, case=False, na=False) |
            df['item_name'].str.contains(search, case=False, na=False)
        ]
    
    result = paginate_df(df, page, per_page)
    return jsonify(result), 200
```

---

## ⏭️ Langkah Selanjutnya

Lanjut ke **[06_BUSINESS_LOGIC_MIGRATION.md](./06_BUSINESS_LOGIC_MIGRATION.md)** untuk migrasi ML pipeline dan analytics.
