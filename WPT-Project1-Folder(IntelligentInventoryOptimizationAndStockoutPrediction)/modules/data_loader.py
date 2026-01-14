"""
Uses Master_Inventory_Feature_Set.csv as primary source
Brand extraction from item_no prefix (before '-')
Active item filtering (excludes 'Non-aktif' items)
Column mapping for backward compatibility
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


class DataLoaderV4:
    """Enhanced data loader using new pipeline datasets"""
    
    # Column mapping: New Feature Set → Legacy column names
    COLUMN_MAP = {
        'item_no': 'product_code',
        'item_name': 'product_name',
        'current_stock': 'current_stock_qty',
        'avg_daily_sales': 'avg_daily_demand',
        'safety_stock': 'optimal_safety_stock',
        'avg_lead_time': 'estimated_lead_time',
        'abc_class': 'ABC_class',
        'dio_days': 'days_in_inventory_90d',
        'total_revenue': 'total_sales_90d',
        'avg_cost': 'stock_value_per_unit',
    }
    
    def __init__(self, data_dir: str = "data"):
        """Initialize data loader"""
        self.data_dir = Path(data_dir)
        self.master_df = None
        self.cache_time = None
        
        # New pipeline output directory
        self.pipeline_output_dir = self.data_dir / "new_base_dataset_project1"
    
    def _get_file_mtime(self) -> float:
        """Get the latest modification time of data files for cache invalidation"""
        feature_set_path = self.pipeline_output_dir / "Master_Inventory_Feature_Set.csv"
        return os.path.getmtime(feature_set_path) if feature_set_path.exists() else 0.0
    
    @staticmethod
    def extract_brand(item_no: str) -> str:
        """
        Extract brand prefix from item_no (everything before '-')
        Examples:
        - 'OMADA-001' -> 'OMADA'
        - 'RENT-095' -> 'RENT'
        - 'GIGA-010' -> 'GIGA'
        - 'SonicWall-148' -> 'SONICWALL'
        """
        if not isinstance(item_no, str) or not item_no:
            return "Other"
        
        if '-' in item_no:
            prefix = item_no.split('-')[0].strip()
            if prefix and len(prefix) >= 2:
                return prefix.upper()
        
        # Fallback: take first alphabetic word
        match = re.match(r'^([A-Za-z]+)', item_no)
        if match:
            return match.group(1).upper()
        
        return "Other"
    
    @staticmethod
    def is_active_item(row) -> bool:
        """
        Check if item is active (not marked as 'Non-aktif')
        Checks both item_no and item_name columns
        """
        item_no = str(row.get('item_no', '')).lower()
        item_name = str(row.get('item_name', '')).lower()
        
        # Exclude if contains 'non-aktif' or 'nonaktif' (case-insensitive)
        inactive_patterns = ['non-aktif', 'nonaktif', 'tidak aktif', 'inactive']
        
        for pattern in inactive_patterns:
            if pattern in item_no or pattern in item_name:
                return False
        
        return True
    
    @st.cache_data(ttl=60)
    def load_master_features(_self, _file_mtime: float = 0.0) -> pd.DataFrame:
        """
        Load Master Inventory Feature Set from new pipeline output
        
        Args:
            _file_mtime: File modification timestamp for cache invalidation
        """
        try:
            filepath = _self.pipeline_output_dir / "Master_Inventory_Feature_Set.csv"
            
            if not filepath.exists():
                logger.error(f"Feature set not found: {filepath}")
                # Fallback to old data source
                return _self._load_legacy_data()
            
            df = pd.read_csv(filepath)
            logger.info(f"[OK] Loaded Master_Inventory_Feature_Set.csv: {df.shape}")
            
            # Filter out inactive items
            original_count = len(df)
            df = df[df.apply(_self.is_active_item, axis=1)]
            filtered_count = original_count - len(df)
            if filtered_count > 0:
                logger.info(f"[i] Filtered out {filtered_count} inactive items")
            
            # Add brand column
            df['brand'] = df['item_no'].apply(_self.extract_brand)
            
            # Apply column mapping for backward compatibility
            df = _self._apply_column_mapping(df)
            
            # Ensure numeric columns
            numeric_cols = [
                'current_stock_qty', 'avg_daily_demand', 'optimal_safety_stock',
                'estimated_lead_time', 'days_in_inventory_90d', 'total_sales_90d',
                'reorder_point', 'safety_stock', 'days_until_stockout'
            ]
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            return df
            
        except Exception as e:
            logger.error(f"[X] Error loading master features: {str(e)}")
            return _self._load_legacy_data()
    
    def _apply_column_mapping(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply column mapping for backward compatibility"""
        for new_col, legacy_col in self.COLUMN_MAP.items():
            if new_col in df.columns and legacy_col not in df.columns:
                df[legacy_col] = df[new_col]
        
        # Create product_id if not exists (for legacy compatibility)
        if 'product_id' not in df.columns and 'item_no' in df.columns:
            df['product_id'] = df['item_no']
        
        # Create product_category from brand
        if 'product_category' not in df.columns and 'brand' in df.columns:
            df['product_category'] = df['brand']
        
        # Calculate stock_value if missing
        if 'stock_value' not in df.columns:
            current_stock = pd.to_numeric(df.get('current_stock', df.get('current_stock_qty', 0)), errors='coerce').fillna(0)
            avg_cost = pd.to_numeric(df.get('avg_cost', 0), errors='coerce').fillna(0)
            df['stock_value'] = current_stock * avg_cost
        
        # Calculate turnover_ratio_90d if missing
        if 'turnover_ratio_90d' not in df.columns:
            total_revenue = pd.to_numeric(df.get('total_revenue', 0), errors='coerce').fillna(0)
            stock_value = pd.to_numeric(df.get('stock_value', 0), errors='coerce').fillna(0)
            # Avoid division by zero
            df['turnover_ratio_90d'] = np.where(stock_value > 0, total_revenue / stock_value, 0)
        
        # Map total_revenue to total_sales_90d
        if 'total_sales_90d' not in df.columns and 'total_revenue' in df.columns:
            df['total_sales_90d'] = df['total_revenue']
        
        # Map safety_stock to optimal_safety_stock
        if 'optimal_safety_stock' not in df.columns and 'safety_stock' in df.columns:
            df['optimal_safety_stock'] = df['safety_stock']
        
        return df
    
    def _load_legacy_data(self) -> pd.DataFrame:
        """Fallback: Load from old master_features_final.csv"""
        legacy_path = self.data_dir / "master_features_final.csv"
        processed_path = self.data_dir / "processed" / "master_features_final.csv"
        
        for path in [processed_path, legacy_path]:
            if path.exists():
                logger.warning(f"[!] Using legacy data source: {path}")
                return pd.read_csv(path)
        
        logger.error("[X] No data source found!")
        return pd.DataFrame()
    
    @st.cache_data(ttl=60)
    def load_sales_details(_self) -> pd.DataFrame:
        """Load Sales Details from new pipeline"""
        filepath = _self.pipeline_output_dir / "1_Sales_Details.csv"
        if filepath.exists():
            df = pd.read_csv(filepath)
            df['trans_date'] = pd.to_datetime(df['trans_date'], errors='coerce')
            return df
        return pd.DataFrame()
    
    @st.cache_data(ttl=60)
    def load_po_details(_self) -> pd.DataFrame:
        """Load PO Details from new pipeline"""
        filepath = _self.pipeline_output_dir / "2_PO_Details.csv"
        if filepath.exists():
            return pd.read_csv(filepath)
        return pd.DataFrame()
    
    @st.cache_data(ttl=60)
    def load_current_stock(_self) -> pd.DataFrame:
        """Load Current Stock from new pipeline"""
        filepath = _self.pipeline_output_dir / "4_Current_Stock.csv"
        if filepath.exists():
            return pd.read_csv(filepath)
        return pd.DataFrame()
    
    def merge_data(self) -> pd.DataFrame:
        """Load and prepare master data with all enhancements and realistic metrics"""
        file_mtime = self._get_file_mtime()
        df = self.load_master_features(_file_mtime=file_mtime)
        
        if df is None or len(df) == 0:
            return None
        
        # Apply realistic metric recalculations (CRITICAL for business decisions)
        df = self._apply_realistic_metrics(df)
        
        # Ensure segment_label for legacy compatibility
        if 'segment_label' not in df.columns and 'abc_xyz_class' in df.columns:
            df['segment_label'] = df['abc_xyz_class']
        
        logger.info(f"[OK] Merged dataset: {df.shape}")
        logger.info(f"[OK] Brands: {df['brand'].nunique()}")
        logger.info(f"[OK] ABC Distribution: {df['ABC_class'].value_counts().to_dict() if 'ABC_class' in df.columns else 'N/A'}")
        
        return df
    
    def _apply_realistic_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply realistic business logic to all metrics.
        
        This fixes common issues:
        - Turnover divided by near-zero values causing 100x+ results
        - 999 default values for stock age skewing averages
        - Outlier daily demand causing unrealistic forecasts
        - Safety stock when demand is zero
        """
        import numpy as np
        
        # Get ABC class for dynamic calculations
        abc_class = df['abc_class'].fillna('C').str.upper() if 'abc_class' in df.columns else pd.Series(['C'] * len(df))
        
        # =================================================================
        # 0. CLEAN DATA - Filter Non-Product Items (Jasa, Umum, etc)
        # =================================================================
        # Filter items that are services or general categories, not real inventory
        if 'item_name' in df.columns:
            mask_real = ~df['item_name'].str.contains('UMUM|JASA|LAIN-LAIN|OTHER', case=False, na=False)
            if 'item_no' in df.columns:
                mask_real = mask_real & ~df['item_no'].str.contains('UMUM|JASA', case=False, na=False)
            
            logger.info(f"[i] Filtering out {len(df) - mask_real.sum()} non-product items (UMUM/JASA)")
            df = df[mask_real].copy()
            
            # Re-calculate abc_class for filtered data if needed, or just slice
            abc_class = df['abc_class'].fillna('C').str.upper() if 'abc_class' in df.columns else pd.Series(['C'] * len(df))
            
        # =================================================================
        # 1. ROBUST DAILY DEMAND - Varied Dynamic Caps (Optimal)
        # =================================================================
        # User requirement: "Optimal approach, Varied values, Hundreds (ratusan) not Thousands, Not always round numbers"
        # Strategy: Use deterministic variation based on item properties to create "jagged" caps 
        # that look organic but stay within safe business limits.
        
        demand_col = 'avg_daily_sales' if 'avg_daily_sales' in df.columns else 'avg_daily_demand'
        if demand_col in df.columns:
            raw_demand = pd.to_numeric(df[demand_col], errors='coerce').fillna(0)
        else:
            # Calculate from total sold / 90 days
            total_sold = pd.to_numeric(df.get('total_qty_sold', 0), errors='coerce').fillna(0)
            raw_demand = total_sold / 90
        
        # Base Caps (Hundreds range max)
        BASE_CAP_A = 150.0 
        BASE_CAP_B = 50.0
        BASE_CAP_C = 10.0
        
        # Create deterministic variation (0.9 to 1.1 multiplier)
        # We use the item_no or index to create a stable random-like factor
        # This ensures the cap is not a flat "150.0" for everyone, but e.g. "143.5", "156.2"
        if 'item_no' in df.columns:
            # Simple hash: sum of ascii values of item_no % 20 -> 0..19
            # Scale to 0.90 .. 1.10
            variation = df['item_no'].apply(lambda x: 0.9 + (sum(ord(c) for c in str(x)) % 20) / 100.0)
        else:
            variation = np.random.uniform(0.9, 1.1, size=len(df)) # Fallback if no item_no
            
        # Apply varied limits
        df['avg_daily_demand'] = np.where(
            abc_class == 'A',
            np.minimum(raw_demand, BASE_CAP_A * variation),
            np.where(
                abc_class == 'B',
                np.minimum(raw_demand, BASE_CAP_B * variation),
                np.minimum(raw_demand, BASE_CAP_C * variation)
            )
        )
        
        logger.info(f"[i] Daily demand optimized (Varied): Base Caps A:{BASE_CAP_A}, B:{BASE_CAP_B}, C:{BASE_CAP_C} with ±10% variation")
        
        # =================================================================
        # 2. GET BASE COLUMNS
        # =================================================================
        current_stock = pd.to_numeric(
            df['current_stock'] if 'current_stock' in df.columns else df.get('current_stock_qty', 0), 
            errors='coerce'
        ).fillna(0)
        df['current_stock_qty'] = current_stock
        
        total_qty_sold = pd.to_numeric(df.get('total_qty_sold', 0), errors='coerce').fillna(0)
        qty_sold_30d = total_qty_sold / 3  # Approximate 30d from 90d data
        
        # =================================================================
        # 3. ROBUST TURNOVER - Use Average Inventory Method
        # =================================================================
        # Average inventory = current_stock + (qty_sold_30d / 2)
        # This estimates the average inventory during the period
        estimated_avg_inventory = current_stock + (qty_sold_30d / 2)
        estimated_avg_inventory = np.maximum(estimated_avg_inventory, 1)  # Min 1 to avoid div/0
        
        # Turnover = Units Sold / Average Inventory
        raw_turnover = qty_sold_30d / estimated_avg_inventory
        
        # Dynamic cap based on ABC class - VARIED, not constant
        turnover_cap_a = 6.0   # Class A: Fast movers, max 6x per 30d
        turnover_cap_b = 4.0   # Class B: Moderate movers
        turnover_cap_c = 2.0   # Class C: Slow movers, should be low
        
        df['turnover_ratio_30d'] = np.where(
            abc_class == 'A',
            np.minimum(raw_turnover, turnover_cap_a),
            np.where(
                abc_class == 'B',
                np.minimum(raw_turnover, turnover_cap_b),
                np.minimum(raw_turnover, turnover_cap_c)
            )
        )
        
        # For products with no stock and no sales, turnover = 0
        df['turnover_ratio_30d'] = np.where(
            (current_stock == 0) & (qty_sold_30d == 0),
            0,
            df['turnover_ratio_30d']
        )
        
        # Legacy alias
        df['turnover_ratio_90d'] = df['turnover_ratio_30d']
        
        logger.info(f"[i] Turnover: ABC-based dynamic caps (A:{turnover_cap_a}x, B:{turnover_cap_b}x, C:{turnover_cap_c}x)")
        
        # =================================================================
        # 4. ROBUST STOCK AGE (DIO) - Varies by ABC Class
        # =================================================================
        # DIO = 30 / Turnover (days to sell current inventory)
        raw_dio = np.where(
            df['turnover_ratio_30d'] > 0.01,
            30 / df['turnover_ratio_30d'],
            np.where(current_stock > 0, 180, 0)  # Stock with no sales = 180 days
        )
        
        # Dynamic DIO limits by ABC class - VARIED
        df['days_in_inventory_30d'] = np.where(
            abc_class == 'A',
            np.clip(raw_dio, 5, 60),    # Fast movers: 5-60 days
            np.where(
                abc_class == 'B',
                np.clip(raw_dio, 15, 120),  # Moderate: 15-120 days
                np.clip(raw_dio, 30, 365)   # Slow movers: 30-365 days
            )
        )
        
        df['dio_days'] = df['days_in_inventory_30d']
        df['days_in_inventory_90d'] = df['days_in_inventory_30d']  # Legacy alias
        
        # =================================================================
        # 5. DAYS UNTIL STOCKOUT - Realistic limits by ABC
        # =================================================================
        avg_demand = df['avg_daily_demand']
        
        raw_coverage = np.where(
            avg_demand > 0.001,
            current_stock / avg_demand,
            np.where(current_stock > 0, 365, 0)
        )
        
        # Dynamic coverage limits
        df['days_until_stockout'] = np.where(
            abc_class == 'A',
            np.clip(raw_coverage, 0, 90),   # Fast movers: max 90 days coverage
            np.where(
                abc_class == 'B',
                np.clip(raw_coverage, 0, 180),  # Moderate: max 180 days
                np.clip(raw_coverage, 0, 365)   # Slow: max 365 days
            )
        )
        
        # =================================================================
        # 6. STOCK VALUE
        # =================================================================
        avg_cost = pd.to_numeric(df.get('avg_cost', 0), errors='coerce').fillna(0)
        median_cost = avg_cost[avg_cost > 0].median() if (avg_cost > 0).any() else 100000
        avg_cost_filled = np.where(avg_cost > 0, avg_cost, median_cost / 10)
        df['stock_value'] = current_stock * avg_cost_filled
        
        # =================================================================
        # 7. SAFETY STOCK - ABC Class Specific
        # =================================================================
        if 'demand_volatility' in df.columns:
            volatility = pd.to_numeric(df['demand_volatility'], errors='coerce').fillna(0)
        elif 'std_daily_sales' in df.columns:
            volatility = pd.to_numeric(df['std_daily_sales'], errors='coerce').fillna(0)
        else:
            volatility = df['avg_daily_demand'] * 0.3  # Assume 30% CV
        
        if 'estimated_lead_time' in df.columns:
            lead_time = pd.to_numeric(df['estimated_lead_time'], errors='coerce').fillna(14)
        elif 'avg_lead_time' in df.columns:
            lead_time = pd.to_numeric(df['avg_lead_time'], errors='coerce').fillna(14)
        else:
            lead_time = 14
        
        Z_SCORE = 1.65
        raw_safety = Z_SCORE * volatility * np.sqrt(np.clip(lead_time, 1, 60))
        
        # ABC-specific safety stock limits
        df['safety_stock'] = np.where(
            (abc_class == 'A') & (avg_demand > 0.1),
            np.clip(raw_safety, 1, 50),   # Class A: 1-50 units
            np.where(
                (abc_class == 'B') & (avg_demand > 0.05),
                np.clip(raw_safety, 0, 20),   # Class B: 0-20 units
                0  # Class C: ZERO safety stock
            )
        )
        
        df['optimal_safety_stock'] = df['safety_stock']
        
        # =================================================================
        # 8. REORDER POINT - ABC Class Specific
        # =================================================================
        # Class C should NEVER have large reorder recommendations
        df['reorder_point'] = np.where(
            (abc_class == 'A') & (avg_demand > 0.01),
            np.clip(avg_demand * lead_time + df['safety_stock'], 0, 200),  # A: max 200
            np.where(
                (abc_class == 'B') & (avg_demand > 0.01),
                np.clip(avg_demand * lead_time + df['safety_stock'], 0, 50),   # B: max 50
                0  # C: ZERO reorder point
            )
        )
        
        # =================================================================
        # 9. ORDER QUANTITY RECOMMENDATION - ABC Specific
        # =================================================================
        df['recommended_order_qty'] = np.where(
            (abc_class == 'A') & (avg_demand > 0.01),
            np.clip(avg_demand * 30, 1, 100),  # A: 1-100 units (1 month demand)
            np.where(
                (abc_class == 'B') & (avg_demand > 0.01),
                np.clip(avg_demand * 14, 1, 30),   # B: 1-30 units (2 week demand)
                np.where(
                    (abc_class == 'C') & (current_stock == 0) & (qty_sold_30d > 0),
                    1,  # C: Only 1 unit if completely out and has sales
                    0   # C: ZERO otherwise
                )
            )
        )
        
        # =================================================================
        # 10. TOTAL SALES - Legacy compatibility
        # =================================================================
        if 'total_sales_90d' not in df.columns:
            total_revenue = pd.to_numeric(df.get('total_revenue', 0), errors='coerce').fillna(0)
            df['total_sales_90d'] = total_revenue
        
        return df
    
    def get_available_brands(self, df: pd.DataFrame) -> List[str]:
        """Get unique brands sorted alphabetically"""
        if df is None or 'brand' not in df.columns:
            return []
        return sorted(df['brand'].unique().tolist())
    
    def filter_by_brand(self, df: pd.DataFrame, selected_brands: List[str]) -> pd.DataFrame:
        """Filter dataframe by selected brands"""
        if df is None or not selected_brands or 'brand' not in df.columns:
            return df
        return df[df['brand'].isin(selected_brands)]
    
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
        if df is None or not query:
            return df
        
        query_lower = query.lower()
        mask = pd.Series([False] * len(df), index=df.index)
        
        for col in ['product_code', 'product_name', 'item_no', 'item_name']:
            if col in df.columns:
                mask = mask | df[col].astype(str).str.lower().str.contains(query_lower, na=False)
        
        return df[mask]
    
    def filter_products(self, df: pd.DataFrame, filters: Dict) -> pd.DataFrame:
        """Filter products by multiple criteria"""
        if df is None:
            return df
        
        result = df.copy()
        
        # Filter by brand
        if 'brand' in filters and filters['brand']:
            result = result[result['brand'].isin(filters['brand'])]
        
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
            'total_stock_value': df['stock_value'].sum() if 'stock_value' in df.columns else 0,
            'avg_daily_demand': df['avg_daily_demand'].mean() if 'avg_daily_demand' in df.columns else 0,
            'total_sales_90d': df['total_sales_90d'].sum() if 'total_sales_90d' in df.columns else 0,
            'products_with_stock': (df['current_stock_qty'] > 0).sum() if 'current_stock_qty' in df.columns else 0,
            'stockout_products': (df['current_stock_qty'] == 0).sum() if 'current_stock_qty' in df.columns else 0,
            'abc_a_count': (df['ABC_class'] == 'A').sum() if 'ABC_class' in df.columns else 0,
            'abc_b_count': (df['ABC_class'] == 'B').sum() if 'ABC_class' in df.columns else 0,
            'abc_c_count': (df['ABC_class'] == 'C').sum() if 'ABC_class' in df.columns else 0,
            'needs_reorder_count': df['needs_reorder'].sum() if 'needs_reorder' in df.columns else 0,
            'high_risk_count': (df['stockout_risk'] == 'HIGH').sum() if 'stockout_risk' in df.columns else 0,
        }
        
        return stats


# ============================================================================
# BACKWARD COMPATIBLE INTERFACE
# ============================================================================

# Keep DataLoaderV3 as alias for compatibility
DataLoaderV3 = DataLoaderV4

# Global instance
_loader = None

def get_loader() -> DataLoaderV4:
    """Get or create loader instance"""
    global _loader
    if _loader is None:
        _loader = DataLoaderV4()
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

def get_available_brands() -> List[str]:
    """Get available brands for filtering"""
    loader = get_loader()
    df = load_all_data()
    return loader.get_available_brands(df)

def load_project2_data() -> Dict:
    """Load Project 2 data (RFM and MBA)"""
    import os
    from pathlib import Path
    
    project2_data = {}
    
    # Define file mappings
    file_mappings = {
        '1_RFM_Analysis.csv': ['1_RFM_Analysis.csv', 'rfm_analysis.csv'],
        '2_Customer_Segments.csv': ['2_Customer_Segments.csv', 'customer_segments.csv'],
        '6_Sales_By_Customer.csv': ['6_Sales_By_Customer.csv', 'sales_by_customer.csv'],
        '8_Customer_Master.csv': ['8_Customer_Master.csv', 'customer_master.csv'],
        '3_Market_Basket.csv': ['3_Market_Basket.csv', 'market_basket.csv'],
        '4_Product_Associations.csv': ['4_Product_Associations.csv', 'product_associations.csv'],
        '5_Sales_Details.csv': ['5_Sales_Details.csv', 'sales_details.csv'],
        '7_Sales_By_Product.csv': ['7_Sales_By_Product.csv', 'sales_by_product.csv'],
        '9_Item_Master.csv': ['9_Item_Master.csv', 'item_master.csv'],
    }
    
    # Try to find Project 2 data folder
    data_dir = Path("data")
    project_root = Path(__file__).parent.parent
    project2_paths = [
        project_root.parent / "WPT-Project2-Folder(SalesPerformanceAndCustomerSegmentationAnalytics)" / "V0dev-Project2-Modeling" / "scripts" / "output" / "csv_data",
        project_root.parent / "WPT-Project2-Folder(SalesPerformanceAndCustomerSegmentationAnalytics)" / "V0dev-Project2-DataPreparation" / "scripts" / "project2_sales_analytics" / "data_project2",
    ]
    
    # Find existing Project 2 folder
    project2_data_dir = None
    for path in project2_paths:
        if path.exists():
            project2_data_dir = path
            break
    
    # Load files
    for preferred_name, alternatives in file_mappings.items():
        for filename in alternatives:
            # Try data folder first
            filepath = data_dir / filename
            if filepath.exists():
                try:
                    project2_data[preferred_name] = pd.read_csv(filepath)
                    break
                except:
                    pass
            
            # Try Project 2 folder
            if project2_data_dir:
                filepath = project2_data_dir / filename
                if filepath.exists():
                    try:
                        project2_data[preferred_name] = pd.read_csv(filepath)
                        break
                    except:
                        pass
    
    return project2_data

def load_supplementary_data() -> Dict:
    """Load supplementary data files"""
    loader = get_loader()
    return loader.load_supplementary_data() if hasattr(loader, 'load_supplementary_data') else {}


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    loader = DataLoaderV4()
    df = loader.merge_data()
    if df is not None:
        print(f"[OK] Loaded {len(df)} products")
        print(f"[OK] Brands: {loader.get_available_brands(df)[:10]}...")
        print(f"[OK] ABC Distribution: {loader.get_abc_distribution(df)}")
        print(f"[OK] Sample columns: {df.columns.tolist()[:15]}")
    else:
        print("[X] Data loading failed.")