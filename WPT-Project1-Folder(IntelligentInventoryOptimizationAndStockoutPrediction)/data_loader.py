"""
🔄 Data Loader Module v3.2 - FIXED VERSION
✅ FIXED: Realistic DIO (Days Inventory Outstanding) Calculation
✅ FIXED: Product Category Extraction Enhancement
✅ NEW: Multi-method DIO calculation with fallback logic

Author: Data Science Team (Enhanced)
Date: 2025-11-18
Version: 3.2
"""

import pandas as pd
import numpy as np
import streamlit as st
import os
import logging
import re
from typing import Dict, List, Optional, Tuple
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataLoaderV3:
    """Enhanced data loader with fixed DIO calculation"""
    
    def __init__(self, data_dir: str = "data"):
        """Initialize data loader"""
        self.data_dir = data_dir
        self.master_df = None
        self.cache_time = None
    
    @st.cache_data(ttl=3600)
    def load_master_features(_self):
        """Load master features as primary source"""
        try:
            filepath = os.path.join(_self.data_dir, "master_features_final.csv")
            df = pd.read_csv(filepath)
            
            # Validate required columns
            required_cols = ['product_name', 'turnover_ratio_90d', 'stock_value', 'total_sales_90d', 
                           'current_stock_qty', 'avg_daily_demand', 'optimal_safety_stock', 'estimated_lead_time',
                           'ABC_class']
            
            for col in required_cols:
                if col not in df.columns:
                    logger.warning(f"⚠️ Column '{col}' not found. Filling with appropriate default.")
                    if col in ['turnover_ratio_90d', 'total_sales_90d', 'stock_value', 'avg_daily_demand']:
                        df[col] = 0.0
                    elif col in ['current_stock_qty', 'optimal_safety_stock', 'estimated_lead_time']:
                        df[col] = 0
                    else:
                        df[col] = np.nan
            
            logger.info(f"✅ Loaded master_features_final.csv: {df.shape}")
            return df
            
        except Exception as e:
            logger.error(f"❌ Error loading master features: {str(e)}")
            return None
    
    def calculate_realistic_dio(self, row):
        """
        🎯 FIXED: Calculate realistic Days Inventory Outstanding (DIO)
        
        Methods:
        1. If turnover_ratio_90d > 0: DIO = 90 / turnover_ratio_90d
        2. If stock_value > 0 and total_sales_90d > 0: DIO = 90 / (total_sales_90d / stock_value)
        3. Fallback by ABC class: A=30d, B=60d, C=90d
        """
        
        # Method 1: Use turnover ratio if valid
        turnover = row.get('turnover_ratio_90d', 0)
        if pd.notna(turnover) and turnover > 0:
            dio = 90 / turnover
            return min(dio, 365)  # Cap at 1 year maximum
        
        # Method 2: Use sales-to-stock ratio
        stock_value = row.get('stock_value', 0)
        total_sales = row.get('total_sales_90d', 0)
        
        if stock_value > 0 and total_sales > 0:
            # DIO = (Inventory Value / Cost of Goods Sold) × 90 days
            cogs_ratio = total_sales / stock_value
            dio = 90 / cogs_ratio
            return min(dio, 365)
        
        # Method 3: Fallback by ABC class
        abc_class = row.get('ABC_class', 'C')
        abc_dio_map = {'A': 30, 'B': 60, 'C': 90}
        return abc_dio_map.get(abc_class, 90)
    
    def extract_product_category(self, product_name: str) -> str:
        """Extract product category from product name"""
        if not isinstance(product_name, str):
            return "Other"
        
        # Look for brand prefixes (e.g., "RSMB-077", "Omada-050", "SonicWall-148")
        match = re.search(r'^([A-Za-z]+)', product_name.split('-')[0].split(' ')[0])
        
        if match:
            category = match.group(1).upper()
            
            # Map common variations
            if category.startswith("RG"): return "RSMB"
            if category.startswith("RENT"): return "SERVICE"
            if category.startswith("SONICWALL"): return "SONICWALL"
            if len(category) > 2 and category.isalnum():
                return category
        
        return "Other"
    
    @st.cache_data(ttl=3600)
    def load_supplementary_data(_self):
        """Load supplementary data files"""
        supplementary = {}
        
        files_to_load = [
            'Final_1_Optimization_Insights.csv',
            'Final_2_Metrics.csv',
            'Final_3_Sales_Details.csv',
            'Final_4_Current_Stocks.csv',
            'Final_5_Stock_Mutations.csv',
            'Final_6_Purchase_Details.csv',
            'alerts_2025-11-06.csv',
            'product_segments.csv'
        ]
        
        for filename in files_to_load:
            try:
                filepath = os.path.join(_self.data_dir, filename)
                if os.path.exists(filepath):
                    df = pd.read_csv(filepath)
                    supplementary[filename] = df
                    logger.info(f"✅ Loaded {filename}: {df.shape}")
            except Exception as e:
                logger.warning(f"⚠️ Could not load {filename}: {str(e)}")
        
        return supplementary
    
    def merge_data(self) -> pd.DataFrame:
        """Merge all data sources with FIXED DIO calculation"""
        try:
            # Load master features
            df = self.load_master_features()
            if df is None:
                return None
            
            # 🎯 ENHANCEMENT 1: Product Category Extraction
            df['product_category'] = df['product_name'].apply(self.extract_product_category)
            
            # 🎯 FIXED: Days Inventory Outstanding (DIO) Calculation
            df['days_in_inventory_90d'] = df.apply(self.calculate_realistic_dio, axis=1)
            
            # Validation: Ensure no negative or unrealistic values
            df['days_in_inventory_90d'] = df['days_in_inventory_90d'].clip(lower=1, upper=365)
            
            logger.info(f"DIO Statistics - Min: {df['days_in_inventory_90d'].min():.1f}, Max: {df['days_in_inventory_90d'].max():.1f}, Median: {df['days_in_inventory_90d'].median():.1f}")
            
            # Load supplementary data
            supp_data = self.load_supplementary_data()
            
            # Merge with alerts if available
            if 'alerts_2025-11-06.csv' in supp_data:
                alerts_df = supp_data['alerts_2025-11-06.csv']
                alerts_df = alerts_df.drop_duplicates(subset=['product_id'])
                df = df.merge(
                    alerts_df[['product_id', 'alert_type', 'message']],
                    on='product_id',
                    how='left'
                )
            
            # Merge with product segments if available
            if 'product_segments.csv' in supp_data:
                seg_df = supp_data['product_segments.csv']
                merge_cols_to_add = ['segment_label', 'ABC_class']
                
                cols_to_add = [
                    col for col in merge_cols_to_add 
                    if col in seg_df.columns and (col not in df.columns or df[col].isnull().sum() > len(df) * 0.5)
                ]
                
                if cols_to_add:
                    cols_to_merge = ['product_id'] + cols_to_add
                    
                    df = df.merge(
                        seg_df[cols_to_merge].drop_duplicates(subset=['product_id']),
                        on='product_id',
                        how='left',
                        suffixes=('', '_seg')
                    )
            
            logger.info(f"✅ Merged dataset shape: {df.shape}")
            logger.info(f"✅ Product categories: {df['product_category'].nunique()}")
            return df
        
        except Exception as e:
            logger.error(f"❌ Error merging data: {str(e)}")
            return None
    
    def get_abc_distribution(self, df: pd.DataFrame) -> Dict:
        """Get ABC class distribution"""
        if df is None or 'ABC_class' not in df.columns:
            return {}
        
        return df['ABC_class'].value_counts().to_dict()
    
    def get_segment_distribution(self, df: pd.DataFrame) -> Dict:
        """Get segment distribution"""
        if df is None or 'segment_label' not in df.columns:
            return {}
        
        return df['segment_label'].value_counts().to_dict()
    
    def search_products(self, df: pd.DataFrame, query: str) -> pd.DataFrame:
        """Search products by name or code"""
        if df is None or query == "":
            return df
        
        query_lower = query.lower()
        mask = (
            df['product_code'].str.lower().str.contains(query_lower, na=False) |
            df['product_name'].str.lower().str.contains(query_lower, na=False)
        )
        return df[mask]
    
    def filter_products(self, df: pd.DataFrame, filters: Dict) -> pd.DataFrame:
        """Filter products by multiple criteria"""
        if df is None:
            return df
        
        result = df.copy()
        
        # Filter by ABC class
        if 'abc_class' in filters and filters['abc_class']:
            result = result[result['ABC_class'].isin(filters['abc_class'])]
        
        # Filter by segment
        if 'segment' in filters and filters['segment']:
            result = result[result['segment_label'].isin(filters['segment'])]
        
        # Filter by stock level
        if 'min_stock' in filters and filters['min_stock'] is not None:
            result = result[result['current_stock_qty'] >= filters['min_stock']]
        
        if 'max_stock' in filters and filters['max_stock'] is not None:
            result = result[result['current_stock_qty'] <= filters['max_stock']]
        
        # Filter by demand
        if 'min_demand' in filters and filters['min_demand'] is not None:
            result = result[result['avg_daily_demand'] >= filters['min_demand']]
        
        if 'max_demand' in filters and filters['max_demand'] is not None:
            result = result[result['avg_daily_demand'] <= filters['max_demand']]
        
        return result
    
    def sort_products(self, df: pd.DataFrame, sort_by: str, ascending: bool = False) -> pd.DataFrame:
        """Sort products"""
        if df is None or sort_by not in df.columns:
            return df
        
        return df.sort_values(by=sort_by, ascending=ascending)
    
    def get_summary_statistics(self, df: pd.DataFrame) -> Dict:
        """Calculate summary statistics"""
        if df is None or len(df) == 0:
            return {}
        
        stats = {
            'total_products': len(df),
            'total_stock_value': df['stock_value'].sum(),
            'avg_daily_demand': df['avg_daily_demand'].mean(),
            'total_sales_90d': df['total_sales_90d'].sum(),
            'avg_turnover': df['turnover_ratio_90d'].mean(),
            'products_with_stock': (df['current_stock_qty'] > 0).sum(),
            'stockout_products': (df['current_stock_qty'] == 0).sum(),
            'abc_a_count': (df['ABC_class'] == 'A').sum(),
            'abc_b_count': (df['ABC_class'] == 'B').sum(),
            'abc_c_count': (df['ABC_class'] == 'C').sum(),
            'avg_dio': df['days_in_inventory_90d'].median(),  # NEW: Average DIO
        }
        
        return stats

# Global instance
_loader = None

def get_loader() -> DataLoaderV3:
    """Get or create loader instance"""
    global _loader
    if _loader is None:
        _loader = DataLoaderV3()
    return _loader

def load_all_data() -> pd.DataFrame:
    """Load and merge all data"""
    loader = get_loader()
    return loader.merge_data()

def get_abc_distribution() -> Dict:
    """Get ABC distribution"""
    loader = get_loader()
    df = load_all_data()
    return loader.get_abc_distribution(df)

def get_segment_distribution() -> Dict:
    """Get segment distribution"""
    loader = get_loader()
    df = load_all_data()
    return loader.get_segment_distribution(df)

if __name__ == "__main__":
    loader = DataLoaderV3()
    df = loader.merge_data()
    if df is not None:
        print(f"✅ Loaded {len(df)} products")
        print(f"✅ Product categories: {df['product_category'].nunique()}")
        print(f"✅ ABC Distribution: {loader.get_abc_distribution(df)}")
        print(f"✅ Segment Distribution: {loader.get_segment_distribution(df)}")
        print(f"✅ Average DIO (Median): {df['days_in_inventory_90d'].median():.1f} days")
        print(f"✅ DIO Range: {df['days_in_inventory_90d'].min():.1f} - {df['days_in_inventory_90d'].max():.1f} days")
    else:
        print("❌ Data loading failed.")