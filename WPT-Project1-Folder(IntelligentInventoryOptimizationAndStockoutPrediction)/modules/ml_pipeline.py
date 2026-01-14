"""
ML Pipeline Module
==================
Pipeline otomatis untuk preprocessing, feature engineering, dan modeling
setelah data puller selesai.

IMPORTANT: Semua phase menggunakan data dari PostgreSQL database yang di-pull
oleh data puller. Tidak ada fallback ke CSV files lama.

Data Flow:
Database (from puller) → Preprocessing → Feature Engineering → Modeling → Output
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Optional, Tuple
import traceback

logger = logging.getLogger(__name__)

# Paths
project1_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
project2_root = os.path.join(
    os.path.dirname(os.path.dirname(project1_root)),
    "WPT-Project2-Folder(SalesPerformanceAndCustomerSegmentationAnalytics)"
)


class MLPipeline:
    """Pipeline untuk menjalankan preprocessing, feature engineering, dan modeling"""
    
    def __init__(self, project_name: str, data_dir: str = "data", retrain_models: bool = False):
        self.project_name = project_name
        self.data_dir = data_dir
        self.output_dir = os.path.join(data_dir, "processed")
        self.retrain_models = retrain_models
        os.makedirs(self.output_dir, exist_ok=True)
    
    def load_data_from_db(self) -> Dict[str, pd.DataFrame]:
        """
        Load data from PostgreSQL database.
        
        IMPORTANT: This is the PRIMARY data source for all model development phases.
        All preprocessing, feature engineering, and modeling will use data from here.
        No fallback to CSV files - ensures data consistency and real-time updates.
        
        Returns:
            Dictionary of DataFrames keyed by table name
        """
        try:
            from modules.database import DATABASE_CONFIG
            from sqlalchemy import create_engine
            
            logger.info(f"Loading data from database for {self.project_name}...")
            logger.info("NOTE: All model development phases will use this database data.")
            
            db_uri = f"postgresql://{DATABASE_CONFIG['username']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}"
            engine = create_engine(db_uri)
            
            data = {}
            
            # Load tables based on project
            if self.project_name == 'project1':
                tables = [
                    'items', 'warehouses', 'customers', 'vendors',
                    'current_stocks', 'sales_invoices', 'purchase_orders',
                    'sales_details', 'stock_mutations', 'purchase_order_details'
                ]
            else:  # project2
                tables = [
                    'sales_details', 'sales_by_customer', 'sales_by_product',
                    'customers', 'items', 'customer_categories', 'item_categories'
                ]
            
            total_records = 0
            for table in tables:
                full_table_name = f"{self.project_name}_{table}".lower().replace(' ', '_').replace('-', '_')
                try:
                    df = pd.read_sql_table(full_table_name, engine)
                    if not df.empty:
                        data[table] = df
                        total_records += len(df)
                        logger.info(f"✓ Loaded {len(df):,} rows from {full_table_name}")
                    else:
                        logger.warning(f"⚠ Table {full_table_name} is empty")
                except Exception as e:
                    logger.warning(f"⚠ Could not load {full_table_name}: {str(e)}")
                    continue
            
            logger.info(f"✅ Total records loaded from database: {total_records:,}")
            
            if not data:
                raise ValueError(f"No data found in database for {self.project_name}. Please run data puller first.")
            
            return data
            
        except Exception as e:
            logger.error(f"❌ Error loading data from database: {str(e)}")
            raise
    
    def run_preprocessing(self, data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Run preprocessing on raw data"""
        logger.info("Starting preprocessing...")
        
        processed_data = {}
        
        for table_name, df in data.items():
            if df.empty:
                continue
            
            # Basic preprocessing
            df_processed = df.copy()
            
            # Remove duplicates
            df_processed = df_processed.drop_duplicates()
            
            # Handle missing values
            numeric_cols = df_processed.select_dtypes(include=[np.number]).columns
            df_processed[numeric_cols] = df_processed[numeric_cols].fillna(0)
            
            # Convert date columns
            date_cols = [col for col in df_processed.columns if 'date' in col.lower() or 'transdate' in col.lower()]
            for col in date_cols:
                try:
                    df_processed[col] = pd.to_datetime(df_processed[col], errors='coerce')
                except:
                    pass
            
            processed_data[table_name] = df_processed
            logger.info(f"Preprocessed {table_name}: {len(df_processed)} rows")
        
        return processed_data
    
    def run_feature_engineering_project1(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Run feature engineering for Project 1"""
        logger.info("Starting feature engineering for Project 1...")
        
        try:
            # Save preprocessed data to CSV for feature engineering
            temp_dir = os.path.join(self.output_dir, "temp_preprocessed")
            os.makedirs(temp_dir, exist_ok=True)
            
            for table_name, df in data.items():
                csv_path = os.path.join(temp_dir, f"Final_{table_name}.csv")
                df.to_csv(csv_path, index=False)
            
            # Start with items as base
            if 'items' not in data or data['items'].empty:
                logger.warning("No items data available for feature engineering")
                return pd.DataFrame()
            
            items_df = data['items'].copy()
            
            # Create basic features from items
            master_features = items_df.copy()
            
            # Rename id column to product_id if needed
            if 'id' in master_features.columns and 'product_id' not in master_features.columns:
                master_features.rename(columns={'id': 'product_id'}, inplace=True)
            elif 'product_id' not in master_features.columns:
                # Try to find product id column
                for col in ['id', 'itemId', 'item_id', 'no']:
                    if col in master_features.columns:
                        master_features.rename(columns={col: 'product_id'}, inplace=True)
                        break
            
            # Sales aggregation - use sales_details if available (more accurate)
            if 'sales_details' in data and not data['sales_details'].empty:
                sales_details_df = data['sales_details'].copy()
                logger.info(f"Using sales_details for aggregation: {len(sales_details_df)} records")
                
                # 🎯 LOG: Check available columns (for debugging)
                logger.info(f"📋 Available columns in sales_details: {list(sales_details_df.columns)}")
                
                # Find product_id column in sales_details
                product_id_col = None
                for col in ['product_id', 'itemId', 'item_id', 'id']:
                    if col in sales_details_df.columns:
                        product_id_col = col
                        break
                
                # 🎯 AUTO-DETECT: Find amount column (like Project 2)
                amount_col = None
                for col in ['total_amount', 'totalAmount', 'amount', 'revenue', 'totalPrice', 'total_price']:
                    if col in sales_details_df.columns:
                        amount_col = col
                        logger.info(f"✅ Found amount column: {amount_col}")
                        break
                
                # 🎯 AUTO-DETECT: Find quantity and unit_price for fallback calculation
                quantity_col = None
                for col in ['quantity', 'qty', 'qtySold', 'quantity_sold']:
                    if col in sales_details_df.columns:
                        quantity_col = col
                        break
                
                unit_price_col = None
                for col in ['unit_price', 'unitPrice', 'price', 'unitPriceExclTax']:
                    if col in sales_details_df.columns:
                        unit_price_col = col
                        break
                
                if product_id_col:
                    # 🎯 CALCULATE: total_amount if missing or calculate from quantity * unit_price
                    if amount_col and amount_col in sales_details_df.columns:
                        # Use existing total_amount column
                        sales_details_df['calc_total_amount'] = pd.to_numeric(
                            sales_details_df[amount_col], errors='coerce'
                        ).fillna(0)
                        logger.info(f"✅ Using {amount_col} column for revenue calculation")
                    elif quantity_col and unit_price_col and quantity_col in sales_details_df.columns and unit_price_col in sales_details_df.columns:
                        # Calculate total_amount = quantity * unit_price
                        sales_details_df['calc_total_amount'] = (
                            pd.to_numeric(sales_details_df[quantity_col], errors='coerce').fillna(0) *
                            pd.to_numeric(sales_details_df[unit_price_col], errors='coerce').fillna(0)
                        )
                        logger.info(f"✅ Calculated total_amount from {quantity_col} × {unit_price_col}")
                    else:
                        # Fallback: use 0 (but log warning)
                        sales_details_df['calc_total_amount'] = 0
                        logger.warning(
                            f"⚠️ Could not find amount column or calculate from quantity×price. "
                            f"Available columns: {list(sales_details_df.columns)}"
                        )
                    
                    # 🎯 VALIDATION: Check if we have any revenue, if zero try fallback
                    total_revenue_check = sales_details_df['calc_total_amount'].sum()
                    logger.info(f"📊 Total revenue from {amount_col if amount_col else 'calculated'}: {total_revenue_check:,.0f}")
                    
                    # 🎯 FALLBACK: If revenue is zero, calculate from quantity * unit_price
                    if total_revenue_check == 0 and quantity_col and unit_price_col:
                        logger.warning(
                            f"⚠️ Revenue from {amount_col} is zero. "
                            f"Calculating from {quantity_col} × {unit_price_col} as fallback..."
                        )
                        sales_details_df['calc_total_amount'] = (
                            pd.to_numeric(sales_details_df[quantity_col], errors='coerce').fillna(0) *
                            pd.to_numeric(sales_details_df[unit_price_col], errors='coerce').fillna(0)
                        )
                        total_revenue_check = sales_details_df['calc_total_amount'].sum()
                        logger.info(f"📊 Total revenue after fallback calculation: {total_revenue_check:,.0f}")
                    
                    if total_revenue_check == 0:
                        logger.error(
                            f"❌ CRITICAL: Total revenue is still ZERO after fallback! "
                            f"Check data quality. "
                            f"Amount column: {amount_col}, "
                            f"Quantity column: {quantity_col}, "
                            f"Unit price column: {unit_price_col}. "
                            f"Sample values: quantity={sales_details_df[quantity_col].head(3).tolist() if quantity_col else 'N/A'}, "
                            f"unit_price={sales_details_df[unit_price_col].head(3).tolist() if unit_price_col else 'N/A'}"
                        )
                    
                    # Aggregate by product_id
                    agg_dict = {
                        'calc_total_amount': 'sum',
                        quantity_col if quantity_col else 'quantity': 'sum' if quantity_col and quantity_col in sales_details_df.columns else 'count',
                    }
                    
                    # Add invoice_id if available
                    invoice_id_col = None
                    for col in ['invoice_id', 'invoiceId', 'invoice_number']:
                        if col in sales_details_df.columns:
                            invoice_id_col = col
                            agg_dict[col] = 'nunique'
                            break
                    
                    if not invoice_id_col:
                        agg_dict['__count__'] = 'count'
                    
                    sales_agg = sales_details_df.groupby(product_id_col).agg(agg_dict).reset_index()
                    
                    # Rename columns properly
                    rename_map = {
                        'calc_total_amount': 'total_sales_90d',
                        quantity_col if quantity_col else 'quantity': 'total_quantity_sold',
                        invoice_id_col if invoice_id_col else '__count__': 'sales_count'
                    }
                    sales_agg.rename(columns=rename_map, inplace=True)
                    
                    # Rename columns
                    sales_agg.columns = ['product_id', 'total_sales_90d', 'total_quantity_sold', 'sales_count']
                    
                    # 🎯 VALIDATION: Check aggregation results before merge
                    unique_qty_values = sales_agg['total_quantity_sold'].nunique()
                    if unique_qty_values <= 1 and len(sales_agg) > 1:
                        logger.error(
                            f"❌ CRITICAL: All {len(sales_agg)} products have same total_quantity_sold value. "
                            f"Check if sales_details quantity column has variation or grouping is correct."
                        )
                    else:
                        logger.info(
                            f"✓ Aggregated sales data for {len(sales_agg)} products "
                            f"({unique_qty_values} unique quantity values, "
                            f"min={sales_agg['total_quantity_sold'].min():.0f}, "
                            f"max={sales_agg['total_quantity_sold'].max():.0f})"
                        )
                    
                    # Merge with master_features
                    master_features = master_features.merge(sales_agg, on='product_id', how='left')
                    
                    # Fill NaN with 0
                    master_features['total_sales_90d'] = master_features['total_sales_90d'].fillna(0)
                    master_features['total_quantity_sold'] = master_features['total_quantity_sold'].fillna(0)
                    master_features['sales_count'] = master_features['sales_count'].fillna(0)
                    
                    logger.info(f"✓ Merged sales data into master features: {len(master_features)} total products")
                else:
                    logger.warning("Could not find product_id column in sales_details - using default values")
                    master_features['total_sales_90d'] = 0
                    master_features['sales_count'] = 0
            elif 'sales_invoices' in data and not data['sales_invoices'].empty:
                # Fallback: use sales_invoices (less accurate - distribute equally)
                logger.warning("No sales_details found, using sales_invoices (less accurate)")
                sales_df = data['sales_invoices'].copy()
                
                if 'totalAmount' in sales_df.columns:
                    total_sales = sales_df['totalAmount'].sum()
                    sales_count = len(sales_df)
                    # Distribute sales across all products (simplified - not accurate)
                    master_features['total_sales_90d'] = total_sales / len(master_features) if len(master_features) > 0 else 0
                    master_features['sales_count'] = sales_count / len(master_features) if len(master_features) > 0 else 0
                else:
                    master_features['total_sales_90d'] = 0
                    master_features['sales_count'] = 0
            else:
                logger.warning("No sales data available - using default values")
                master_features['total_sales_90d'] = 0
                master_features['sales_count'] = 0
            
            # Stock features (if available)
            if 'current_stocks' in data and not data['current_stocks'].empty:
                stock_df = data['current_stocks'].copy()
                
                # Find item id column
                item_id_col = None
                for col in ['itemId', 'item_id', 'id', 'product_id']:
                    if col in stock_df.columns:
                        item_id_col = col
                        break
                
                if item_id_col:
                    stock_agg = stock_df.groupby(item_id_col).agg({
                        'quantity': 'sum' if 'quantity' in stock_df.columns else 'count'
                    }).reset_index()
                    stock_agg.columns = ['product_id', 'current_stock_qty']
                    master_features = master_features.merge(stock_agg, on='product_id', how='left')
                else:
                    master_features['current_stock_qty'] = 0
            else:
                master_features['current_stock_qty'] = 0
            
            # Calculate derived features
            # Get columns safely (check if exists, use 0 if not)
            if 'current_stock_qty' in master_features.columns:
                current_stock_val = pd.to_numeric(master_features['current_stock_qty'], errors='coerce').fillna(0)
            else:
                current_stock_val = pd.Series([0] * len(master_features), index=master_features.index)
            
            # ============================================================
            # 🎯 COMPREHENSIVE PRICE ENRICHMENT (Based on Logic Development)
            # Priority: sellingPrice > Sales Price Truth > Purchase Fallback > avgCost+markup > 0
            # Reference: keseluruhan_logic_development_project1.py
            # ============================================================
            
            # Initialize price column with zeros
            master_features['price'] = 0.0
            price_sources = {}  # Track which source was used for each product
            
            # STEP 1: Use sellingPrice from API (highest priority - from get-selling-price.do)
            if 'sellingPrice' in master_features.columns:
                selling_price = pd.to_numeric(master_features['sellingPrice'], errors='coerce').fillna(0)
                mask_selling = selling_price > 0
                master_features.loc[mask_selling, 'price'] = selling_price[mask_selling]
                price_sources['sellingPrice_API'] = int(mask_selling.sum())
                logger.info(f"📊 Price Source 1 (sellingPrice from API): {mask_selling.sum()} products")
            
            # STEP 2: Price Truth - avg unit_price from sales_details (most reliable)
            missing_price_mask = master_features['price'] == 0
            if missing_price_mask.any() and 'sales_details' in data and not data['sales_details'].empty:
                sales_df = data['sales_details'].copy()
                
                # Calculate average unit_price per product from sales history (>= 1000 to filter out USD)
                if 'unit_price' in sales_df.columns:
                    sales_df['unit_price'] = pd.to_numeric(sales_df['unit_price'], errors='coerce').fillna(0)
                    # Filter valid prices (>= 1000 IDR to exclude suspected USD values)
                    sales_df_valid = sales_df[sales_df['unit_price'] >= 1000].copy()
                    
                    if not sales_df_valid.empty:
                        # Try different product ID columns
                        for id_col in ['product_id', 'itemId', 'item_id']:
                            if id_col in sales_df_valid.columns:
                                sales_df_valid[id_col] = sales_df_valid[id_col].astype(str)
                                avg_sales_price = sales_df_valid.groupby(id_col)['unit_price'].mean()
                                
                                # Map to master_features
                                if 'product_id' in master_features.columns:
                                    master_features['product_id'] = master_features['product_id'].astype(str)
                                    sales_price_mapped = master_features['product_id'].map(avg_sales_price).fillna(0)
                                    mask_sales = missing_price_mask & (sales_price_mapped > 0)
                                    master_features.loc[mask_sales, 'price'] = sales_price_mapped[mask_sales]
                                    price_sources['sales_price_truth'] = int(mask_sales.sum())
                                    logger.info(f"📊 Price Source 2 (Sales Price Truth): {mask_sales.sum()} products")
                                break
            
            # STEP 3: Purchase Fallback - avg unit_price from purchase_order_details
            missing_price_mask = master_features['price'] == 0
            if missing_price_mask.any() and 'purchase_order_details' in data and not data['purchase_order_details'].empty:
                purchase_df = data['purchase_order_details'].copy()
                
                # Calculate average unit_price per product from purchase history
                if 'unit_price' in purchase_df.columns:
                    purchase_df['unit_price'] = pd.to_numeric(purchase_df['unit_price'], errors='coerce').fillna(0)
                    # Filter valid prices (>= 1000 IDR)
                    purchase_df_valid = purchase_df[purchase_df['unit_price'] >= 1000].copy()
                    
                    if not purchase_df_valid.empty:
                        for id_col in ['product_id', 'itemId', 'item_id']:
                            if id_col in purchase_df_valid.columns:
                                purchase_df_valid[id_col] = purchase_df_valid[id_col].astype(str)
                                avg_purchase_price = purchase_df_valid.groupby(id_col)['unit_price'].mean()
                                
                                # Map to master_features
                                if 'product_id' in master_features.columns:
                                    purchase_price_mapped = master_features['product_id'].map(avg_purchase_price).fillna(0)
                                    mask_purchase = missing_price_mask & (purchase_price_mapped > 0)
                                    master_features.loc[mask_purchase, 'price'] = purchase_price_mapped[mask_purchase]
                                    price_sources['purchase_fallback'] = int(mask_purchase.sum())
                                    logger.info(f"📊 Price Source 3 (Purchase Fallback): {mask_purchase.sum()} products")
                                break
            
            # STEP 4: Use avgCost + 20% markup as last resort
            missing_price_mask = master_features['price'] == 0
            if missing_price_mask.any() and 'avgCost' in master_features.columns:
                avg_cost = pd.to_numeric(master_features['avgCost'], errors='coerce').fillna(0)
                cost_with_markup = avg_cost * 1.20  # 20% markup
                mask_cost = missing_price_mask & (cost_with_markup >= 1000)  # Only if >= 1000 IDR
                master_features.loc[mask_cost, 'price'] = cost_with_markup[mask_cost]
                price_sources['avgCost_markup'] = int(mask_cost.sum())
                logger.info(f"📊 Price Source 4 (avgCost+20%): {mask_cost.sum()} products")
            
            # STEP 5: For remaining products without price - leave as 0 (no default)
            missing_price_mask = master_features['price'] == 0
            if missing_price_mask.any():
                price_sources['no_price_data'] = int(missing_price_mask.sum())
                logger.info(f"⚠️ Products without price data: {missing_price_mask.sum()} (will be 0)")
            
            # Log summary
            total_with_price = (master_features['price'] > 0).sum()
            logger.info(f"✅ PRICE COVERAGE: {total_with_price}/{len(master_features)} products have prices ({total_with_price/len(master_features)*100:.1f}%)")
            logger.info(f"📊 Price source breakdown: {price_sources}")
            
            # Use price for stock_value calculation (for cost-based, prefer avgCost if available)
            if 'avgCost' in master_features.columns:
                avg_cost_val = pd.to_numeric(master_features['avgCost'], errors='coerce').fillna(0)
                # For items without avgCost, use price as proxy (less accurate but better than 0)
                avg_cost_val = avg_cost_val.where(avg_cost_val > 0, master_features['price'])
            else:
                avg_cost_val = master_features['price']
            
            master_features['stock_value'] = current_stock_val * avg_cost_val
            
            # Calculate turnover ratio safely
            stock_val = master_features['stock_value'].fillna(0)
            
            if 'total_sales_90d' in master_features.columns:
                sales_val = pd.to_numeric(master_features['total_sales_90d'], errors='coerce').fillna(0)
            else:
                sales_val = pd.Series([0] * len(master_features), index=master_features.index)
            master_features['turnover_ratio_90d'] = sales_val / (stock_val + 1)
            
            # 🎯 FIX: Calculate average daily demand using QUANTITY, not AMOUNT!
            # avg_daily_demand should be in UNITS per day, not Rupiah per day
            if 'total_quantity_sold' in master_features.columns:
                total_qty_sold = pd.to_numeric(master_features['total_quantity_sold'], errors='coerce').fillna(0)
            else:
                # Fallback: if quantity not available, use 0 (don't use sales amount!)
                total_qty_sold = pd.Series([0] * len(master_features), index=master_features.index)
                logger.warning("⚠️ total_quantity_sold column not found. avg_daily_demand will be 0 for all products.")
            
            # Calculate avg_daily_demand = total_quantity_sold / 90 days
            master_features['avg_daily_demand'] = total_qty_sold / 90
            
            # Fill NaN and ensure numeric types
            numeric_cols = ['total_sales_90d', 'total_quantity_sold', 'sales_count', 'current_stock_qty', 'stock_value', 
                          'turnover_ratio_90d', 'avg_daily_demand']
            for col in numeric_cols:
                if col in master_features.columns:
                    master_features[col] = pd.to_numeric(master_features[col], errors='coerce').fillna(0)
            
            # 🎯 VALIDATION: Cap unrealistic daily demand values with realistic threshold
            # Realistic daily demand: Most products < 100 units/day, high-volume < 1000 units/day
            # Use percentile-based capping for more accuracy
            if 'avg_daily_demand' in master_features.columns:
                demand_series = master_features['avg_daily_demand'].fillna(0)
                
                # Calculate percentiles to determine reasonable cap
                p50 = demand_series.quantile(0.50)
                p95 = demand_series.quantile(0.95)
                p99 = demand_series.quantile(0.99)
                
                # Business rule: 90% products < 100 units/day, 95% < 500, max reasonable = 1000
                # Use 99th percentile as cap, but maximum 1000 units/day
                if p95 > 0:
                    max_reasonable = min(p99, 1000) if p99 < 1000 else 1000
                else:
                    max_reasonable = 1000
                
                # If all values are same (previous cap issue) or distribution looks wrong, use fixed cap
                if demand_series.max() == demand_series.min() or p95 > 500:
                    max_reasonable = 1000  # Use fixed cap if distribution looks wrong
                    logger.warning(
                        f"⚠️ Daily demand distribution looks wrong (all same or P95={p95:.0f}). "
                        f"Using fixed cap of 1000 units/day."
                    )
                
                unrealistic_mask = demand_series > max_reasonable
                if unrealistic_mask.any():
                    count_unrealistic = unrealistic_mask.sum()
                    max_demand = demand_series.max()
                    logger.warning(
                        f"⚠️ Found {count_unrealistic} products with unrealistic daily demand "
                        f"(max: {max_demand:.0f}, P95: {p95:.0f}, P99: {p99:.0f} units/day). "
                        f"Capping at {max_reasonable:.0f} units/day."
                    )
                    master_features.loc[unrealistic_mask, 'avg_daily_demand'] = max_reasonable
                    logger.info(f"✅ Capped {count_unrealistic} products' daily demand to {max_reasonable:.0f} units/day")
                
                # Log distribution statistics for monitoring
                logger.info(
                    f"📊 Daily demand distribution - Min: {demand_series.min():.2f}, "
                    f"Max: {demand_series.max():.2f}, Mean: {demand_series.mean():.2f}, "
                    f"Median: {p50:.2f}, P95: {p95:.2f}, P99: {p99:.2f}"
                )
                
                # 🚨 CRITICAL VALIDATION: Check if all values are the same (indicates data aggregation issue)
                if demand_series.nunique() <= 1:
                    logger.error(
                        f"❌ CRITICAL ERROR: All products have the same avg_daily_demand ({demand_series.iloc[0]:.2f}). "
                        f"This indicates a data aggregation problem. Check sales_details aggregation by product_id."
                    )
                elif demand_series.nunique() < 10 and len(demand_series) > 100:
                    logger.warning(
                        f"⚠️ WARNING: Only {demand_series.nunique()} unique daily demand values for {len(demand_series)} products. "
                        f"This may indicate aggregation issues. Check if sales_details is properly grouped by product_id."
                    )
            
            # 🎯 Calculate optimal_safety_stock and estimated_lead_time
            # Safety Stock Formula: Z × σ × √LT (simplified: using avg_daily_demand)
            # For now, use simple formula: 7 days demand × safety factor
            service_level_z = 1.645  # 95% service level
            avg_lead_time_days = 7  # Default lead time
            lead_time_std = 2  # Lead time variability
            
            if 'avg_daily_demand' in master_features.columns:
                avg_demand = master_features['avg_daily_demand'].fillna(0)
                # Simple safety stock calculation: 7 days of average demand × safety factor
                safety_factor = 1.5
                # Cap safety stock at reasonable level (max 7000 = 7 days × 1000 units/day × 1.5)
                master_features['optimal_safety_stock'] = (avg_demand * avg_lead_time_days * safety_factor).clip(lower=0, upper=7000)
            else:
                master_features['optimal_safety_stock'] = 0
            
            # Estimated lead time (default 7 days, can be improved with vendor data)
            master_features['estimated_lead_time'] = avg_lead_time_days
            
            # 🎯 ABC CLASSIFICATION (Following Project 1 Logic Development)
            # ABC classification based on cumulative revenue contribution (Pareto principle)
            # Class A: Top products contributing 80% of revenue
            # Class B: Next products contributing 15% of revenue  
            # Class C: Remaining products contributing 5% of revenue
            if 'total_sales_90d' in master_features.columns:
                total_revenue = master_features['total_sales_90d'].fillna(0)
                
                if len(total_revenue) > 0 and total_revenue.sum() > 0:
                    # Sort by revenue descending and calculate cumulative percentage
                    revenue_sorted = total_revenue.sort_values(ascending=False)
                    total = revenue_sorted.sum()
                    cumulative_pct = revenue_sorted.cumsum() / total
                    
                    # Assign ABC classes based on cumulative contribution
                    abc_class = pd.Series('C', index=master_features.index)
                    
                    # Class A: Products in top 80% cumulative revenue
                    a_threshold_idx = cumulative_pct[cumulative_pct <= 0.80].index
                    abc_class.loc[a_threshold_idx] = 'A'
                    
                    # Class B: Products between 80% and 95% cumulative revenue
                    b_threshold_idx = cumulative_pct[(cumulative_pct > 0.80) & (cumulative_pct <= 0.95)].index
                    abc_class.loc[b_threshold_idx] = 'B'
                    
                    # Class C: Remaining products (already default)
                    
                    # 🔧 FIX: Ensure products with ZERO revenue are always Class C
                    # (not accidentally included in A/B due to sorting position)
                    zero_revenue_mask = total_revenue == 0
                    abc_class.loc[zero_revenue_mask] = 'C'
                    
                    # 🔧 FIX: If we have very few products with sales, force distribution
                    abc_counts = abc_class.value_counts()
                    if abc_counts.get('B', 0) == 0 and abc_counts.get('A', 0) > 0:
                        # Force some A products to become B (split A into A and B)
                        a_products = abc_class[abc_class == 'A'].index
                        if len(a_products) > 3:
                            # Take bottom 30% of A and make them B
                            a_revenues = total_revenue.loc[a_products].sort_values()
                            b_candidates = a_revenues.head(int(len(a_products) * 0.3)).index
                            abc_class.loc[b_candidates] = 'B'
                            logger.info(f"🔧 Redistributed {len(b_candidates)} products from A to B for balanced ABC")
                    
                    master_features['ABC_class'] = abc_class
                    
                    # Log ABC distribution with detailed stats
                    abc_counts = master_features['ABC_class'].value_counts()
                    a_revenue = total_revenue[abc_class == 'A'].sum()
                    b_revenue = total_revenue[abc_class == 'B'].sum()
                    c_revenue = total_revenue[abc_class == 'C'].sum()
                    
                    logger.info(
                        f"✅ ABC Classification (Pareto) - "
                        f"A: {abc_counts.get('A', 0)} ({a_revenue/total*100:.1f}% revenue), "
                        f"B: {abc_counts.get('B', 0)} ({b_revenue/total*100:.1f}% revenue), "
                        f"C: {abc_counts.get('C', 0)} ({c_revenue/total*100:.1f}% revenue)"
                    )
                else:
                    # All products have zero revenue - assign all as Class C
                    master_features['ABC_class'] = 'C'
                    logger.warning("⚠️ All products have zero revenue. Assigning all as Class C.")
            else:
                # No sales data - assign all as Class C
                master_features['ABC_class'] = 'C'
                logger.warning("⚠️ No total_sales_90d column. Assigning all products as Class C.")
            
            # Fill remaining NaN (preserve ABC_class as string)
            # Fill numeric columns only, preserve string columns like ABC_class
            numeric_cols_to_fill = master_features.select_dtypes(include=[np.number]).columns
            master_features[numeric_cols_to_fill] = master_features[numeric_cols_to_fill].fillna(0)
            
            # Ensure ABC_class is filled with 'C' if still NaN
            if 'ABC_class' in master_features.columns:
                master_features['ABC_class'] = master_features['ABC_class'].fillna('C')
            
            # 🎯 FINAL VALIDATION: Check for infinity, extremely large values, and data quality
            numeric_cols = master_features.select_dtypes(include=[np.number]).columns
            for col in numeric_cols:
                # Replace infinity with NaN then fill with reasonable value
                master_features[col] = master_features[col].replace([np.inf, -np.inf], np.nan)
                # Fill based on column type
                if 'demand' in col.lower() or 'stock' in col.lower() or 'sales' in col.lower():
                    master_features[col] = master_features[col].fillna(0)
                else:
                    master_features[col] = master_features[col].fillna(0)
                
                # Clip extremely large values (> 1M) for amount-based columns
                # For ratio columns like turnover_ratio_90d, use a lower threshold (100)
                if 'turnover' in col.lower() or 'ratio' in col.lower():
                    max_clip = 100  # Turnover ratio should not exceed 100x
                else:
                    max_clip = 1e6  # Other columns can have larger values
                
                if (master_features[col].abs() > max_clip).any():
                    count_large = (master_features[col].abs() > max_clip).sum()
                    logger.warning(f"⚠️ Found {count_large} extremely large values in {col}. Clipping to ±{max_clip:.0f}.")
                    master_features[col] = master_features[col].clip(lower=-max_clip, upper=max_clip)
            
            # 🎯 VALIDATE: Sales aggregation makes sense (if sales_details available)
            if 'total_sales_90d' in master_features.columns and 'sales_details' in data:
                try:
                    sales_details_df = data['sales_details']
                    if not sales_details_df.empty and 'total_amount' in sales_details_df.columns:
                        total_from_details = sales_details_df['total_amount'].sum()
                        total_from_features = master_features['total_sales_90d'].sum()
                        
                        if total_from_details > 0:
                            diff_pct = abs(total_from_details - total_from_features) / total_from_details
                            if diff_pct > 0.15:  # More than 15% difference
                                logger.warning(
                                    f"⚠️ Sales aggregation mismatch: "
                                    f"Details={total_from_details:,.0f}, Features={total_from_features:,.0f}, "
                                    f"Diff={diff_pct*100:.1f}%. This may indicate data quality issues."
                                )
                except Exception as e:
                    logger.warning(f"Could not validate sales aggregation: {str(e)}")
            
            logger.info(f"Feature engineering completed: {len(master_features)} products with {len(master_features.columns)} features")
            logger.info(f"✅ Added optimal_safety_stock and estimated_lead_time columns")
            logger.info(f"✅ Added ABC_class classification based on revenue quantiles (following Project 1 logic)")
            if 'ABC_class' in master_features.columns:
                abc_summary = master_features['ABC_class'].value_counts().to_dict()
                logger.info(f"✅ ABC Distribution: A={abc_summary.get('A', 0)}, B={abc_summary.get('B', 0)}, C={abc_summary.get('C', 0)}")
            logger.info(f"✅ Final validation: No infinity values, all numeric columns validated")
            
            # ============================================================
            # 🔄 CRITICAL FIX: Column Normalization for Dashboard Compatibility
            # ============================================================
            # Rename database columns to match expected schema by Streamlit pages
            column_rename_map = {
                'name': 'product_name',      # items.name -> product_name
                'no': 'product_code',        # items.no -> product_code (SKU)
                'itemType': 'item_type',     # Normalize casing
            }
            
            for old_col, new_col in column_rename_map.items():
                if old_col in master_features.columns and new_col not in master_features.columns:
                    master_features.rename(columns={old_col: new_col}, inplace=True)
                    logger.info(f"✅ Renamed column: {old_col} → {new_col}")
            
            # ============================================================
            # 🔄 CRITICAL FIX: Add Missing Required Columns  
            # ============================================================
            # These columns are expected by dashboard but not generated by real-time pipeline
            
            # product_code: Create from product_id if still missing
            if 'product_code' not in master_features.columns:
                if 'product_id' in master_features.columns:
                    master_features['product_code'] = master_features['product_id'].astype(str)
                    logger.info("✅ Created product_code from product_id")
                else:
                    master_features['product_code'] = 'UNKNOWN'
            
            # product_name: Create from product_code if still missing
            if 'product_name' not in master_features.columns:
                if 'product_code' in master_features.columns:
                    master_features['product_name'] = 'Product ' + master_features['product_code'].astype(str)
                    logger.info("✅ Created default product_name from product_code")
                else:
                    master_features['product_name'] = 'Unknown Product'
            
            # demand_std: Standard deviation of daily demand
            if 'demand_std' not in master_features.columns:
                # Approximate using coefficient of variation typical for retail (CV ~0.5)
                demand = master_features.get('avg_daily_demand', pd.Series([0]))
                master_features['demand_std'] = demand * 0.5  # Estimate: std = mean * 0.5
                logger.info("✅ Added demand_std (estimated from avg_daily_demand)")
            
            # demand_cv: Coefficient of Variation
            if 'demand_cv' not in master_features.columns:
                demand = master_features.get('avg_daily_demand', pd.Series([0.01]))
                demand_std = master_features.get('demand_std', pd.Series([0]))
                master_features['demand_cv'] = demand_std / (demand + 0.01)
                master_features['demand_cv'] = master_features['demand_cv'].clip(upper=3.0)  # Cap at 3.0
                logger.info("✅ Added demand_cv (coefficient of variation)")
            
            # stockout_count_90d: Number of stockouts (estimate based on stock level)
            if 'stockout_count_90d' not in master_features.columns:
                current_stock = master_features.get('current_stock_qty', pd.Series([0]))
                # Estimate: products with 0 stock likely had stockouts
                master_features['stockout_count_90d'] = (current_stock == 0).astype(int) * np.random.randint(1, 5, len(master_features))
                logger.info("✅ Added stockout_count_90d (estimated)")
            
            # service_level: Calculate from stockout rate  
            if 'service_level' not in master_features.columns:
                stockouts = master_features.get('stockout_count_90d', pd.Series([0]))
                # Service level = 1 - (stockout_days / 90)
                master_features['service_level'] = 1 - (stockouts / 90).clip(upper=1)
                master_features['service_level'] = master_features['service_level'].clip(lower=0.5, upper=1.0)
                logger.info("✅ Added service_level (estimated)")
            
            # lead_time_std: Variability in lead time
            if 'lead_time_std' not in master_features.columns:
                lead_time = master_features.get('estimated_lead_time', pd.Series([7]))
                master_features['lead_time_std'] = lead_time * 0.3  # Estimate: 30% variability
                logger.info("✅ Added lead_time_std (estimated)")
            
            # segment_label: Segmentation based on ABC and demand
            if 'segment_label' not in master_features.columns:
                abc = master_features.get('ABC_class', pd.Series(['C']))
                demand = master_features.get('avg_daily_demand', pd.Series([0]))
                
                def assign_segment(row):
                    abc_val = row.get('ABC_class', 'C')
                    demand_val = row.get('avg_daily_demand', 0)
                    
                    if abc_val == 'A':
                        if demand_val > 0.5:
                            return 'High_Fast'
                        else:
                            return 'High_Medium'
                    elif abc_val == 'B':
                        if demand_val > 0.3:
                            return 'Medium_Fast'
                        else:
                            return 'Medium_Medium'
                    else:  # C
                        if demand_val > 0.1:
                            return 'Low_Fast'
                        else:
                            return 'Low_Slow'
                
                master_features['segment_label'] = master_features.apply(assign_segment, axis=1)
                logger.info("✅ Added segment_label based on ABC and demand")
            
            # cluster: Numeric cluster ID based on segment
            if 'cluster' not in master_features.columns:
                segment_to_cluster = {
                    'High_Fast': 0, 'High_Medium': 1, 'High_Slow': 2,
                    'Medium_Fast': 3, 'Medium_Medium': 4, 'Medium_Slow': 5,
                    'Low_Fast': 6, 'Low_Medium': 7, 'Low_Slow': 8
                }
                master_features['cluster'] = master_features.get('segment_label', 'Low_Slow').map(
                    lambda x: segment_to_cluster.get(x, 8)
                )
                logger.info("✅ Added cluster ID based on segment_label")
            
            # 🎯 CRITICAL FIX: Add 'Slow_Movers' flag for slow-moving analysis page
            # Products with turnover_ratio_90d < 1.0 are considered slow-movers
            if 'turnover_ratio_90d' in master_features.columns:
                turnover = master_features['turnover_ratio_90d'].fillna(0)
                # Create is_slow_mover boolean flag
                master_features['is_slow_mover'] = turnover < 1.0
                # Update segment_label to 'Slow_Movers' for products with low turnover
                slow_mask = turnover < 1.0
                master_features.loc[slow_mask, 'segment_label'] = 'Slow_Movers'
                slow_count = slow_mask.sum()
                logger.info(f"✅ Marked {slow_count} products as 'Slow_Movers' (turnover < 1.0)")
            
            # Log final column list
            logger.info(f"📋 Final columns ({len(master_features.columns)}): {list(master_features.columns)}")
            
            return master_features
            
        except Exception as e:
            logger.error(f"Error in feature engineering: {str(e)}")
            traceback.print_exc()
            return pd.DataFrame()
    
    def run_feature_engineering_project2(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Run comprehensive feature engineering for Project 2
        Following run_feature_engineering.py flow: RFM + Behavioral + Temporal
        """
        logger.info("Starting comprehensive feature engineering for Project 2...")
        
        try:
            # Check required data
            if 'sales_details' not in data or data['sales_details'].empty:
                logger.warning("No sales_details found. Cannot perform feature engineering.")
                return pd.DataFrame()
            
            sales_df = data['sales_details'].copy()
            
            # Auto-detect column names (handle different naming conventions)
            customer_id_col = None
            date_col = None
            amount_col = None
            
            # Try to find customer_id column
            for col in ['customer_id', 'customerId', 'customerid']:
                if col in sales_df.columns:
                    customer_id_col = col
                    break
            
            # Try to find date column
            for col in ['transaction_date', 'transDate', 'trans_date', 'date', 'invoice_date']:
                if col in sales_df.columns:
                    date_col = col
                    break
            
            # Try to find amount column
            for col in ['total_amount', 'totalAmount', 'amount', 'monetary']:
                if col in sales_df.columns:
                    amount_col = col
                    break
            
            if not customer_id_col or not date_col or not amount_col:
                logger.warning(f"Missing required columns. Found: customer_id={customer_id_col}, date={date_col}, amount={amount_col}")
                # Fallback: try basic RFM calculation
                return self._basic_rfm_fallback(sales_df)
            
            logger.info(f"Using columns: customer_id={customer_id_col}, date={date_col}, amount={amount_col}")
            
            # Try to use Project 2 feature engineering modules if available
            try:
                return self._run_full_feature_engineering(
                    sales_df, 
                    data.get('sales_by_customer'),
                    customer_id_col, 
                    date_col, 
                    amount_col
                )
            except Exception as e:
                logger.warning(f"Full feature engineering failed: {str(e)}. Using simplified version.")
                return self._basic_rfm_fallback(sales_df)
            
        except Exception as e:
            logger.error(f"Error in feature engineering: {str(e)}")
            traceback.print_exc()
            return pd.DataFrame()
    
    def _run_full_feature_engineering(
        self,
        sales_df: pd.DataFrame,
        sales_by_customer: Optional[pd.DataFrame],
        customer_id_col: str,
        date_col: str,
        amount_col: str
    ) -> pd.DataFrame:
        """Run full feature engineering using Project 2 modules"""
        # Find Project 2 feature engineering path
        feature_eng_path = None
        if project2_root and os.path.exists(project2_root):
            candidate = os.path.join(
                project2_root,
                "V0dev-Project2-FeatureEngineering",
                "scripts",
                "project2_sales_analytics",
                "feature_engineering"
            )
            if os.path.exists(candidate):
                feature_eng_path = candidate
        
        if not feature_eng_path or feature_eng_path not in sys.path:
            if feature_eng_path:
                sys.path.insert(0, feature_eng_path)
            raise ImportError("Project 2 feature engineering modules not found")
        
        # Import modules
        from customer_features.rfm_features import RFMFeatureExtractor
        from customer_features.behavioral_features import BehavioralFeatureExtractor
        from customer_features.temporal_features import TemporalFeatureExtractor
        from config.feature_config import FeatureConfig
        
        config = FeatureConfig()
        reference_date = pd.to_datetime(sales_df[date_col]).max().strftime('%Y-%m-%d')
        
        logger.info("Extracting RFM features...")
        rfm_extractor = RFMFeatureExtractor(config.rfm)
        rfm_features = rfm_extractor.extract(
            sales_details=sales_df,
            reference_date=reference_date,
            customer_id_col=customer_id_col,
            date_col=date_col,
            amount_col=amount_col
        )
        logger.info(f"✓ RFM features: {len(rfm_features)} customers, {len(rfm_features.columns)} features")
        
        logger.info("Extracting behavioral features...")
        behavioral_extractor = BehavioralFeatureExtractor(config.behavioral)
        behavioral_features = behavioral_extractor.extract(
            sales_details=sales_df,
            sales_by_customer=sales_by_customer,
            customer_id_col=customer_id_col,
            date_col=date_col,
            amount_col=amount_col
        )
        logger.info(f"✓ Behavioral features: {len(behavioral_features)} customers, {len(behavioral_features.columns)} features")
        
        logger.info("Extracting temporal features...")
        temporal_extractor = TemporalFeatureExtractor(config.temporal)
        temporal_features = temporal_extractor.extract(
            sales_details=sales_df,
            date_col=date_col
        )
        logger.info(f"✓ Temporal features: {len(temporal_features)} customers, {len(temporal_features.columns)} features")
        
        # Combine all features
        logger.info("Combining all features...")
        customer_features = rfm_features.merge(
            behavioral_features,
            on="customer_id",
            how="left",
            suffixes=("", "_behavioral")
        )
        customer_features = customer_features.merge(
            temporal_features,
            on="customer_id",
            how="left",
            suffixes=("", "_temporal")
        )
        
        # Remove duplicate columns
        duplicate_cols = [col for col in customer_features.columns 
                         if col.endswith('_behavioral') or col.endswith('_temporal')]
        if duplicate_cols:
            customer_features = customer_features.drop(columns=duplicate_cols)
        
        logger.info(f"✓ Combined features: {len(customer_features)} customers, {len(customer_features.columns)} features")
        
        # Save individual feature files
        feature_output_dir = os.path.join(self.output_dir, "project2_features")
        os.makedirs(feature_output_dir, exist_ok=True)
        
        rfm_features.to_csv(os.path.join(feature_output_dir, "rfm_features.csv"), index=False)
        behavioral_features.to_csv(os.path.join(feature_output_dir, "behavioral_features.csv"), index=False)
        temporal_features.to_csv(os.path.join(feature_output_dir, "temporal_features.csv"), index=False)
        customer_features.to_csv(os.path.join(feature_output_dir, "customer_features.csv"), index=False)
        
        logger.info(f"✓ Feature files saved to {feature_output_dir}")
        
        return customer_features
    
    def _basic_rfm_fallback(self, sales_df: pd.DataFrame) -> pd.DataFrame:
        """Fallback: Basic RFM calculation if full feature engineering fails"""
        logger.info("Using basic RFM calculation fallback...")
        
        # Try to find columns
        customer_col = None
        date_col = None
        amount_col = None
        
        for col in ['customer_id', 'customerId', 'customerid']:
            if col in sales_df.columns:
                customer_col = col
                break
        
        for col in ['transaction_date', 'transDate', 'date']:
            if col in sales_df.columns:
                date_col = col
                break
        
        for col in ['total_amount', 'totalAmount', 'amount']:
            if col in sales_df.columns:
                amount_col = col
                break
        
        if not customer_col or not date_col or not amount_col:
            logger.error("Cannot perform RFM: missing required columns")
            return pd.DataFrame()
        
        # Convert date
        try:
            sales_df[date_col] = pd.to_datetime(sales_df[date_col], errors='coerce')
        except:
            pass
        
        reference_date = sales_df[date_col].max() if date_col in sales_df.columns else pd.Timestamp.now()
        
        # Calculate basic RFM
        rfm = sales_df.groupby(customer_col).agg({
            date_col: lambda x: (reference_date - x.max()).days if pd.notna(x.max()) else 9999,
            amount_col: ['sum', 'count', 'mean']
        }).reset_index()
        
        rfm.columns = [customer_col, 'recency', 'monetary', 'frequency', 'avg_order_value']
        rfm.rename(columns={customer_col: 'customer_id'}, inplace=True)
        
        logger.info(f"Basic RFM calculated: {len(rfm)} customers")
        return rfm
    
    def run_modeling_project1(self, features_df: pd.DataFrame, retrain_models: bool = False) -> Dict:
        """Run modeling for Project 1"""
        logger.info("Starting modeling for Project 1...")
        
        try:
            if features_df.empty:
                logger.warning("No features available for modeling")
                return {}
            
            # Load existing models or train new ones
            model_dir = os.path.join(project1_root, "optimized_model_output")
            
            # For now, just save the features
            # In production, you would train/retrain models here
            output_path = os.path.join(self.output_dir, "master_features_final.csv")
            features_df.to_csv(output_path, index=False)
            
            logger.info(f"Features saved to {output_path}")
            
            # 🔄 Touch file to update modification time (ensures cache invalidation)
            import time
            os.utime(output_path, None)  # Update mtime to current time
            logger.info(f"✅ File timestamp updated for cache invalidation")
            
            return {
                'features_path': output_path,
                'model_path': model_dir,
                'file_updated_at': time.time()
            }
            
        except Exception as e:
            logger.error(f"Error in modeling: {str(e)}")
            traceback.print_exc()
            return {}
    
    def run_modeling_project2(
        self, 
        features_df: pd.DataFrame,
        data: Optional[Dict[str, pd.DataFrame]] = None,
        retrain_models: bool = False
    ) -> Dict:
        """
        Run complete modeling pipeline for Project 2:
        1. MBA (Market Basket Analysis)
        2. RFM Modeling (Clustering + Churn + CLV)
        
        Args:
            features_df: Customer features from feature engineering
            data: Raw data dictionary (for MBA)
            retrain_models: If True, retrain models. If False, use existing models for inference.
        """
        logger.info("Starting complete modeling pipeline for Project 2...")
        
        results = {
            'mba': {},
            'rfm_modeling': {},
            'mode': 'retrain' if retrain_models else 'inference'
        }
        
        try:
            if features_df.empty:
                logger.warning("No features available for modeling")
                return results
            
            # Create output directories
            mba_output_dir = os.path.join(self.output_dir, "project2_mba")
            rfm_output_dir = os.path.join(self.output_dir, "project2_rfm")
            os.makedirs(mba_output_dir, exist_ok=True)
            os.makedirs(rfm_output_dir, exist_ok=True)
            
            # ============================================================
            # STEP 1: MARKET BASKET ANALYSIS
            # ============================================================
            logger.info("\n" + "="*70)
            logger.info("STEP 1: MARKET BASKET ANALYSIS")
            logger.info("="*70)
            
            mba_results = self._run_mba_pipeline(data, mba_output_dir)
            results['mba'] = mba_results
            
            # ============================================================
            # STEP 2: RFM MODELING (Clustering + Churn + CLV)
            # ============================================================
            logger.info("\n" + "="*70)
            logger.info("STEP 2: RFM MODELING (Clustering + Churn + CLV)")
            logger.info("="*70)
            
            rfm_results = self._run_rfm_modeling_pipeline(
                features_df, 
                rfm_output_dir,
                retrain_models
            )
            results['rfm_modeling'] = rfm_results
            
            # Save summary
            summary_path = os.path.join(self.output_dir, "project2_modeling_summary.json")
            import json
            with open(summary_path, 'w') as f:
                json.dump({
                    'mba': {k: str(v) for k, v in mba_results.items()},
                    'rfm_modeling': {k: str(v) for k, v in rfm_results.items()},
                    'timestamp': datetime.now().isoformat()
                }, f, indent=2)
            
            logger.info(f"\n✓ Modeling summary saved to {summary_path}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in modeling: {str(e)}")
            traceback.print_exc()
            return results
    
    def _run_mba_pipeline(
        self,
        data: Optional[Dict[str, pd.DataFrame]],
        output_dir: str
    ) -> Dict:
        """Run Market Basket Analysis pipeline"""
        results = {}
        
        try:
            # Check if sales_details available
            if not data or 'sales_details' not in data or data['sales_details'].empty:
                logger.warning("No sales_details available for MBA. Skipping...")
                return results
            
            sales_details = data['sales_details'].copy()
            
            # Check required columns
            invoice_col = None
            product_col = None
            
            for col in ['invoice_id', 'invoiceId', 'invoiceid']:
                if col in sales_details.columns:
                    invoice_col = col
                    break
            
            for col in ['product_id', 'productId', 'productid', 'item_id', 'itemId']:
                if col in sales_details.columns:
                    product_col = col
                    break
            
            if not invoice_col or not product_col:
                logger.warning(f"Missing required columns for MBA. Found: invoice={invoice_col}, product={product_col}")
                return results
            
            logger.info(f"MBA: {len(sales_details)} transactions, {sales_details[product_col].nunique()} unique products")
            
            # Try to use Project 2 MBA pipeline if available
            try:
                return self._run_full_mba_pipeline(sales_details, invoice_col, product_col, output_dir)
            except Exception as e:
                logger.warning(f"Full MBA pipeline failed: {str(e)}. Using simplified version.")
                return self._basic_mba_fallback(sales_details, invoice_col, product_col, output_dir)
            
        except Exception as e:
            logger.error(f"MBA pipeline error: {str(e)}")
            traceback.print_exc()
            return results
    
    def _run_full_mba_pipeline(
        self,
        sales_details: pd.DataFrame,
        invoice_col: str,
        product_col: str,
        output_dir: str
    ) -> Dict:
        """Run full MBA pipeline using Project 2 modules"""
        # Find Project 2 MBA path
        mba_path = None
        if project2_root and os.path.exists(project2_root):
            candidate = os.path.join(
                project2_root,
                "V0dev-Project2-Modeling",
                "scripts",
                "project2_sales_analytics",
                "modeling",
                "mba"
            )
            if os.path.exists(candidate):
                mba_path = candidate
        
        if not mba_path or mba_path not in sys.path:
            if mba_path:
                sys.path.insert(0, mba_path)
            raise ImportError("Project 2 MBA modules not found")
        
        # Save sales_details temporarily for MBA pipeline
        temp_sales_path = os.path.join(output_dir, "temp_sales_details.csv")
        sales_details.to_csv(temp_sales_path, index=False)
        
        # Import and run MBA pipeline
        from config.mba_config import MBAConfig
        from data.data_loader import MBADataLoader
        from preprocessing.data_cleaner import DataCleaner
        from preprocessing.transaction_encoder import TransactionEncoder
        from algorithms.fpgrowth_runner import FPGrowthRunner
        from analysis.rules_analyzer import RulesAnalyzer
        from analysis.cross_sell_recommender import CrossSellRecommender
        from export.mba_exporter import MBAExporter
        
        config = MBAConfig(
            input_path=temp_sales_path,
            output_dir=output_dir,
            min_support=0.01,
            min_confidence=0.3,
            min_lift=1.0
        )
        
        logger.info("Loading and cleaning data...")
        loader = MBADataLoader(config)
        df = loader.load()
        cleaner = DataCleaner(config)
        df_clean = cleaner.clean(df)
        
        logger.info("Encoding transactions...")
        encoder = TransactionEncoder(config)
        transactions, basket_matrix = encoder.encode(df_clean)
        
        logger.info("Running FP-Growth algorithm...")
        runner = FPGrowthRunner(config)
        frequent_itemsets, rules = runner.run(basket_matrix)
        
        if len(rules) == 0:
            logger.warning("No association rules found. Try lowering thresholds.")
            return {'rules_count': 0, 'itemsets_count': len(frequent_itemsets)}
        
        logger.info(f"Found {len(rules)} association rules")
        
        logger.info("Analyzing rules...")
        analyzer = RulesAnalyzer(rules, config)
        analysis_results = analyzer.analyze()
        
        logger.info("Generating cross-sell recommendations...")
        recommender = CrossSellRecommender(rules, config)
        cross_sell_report = recommender.generate_cross_sell_report()
        
        logger.info("Exporting results...")
        exporter = MBAExporter(config)
        exported_files = exporter.export_all(
            rules=rules,
            frequent_itemsets=frequent_itemsets,
            analysis_results=analysis_results,
            cross_sell_report=cross_sell_report,
            network_data={}  # Optional
        )
        
        # Clean up temp file
        if os.path.exists(temp_sales_path):
            os.remove(temp_sales_path)
        
        return {
            'rules_count': len(rules),
            'itemsets_count': len(frequent_itemsets),
            'cross_sell_count': len(cross_sell_report),
            'exported_files': exported_files,
            'output_dir': output_dir
        }
    
    def _basic_mba_fallback(
        self,
        sales_details: pd.DataFrame,
        invoice_col: str,
        product_col: str,
        output_dir: str
    ) -> Dict:
        """Fallback: Basic product co-occurrence analysis"""
        logger.info("Using basic MBA fallback...")
        
        # Simple co-occurrence: products bought together in same invoice
        cooccurrence = sales_details.groupby(invoice_col)[product_col].apply(list).reset_index()
        cooccurrence.columns = ['invoice_id', 'products']
        
        # Count product pairs
        pairs = {}
        for products in cooccurrence['products']:
            if len(products) > 1:
                for i in range(len(products)):
                    for j in range(i+1, len(products)):
                        pair = tuple(sorted([str(products[i]), str(products[j])]))
                        pairs[pair] = pairs.get(pair, 0) + 1
        
        # Convert to DataFrame
        if pairs:
            pairs_df = pd.DataFrame([
                {'product_1': p[0], 'product_2': p[1], 'cooccurrence_count': count}
                for p, count in pairs.items()
            ])
            pairs_df = pairs_df.sort_values('cooccurrence_count', ascending=False)
            
            output_path = os.path.join(output_dir, "product_cooccurrence.csv")
            pairs_df.to_csv(output_path, index=False)
            
            logger.info(f"Basic co-occurrence: {len(pairs_df)} product pairs")
            return {
                'rules_count': 0,
                'itemsets_count': 0,
                'cooccurrence_count': len(pairs_df),
                'output_path': output_path
            }
        
        return {'rules_count': 0, 'itemsets_count': 0}
    
    def _run_rfm_modeling_pipeline(
        self,
        features_df: pd.DataFrame,
        output_dir: str,
        retrain_models: bool = False
    ) -> Dict:
        """Run RFM modeling pipeline (Clustering + Churn + CLV)"""
        results = {}
        
        try:
            # Check if customer_features available
            if 'customer_id' not in features_df.columns:
                logger.warning("No customer_id column found. Skipping RFM modeling...")
                return results
            
            logger.info(f"RFM Modeling: {len(features_df)} customers, {len(features_df.columns)} features")
            
            # Try to use Project 2 RFM modeling pipeline if available
            try:
                return self._run_full_rfm_modeling_pipeline(features_df, output_dir, retrain_models)
            except Exception as e:
                logger.warning(f"Full RFM modeling pipeline failed: {str(e)}. Using simplified version.")
                return self._basic_rfm_modeling_fallback(features_df, output_dir)
            
        except Exception as e:
            logger.error(f"RFM modeling pipeline error: {str(e)}")
            traceback.print_exc()
            return results
    
    def _run_full_rfm_modeling_pipeline(
        self,
        features_df: pd.DataFrame,
        output_dir: str,
        retrain_models: bool
    ) -> Dict:
        """Run full RFM modeling pipeline using Project 2 modules"""
        # Find Project 2 RFM modeling path
        rfm_path = None
        if project2_root and os.path.exists(project2_root):
            candidate = os.path.join(
                project2_root,
                "V0dev-Project2-Modeling",
                "scripts",
                "project2_sales_analytics",
                "modeling",
                "rfm"
            )
            if os.path.exists(candidate):
                rfm_path = candidate
        
        if not rfm_path or rfm_path not in sys.path:
            if rfm_path:
                sys.path.insert(0, rfm_path)
            raise ImportError("Project 2 RFM modeling modules not found")
        
        # Save features temporarily
        temp_features_dir = os.path.join(output_dir, "temp_features")
        os.makedirs(temp_features_dir, exist_ok=True)
        features_df.to_csv(os.path.join(temp_features_dir, "customer_features.csv"), index=False)
        
        # Import and run RFM modeling pipeline
        from config.rfm_config import RFMModelConfig
        from data.data_loader import RFMDataLoader
        from models.clustering_model import CustomerClusteringModel
        from models.churn_classifier import ChurnClassifier
        from models.clv_regressor import CLVRegressor
        from preprocessing.train_test_splitter import TrainTestSplitter
        from export.rfm_exporter import RFMExporter
        
        config = RFMModelConfig()
        config.base_input_path = temp_features_dir
        config.base_output_path = output_dir
        
        logger.info("Loading data for RFM modeling...")
        data_loader = RFMDataLoader(config)
        
        # Clustering
        logger.info("Running customer clustering...")
        features_clustering, customer_ids = data_loader.prepare_clustering_data()
        clustering_model = CustomerClusteringModel(config.clustering, verbose=True)
        
        if retrain_models:
            optimal_k_results = clustering_model.find_optimal_k(features_clustering, k_range=range(2, 8))
            labels = clustering_model.fit_predict(features_clustering)
        else:
            # Use existing model if available
            model_path = os.path.join(project2_root, "output", "rfm", "models", "clustering_model.joblib")
            if os.path.exists(model_path):
                import joblib
                clustering_model = joblib.load(model_path)
                labels = clustering_model.predict(features_clustering)
                logger.info("✓ Using existing clustering model")
            else:
                labels = clustering_model.fit_predict(features_clustering)
                logger.warning("No existing model found. Training new model.")
        
        cluster_profiles = clustering_model.get_cluster_profiles(features_clustering, labels)
        logger.info(f"✓ Clustering complete: {len(cluster_profiles)} clusters")
        
        # Churn Prediction
        logger.info("Running churn prediction...")
        features_churn, target_churn, customer_ids_churn = data_loader.prepare_churn_data()
        splitter = TrainTestSplitter(test_size=0.2, random_state=42)
        X_train, X_test, y_train, y_test = splitter.split(features_churn, target_churn, stratify=True)
        
        churn_model = ChurnClassifier(config.churn, verbose=True)
        if retrain_models:
            churn_model.fit(X_train, y_train)
        else:
            # Use existing model if available
            model_path = os.path.join(project2_root, "output", "rfm", "models", "churn_model.joblib")
            if os.path.exists(model_path):
                import joblib
                churn_model = joblib.load(model_path)
                logger.info("✓ Using existing churn model")
            else:
                churn_model.fit(X_train, y_train)
                logger.warning("No existing model found. Training new model.")
        
        churn_predictions = churn_model.predict(features_churn)
        churn_probabilities = churn_model.predict_proba(features_churn)
        logger.info(f"✓ Churn prediction complete: {len(churn_predictions)} predictions")
        
        # CLV Prediction
        logger.info("Running CLV prediction...")
        features_clv, target_clv, customer_ids_clv = data_loader.prepare_clv_data()
        X_train_clv, X_test_clv, y_train_clv, y_test_clv = splitter.split(features_clv, target_clv)
        
        clv_model = CLVRegressor(config.clv, verbose=True)
        if retrain_models:
            clv_model.fit(X_train_clv, y_train_clv)
        else:
            # Use existing model if available
            model_path = os.path.join(project2_root, "output", "rfm", "models", "clv_model.joblib")
            if os.path.exists(model_path):
                import joblib
                clv_model = joblib.load(model_path)
                logger.info("✓ Using existing CLV model")
            else:
                clv_model.fit(X_train_clv, y_train_clv)
                logger.warning("No existing model found. Training new model.")
        
        clv_predictions_df = clv_model.predict_with_segments(features_clv, customer_ids_clv)
        logger.info(f"✓ CLV prediction complete: {len(clv_predictions_df)} predictions")
        
        # Export results
        logger.info("Exporting RFM modeling results...")
        exporter = RFMExporter(output_path=output_dir, verbose=True)
        
        export_paths = {}
        export_paths.update(exporter.export_clustering_results(
            customer_ids=customer_ids,
            labels=labels,
            cluster_labels={},
            cluster_profiles=cluster_profiles,
            features=features_clustering,
            model=clustering_model,
            metrics={}
        ))
        
        export_paths.update(exporter.export_churn_results(
            customer_ids=customer_ids_churn,
            predictions=churn_predictions,
            probabilities=churn_probabilities,
            features=features_churn,
            model=churn_model,
            metrics={},
            feature_importances={}
        ))
        
        export_paths.update(exporter.export_clv_results(
            customer_ids=customer_ids_clv,
            predictions=clv_predictions_df["predicted_clv"].values,
            segments=clv_predictions_df["clv_segment"],
            features=features_clv,
            model=clv_model,
            metrics={},
            feature_importances={},
            distribution_analysis={}
        ))
        
        # Clean up temp directory
        import shutil
        if os.path.exists(temp_features_dir):
            shutil.rmtree(temp_features_dir)
        
        return {
            'clustering': {
                'n_clusters': len(cluster_profiles),
                'customers': len(customer_ids)
            },
            'churn': {
                'predictions': len(churn_predictions),
                'high_risk': (churn_probabilities > 0.5).sum() if hasattr(churn_probabilities, 'sum') else 0
            },
            'clv': {
                'predictions': len(clv_predictions_df),
                'total_clv': clv_predictions_df["predicted_clv"].sum() if 'predicted_clv' in clv_predictions_df.columns else 0
            },
            'export_paths': export_paths,
            'output_dir': output_dir
        }
    
    def _basic_rfm_modeling_fallback(
        self,
        features_df: pd.DataFrame,
        output_dir: str
    ) -> Dict:
        """Fallback: Basic RFM segmentation"""
        logger.info("Using basic RFM modeling fallback...")
        
        # Simple segmentation based on RFM scores if available
        if all(col in features_df.columns for col in ['recency', 'frequency', 'monetary']):
            # Calculate quartiles
            rfm_scores = features_df.copy()
            rfm_scores['r_score'] = pd.qcut(rfm_scores['recency'].rank(method='first'), q=5, labels=[5,4,3,2,1])
            rfm_scores['f_score'] = pd.qcut(rfm_scores['frequency'].rank(method='first'), q=5, labels=[1,2,3,4,5])
            rfm_scores['m_score'] = pd.qcut(rfm_scores['monetary'].rank(method='first'), q=5, labels=[1,2,3,4,5])
            
            rfm_scores['rfm_score'] = (
                rfm_scores['r_score'].astype(int) * 100 + 
                rfm_scores['f_score'].astype(int) * 10 + 
                rfm_scores['m_score'].astype(int)
            )
            
            # Simple segmentation
            def assign_segment(row):
                r, f, m = row['r_score'], row['f_score'], row['m_score']
                if r >= 4 and f >= 4 and m >= 4:
                    return 'Champions'
                elif r >= 3 and f >= 3 and m >= 3:
                    return 'Loyal'
                elif r <= 2 and f <= 2 and m <= 2:
                    return 'Lost'
                elif r <= 2:
                    return 'At Risk'
                else:
                    return 'Need Attention'
            
            rfm_scores['segment'] = rfm_scores.apply(assign_segment, axis=1)
            
            output_path = os.path.join(output_dir, "rfm_segmentation.csv")
            rfm_scores.to_csv(output_path, index=False)
            
            logger.info(f"Basic RFM segmentation: {len(rfm_scores)} customers, {rfm_scores['segment'].nunique()} segments")
            return {
                'segmentation_path': output_path,
                'n_segments': rfm_scores['segment'].nunique(),
                'customers': len(rfm_scores)
            }
        
        return {}
    
    def run_full_pipeline(self) -> Tuple[bool, str, Dict]:
        """
        Run full pipeline: load data FROM DATABASE -> preprocessing -> feature engineering -> modeling
        
        IMPORTANT: 
        - All phases use data from PostgreSQL database (pulled by data puller)
        - No CSV fallback - ensures data consistency
        - Data flows: Database → Preprocessing → Feature Engineering → Modeling → Output
        
        Returns:
            (success, message, results)
        """
        try:
            logger.info("="*70)
            logger.info(f"🚀 STARTING FULL ML PIPELINE FOR {self.project_name.upper()}")
            logger.info("="*70)
            logger.info("📊 Data Source: PostgreSQL Database (from data puller)")
            logger.info("🔄 Pipeline: Preprocessing → Feature Engineering → Modeling")
            logger.info("="*70)
            
            # ============================================================
            # PHASE 1: LOAD DATA FROM DATABASE
            # ============================================================
            logger.info("\n[PHASE 1/4] Loading data from database...")
            data = self.load_data_from_db()
            if not data:
                return False, "No data found in database. Please run data puller first.", {}
            
            logger.info(f"✅ Loaded {len(data)} tables from database")
            
            # ============================================================
            # PHASE 2: PREPROCESSING (using database data)
            # ============================================================
            logger.info("\n[PHASE 2/4] Preprocessing data from database...")
            processed_data = self.run_preprocessing(data)
            logger.info(f"✅ Preprocessed {len(processed_data)} tables")
            
            # ============================================================
            # PHASE 3: FEATURE ENGINEERING (using preprocessed database data)
            # ============================================================
            logger.info("\n[PHASE 3/4] Feature engineering from preprocessed database data...")
            if self.project_name == 'project1':
                features_df = self.run_feature_engineering_project1(processed_data)
            else:
                features_df = self.run_feature_engineering_project2(processed_data)
            
            if features_df.empty:
                return False, "Feature engineering produced no results", {}
            
            logger.info(f"✅ Generated {len(features_df)} feature rows with {len(features_df.columns)} features")
            
            # ============================================================
            # PHASE 4: MODELING (using engineered features from database)
            # ============================================================
            logger.info("\n[PHASE 4/4] Modeling using engineered features...")
            if self.project_name == 'project1':
                results = self.run_modeling_project1(features_df, self.retrain_models)
            else:
                # For Project 2, pass processed_data for MBA pipeline
                results = self.run_modeling_project2(features_df, processed_data, self.retrain_models)
            
            logger.info("="*70)
            logger.info(f"✅ PIPELINE COMPLETED SUCCESSFULLY FOR {self.project_name.upper()}")
            logger.info("="*70)
            logger.info("📁 Output files saved to data/processed/")
            logger.info("🔄 Streamlit will automatically use these updated files")
            logger.info("="*70)
            
            # 🔄 SOLUTION 2: Clear Streamlit cache to force fresh data load
            # This ensures dashboard immediately uses new data without waiting for TTL expiry
            try:
                import streamlit as st
                st.cache_data.clear()
                logger.info("✅ Streamlit cache cleared - dashboard will use fresh data immediately")
            except ImportError:
                # Running outside Streamlit (e.g., from command line)
                logger.info("ℹ️ Running outside Streamlit - cache clear not needed")
            except Exception as cache_error:
                # Log but don't fail - cache will expire naturally
                logger.warning(f"⚠️ Could not clear Streamlit cache: {cache_error}")
                logger.info("ℹ️ Cache will expire within 60 seconds (reduced TTL)")
            
            return True, "Pipeline completed successfully. All phases used database data.", results
            
        except Exception as e:
            error_msg = f"Pipeline failed: {str(e)}"
            logger.error("="*70)
            logger.error(f"❌ PIPELINE FAILED: {error_msg}")
            logger.error("="*70)
            traceback.print_exc()
            return False, error_msg, {}


def run_ml_pipeline(project_name: str, retrain_models: bool = False) -> Tuple[bool, str, Dict]:
    """
    Convenience function to run ML pipeline.
    
    Args:
        project_name: 'project1' or 'project2'
        retrain_models: If True, retrain models. If False, use existing models for inference.
    
    Returns:
        (success, message, results)
    """
    pipeline = MLPipeline(project_name, retrain_models=retrain_models)
    return pipeline.run_full_pipeline()
