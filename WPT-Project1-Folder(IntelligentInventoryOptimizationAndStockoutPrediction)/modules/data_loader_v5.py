"""
Dashboard Data Loader V5
=========================

Loads data from new module outputs and provides:
1. Filtering (removes dummy/umum/jasa items)
2. Group extraction from item codes (prefix before '-')
3. Group normalization (H_DATACOMM = H_DATACOM, etc.)
4. Merged data from all modules

Author: AI Assistant
Date: January 2026
Version: 5.0.0
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
import json
from typing import Dict, Optional, Tuple, List

logger = logging.getLogger(__name__)


# =============================================================================
# GROUP NORMALIZATION MAPPING
# =============================================================================

GROUP_NORMALIZATION = {
    # H_ prefix normalizations
    'H_DATACOMM': 'H_DATACOM',
    'H_DATACOM': 'H_DATACOM',
    'H3C1': 'H3C',
    'H3C': 'H3C',
    'HUAWEI': 'HUAWEI',
    
    # TP-Link variations
    'TPLK': 'TPLINK',
    'TLTO': 'TPLINK',
    'TPLINK': 'TPLINK',
    
    # Others
    'ONE ': 'ONE',
    'ONE': 'ONE',
    'GIGA': 'GIGA',
    'OMADA': 'OMADA',
    'RENT': 'RENT',
    'RSMB': 'RSMB',
    'SANGFOR': 'SANGFOR',
    'SONICWALL': 'SONICWALL',
    'QUEST': 'QUEST',
    'ALTAI': 'ALTAI',
    'ROBUSTEL': 'ROBUSTEL',
    'GROUP': 'GROUP',
}

# Words/patterns to filter out from item no/name
FILTER_WORDS = ['dummy', 'umum', 'jasa', 'test', 'sample']

# Numeric-only groups to filter out
FILTER_NUMERIC_GROUPS = True  # Filter out groups that are just numbers


# =============================================================================
# DATA LOADER CLASS
# =============================================================================

class DashboardDataLoaderV5:
    """Load and preprocess data from all modules for dashboard"""
    
    def __init__(self, base_path: str = None):
        if base_path:
            self.base_path = Path(base_path)
        else:
            # Auto-detect base path
            self.base_path = Path(__file__).parent.parent
        
        self.data_paths = {
            'features': self.base_path / 'data' / 'features' / 'master_features.csv',
            'forecasts': self.base_path / 'data' / 'forecasts' / 'forecast_summary.csv',
            'predictions': self.base_path / 'data' / 'predictions' / 'stockout_predictions.csv',
            'reorder': self.base_path / 'data' / 'reorder' / 'reorder_optimization.csv',
            'slow_moving': self.base_path / 'data' / 'slow_moving' / 'slow_moving_analysis.csv',
            'alerts': self.base_path / 'data' / 'predictions' / 'stockout_alerts.json',
            'lead_times': self.base_path / 'data' / 'features' / 'product_lead_times.csv',
        }
        
        self._cache = {}
    
    def load_all_data(self, apply_filters: bool = True) -> pd.DataFrame:
        """Load and merge all module data"""
        logger.info("Loading dashboard data from all modules...")
        
        # Load master features as base
        df = self._load_features()
        
        if df.empty:
            logger.error("Failed to load master features")
            return pd.DataFrame()
        
        # Extract and normalize groups
        df = self._extract_groups(df)
        
        # Apply filters (remove dummy/umum/jasa)
        if apply_filters:
            df = self._apply_filters(df)
        
        # Merge with other module outputs
        df = self._merge_forecasts(df)
        df = self._merge_predictions(df)
        df = self._merge_reorder(df)
        df = self._merge_slow_moving(df)
        df = self._merge_lead_times(df)
        
        # Apply column aliasing for dashboard compatibility
        df = self._apply_column_aliases(df)
        
        logger.info(f"Loaded {len(df)} items with {len(df.columns)} columns")
        
        return df
    
    def _apply_column_aliases(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply column aliases for backward compatibility with dashboard"""
        df = df.copy()
        
        # Column mappings: new_name -> dashboard_expected_name
        column_aliases = {
            # Core identifiers
            'no': 'product_code',
            'name': 'product_name',
            
            # Stock columns
            'current_stock': 'current_stock_qty',
            
            # Demand columns - handle duplicates
            'avg_daily_demand_x': 'avg_daily_demand',
            
            # Turnover columns
            'turnover_ratio': 'turnover_ratio_90d',
            
            # Classification
            'abc_class': 'ABC_class',
            'item_group_normalized': 'product_category',
            
            # Safety stock from reorder
            'safety_stock_optimized': 'optimal_safety_stock',
            
            # Stock value calculation
            'annual_value': 'stock_value',
        }
        
        for old_col, new_col in column_aliases.items():
            if old_col in df.columns and new_col not in df.columns:
                df[new_col] = df[old_col]
        
        # Calculate missing derived columns
        
        # turnover_ratio_30d from turnover_ratio (annual to 30-day)
        if 'turnover_ratio' in df.columns and 'turnover_ratio_30d' not in df.columns:
            df['turnover_ratio_30d'] = df['turnover_ratio'] / 12  # Monthly
        
        # days_in_inventory_90d from days_in_inventory
        if 'days_in_inventory' in df.columns and 'days_in_inventory_90d' not in df.columns:
            df['days_in_inventory_90d'] = df['days_in_inventory'].clip(upper=90)
        
        # stock_value from current_stock * avgCost
        if 'stock_value' not in df.columns:
            stock = df.get('current_stock', df.get('current_stock_qty', 0)).fillna(0)
            cost = df.get('avgCost', 1000).fillna(1000)
            df['stock_value'] = stock * cost
        
        # total_sales_90d from total_qty_sold
        if 'total_sales_90d' not in df.columns and 'total_qty_sold' in df.columns:
            df['total_sales_90d'] = df['total_qty_sold']  # Assuming pulled data covers ~90 days
        
        # Ensure avg_daily_demand exists (use y version if x doesn't exist)
        if 'avg_daily_demand' not in df.columns:
            if 'avg_daily_demand_y' in df.columns:
                df['avg_daily_demand'] = df['avg_daily_demand_y']
            else:
                df['avg_daily_demand'] = 0
        
        # Fill NaN in critical columns
        df['days_until_stockout'] = df.get('days_until_stockout', 30).fillna(30)
        df['turnover_ratio_90d'] = df.get('turnover_ratio_90d', df.get('turnover_ratio', 1)).fillna(1)
        df['stock_value'] = df['stock_value'].fillna(0)
        
        return df
    
    def _load_features(self) -> pd.DataFrame:
        """Load master features"""
        path = self.data_paths['features']
        
        if path.exists():
            df = pd.read_csv(path, encoding='utf-8-sig')
            logger.info(f"  Loaded features: {len(df)} items")
            return df
        
        logger.warning(f"  Features not found: {path}")
        return pd.DataFrame()
    
    def _extract_groups(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract item group from 'no' column and normalize"""
        df = df.copy()
        
        # Extract prefix before '-'
        df['item_group'] = df['no'].astype(str).str.split('-').str[0].str.strip()
        
        # Normalize groups with better logic
        def normalize_group(x):
            if pd.isna(x) or x == '' or x == 'nan':
                return 'OTHER'
            
            x_upper = x.strip().upper()
            
            # Filter out numeric-only groups (100028, etc)
            if x_upper.isdigit():
                return 'NUMERIC_CODE'
            
            # Filter out groups starting with numbers
            if x_upper and x_upper[0].isdigit():
                return 'NUMERIC_CODE'
            
            # Filter out groups with parentheses or brackets
            if '(' in x_upper or ')' in x_upper or '[' in x_upper or ']' in x_upper:
                return 'OTHER'
            
            # Filter out single-letter groups (like just 'H')
            if len(x_upper) <= 1:
                return 'OTHER'
            
            # Filter out 'NON' and similar
            if x_upper in ['NON', 'NA', 'N/A', 'NAN']:
                return 'OTHER'
            
            # Apply normalization mapping
            return GROUP_NORMALIZATION.get(x_upper, x_upper)
        
        df['item_group_normalized'] = df['item_group'].apply(normalize_group)
        
        # Count groups
        group_counts = df['item_group_normalized'].value_counts()
        logger.info(f"  Extracted {len(group_counts)} item groups")
        
        return df
    
    def _apply_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter out dummy/umum/jasa items"""
        original_count = len(df)
        
        # Create filter mask
        mask = pd.Series([False] * len(df), index=df.index)
        
        for word in FILTER_WORDS:
            if 'no' in df.columns:
                mask |= df['no'].astype(str).str.lower().str.contains(word, na=False)
            if 'name' in df.columns:
                mask |= df['name'].astype(str).str.lower().str.contains(word, na=False)
            if 'item_group_normalized' in df.columns:
                mask |= df['item_group_normalized'].str.lower().str.contains(word, na=False)
        
        # Apply filter (keep items that DON'T match)
        df_filtered = df[~mask].copy()
        
        removed_count = original_count - len(df_filtered)
        logger.info(f"  Filtered out {removed_count} items (dummy/umum/jasa/test/sample)")
        
        return df_filtered
    
    def _merge_forecasts(self, df: pd.DataFrame) -> pd.DataFrame:
        """Merge forecast data"""
        path = self.data_paths['forecasts']
        
        if path.exists():
            forecasts = pd.read_csv(path, encoding='utf-8-sig')
            
            if 'item_id' in forecasts.columns:
                # Rename to avoid conflicts
                forecast_cols = {
                    'next_7_days_avg': 'forecast_7d',
                    'next_30_days_avg': 'forecast_30d',
                    'model': 'forecast_model',
                    'mape': 'forecast_mape'
                }
                
                forecasts = forecasts.rename(columns=forecast_cols)
                
                merge_cols = ['item_id'] + [c for c in forecast_cols.values() if c in forecasts.columns]
                
                df = df.merge(
                    forecasts[merge_cols],
                    left_on='id',
                    right_on='item_id',
                    how='left'
                )
                
                logger.info(f"  Merged forecasts: {len(forecasts)} items")
        
        return df
    
    def _merge_predictions(self, df: pd.DataFrame) -> pd.DataFrame:
        """Merge stockout predictions"""
        path = self.data_paths['predictions']
        
        if path.exists():
            predictions = pd.read_csv(path, encoding='utf-8-sig')
            
            if 'id' in predictions.columns:
                pred_cols = ['id', 'risk_score', 'risk_class', 'reorder_urgency', 
                            'expected_stockout_date', 'stockout_probability']
                
                available_cols = [c for c in pred_cols if c in predictions.columns]
                
                df = df.merge(
                    predictions[available_cols],
                    on='id',
                    how='left',
                    suffixes=('', '_pred')
                )
                
                logger.info(f"  Merged predictions: {len(predictions)} items")
        
        return df
    
    def _merge_reorder(self, df: pd.DataFrame) -> pd.DataFrame:
        """Merge reorder optimization"""
        path = self.data_paths['reorder']
        
        if path.exists():
            reorder = pd.read_csv(path, encoding='utf-8-sig')
            
            if 'id' in reorder.columns:
                reorder_cols = ['id', 'eoq_optimized', 'safety_stock_optimized', 
                               'reorder_point_optimized', 'lead_time_days']
                
                available_cols = [c for c in reorder_cols if c in reorder.columns]
                
                # Only merge columns that don't already exist
                new_cols = [c for c in available_cols if c not in df.columns or c == 'id']
                
                if len(new_cols) > 1:  # More than just 'id'
                    df = df.merge(
                        reorder[new_cols],
                        on='id',
                        how='left',
                        suffixes=('', '_reorder')
                    )
                    
                    logger.info(f"  Merged reorder: {len(reorder)} items")
        
        return df
    
    def _merge_slow_moving(self, df: pd.DataFrame) -> pd.DataFrame:
        """Merge slow-moving analysis"""
        path = self.data_paths['slow_moving']
        
        if path.exists():
            slow_moving = pd.read_csv(path, encoding='utf-8-sig')
            
            if 'id' in slow_moving.columns:
                sm_cols = ['id', 'movement_class', 'days_since_last_sale', 
                          'aging_bucket', 'recommendation', 'markdown_rate',
                          'priority_score']
                
                available_cols = [c for c in sm_cols if c in slow_moving.columns]
                new_cols = [c for c in available_cols if c not in df.columns or c == 'id']
                
                if len(new_cols) > 1:
                    df = df.merge(
                        slow_moving[new_cols],
                        on='id',
                        how='left',
                        suffixes=('', '_sm')
                    )
                    
                    logger.info(f"  Merged slow-moving: {len(slow_moving)} items")
        
        return df
    
    def _merge_lead_times(self, df: pd.DataFrame) -> pd.DataFrame:
        """Merge lead time data"""
        path = self.data_paths['lead_times']
        
        if path.exists():
            lead_times = pd.read_csv(path, encoding='utf-8-sig')
            
            if 'item_id' in lead_times.columns:
                lt_cols = ['item_id', 'lead_time_median']
                available_cols = [c for c in lt_cols if c in lead_times.columns]
                
                if 'lead_time_days' not in df.columns and len(available_cols) > 1:
                    lead_times = lead_times.rename(columns={'lead_time_median': 'lead_time_days_calc'})
                    
                    df = df.merge(
                        lead_times[['item_id', 'lead_time_days_calc']],
                        left_on='id',
                        right_on='item_id',
                        how='left'
                    )
                    
                    logger.info(f"  Merged lead times: {len(lead_times)} items")
        
        return df
    
    def get_available_groups(self, df: pd.DataFrame = None) -> List[str]:
        """Get list of available item groups for filtering"""
        if df is None:
            df = self.load_all_data()
        
        if 'item_group_normalized' in df.columns:
            groups = df['item_group_normalized'].dropna().unique().tolist()
            return sorted(groups)
        
        return []
    
    def load_alerts(self) -> List[Dict]:
        """Load stockout alerts"""
        path = self.data_paths['alerts']
        
        if path.exists():
            with open(path, 'r') as f:
                alerts = json.load(f)
                return alerts if isinstance(alerts, list) else alerts.get('alerts', [])
        
        return []
    
    def get_summary_stats(self, df: pd.DataFrame = None) -> Dict:
        """Get summary statistics for dashboard"""
        if df is None:
            df = self.load_all_data()
        
        stats = {
            'total_items': len(df),
            'total_groups': df['item_group_normalized'].nunique() if 'item_group_normalized' in df.columns else 0,
            'with_forecast': (df['forecast_30d'].notna()).sum() if 'forecast_30d' in df.columns else 0,
            'critical_risk': (df['risk_class'] == 'critical').sum() if 'risk_class' in df.columns else 0,
            'dead_stock': (df['movement_class'] == 'Dead Stock').sum() if 'movement_class' in df.columns else 0,
            'slow_moving': (df['movement_class'] == 'Slow Moving').sum() if 'movement_class' in df.columns else 0,
        }
        
        return stats


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def load_all_data(apply_filters: bool = True) -> pd.DataFrame:
    """Convenience function to load all data"""
    loader = DashboardDataLoaderV5()
    return loader.load_all_data(apply_filters=apply_filters)


def get_available_groups() -> List[str]:
    """Get available item groups"""
    loader = DashboardDataLoaderV5()
    return loader.get_available_groups()


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    loader = DashboardDataLoaderV5(base_path="../")
    df = loader.load_all_data()
    
    print("\n" + "=" * 50)
    print("DASHBOARD DATA LOADER V5 - SUMMARY")
    print("=" * 50)
    print(f"Total items: {len(df)}")
    print(f"Columns: {len(df.columns)}")
    print()
    print("Item Groups (Top 20):")
    print(df['item_group_normalized'].value_counts().head(20).to_string())
    print()
    print("Summary Stats:")
    print(loader.get_summary_stats(df))
