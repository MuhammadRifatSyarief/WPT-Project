
import pandas as pd
import numpy as np
import os
from pathlib import Path
from typing import Dict, List, Optional
import logging

# Setup Logger
logger = logging.getLogger(__name__)

# Constants from data_loader_v5.py
GROUP_NORMALIZATION = {
    'H_DATACOMM': 'H_DATACOM', 'H_DATACOM': 'H_DATACOM',
    'H3C1': 'H3C', 'H3C': 'H3C', 'HUAWEI': 'HUAWEI',
    'TPLK': 'TPLINK', 'TLTO': 'TPLINK', 'TPLINK': 'TPLINK',
    'ONE ': 'ONE', 'ONE': 'ONE', 'GIGA': 'GIGA', 'OMADA': 'OMADA',
    'RENT': 'RENT', 'RSMB': 'RSMB', 'SANGFOR': 'SANGFOR',
    'SONICWALL': 'SONICWALL', 'QUEST': 'QUEST', 'ALTAI': 'ALTAI',
    'ROBUSTEL': 'ROBUSTEL', 'GROUP': 'GROUP',
}

FILTER_WORDS = ['dummy', 'umum', 'jasa', 'test', 'sample']

class DataLoaderService:
    """
    Service untuk load data Inventory & Dashboard
    Mengadopsi logic dari modules/data_loader_v5.py (Streamlit Logic)
    """
    
    # Base Path ke folder 'data'
    # Backend ada di: d:\...\backend
    # Data ada di: d:\...\data
    BASE_DIR = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../data')))

    _cached_df = None

    @classmethod
    def get_data_paths(cls):
        return {
            'features': cls.BASE_DIR / 'features' / 'master_features.csv',
            'forecasts': cls.BASE_DIR / 'forecasts' / 'forecast_summary.csv',
            'predictions': cls.BASE_DIR / 'predictions' / 'stockout_predictions.csv',
            'reorder': cls.BASE_DIR / 'reorder' / 'reorder_optimization.csv',
            'slow_moving': cls.BASE_DIR / 'slow_moving' / 'slow_moving_analysis.csv',
            'lead_times': cls.BASE_DIR / 'features' / 'product_lead_times.csv',
        }

    @classmethod
    def load_products_data(cls, apply_filters: bool = True) -> pd.DataFrame:
        """
        Load dan merge semua data CSV persis seperti data_loader_v5.py
        """
        # Cek cache sederhana (bisa di-optimize pakai Flask-Cache nanti)
        # if cls._cached_df is not None:
        #     return cls._cached_df
            
        paths = cls.get_data_paths()
        
        # 1. Load Master Features
        if not paths['features'].exists():
            print(f"❌ Master features not found at: {paths['features']}")
            return pd.DataFrame()

        df = pd.read_csv(paths['features'], encoding='utf-8-sig')
        
        # 2. Extract Groups & Normalize
        df = cls._extract_groups(df)
        
        # 3. Apply Filters (Dummy/Umum/Jasa)
        if apply_filters:
            df = cls._apply_filters(df)

        # 4. Merge Other Data Sources (Forecasts, Predictions, Reorder, etc)
        df = cls._merge_forecasts(df, paths['forecasts'])
        df = cls._merge_predictions(df, paths['predictions'])
        df = cls._merge_reorder(df, paths['reorder'])
        df = cls._merge_slow_moving(df, paths['slow_moving'])
        
        # 5. Column Aliasing (Mapping ke standard Dashboard/Inventory API)
        df = cls._apply_column_aliases(df)
        
        print(f"✅ Data Loaded: {len(df)} items. Columns: {list(df.columns)}")
        cls._cached_df = df
        return df

    @staticmethod
    def _extract_groups(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        # Logic Normalization Item Group
        df['item_group'] = df['no'].astype(str).str.split('-').str[0].str.strip()
        
        def normalize_group(x):
            if pd.isna(x) or x == '' or x == 'nan': return 'OTHER'
            x_upper = x.strip().upper()
            if x_upper.isdigit(): return 'NUMERIC_CODE'
            if x_upper and x_upper[0].isdigit(): return 'NUMERIC_CODE'
            if any(c in x_upper for c in ['(', ')', '[', ']']): return 'OTHER'
            if len(x_upper) <= 1: return 'OTHER'
            if x_upper in ['NON', 'NA', 'N/A', 'NAN']: return 'OTHER'
            return GROUP_NORMALIZATION.get(x_upper, x_upper)
            
        df['item_group_normalized'] = df['item_group'].apply(normalize_group)
        return df

    @staticmethod
    def _apply_filters(df: pd.DataFrame) -> pd.DataFrame:
        mask = pd.Series([False] * len(df), index=df.index)
        for word in FILTER_WORDS:
            if 'no' in df.columns:
                mask |= df['no'].astype(str).str.lower().str.contains(word, na=False)
            if 'name' in df.columns:
                mask |= df['name'].astype(str).str.lower().str.contains(word, na=False)
            if 'item_group_normalized' in df.columns:
                mask |= df['item_group_normalized'].str.lower().str.contains(word, na=False)
        return df[~mask].copy()

    @staticmethod
    def _merge_forecasts(df: pd.DataFrame, path: Path) -> pd.DataFrame:
        if path.exists():
            forecasts = pd.read_csv(path, encoding='utf-8-sig')
            if 'item_id' in forecasts.columns:
                forecasts = forecasts.rename(columns={
                    'next_7_days_avg': 'forecast_7d',
                    'next_30_days_avg': 'forecast_30d',
                    'model': 'forecast_model',
                    'mape': 'forecast_mape'
                })
                cols = ['item_id', 'forecast_7d', 'forecast_30d', 'forecast_model', 'forecast_mape']
                df = df.merge(forecasts[[c for c in cols if c in forecasts.columns]], 
                              left_on='id', right_on='item_id', how='left')
        return df

    @staticmethod
    def _merge_predictions(df: pd.DataFrame, path: Path) -> pd.DataFrame:
        if path.exists():
            predictions = pd.read_csv(path, encoding='utf-8-sig')
            if 'id' in predictions.columns:
                pred_cols = ['id', 'risk_score', 'risk_class', 'reorder_urgency', 
                             'expected_stockout_date', 'stockout_probability']
                cols = [c for c in pred_cols if c in predictions.columns]
                df = df.merge(predictions[cols], on='id', how='left', suffixes=('', '_pred'))
        return df

    @staticmethod
    def _merge_reorder(df: pd.DataFrame, path: Path) -> pd.DataFrame:
        if path.exists():
            reorder = pd.read_csv(path, encoding='utf-8-sig')
            if 'id' in reorder.columns:
                reorder_cols = ['id', 'eoq_optimized', 'safety_stock_optimized', 
                               'reorder_point_optimized', 'lead_time_days']
                cols = [c for c in reorder_cols if c in reorder.columns]
                # Avoid duplicate columns
                new_cols = [c for c in cols if c not in df.columns or c == 'id']
                df = df.merge(reorder[new_cols], on='id', how='left', suffixes=('', '_reorder'))
        return df
        
    @staticmethod
    def _merge_slow_moving(df: pd.DataFrame, path: Path) -> pd.DataFrame:
        if path.exists():
            sm = pd.read_csv(path, encoding='utf-8-sig')
            if 'id' in sm.columns:
                cols_to_merge = ['id', 'movement_class', 'days_since_last_sale', 'aging_bucket']
                existing = [c for c in cols_to_merge if c in sm.columns]
                new_cols = [c for c in existing if c not in df.columns or c == 'id']
                df = df.merge(sm[new_cols], on='id', how='left', suffixes=('', '_sm'))
        return df

    @staticmethod
    def _apply_column_aliases(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        # Mappings sesuai data_loader_v5.py
        aliases = {
            'no': 'product_code',
            'name': 'product_name',
            'current_stock': 'current_stock_qty',
            'item_group_normalized': 'product_category',
            'safety_stock_optimized': 'optimal_safety_stock',
            'abc_class': 'ABC_class'
        }
        
        for old, new in aliases.items():
            if old in df.columns and new not in df.columns:
                df[new] = df[old]
                
        # Fix product_name if missing
        if 'product_name' not in df.columns:
            if 'name' in df.columns:
                df['product_name'] = df['name']
            else:
                df['product_name'] = 'Product ' + df['product_code'].astype(str)

        # Derived Columns
        # Turnover Ratio 30d
        if 'turnover_ratio' in df.columns and 'turnover_ratio_30d' not in df.columns:
            df['turnover_ratio_30d'] = df['turnover_ratio'] / 12
        else:
            df['turnover_ratio_30d'] = 1.0 # Default
            
        # Days in Inventory 90d
        if 'days_in_inventory' in df.columns and 'days_in_inventory_90d' not in df.columns:
            df['days_in_inventory_90d'] = df['days_in_inventory'].clip(upper=90)
            
        # Stock Value
        if 'stock_value' not in df.columns:
            stock = df.get('current_stock_qty', 0).fillna(0)
            cost = df.get('avgCost', 1000).fillna(1000) # Mock cost if missing
            df['stock_value'] = stock * cost
            
        # Avg Daily Demand (handle x/y columns from merges)
        if 'avg_daily_demand' not in df.columns:
            if 'avg_daily_demand_x' in df.columns:
                df['avg_daily_demand'] = df['avg_daily_demand_x']
            elif 'avg_daily_demand_y' in df.columns:
                 df['avg_daily_demand'] = df['avg_daily_demand_y']
            else:
                df['avg_daily_demand'] = 0.5 # Default fallback
                
        # Fill NaNs for safety
        df['days_until_stockout'] = df.get('days_until_stockout', 30).fillna(30)
        df['risk_class'] = df.get('risk_class', 'Low').fillna('Low')
        df['ABC_class'] = df.get('ABC_class', 'C').fillna('C')
        
        return df

    @classmethod
    def get_dashboard_metrics(cls, groups: List[str] = None):
        """
        Calculates dashboard metrics from ACTUAL data
        Matches logic in dashboard.py
        """
        df = cls.load_products_data()
        if df.empty:
            return {}

        # Filter Groups
        if groups:
            df = df[df['product_category'].isin(groups)]
            
        total_items = len(df)
        
        # 1. Service Level: Mocked in Streamlit as random/fixed, but let's try to base it on stockout
        # In streamlit: (df['current_stock_qty'] > 0).sum() / len(df) * 100
        service_level = (df['current_stock_qty'] > 0).sum() / total_items * 100 if total_items > 0 else 0
        
        # 2. Turnover Ratio 30d (Weighted Average)
        weighted_turnover = 0
        total_weight = df['stock_value'].sum()
        if total_weight > 0:
            weighted_turnover = (df['turnover_ratio_30d'] * df['stock_value']).sum() / total_weight
        else:
            weighted_turnover = df['turnover_ratio_30d'].mean()
            
        # 3. Stockout Risk Counts
        risk_counts = df['risk_class'].fillna('Low').value_counts().to_dict() # Critical, High, Medium, Low
        
        # Mapping lowercase/uppercase risks
        risk_map = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        for k, v in risk_counts.items():
            if str(k).lower() in risk_map:
                risk_map[str(k).lower()] += v
                
        # 4. Avg Stock Age
        avg_stock_age = df['days_in_inventory_90d'].median() if 'days_in_inventory_90d' in df.columns else 45
        
        # 5. Slow Moving Count
        slow_moving_count = (df['turnover_ratio_30d'] < 1.0).sum()
        
        # 6. ABC Counts
        if 'ABC_class' in df.columns:
            abc_counts = df['ABC_class'].value_counts().to_dict()
        else:
            abc_counts = {'A': 0, 'B': 0, 'C': 0}

        return {
            'service_level': round(service_level, 1),
            'turnover_ratio': round(weighted_turnover, 2),
            'stockout_risk': {
                'critical': risk_map['critical'],
                'high': risk_map['high'],
                'medium': risk_map['medium'],
                'total': risk_map['critical'] + risk_map['high'] + risk_map['medium']
            },
            'avg_stock_age': int(avg_stock_age),
            'total_products': total_items,
            'total_stock_value': float(total_weight),
            'slow_moving_count': int(slow_moving_count),
            'abc_breakdown': abc_counts
        }

    @classmethod
    def get_groups_list(cls):
        df = cls.load_products_data()
        if df.empty: return []
        return sorted(df['product_category'].dropna().unique().tolist())

    @classmethod
    def get_risk_distribution(cls, groups: List[str] = None):
        """Pie chart data equivalent"""
        df = cls.load_products_data()
        if groups and not df.empty:
            df = df[df['product_category'].isin(groups)]
            
        # Logic classify_health dari dashboard.py
        def classify_health(row):
            turnover = row.get('turnover_ratio_30d', 0)
            days = row.get('days_until_stockout', 99)
            if turnover > 2.0 and days > 30: return 'Healthy'
            elif turnover > 1.0 and days > 14: return 'Stable'
            elif turnover > 0.5 or days > 7: return 'Warning'
            else: return 'Critical'
            
        df['health_category'] = df.apply(classify_health, axis=1)
        counts = df['health_category'].value_counts()
        
        return [{'name': k, 'value': v, 'count': v} for k, v in counts.items()]

    @classmethod
    def get_top_alerts(cls, limit=20, groups: List[str] = None):
        """Alerts list with ABC class and full details"""
        df = cls.load_products_data()
        if df.empty: return [] # Return list kosong
        
        if groups:
            df = df[df['product_category'].isin(groups)]
            
        # Alert condition: Stockout < 30 days OR Turnover < 1.0
        alerts = df[
            (df['days_until_stockout'] < 30) | 
            (df['turnover_ratio_30d'] < 1.0)
        ].copy()
        
        alerts = alerts.sort_values('days_until_stockout', ascending=True).head(limit)
        
        results = []
        for _, row in alerts.iterrows():
            results.append({
                'product_code': row['product_code'],
                'product_name': row.get('product_name', 'Unknown'),
                'current_stock': int(row.get('current_stock_qty', 0)),
                'daily_demand': float(row.get('avg_daily_demand', 0)),
                'days_coverage': int(row.get('days_until_stockout', 0)),
                'risk_level': str(row.get('risk_class', 'Medium')).capitalize(),
                'abc_class': str(row.get('ABC_class', 'C')),
                'category': str(row.get('product_category', 'OTHER'))
            })
            
        return results

    @classmethod
    def get_top_moving_products(cls, limit=5, groups: List[str] = None):
        """Get top products by daily demand (Fast Moving)"""
        df = cls.load_products_data()
        if df.empty: return []

        if groups:
            df = df[df['product_category'].isin(groups)]

        # Sort by avg_daily_demand (descending)
        # Prioritize forecast_30d if available for better accuracy (like Streamlit)
        sort_col = 'forecast_30d' if 'forecast_30d' in df.columns else 'avg_daily_demand'
        
        # Ensure column exists and is numeric
        if sort_col not in df.columns:
            sort_col = 'avg_daily_demand'
            
        top_products = df.sort_values(sort_col, ascending=False).head(limit)
        
        results = []
        for _, row in top_products.iterrows():
            results.append({
                'product_code': row['product_code'],
                'product_name': row.get('product_name', 'Unknown'),
                'daily_demand': float(row.get(sort_col, 0)),
                'current_stock': int(row.get('current_stock_qty', 0))
            })
            
        return results

    @classmethod
    def get_abc_performance(cls, groups: List[str] = None):
        """
        Get Stock Value and Performance metrics grouped by ABC Class
        Replicates dashboard.py lines 917-977
        """
        df = cls.load_products_data()
        if df.empty: return []

        if groups:
            df = df[df['product_category'].isin(groups)]
            
        # Group by ABC class
        abc_perf = df.groupby('ABC_class').agg({
            'id': 'count',  # Product count
            'current_stock_qty': 'sum',
            'stock_value': 'sum',
            'avg_daily_demand': 'mean',
            'turnover_ratio_30d': 'mean'
        }).reset_index()
        
        results = []
        for _, row in abc_perf.iterrows():
            results.append({
                'abc_class': row['ABC_class'],
                'product_count': int(row['id']),
                'total_stock': int(row['current_stock_qty']),
                'stock_value': float(row['stock_value']),
                'avg_daily_demand': float(row['avg_daily_demand']),
                'turnover_ratio': float(row['turnover_ratio_30d'])
            })
            
        # Sort A, B, C order
        order = {'A': 0, 'B': 1, 'C': 2}
        results.sort(key=lambda x: order.get(x['abc_class'], 99))
        return results

    @classmethod
    def get_category_summary(cls, groups: List[str] = None):
        """
        Get Health Category Summary (Healthy, Stable, Warning, Critical)
        Replicates dashboard.py lines 575-590
        """
        df = cls.load_products_data()
        if df.empty: return []

        if groups:
            df = df[df['product_category'].isin(groups)]
        
        # Classify health
        def classify_health(row):
            turnover = row.get('turnover_ratio_30d', 0)
            days = row.get('days_until_stockout', 99)
            if turnover > 2.0 and days > 30: return 'Healthy'
            elif turnover > 1.0 and days > 14: return 'Stable'
            elif turnover > 0.5 or days > 7: return 'Warning'
            else: return 'Critical'
            
        df['health_category'] = df.apply(classify_health, axis=1)
        
        total = len(df)
        counts = df['health_category'].value_counts()
        
        results = []
        for cat in ['Healthy', 'Stable', 'Warning', 'Critical']:
            count = counts.get(cat, 0)
            results.append({
                'category': cat,
                'count': int(count),
                'percentage': round((count / total) * 100, 1) if total > 0 else 0
            })
            
        return results
