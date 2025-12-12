"""
==========================================================================
PROJECT 2: SALES PERFORMANCE & CUSTOMER SEGMENTATION ANALYTICS
==========================================================================
File: modules/data_puller.py
Purpose: ROBUST Data puller - extracts customerId from invoice DETAIL
Author: v0
Created: 2025
==========================================================================
"""

import os
import time
import pickle
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Optional, Any, List

import sys
sys.path.append('..')
from config.constants import (
    API_ENDPOINTS, FILE_PATHS, API_CONFIG, 
    DATE_CONFIG, EXPORT_CONFIG
)
from .api_client import SalesAnalyticsAPIClient


class SalesDataPuller:
    """
    ROBUST Data puller for Sales Performance & Customer Segmentation Analytics.
    
    Key Fix: Extract customerId from detail.do response (not from list.do)
    """
    
    def __init__(
        self, 
        client: SalesAnalyticsAPIClient, 
        start_date: str, 
        end_date: str
    ):
        self.client = client
        self.start_date = start_date
        self.end_date = end_date
        
        self.data: Dict[str, pd.DataFrame] = {}
        self.mappings: Dict[str, Dict] = {}
        self.checkpoint_file = FILE_PATHS['CHECKPOINT_FILE']
        
        self.debug_mode = True
        self.stats = {
            'api_calls': 0,
            'records_fetched': {},
            'validation_issues': []
        }
    
    # ==========================================================================
    # CHECKPOINT MANAGEMENT
    # ==========================================================================
    
    def save_checkpoint(self) -> None:
        try:
            checkpoint_data = {
                'data': self.data,
                'mappings': self.mappings,
                'timestamp': datetime.now().isoformat(),
                'start_date': self.start_date,
                'end_date': self.end_date,
            }
            with open(self.checkpoint_file, 'wb') as f:
                pickle.dump(checkpoint_data, f)
            print(f"[CHECKPOINT] Saved")
        except Exception as e:
            print(f"[WARNING] Failed to save checkpoint: {e}")
    
    def load_checkpoint(self) -> bool:
        try:
            if os.path.exists(self.checkpoint_file):
                with open(self.checkpoint_file, 'rb') as f:
                    checkpoint_data = pickle.load(f)
                self.data = checkpoint_data.get('data', {})
                self.mappings = checkpoint_data.get('mappings', {})
                timestamp = checkpoint_data.get('timestamp', 'Unknown')
                print(f"[CHECKPOINT] Loaded from {timestamp}")
                return True
        except Exception as e:
            print(f"[WARNING] Failed to load checkpoint: {e}")
        return False
    
    def clear_checkpoint(self) -> None:
        if os.path.exists(self.checkpoint_file):
            os.remove(self.checkpoint_file)
            print("[CHECKPOINT] Cleared")
    
    # ==========================================================================
    # HELPER FUNCTIONS
    # ==========================================================================
    
    def _safe_get(self, data: dict, keys: List[str], default=None):
        """Safely get value from dict with multiple possible key names."""
        if not data:
            return default
        for key in keys:
            if key in data and data[key] is not None:
                return data[key]
        return default
    
    def _safe_float(self, value, default: float = 0.0) -> float:
        if value is None:
            return default
        try:
            result = float(value)
            return result if not np.isnan(result) else default
        except (ValueError, TypeError):
            return default
    
    def _safe_str(self, value, default: str = '') -> str:
        if value is None or pd.isna(value):
            return default
        return str(value).strip()
    
    def _safe_int(self, value, default: int = 0) -> int:
        if value is None:
            return default
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return default
    
    def _debug_log(self, message: str, data: Any = None):
        if self.debug_mode:
            print(f"[DEBUG] {message}")
            if data is not None and isinstance(data, dict):
                print(f"        Keys: {list(data.keys())[:15]}...")
    
    # ==========================================================================
    # MASTER DATA PULLING
    # ==========================================================================
    
    def pull_master_data(self) -> None:
        print("\n" + "=" * 60)
        print("PULLING MASTER DATA")
        print("=" * 60)
        
        self._pull_customers()
        self._pull_customer_categories()
        self._pull_items()
        self._pull_item_categories()
        self._build_mappings()
        self.save_checkpoint()
    
    def _pull_customers(self) -> None:
        print("\n[1/4] Pulling Customer Master...")
        endpoint = API_ENDPOINTS['customers']['list']
        fields = API_ENDPOINTS['customers']['fields']
        
        customers = self.client.fetch_all_pages(
            endpoint,
            params={'fields': fields},
            max_pages=50
        )
        
        if customers:
            standardized = []
            for c in customers:
                standardized.append({
                    'id': self._safe_str(self._safe_get(c, ['id'])),
                    'name': self._safe_str(self._safe_get(c, ['name', 'customerName'])),
                    'customerNo': self._safe_str(self._safe_get(c, ['customerNo', 'no'])),
                    'categoryId': self._safe_str(self._safe_get(c, ['categoryId', 'customerCategoryId'])),
                    'categoryName': self._safe_str(self._safe_get(c, ['categoryName', 'category'])),
                    'email': self._safe_str(self._safe_get(c, ['email'])),
                    'phone': self._safe_str(self._safe_get(c, ['mobilePhone', 'workPhone', 'phone'])),
                    'city': self._safe_str(self._safe_get(c, ['billCity', 'city'])),
                })
            self.data['customers'] = pd.DataFrame(standardized)
            print(f"   [OK] Customers: {len(self.data['customers']):,} records")
        else:
            self.data['customers'] = pd.DataFrame()
            print("   [FAIL] No customers found")
    
    def _pull_customer_categories(self) -> None:
        print("\n[2/4] Pulling Customer Categories...")
        endpoint = API_ENDPOINTS['customer_categories']['list']
        fields = API_ENDPOINTS['customer_categories']['fields']
        
        categories = self.client.fetch_all_pages(endpoint, params={'fields': fields}, max_pages=10)
        
        if categories:
            self.data['customer_categories'] = pd.DataFrame(categories)
            print(f"   [OK] Customer Categories: {len(self.data['customer_categories']):,} records")
        else:
            self.data['customer_categories'] = pd.DataFrame()
    
    def _pull_items(self) -> None:
        print("\n[3/4] Pulling Item Master...")
        endpoint = API_ENDPOINTS['items']['list']
        fields = API_ENDPOINTS['items']['fields']
        
        items = self.client.fetch_all_pages(endpoint, params={'fields': fields}, max_pages=50)
        
        if items:
            standardized = []
            for item in items:
                standardized.append({
                    'id': self._safe_str(self._safe_get(item, ['id'])),
                    'no': self._safe_str(self._safe_get(item, ['no', 'itemNo', 'code'])),
                    'name': self._safe_str(self._safe_get(item, ['name', 'itemName'])),
                    'itemType': self._safe_str(self._safe_get(item, ['itemType', 'type'])),
                    'itemCategoryId': self._safe_str(self._safe_get(item, ['itemCategoryId', 'categoryId'])),
                    'itemCategoryName': self._safe_str(self._safe_get(item, ['itemCategoryName', 'categoryName'])),
                    'avgCost': self._safe_float(self._safe_get(item, ['avgCost', 'averageCost'])),
                    'unitPrice': self._safe_float(self._safe_get(item, ['unitPrice', 'price', 'sellingPrice'])),
                    'unit': self._safe_str(self._safe_get(item, ['unit1Name', 'unit'])),
                    'upcNo': self._safe_str(self._safe_get(item, ['upcNo', 'barcode'])),
                })
            self.data['items'] = pd.DataFrame(standardized)
            print(f"   [OK] Items: {len(self.data['items']):,} records")
        else:
            self.data['items'] = pd.DataFrame()
    
    def _pull_item_categories(self) -> None:
        print("\n[4/4] Pulling Item Categories...")
        try:
            categories = self.client.fetch_all_pages(
                '/api/item-category/list.do',
                params={'fields': 'id,name,description'},
                max_pages=10
            )
            if categories:
                self.data['item_categories'] = pd.DataFrame(categories)
                print(f"   [OK] Item Categories: {len(self.data['item_categories']):,} records")
            else:
                self.data['item_categories'] = pd.DataFrame()
        except Exception as e:
            print(f"   [WARN] Could not fetch item categories: {e}")
            self.data['item_categories'] = pd.DataFrame()
    
    def _build_mappings(self) -> None:
        print("\n" + "-" * 40)
        print("BUILDING DATA MAPPINGS")
        print("-" * 40)
        
        # Customer mapping by ID
        if 'customers' in self.data and not self.data['customers'].empty:
            self.mappings['customers'] = {}
            for _, row in self.data['customers'].iterrows():
                cid = str(row['id'])
                if cid:
                    self.mappings['customers'][cid] = row.to_dict()
            print(f"   Customer map: {len(self.mappings['customers']):,} entries")
        
        # Product mapping by ID
        if 'items' in self.data and not self.data['items'].empty:
            self.mappings['products'] = {}
            for _, row in self.data['items'].iterrows():
                pid = str(row['id'])
                if pid:
                    self.mappings['products'][pid] = row.to_dict()
            print(f"   Product map: {len(self.mappings['products']):,} entries")
        
        # Item category mapping
        if 'item_categories' in self.data and not self.data['item_categories'].empty:
            self.mappings['item_categories'] = {}
            for _, row in self.data['item_categories'].iterrows():
                cat_id = str(row.get('id', ''))
                if cat_id:
                    self.mappings['item_categories'][cat_id] = row.to_dict()
            print(f"   Item Category map: {len(self.mappings['item_categories']):,} entries")
    
    # ==========================================================================
    # SALES DATA PULLING - EXTRACT CUSTOMER FROM DETAIL
    # ==========================================================================
    
    def pull_sales_data(self) -> None:
        print("\n" + "=" * 60)
        print("PULLING SALES DATA (COMPREHENSIVE)")
        print("=" * 60)
        
        self._pull_sales_invoices()
        self._pull_sales_invoice_details_with_customer()  # New method
        self._validate_sales_data()
        self.save_checkpoint()
    
    def _pull_sales_invoices(self) -> None:
        """Pull sales invoices list (for IDs only, customer from detail)."""
        print("\n[1/2] Pulling Sales Invoices (List)...")
        
        endpoint = API_ENDPOINTS['sales_invoices']['list']
        fields = API_ENDPOINTS['sales_invoices']['fields']
        
        invoices = self.client.fetch_all_pages(
            endpoint,
            params={
                'fields': fields,
                'filter.transDate.>=': self.start_date,
                'filter.transDate.<=': self.end_date,
            },
            max_pages=100
        )
        
        if invoices:
            if self.debug_mode and len(invoices) > 0:
                self._debug_log("Sales Invoice List sample", invoices[0])
            
            standardized = []
            for inv in invoices:
                standardized.append({
                    'id': self._safe_str(self._safe_get(inv, ['id'])),
                    'number': self._safe_str(self._safe_get(inv, ['number', 'invoiceNumber', 'no'])),
                    'transDate': self._safe_str(self._safe_get(inv, ['transDate', 'transactionDate'])),
                    'totalAmount': self._safe_float(self._safe_get(inv, ['totalAmount', 'total', 'grandTotal'])),
                    'description': self._safe_str(self._safe_get(inv, ['description'])),
                })
            
            self.data['sales_invoices'] = pd.DataFrame(standardized)
            print(f"   [OK] Sales Invoices: {len(self.data['sales_invoices']):,} records")
        else:
            self.data['sales_invoices'] = pd.DataFrame()
            print("   [FAIL] No sales invoices found")
    
    def _pull_sales_invoice_details_with_customer(self) -> None:
        """
        Extract customerId from DETAIL response, not from list.
        This is the key fix for the customer_id NULL issue.
        """
        print("\n[2/2] Pulling Sales Invoice Details (with Customer from Detail)...")
        
        if 'sales_invoices' not in self.data or self.data['sales_invoices'].empty:
            print("   [FAIL] No invoices to fetch details for")
            return
        
        invoices = self.data['sales_invoices'].to_dict('records')
        total_invoices = len(invoices)
        print(f"   Processing {total_invoices:,} invoices...")
        
        all_details = []
        detail_endpoint = API_ENDPOINTS['sales_invoices']['detail']
        first_detail_logged = False
        
        for idx, invoice in enumerate(invoices):
            if (idx + 1) % 50 == 0 or idx == 0:
                print(f"   Progress: {idx + 1}/{total_invoices} invoices...")
            
            try:
                detail_response = self.client.request_api(
                    detail_endpoint,
                    params={'id': invoice['id']}
                )
                
                if detail_response and detail_response.get('s'):
                    detail_data = detail_response['d']
                    
                    if not first_detail_logged and self.debug_mode:
                        print(f"\n[INSPECT] Invoice Detail Response Keys:")
                        print(f"   {list(detail_data.keys())}")
                        first_detail_logged = True
                    
                    customer_id = self._safe_str(self._safe_get(detail_data, [
                        'customerId', 'customer.id', 'customerid'
                    ]))
                    customer_name = self._safe_str(self._safe_get(detail_data, [
                        'customerName', 'customer.name', 'customername'
                    ]))
                    
                    # Additional fields from detail
                    trans_date = self._safe_str(self._safe_get(detail_data, [
                        'transDate', 'transactionDate', 'date'
                    ])) or invoice.get('transDate', '')
                    
                    salesman_name = self._safe_str(self._safe_get(detail_data, [
                        'salesmanName', 'salesman', 'salesMan'
                    ]))
                    branch_id = self._safe_str(self._safe_get(detail_data, [
                        'branchId', 'branch.id'
                    ]))
                    branch_name = self._safe_str(self._safe_get(detail_data, [
                        'branchName', 'branch.name'
                    ]))
                    currency_code = self._safe_str(self._safe_get(detail_data, [
                        'currencyCode', 'currency'
                    ]))
                    
                    # Find items array
                    items_key = None
                    for key in ['detailItem', 'items', 'detail', 'lineItems', 'details']:
                        if key in detail_data and detail_data[key]:
                            items_key = key
                            break
                    
                    if items_key:
                        for item in detail_data[items_key]:
                            quantity = self._safe_float(self._safe_get(item, [
                                'quantity', 'qty', 'itemQuantity'
                            ]), 0)
                            unit_price = self._safe_float(self._safe_get(item, [
                                'unitPrice', 'price', 'itemPrice'
                            ]), 0)
                            raw_amount = self._safe_float(self._safe_get(item, [
                                'amount', 'totalAmount', 'lineTotal', 'total'
                            ]), 0)
                            
                            # Calculate amount if missing
                            if raw_amount == 0 and quantity > 0 and unit_price > 0:
                                raw_amount = quantity * unit_price
                            
                            detail_record = {
                                'invoice_id': invoice['id'],
                                'invoice_number': invoice.get('number', ''),
                                'transaction_date': trans_date,
                                'customer_id': customer_id,
                                'customer_name': customer_name,
                                'salesman_name': salesman_name,
                                'branch_id': branch_id,
                                'branch_name': branch_name,
                                'currency_code': currency_code,
                                # Product info
                                'product_id': self._safe_str(self._safe_get(item, [
                                    'itemId', 'id', 'productId', 'item.id'
                                ])),
                                'product_code': self._safe_str(self._safe_get(item, [
                                    'itemNo', 'no', 'itemCode', 'item.no'
                                ])),
                                'product_name': self._safe_str(self._safe_get(item, [
                                    'itemName', 'name', 'productName', 'item.name'
                                ])),
                                'quantity': quantity,
                                'unit_price': unit_price,
                                'total_amount': raw_amount,
                                'discount': self._safe_float(self._safe_get(item, [
                                    'discount', 'discountAmount'
                                ]), 0),
                                'warehouse_id': self._safe_str(self._safe_get(item, [
                                    'warehouseId', 'warehouse.id'
                                ])),
                                'warehouse_name': self._safe_str(self._safe_get(item, [
                                    'warehouseName', 'warehouse.name'
                                ])),
                                'unit': self._safe_str(self._safe_get(item, [
                                    'unitName', 'unit', 'uom'
                                ])),
                            }
                            all_details.append(detail_record)
                
            except Exception as e:
                if self.debug_mode and idx < 5:
                    print(f"   [ERROR] Invoice {invoice.get('number', 'unknown')}: {e}")
            
            time.sleep(API_CONFIG['DELAY_BETWEEN_DETAILS'])
        
        if all_details:
            self.data['sales_details'] = pd.DataFrame(all_details)
            print(f"\n   [OK] Sales Details: {len(all_details):,} line items")
            self._validate_sales_details()
        else:
            self.data['sales_details'] = pd.DataFrame()
            print("\n   [FAIL] No sales details extracted!")
    
    def _validate_sales_details(self) -> None:
        """Validate sales details data quality."""
        if 'sales_details' not in self.data or self.data['sales_details'].empty:
            return
        
        df = self.data['sales_details']
        print("\n   --- SALES DETAILS VALIDATION ---")
        
        # Check customer_id
        valid_customer = (df['customer_id'] != '') & (df['customer_id'].notna())
        pct_customer = valid_customer.mean() * 100
        print(f"   customer_id valid: {valid_customer.sum():,} / {len(df):,} ({pct_customer:.1f}%)")
        
        # Check product_id
        valid_product = (df['product_id'] != '') & (df['product_id'].notna())
        print(f"   product_id valid: {valid_product.sum():,} / {len(df):,} ({valid_product.mean()*100:.1f}%)")
        
        # Check amounts
        valid_amount = df['total_amount'] > 0
        print(f"   total_amount > 0: {valid_amount.sum():,} / {len(df):,} ({valid_amount.mean()*100:.1f}%)")
        
        # Check quantity
        valid_qty = df['quantity'] > 0
        print(f"   quantity > 0: {valid_qty.sum():,} / {len(df):,} ({valid_qty.mean()*100:.1f}%)")
        
        if pct_customer < 50:
            print(f"   [WARNING] Low customer_id coverage ({pct_customer:.1f}%)")
            self.stats['validation_issues'].append(f'Low customer_id coverage: {pct_customer:.1f}%')
        
        if pct_customer == 0:
            print("   [CRITICAL] No valid customer_id - RFM Analysis will fail!")
            self.stats['validation_issues'].append('No valid customer_id in sales details')
    
    def _validate_sales_data(self) -> None:
        """Overall sales data validation."""
        print("\n" + "-" * 40)
        print("SALES DATA VALIDATION SUMMARY")
        print("-" * 40)
        
        if 'sales_invoices' in self.data:
            print(f"Sales Invoices: {len(self.data['sales_invoices']):,}")
        
        if 'sales_details' in self.data and not self.data['sales_details'].empty:
            df = self.data['sales_details']
            unique_customers = df[df['customer_id'] != '']['customer_id'].nunique()
            unique_products = df['product_id'].nunique()
            total_revenue = df['total_amount'].sum()
            
            print(f"Sales Details: {len(df):,} line items")
            print(f"Unique Customers: {unique_customers:,}")
            print(f"Unique Products: {unique_products:,}")
            print(f"Total Revenue: Rp {total_revenue:,.0f}")
    
    # ==========================================================================
    # DATA AGGREGATION
    # ==========================================================================
    
    def aggregate_sales_by_customer(self) -> pd.DataFrame:
        """Aggregate sales data by customer for RFM analysis."""
        print("\n" + "-" * 40)
        print("AGGREGATING SALES BY CUSTOMER")
        print("-" * 40)
        
        if 'sales_details' not in self.data or self.data['sales_details'].empty:
            print("   [FAIL] No sales details to aggregate")
            return pd.DataFrame()
        
        df = self.data['sales_details'].copy()
        print(f"   Starting records: {len(df):,}")
        
        # Filter valid customer_id
        df = df[df['customer_id'].notna() & (df['customer_id'] != '')]
        print(f"   After customer_id filter: {len(df):,}")
        
        if df.empty:
            print("   [FAIL] No records with valid customer_id!")
            return pd.DataFrame()
        
        # Parse dates
        df['transaction_date'] = pd.to_datetime(df['transaction_date'], errors='coerce')
        reference_date = pd.Timestamp.now()
        
        try:
            customer_agg = df.groupby('customer_id').agg({
                'transaction_date': ['max', 'min', 'count'],
                'invoice_id': 'nunique',
                'total_amount': 'sum',
                'quantity': 'sum',
                'customer_name': 'first',
            }).reset_index()
            
            customer_agg.columns = [
                'customer_id', 'last_purchase_date', 'first_purchase_date',
                'transaction_count', 'total_orders', 'monetary',
                'total_items_purchased', 'customer_name'
            ]
            
            customer_agg['recency_days'] = (
                reference_date - customer_agg['last_purchase_date']
            ).dt.days.fillna(9999)
            customer_agg['frequency'] = customer_agg['total_orders']
            customer_agg['avg_order_value'] = (
                customer_agg['monetary'] / customer_agg['total_orders'].replace(0, 1)
            ).fillna(0)
            
            self.data['sales_by_customer'] = customer_agg
            print(f"   [OK] Aggregated: {len(customer_agg):,} customers")
            print(f"   Total Monetary: Rp {customer_agg['monetary'].sum():,.0f}")
            
            return customer_agg
            
        except Exception as e:
            print(f"   [ERROR] Aggregation failed: {e}")
            return pd.DataFrame()
    
    def aggregate_sales_by_product(self) -> pd.DataFrame:
        """Aggregate sales data by product."""
        print("\n" + "-" * 40)
        print("AGGREGATING SALES BY PRODUCT")
        print("-" * 40)
        
        if 'sales_details' not in self.data or self.data['sales_details'].empty:
            print("   [FAIL] No sales details to aggregate")
            return pd.DataFrame()
        
        df = self.data['sales_details'].copy()
        df = df[df['product_id'].notna() & (df['product_id'] != '')]
        print(f"   Records with valid product_id: {len(df):,}")
        
        if df.empty:
            print("   [FAIL] No records with valid product_id!")
            return pd.DataFrame()
        
        try:
            product_agg = df.groupby('product_id').agg({
                'product_code': 'first',
                'product_name': 'first',
                'quantity': 'sum',
                'total_amount': 'sum',
                'invoice_id': 'nunique',
                'customer_id': 'nunique',
            }).reset_index()
            
            product_agg.columns = [
                'product_id', 'product_code', 'product_name',
                'total_quantity_sold', 'total_revenue', 'order_count', 'unique_customers',
            ]
            
            product_agg['avg_price'] = (
                product_agg['total_revenue'] / product_agg['total_quantity_sold'].replace(0, 1)
            ).fillna(0)
            
            self.data['sales_by_product'] = product_agg
            print(f"   [OK] Aggregated: {len(product_agg):,} products")
            print(f"   Total Revenue: Rp {product_agg['total_revenue'].sum():,.0f}")
            
            return product_agg
            
        except Exception as e:
            print(f"   [ERROR] Aggregation failed: {e}")
            return pd.DataFrame()
    
    # ==========================================================================
    # MAIN PULL FUNCTION
    # ==========================================================================
    
    def pull_all_data(self) -> None:
        """Pull all required data for Sales Analytics."""
        print("\n" + "=" * 70)
        print("STARTING DATA COLLECTION - SALES PERFORMANCE ANALYTICS")
        print("=" * 70)
        print(f"Period: {self.start_date} to {self.end_date}")
        
        start_time = time.time()
        
        self.pull_master_data()
        self.pull_sales_data()
        self.aggregate_sales_by_customer()
        self.aggregate_sales_by_product()
        
        end_time = time.time()
        duration = (end_time - start_time) / 60
        
        print("\n" + "=" * 70)
        print("DATA COLLECTION COMPLETE")
        print("=" * 70)
        print(f"Duration: {duration:.1f} minutes")
        
        if self.stats['validation_issues']:
            print("\n[WARNING] Validation Issues Found:")
            for issue in self.stats['validation_issues']:
                print(f"   - {issue}")
        
        self.save_checkpoint()
    
    def get_data_summary(self) -> Dict[str, Any]:
        """Get summary of all pulled data."""
        summary = {}
        for key, df in self.data.items():
            if isinstance(df, pd.DataFrame):
                summary[key] = {
                    'rows': len(df),
                    'columns': len(df.columns) if not df.empty else 0,
                }
        return summary
