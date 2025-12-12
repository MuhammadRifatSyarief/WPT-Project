"""
==========================================================================
PROJECT 2: SALES PERFORMANCE & CUSTOMER SEGMENTATION ANALYTICS
==========================================================================
File: modules/data_enricher.py
Purpose: ROBUST Data enrichment and preprocessing with validation
Author: v0
Created: 2025
==========================================================================

OVERVIEW:
---------
Comprehensive data enrichment including:
- USD to IDR currency detection and conversion
- Hierarchical price truth establishment
- Missing value imputation from master data
- Data quality validation and reporting
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Any, List, Tuple

import sys
sys.path.append('..')
from config.constants import CURRENCY_CONFIG


class DataEnricher:
    """
    ROBUST Data Enricher for preprocessing and enrichment.
    
    Key Improvements:
    -----------------
    1. Hierarchical price truth (Sales -> Purchase -> Master)
    2. Smart USD detection with configurable thresholds
    3. Comprehensive missing value imputation
    4. Data quality reporting
    5. Validation at each step
    """
    
    def __init__(
        self, 
        data: Dict[str, pd.DataFrame],
        mappings: Dict[str, Dict]
    ):
        self.data = data
        self.mappings = mappings
        self.usd_rate = CURRENCY_CONFIG['USD_TO_IDR_RATE']
        self.min_valid_idr = CURRENCY_CONFIG['MIN_VALID_IDR_PRICE']
        
        self.price_truth: Dict[str, float] = {}
        
        self.enrichment_stats = {
            'usd_conversions': 0,
            'values_imputed': {},
            'validation_issues': []
        }
    
    def enrich_all(self) -> Dict[str, pd.DataFrame]:
        """
        Run all enrichment processes in correct order.
        
        Returns:
            Enriched data dictionary
        """
        print("\n" + "=" * 60)
        print("DATA ENRICHMENT & PREPROCESSING")
        print("=" * 60)
        
        self._establish_price_truth()
        
        # Step 1: Convert USD prices
        self._convert_usd_prices()
        
        # Step 2: Enrich from master data
        self._enrich_sales_details()
        
        # Step 3: Re-aggregate after enrichment
        self._re_aggregate_after_enrichment()
        
        # Step 4: Final standardization
        self._standardize_columns()
        
        # Step 5: Calculate derived metrics
        self.calculate_derived_metrics()
        
        # Step 6: Validation report
        self._print_enrichment_report()
        
        print("\n[OK] Data enrichment complete")
        
        return self.data
    
    # ==========================================================================
    # ==========================================================================
    
    def _establish_price_truth(self) -> None:
        """
        Establish price truth hierarchy:
        1. Sales prices (most reliable)
        2. Purchase prices (fallback)
        3. Master item prices (last resort)
        """
        print("\n--- STEP 0: ESTABLISHING PRICE TRUTH ---")
        
        # From sales details
        if 'sales_details' in self.data and not self.data['sales_details'].empty:
            df = self.data['sales_details'].copy()
            
            # Convert to numeric
            df['unit_price'] = pd.to_numeric(df['unit_price'], errors='coerce').fillna(0)
            df['product_id'] = df['product_id'].astype(str)
            
            # Filter valid prices (likely IDR)
            valid_prices = df[df['unit_price'] >= self.min_valid_idr]
            
            if not valid_prices.empty:
                avg_prices = valid_prices.groupby('product_id')['unit_price'].mean()
                self.price_truth = avg_prices.to_dict()
                print(f"   Price truth from sales: {len(self.price_truth):,} products")
            else:
                potential_usd = df[df['unit_price'] > 0]
                if not potential_usd.empty:
                    avg_price = potential_usd['unit_price'].mean()
                    print(f"   [INFO] Avg unit_price = {avg_price:.2f} (likely USD, will convert)")
        
        # From item master as fallback
        if 'items' in self.data and not self.data['items'].empty:
            df = self.data['items'].copy()
            df['unitPrice'] = pd.to_numeric(df.get('unitPrice', 0), errors='coerce').fillna(0)
            df['id'] = df['id'].astype(str)
            
            # Add items not in price_truth
            for _, row in df.iterrows():
                pid = row['id']
                if pid not in self.price_truth and row['unitPrice'] > 0:
                    self.price_truth[pid] = row['unitPrice']
            
            print(f"   Total price truth entries: {len(self.price_truth):,}")
    
    # ==========================================================================
    # ==========================================================================
    
    def _convert_usd_prices(self) -> None:
        """
        Convert suspected USD prices to IDR.
        Uses configurable thresholds and logging.
        """
        print("\n--- STEP 1: USD TO IDR CONVERSION ---")
        
        price_columns = ['unit_price', 'unitPrice', 'total_amount', 'monetary', 'avgCost', 'avg_price']
        
        tables_to_check = ['sales_details', 'sales_by_customer', 'sales_by_product', 'items']
        
        total_converted = 0
        
        for table_name in tables_to_check:
            if table_name not in self.data or self.data[table_name].empty:
                continue
            
            df = self.data[table_name]
            table_converted = 0
            
            for col in price_columns:
                if col not in df.columns:
                    continue
                
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
                # USD prices typically: 1 < price < 1000
                # But we also check if MAJORITY of prices are in this range
                non_zero = df[df[col] > 0][col]
                
                if len(non_zero) > 0:
                    pct_likely_usd = ((non_zero > 1) & (non_zero < self.min_valid_idr)).mean()
                    
                    # If >50% of prices look like USD, convert all
                    if pct_likely_usd > 0.5:
                        usd_mask = (df[col] > 1) & (df[col] < self.min_valid_idr)
                        count = usd_mask.sum()
                        
                        if count > 0:
                            df.loc[usd_mask, col] = df.loc[usd_mask, col] * self.usd_rate
                            table_converted += count
                            total_converted += count
            
            self.data[table_name] = df
            
            if table_converted > 0:
                print(f"   {table_name}: Converted {table_converted:,} values (USD -> IDR)")
        
        self.enrichment_stats['usd_conversions'] = total_converted
        
        if total_converted == 0:
            print("   No USD conversions needed (prices already in IDR)")
    
    # ==========================================================================
    # ==========================================================================
    
    def _enrich_sales_details(self) -> None:
        """Enrich sales_details with data from master tables."""
        print("\n--- STEP 2: ENRICHING SALES DETAILS ---")
        
        if 'sales_details' not in self.data or self.data['sales_details'].empty:
            print("   [SKIP] No sales_details to enrich")
            return
        
        df = self.data['sales_details'].copy()
        initial_count = len(df)
        
        # Ensure ID columns are strings
        df['customer_id'] = df['customer_id'].astype(str)
        df['product_id'] = df['product_id'].astype(str)
        
        if 'customers' in self.mappings:
            print("   Enriching customer data...")
            customer_map = self.mappings['customers']
            
            # Customer name
            missing_names = df['customer_name'].isna() | (df['customer_name'] == '')
            if missing_names.any():
                df.loc[missing_names, 'customer_name'] = df.loc[missing_names, 'customer_id'].apply(
                    lambda x: customer_map.get(x, {}).get('name', '')
                )
                filled = (~(df.loc[missing_names, 'customer_name'].isna() | (df.loc[missing_names, 'customer_name'] == ''))).sum()
                print(f"      Customer names imputed: {filled}")
            
            # Add customer category
            if 'customer_category' not in df.columns:
                df['customer_category'] = df['customer_id'].apply(
                    lambda x: customer_map.get(x, {}).get('categoryName', '')
                )
        
        if 'products' in self.mappings:
            print("   Enriching product data...")
            product_map = self.mappings['products']
            
            # Product code
            missing_codes = df['product_code'].isna() | (df['product_code'] == '')
            if missing_codes.any():
                df.loc[missing_codes, 'product_code'] = df.loc[missing_codes, 'product_id'].apply(
                    lambda x: product_map.get(x, {}).get('no', '')
                )
                filled = (~(df.loc[missing_codes, 'product_code'].isna() | (df.loc[missing_codes, 'product_code'] == ''))).sum()
                print(f"      Product codes imputed: {filled}")
            
            # Product name
            missing_names = df['product_name'].isna() | (df['product_name'] == '')
            if missing_names.any():
                df.loc[missing_names, 'product_name'] = df.loc[missing_names, 'product_id'].apply(
                    lambda x: product_map.get(x, {}).get('name', '')
                )
                filled = (~(df.loc[missing_names, 'product_name'].isna() | (df.loc[missing_names, 'product_name'] == ''))).sum()
                print(f"      Product names imputed: {filled}")
            
            # Add product category
            if 'product_category' not in df.columns:
                df['product_category'] = df['product_id'].apply(
                    lambda x: product_map.get(x, {}).get('itemCategoryName', '')
                )
            
            if self.price_truth:
                missing_prices = df['unit_price'] <= 0
                if missing_prices.any():
                    df.loc[missing_prices, 'unit_price'] = df.loc[missing_prices, 'product_id'].apply(
                        lambda x: self.price_truth.get(x, 0)
                    )
                    filled = (df.loc[missing_prices, 'unit_price'] > 0).sum()
                    print(f"      Unit prices imputed: {filled}")
                    
                    need_recalc = (df['total_amount'] <= 0) & (df['unit_price'] > 0) & (df['quantity'] > 0)
                    if need_recalc.any():
                        df.loc[need_recalc, 'total_amount'] = (
                            df.loc[need_recalc, 'unit_price'] * df.loc[need_recalc, 'quantity']
                        )
                        print(f"      Total amounts recalculated: {need_recalc.sum()}")
        
        self.data['sales_details'] = df
        print(f"   [OK] Enriched {initial_count:,} records")
        
        self._validate_enrichment('sales_details')
    
    def _validate_enrichment(self, table_name: str) -> None:
        """Validate data after enrichment."""
        if table_name not in self.data:
            return
        
        df = self.data[table_name]
        
        print(f"\n   --- Validation: {table_name} ---")
        
        # Check key columns
        checks = {
            'customer_id': (df['customer_id'] != '') & df['customer_id'].notna() if 'customer_id' in df.columns else None,
            'product_id': (df['product_id'] != '') & df['product_id'].notna() if 'product_id' in df.columns else None,
            'total_amount': df['total_amount'] > 0 if 'total_amount' in df.columns else None,
            'unit_price': df['unit_price'] > 0 if 'unit_price' in df.columns else None,
        }
        
        for col, mask in checks.items():
            if mask is not None:
                valid_pct = mask.mean() * 100
                print(f"      {col}: {valid_pct:.1f}% valid")
                
                if valid_pct < 50:
                    self.enrichment_stats['validation_issues'].append(f"{table_name}.{col}: only {valid_pct:.1f}% valid")
    
    # ==========================================================================
    # ==========================================================================
    
    def _re_aggregate_after_enrichment(self) -> None:
        """Re-aggregate sales data after enrichment to ensure accuracy."""
        print("\n--- STEP 3: RE-AGGREGATING AFTER ENRICHMENT ---")
        
        if 'sales_details' not in self.data or self.data['sales_details'].empty:
            print("   [SKIP] No sales_details to aggregate")
            return
        
        df = self.data['sales_details'].copy()
        
        if (df['customer_id'] != '').any():
            valid_df = df[(df['customer_id'] != '') & df['customer_id'].notna()]
            
            if not valid_df.empty:
                # Parse dates
                valid_df['transaction_date'] = pd.to_datetime(
                    valid_df['transaction_date'], 
                    errors='coerce'
                )
                
                reference_date = pd.Timestamp.now()
                
                customer_agg = valid_df.groupby('customer_id').agg({
                    'transaction_date': ['max', 'min', 'count'],
                    'invoice_id': 'nunique',
                    'total_amount': 'sum',
                    'quantity': 'sum',
                    'customer_name': 'first',
                }).reset_index()
                
                customer_agg.columns = [
                    'customer_id', 
                    'last_purchase_date', 
                    'first_purchase_date',
                    'transaction_count',
                    'total_orders', 
                    'monetary',
                    'total_items_purchased',
                    'customer_name'
                ]
                
                customer_agg['recency_days'] = (
                    reference_date - customer_agg['last_purchase_date']
                ).dt.days.fillna(9999)
                
                customer_agg['frequency'] = customer_agg['total_orders']
                
                customer_agg['avg_order_value'] = (
                    customer_agg['monetary'] / customer_agg['total_orders'].replace(0, 1)
                ).fillna(0)
                
                self.data['sales_by_customer'] = customer_agg
                print(f"   [OK] sales_by_customer: {len(customer_agg):,} customers")
                print(f"        Total monetary: Rp {customer_agg['monetary'].sum():,.0f}")
        
        if (df['product_id'] != '').any():
            valid_df = df[(df['product_id'] != '') & df['product_id'].notna()]
            
            if not valid_df.empty:
                product_agg = valid_df.groupby('product_id').agg({
                    'product_code': 'first',
                    'product_name': 'first',
                    'quantity': 'sum',
                    'total_amount': 'sum',
                    'invoice_id': 'nunique',
                    'customer_id': 'nunique',
                }).reset_index()
                
                product_agg.columns = [
                    'product_id',
                    'product_code',
                    'product_name',
                    'total_quantity_sold',
                    'total_revenue',
                    'order_count',
                    'unique_customers',
                ]
                
                product_agg['avg_price'] = (
                    product_agg['total_revenue'] / product_agg['total_quantity_sold'].replace(0, 1)
                ).fillna(0)
                
                if 'products' in self.mappings:
                    product_agg['product_category'] = product_agg['product_id'].apply(
                        lambda x: self.mappings['products'].get(str(x), {}).get('itemCategoryName', '')
                    )
                
                self.data['sales_by_product'] = product_agg
                print(f"   [OK] sales_by_product: {len(product_agg):,} products")
                print(f"        Total revenue: Rp {product_agg['total_revenue'].sum():,.0f}")
    
    # ==========================================================================
    # STANDARDIZATION & DERIVED METRICS
    # ==========================================================================
    
    def _standardize_columns(self) -> None:
        """Standardize column names and data types."""
        print("\n--- STEP 4: STANDARDIZING COLUMNS ---")
        
        date_columns = ['transaction_date', 'last_purchase_date', 'first_purchase_date']
        
        for table_name, df in self.data.items():
            for col in date_columns:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
            
            self.data[table_name] = df
        
        print("   [OK] Columns standardized")
    
    def calculate_derived_metrics(self) -> None:
        """Calculate additional derived metrics."""
        print("\n--- STEP 5: CALCULATING DERIVED METRICS ---")
        
        # Customer metrics
        if 'sales_by_customer' in self.data and not self.data['sales_by_customer'].empty:
            df = self.data['sales_by_customer']
            
            if 'first_purchase_date' in df.columns and 'last_purchase_date' in df.columns:
                df['customer_age_days'] = (
                    df['last_purchase_date'] - df['first_purchase_date']
                ).dt.days.fillna(0)
            
            self.data['sales_by_customer'] = df
            print("   [OK] Customer metrics calculated")
        
        # Product metrics
        if 'sales_by_product' in self.data and not self.data['sales_by_product'].empty:
            df = self.data['sales_by_product']
            
            if 'total_revenue' in df.columns:
                total_revenue = df['total_revenue'].sum()
                if total_revenue > 0:
                    df['revenue_contribution_pct'] = (
                        df['total_revenue'] / total_revenue * 100
                    ).fillna(0)
            
            self.data['sales_by_product'] = df
            print("   [OK] Product metrics calculated")
    
    # ==========================================================================
    # ==========================================================================
    
    def _print_enrichment_report(self) -> None:
        """Print comprehensive enrichment report."""
        print("\n" + "=" * 60)
        print("ENRICHMENT SUMMARY REPORT")
        print("=" * 60)
        
        print(f"\nUSD Conversions: {self.enrichment_stats['usd_conversions']:,}")
        print(f"Price Truth Entries: {len(self.price_truth):,}")
        
        # Data quality summary
        print("\nData Quality After Enrichment:")
        
        for table_name, df in self.data.items():
            if isinstance(df, pd.DataFrame) and not df.empty:
                print(f"\n   {table_name}: {len(df):,} rows")
                
                # Check for critical columns
                if 'total_amount' in df.columns:
                    valid = (df['total_amount'] > 0).sum()
                    print(f"      - with revenue: {valid:,} ({valid/len(df)*100:.1f}%)")
                
                if 'monetary' in df.columns:
                    valid = (df['monetary'] > 0).sum()
                    print(f"      - with monetary: {valid:,} ({valid/len(df)*100:.1f}%)")
        
        # Issues
        if self.enrichment_stats['validation_issues']:
            print("\n[WARNING] Issues Found:")
            for issue in self.enrichment_stats['validation_issues']:
                print(f"   - {issue}")
        else:
            print("\n[OK] No critical issues found")
    
    # ==========================================================================
    # PUBLIC METHODS FOR SPECIFIC ENRICHMENT
    # ==========================================================================
    
    def get_enrichment_stats(self) -> Dict[str, Any]:
        """Get enrichment statistics."""
        return self.enrichment_stats
    
    def get_price_truth(self) -> Dict[str, float]:
        """Get established price truth mapping."""
        return self.price_truth
