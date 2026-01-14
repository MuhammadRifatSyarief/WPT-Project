"""
Project 1 Data Puller Module
============================
"""

import time
import requests
import hmac
import hashlib
import base64
import pandas as pd
import numpy as np
import pytz
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


class InventoryOptimizationAPIClient:
    """API Client for Project 1"""
    
    def __init__(self, api_token: str, signature_secret: str):
        self.api_token = api_token
        self.signature_secret = signature_secret
        self.host = None
        self.total_requests = 0
        self.failed_requests = 0
        self.last_request_time = 0
        self.request_count = 0
    
    def rate_limit(self):
        """Rate limiting: max 3 requests per second"""
        current_time = time.time()
        if current_time - self.last_request_time >= 1.0:
            self.request_count = 0
            self.last_request_time = current_time
        
        if self.request_count >= 3:
            sleep_time = 1.0 - (current_time - self.last_request_time)
            if sleep_time > 0:
                time.sleep(sleep_time)
            self.request_count = 0
            self.last_request_time = time.time()
        
        self.request_count += 1
    
    def get_headers(self):
        """Generate headers with signature - using format from Project 1 logic"""
        import pytz
        # Use WIB timezone format like Project 1 original logic
        wib = pytz.timezone('Asia/Jakarta')
        now = datetime.now(wib)
        timestamp = now.strftime('%d/%m/%Y %H:%M:%S')
        
        # Generate signature using timestamp only (not api_token + timestamp)
        message = timestamp.encode('utf-8')
        secret = self.signature_secret.encode('utf-8')
        signature = base64.b64encode(
            hmac.new(secret, message, hashlib.sha256).digest()
        ).decode('utf-8')
        
        return {
            'Authorization': f'Bearer {self.api_token}',
            'X-Api-Timestamp': timestamp,
            'X-Api-Signature': signature,
            'Content-Type': 'application/json'
        }
    
    def initialize_host(self):
        """Initialize host URL from API token"""
        url = 'https://account.accurate.id/api/api-token.do'
        try:
            response = requests.post(url, headers=self.get_headers(), timeout=30)
            response.raise_for_status()
            data = response.json()
            if data.get('s'):
                db_key = 'database' if 'database' in data['d'] else 'data usaha'
                self.host = data['d'][db_key]['host']
                logger.info(f"✓ Connection successful: {self.host}")
                return True
            else:
                error_msg = data.get('d', {}).get('error', 'Unknown error')
                logger.error(f"✗ Failed to get API token information: {error_msg}")
                logger.error("Please check if API_TOKEN is valid and not expired.")
                return False
        except requests.exceptions.Timeout:
            logger.error("✗ Connection timeout. Please check your internet connection.")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Connection error: {str(e)}")
            logger.error("Please check API_TOKEN and SIGNATURE_SECRET are correct.")
            return False
        except Exception as e:
            logger.error(f"✗ Unexpected error: {str(e)}")
            return False
    
    def request_api(self, endpoint, method='GET', params=None, data=None, max_retries=3):
        """Make API request with retry mechanism"""
        if not self.host:
            logger.error("✗ Host not initialized")
            return None
        
        for attempt in range(max_retries + 1):
            self.rate_limit()
            url = f"{self.host}/accurate{endpoint}"
            headers = self.get_headers()
            
            try:
                if method.upper() == 'GET':
                    response = requests.get(url, headers=headers, params=params, timeout=30)
                else:
                    response = requests.post(url, headers=headers, json=data, timeout=30)
                
                if response.status_code == 429:
                    wait_time = (2 ** attempt) + 5
                    logger.warning(f"Rate limit hit, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                response.raise_for_status()
                self.total_requests += 1
                return response.json()
                
            except requests.exceptions.HTTPError as e:
                if response.status_code == 429 and attempt < max_retries:
                    continue
                else:
                    self.failed_requests += 1
                    logger.warning(f"HTTP Error {response.status_code} on {endpoint}")
                    return None
            except Exception as e:
                self.failed_requests += 1
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
                else:
                    logger.warning(f"Error on {endpoint}: {str(e)}")
                    return None
        
        return None
    
    def fetch_all_pages(self, endpoint, params=None, max_pages=50, delay_between_pages=0.5):
        """Fetch data with pagination"""
        if params is None:
            params = {}
        
        all_data = []
        page = 1
        
        while True:
            params['sp.page'] = page
            params['sp.pageSize'] = 100
            
            response = self.request_api(endpoint, params=params)
            if not response or not response.get('s'):
                break
            
            data = response.get('d', [])
            if not data:
                break
            
            all_data.extend(data)
            sp = response.get('sp', {})
            
            if page >= sp.get('pageCount', 1) or page >= max_pages:
                break
            
            page += 1
            if delay_between_pages > 0:
                time.sleep(delay_between_pages)
        
        logger.info(f"Fetched {len(all_data)} records from {page - 1} pages")
        return all_data


class Project1DataPuller:
    """Project 1 Data Puller"""
    
    def __init__(self, api_token: str, signature_secret: str, start_date: str, end_date: str):
        self.client = InventoryOptimizationAPIClient(api_token, signature_secret)
        self.start_date = start_date
        self.end_date = end_date
        self.data: Dict[str, pd.DataFrame] = {}
        self.mappings: Dict[str, Dict] = {}
        
        if not self.client.initialize_host():
            raise Exception("Failed to initialize API client")
    
    def pull_master_data(self):
        """Pull master data including selling prices"""
        logger.info("Pulling master data...")
        
        # Items - include unitPrice and avgCost
        items = self.client.fetch_all_pages(
            '/api/item/list.do',
            params={'fields': 'id,no,name,itemType,itemCategoryName,avgCost,unitPrice,unit1Name,minimumStock'},
            max_pages=50
        )
        self.data['items'] = pd.DataFrame(items) if items else pd.DataFrame()
        
        # 🎯 NEW: Fetch detailed selling prices for each item
        # Use /api/item/get-selling-price.do endpoint for accurate pricing
        if not self.data['items'].empty:
            logger.info(f"Fetching selling prices for {len(self.data['items'])} items...")
            selling_prices = {}
            debug_logged = False  # Log first response for debugging
            
            for idx, item in self.data['items'].iterrows():
                item_id = item.get('id')
                if not item_id:
                    continue
                
                # Show progress every 200 items
                if (idx + 1) % 200 == 0:
                    logger.info(f"   Selling price progress: {idx + 1}/{len(self.data['items'])} items...")
                
                try:
                    price_response = self.client.request_api(
                        '/api/item/get-selling-price.do',
                        params={'id': item_id}
                    )
                    
                    if price_response and price_response.get('s'):
                        price_data = price_response.get('d', {})
                        
                        # Debug: Log first non-empty response to understand structure
                        if not debug_logged and price_data:
                            logger.info(f"📋 Sample price response structure: {type(price_data).__name__}")
                            if isinstance(price_data, list) and len(price_data) > 0:
                                logger.info(f"   First element keys: {list(price_data[0].keys()) if isinstance(price_data[0], dict) else 'N/A'}")
                                logger.info(f"   First element: {price_data[0]}")
                            elif isinstance(price_data, dict):
                                logger.info(f"   Dict keys: {list(price_data.keys())}")
                            debug_logged = True
                        
                        # Try multiple price extraction strategies
                        price = 0
                        
                        if isinstance(price_data, list) and len(price_data) > 0:
                            # Response is a list of price categories
                            first_price = price_data[0]
                            if isinstance(first_price, dict):
                                # Try common price field names
                                price = float(first_price.get('price', 0) or 
                                             first_price.get('unitPrice', 0) or 
                                             first_price.get('sellingPrice', 0) or 
                                             first_price.get('amount', 0) or 0)
                            elif isinstance(first_price, (int, float)):
                                price = float(first_price)
                                
                        elif isinstance(price_data, dict):
                            # Response is a single price object
                            # 🎯 CRITICAL FIX: Based on logs, the key is likely 'unit1Price'
                            price = float(price_data.get('unit1Price', 0) or 
                                         price_data.get('price', 0) or 
                                         price_data.get('unitPrice', 0) or 
                                         price_data.get('sellingPrice', 0) or 
                                         price_data.get('amount', 0) or 0)
                            
                            # If simplified price is 0, check other fields
                            if price == 0:
                                # Try unit2Price, unit3Price, etc.
                                for i in range(2, 6):
                                    alt_price = float(price_data.get(f'unit{i}Price', 0) or 0)
                                    if alt_price > 0:
                                        price = alt_price
                                        break
                                         
                        elif isinstance(price_data, (int, float)):
                            # Response is just a number
                            price = float(price_data)
                        
                        if price > 0:
                            selling_prices[item_id] = price
                            
                except Exception as e:
                    # Continue without price if fetch fails
                    pass
                
                # Rate limit: small delay every 10 items
                if idx > 0 and idx % 10 == 0:
                    time.sleep(0.35)
            
            # Merge selling prices into items dataframe
            logger.info(f"✓ Fetched selling prices for {len(selling_prices)} items (non-zero: {sum(1 for v in selling_prices.values() if v > 0)})")
            
            if selling_prices:
                self.data['items']['sellingPrice'] = self.data['items']['id'].map(selling_prices)
            
            # 🎯 CRITICAL: Always use unitPrice as fallback if sellingPrice is missing
            # The unitPrice from /api/item/list.do already contains default prices!
            if 'unitPrice' in self.data['items'].columns:
                unit_prices = pd.to_numeric(self.data['items']['unitPrice'], errors='coerce').fillna(0)
                non_zero_unit = (unit_prices > 0).sum()
                logger.info(f"📊 unitPrice from item list: {non_zero_unit}/{len(self.data['items'])} have non-zero values")
                
                if 'sellingPrice' not in self.data['items'].columns:
                    self.data['items']['sellingPrice'] = unit_prices
                else:
                    # Fill missing sellingPrice with unitPrice
                    self.data['items']['sellingPrice'] = self.data['items']['sellingPrice'].fillna(unit_prices)
                    # Also fill zeros with unitPrice
                    zero_mask = self.data['items']['sellingPrice'] == 0
                    self.data['items'].loc[zero_mask, 'sellingPrice'] = unit_prices[zero_mask]
            
            final_non_zero = (pd.to_numeric(self.data['items'].get('sellingPrice', 0), errors='coerce').fillna(0) > 0).sum()
            logger.info(f"✓ Final selling prices: {final_non_zero}/{len(self.data['items'])} have non-zero values")
        
        # Warehouses - get more fields but handle dict columns
        warehouses = self.client.fetch_all_pages(
            '/api/warehouse/list.do',
            params={'fields': 'id,name,description,address,locationId'},
            max_pages=5
        )
        if warehouses:
            warehouses_df = pd.DataFrame(warehouses)
            # Flatten address dict if exists
            if 'address' in warehouses_df.columns:
                import json
                warehouses_df['address'] = warehouses_df['address'].apply(
                    lambda x: json.dumps(x) if isinstance(x, dict) else x
                )
            self.data['warehouses'] = warehouses_df
        else:
            self.data['warehouses'] = pd.DataFrame()
        
        # Customers
        customers = self.client.fetch_all_pages(
            '/api/customer/list.do',
            params={'fields': 'id,name,customerNo'},
            max_pages=20
        )
        self.data['customers'] = pd.DataFrame(customers) if customers else pd.DataFrame()
        
        # Vendors
        vendors = self.client.fetch_all_pages(
            '/api/vendor/list.do',
            params={'fields': 'id,name,vendorNo'},
            max_pages=10
        )
        self.data['vendors'] = pd.DataFrame(vendors) if vendors else pd.DataFrame()
        
        logger.info("Master data pulled successfully")
    
    def pull_inventory_data(self):
        """Pull inventory data using CORRECT API endpoints (matching manual logic)"""
        logger.info("Pulling inventory data...")
        
        # ============================================================
        # 1. Current stocks using /api/item/list-stock.do (CORRECT!)
        # ============================================================
        try:
            stocks = self.client.fetch_all_pages(
                '/api/item/list-stock.do',  # 🔧 FIXED: Was /api/stock-item/list.do (doesn't exist!)
                params={
                    'fields': 'id,no,name,warehouseId,warehouseName,unitName,stockAvailable,qtyStock,itemType,itemCategoryName,avgCost,unitPrice,upcNo'
                },
                max_pages=50
            )
            if stocks:
                df_stocks = pd.DataFrame(stocks)
                # Rename columns to match expected schema
                df_stocks.rename(columns={
                    'id': 'product_id',
                    'no': 'product_code',
                    'name': 'product_name',
                    'qtyStock': 'quantity',
                    'stockAvailable': 'quantityInAllUnit',
                    'itemCategoryName': 'category',
                    'unitName': 'unit'
                }, inplace=True)
                self.data['current_stocks'] = df_stocks
                logger.info(f"✓ Fetched {len(stocks)} current stock records")
            else:
                self.data['current_stocks'] = pd.DataFrame()
                logger.warning("No current stocks found")
        except Exception as e:
            logger.warning(f"Error pulling current stocks: {str(e)}")
            self.data['current_stocks'] = pd.DataFrame()
        
        # ============================================================
        # 2. Stock mutations using /api/item/stock-mutation-history.do (CORRECT!)
        # This requires fetching per-item, similar to manual logic development
        # ============================================================
        try:
            # Get list of inventory items to fetch mutations for
            items_df = self.data.get('items', pd.DataFrame())
            if items_df.empty:
                logger.warning("No items data for stock mutation fetch")
                self.data['stock_mutations'] = pd.DataFrame()
            else:
                # Filter only INVENTORY and GROUP type items (as per manual logic)
                inventory_types = ['INVENTORY', 'GROUP']
                if 'itemType' in items_df.columns:
                    inventory_items = items_df[items_df['itemType'].isin(inventory_types)]
                else:
                    inventory_items = items_df
                
                logger.info(f"Fetching stock mutations for {len(inventory_items)} inventory items...")
                
                mutations = []
                for idx, item in inventory_items.iterrows():
                    if idx > 0 and idx % 100 == 0:
                        logger.info(f"   Progress: {idx}/{len(inventory_items)} items...")
                    
                    mutation_response = self.client.request_api(
                        '/api/item/stock-mutation-history.do',  # 🔧 FIXED: Correct endpoint!
                        params={
                            'id': item.get('id') or item.get('product_id'),
                            'startDate': self.start_date,
                            'endDate': self.end_date
                        }
                    )
                    
                    if mutation_response and mutation_response.get('s'):
                        for record in mutation_response.get('d', []):
                            # Enrich with product info to avoid missing values
                            record['product_id'] = item.get('id') or item.get('product_id')
                            record['product_code'] = item.get('no') or item.get('product_code')
                            record['product_name'] = item.get('name') or item.get('product_name')
                            mutations.append(record)
                    
                    # Rate limit: 3 requests per second max
                    import time
                    time.sleep(0.35)
                
                if mutations:
                    self.data['stock_mutations'] = pd.DataFrame(mutations)
                    logger.info(f"✓ Fetched {len(mutations)} stock mutation records")
                else:
                    self.data['stock_mutations'] = pd.DataFrame()
                    logger.warning("No stock mutations found")
                    
        except Exception as e:
            logger.warning(f"Error pulling stock mutations: {str(e)}")
            self.data['stock_mutations'] = pd.DataFrame()
        
        logger.info("Inventory data pulled successfully")
    
    def pull_sales_data(self):
        """Pull sales data including invoice details"""
        logger.info("Pulling sales data...")
        
        # Sales invoices - try without filter first, then with filter
        try:
            invoices = self.client.fetch_all_pages(
                '/api/sales-invoice/list.do',
                params={
                    'fields': 'id,number,transDate,customerId,totalAmount,invoiceDp'
                },
                max_pages=100
            )
            
            if invoices:
                invoices_df = pd.DataFrame(invoices)
                # Filter by date range in Python if transDate column exists
                if 'transDate' in invoices_df.columns and not invoices_df.empty:
                    try:
                        invoices_df['transDate'] = pd.to_datetime(invoices_df['transDate'], errors='coerce')
                        start_dt = pd.to_datetime(self.start_date, format='%d/%m/%Y', errors='coerce')
                        end_dt = pd.to_datetime(self.end_date, format='%d/%m/%Y', errors='coerce')
                        
                        if pd.notna(start_dt) and pd.notna(end_dt):
                            mask = (invoices_df['transDate'] >= start_dt) & (invoices_df['transDate'] <= end_dt)
                            invoices_df = invoices_df[mask]
                            logger.info(f"Filtered {len(invoices_df)} invoices in date range {self.start_date} to {self.end_date}")
                    except Exception as e:
                        logger.warning(f"Could not filter by date: {str(e)}")
                
                # 🎯 NEW: Log how many invoices are Down Payments
                if 'invoiceDp' in invoices_df.columns:
                    dp_count = invoices_df['invoiceDp'].fillna(False).sum()
                    if dp_count > 0:
                        logger.info(f"ℹ️ Found {dp_count} Down Payment invoices (will be filtered out)")
                
                self.data['sales_invoices'] = invoices_df
            else:
                self.data['sales_invoices'] = pd.DataFrame()
        except Exception as e:
            logger.warning(f"Error pulling sales invoices: {str(e)}")
            self.data['sales_invoices'] = pd.DataFrame()
        
        logger.info(f"Sales invoices pulled: {len(self.data['sales_invoices'])} invoices")
        
        # ✅ PULL SALES DETAILS (Invoice details with items)
        if not self.data['sales_invoices'].empty:
            logger.info(f"Pulling sales invoice details for {len(self.data['sales_invoices'])} invoices...")
            sales_details_list = []
            invoices_df = self.data['sales_invoices']
            
            for idx, invoice in invoices_df.iterrows():
                invoice_id = invoice.get('id')
                if not invoice_id:
                    continue
                
                # Filter out Down Payment invoices
                if invoice.get('invoiceDp') is True:
                    # logger.debug(f"Skipping Down Payment invoice: {invoice.get('number')}")
                    continue
                
                # Show progress every 50 invoices
                if (idx + 1) % 50 == 0 or idx == 0:
                    logger.info(f"   Progress: {idx + 1}/{len(invoices_df)} invoices...")
                
                # Rate limiting: small delay between requests
                if idx > 0 and idx % 10 == 0:
                    time.sleep(0.5)  # Small delay every 10 requests
                
                try:
                    # Fetch invoice detail
                    detail_response = self.client.request_api(
                        '/api/sales-invoice/detail.do',
                        params={'id': invoice_id}
                    )
                    
                    if detail_response and detail_response.get('s'):
                        detail_data = detail_response.get('d', {})
                        
                        # Double check invoiceDp in detail if not in list
                        if detail_data.get('invoiceDp') is True:
                            continue
                        
                        # Extract items from detail (try different key names)
                        items_key = None
                        for key in ['detailItem', 'items', 'detail', 'detailItems']:
                            if key in detail_data and detail_data[key] is not None:
                                items_key = key
                                break
                        
                        if items_key and detail_data[items_key]:
                            for item in detail_data[items_key]:
                                sales_details_list.append({
                                    'invoice_id': invoice_id,
                                    'invoice_number': invoice.get('number', ''),
                                    'transaction_date': invoice.get('transDate', ''),
                                    'customer_id': invoice.get('customerId') or detail_data.get('customerId'),
                                    'product_id': item.get('itemId') or item.get('id') or item.get('item_id'),
                                    'product_code': item.get('itemNo') or item.get('no') or item.get('item_no'),
                                    'product_name': item.get('itemName') or item.get('name') or item.get('item_name'),
                                    'quantity': float(item.get('quantity', 0) or 0),
                                    'unit_price': float(item.get('unitPrice', 0) or item.get('unit_price', 0) or 0),
                                    'total_amount': float(item.get('amount', 0) or item.get('totalAmount', 0) or item.get('total_amount', 0) or 0),
                                    'discount': float(item.get('discount', 0) or 0),
                                    'warehouse_id': item.get('warehouseId') or item.get('warehouse_id'),
                                    'warehouse_name': item.get('warehouseName') or item.get('warehouse_name')
                                })
                except Exception as e:
                    logger.warning(f"Error fetching detail for invoice {invoice_id}: {str(e)}")
                    continue
            
            # Create sales_details DataFrame
            if sales_details_list:
                self.data['sales_details'] = pd.DataFrame(sales_details_list)
                logger.info(f"✓ Pulled {len(sales_details_list)} sales detail records from {len(invoices_df)} invoices")
            else:
                self.data['sales_details'] = pd.DataFrame()
                logger.warning("No sales details found")
        else:
            self.data['sales_details'] = pd.DataFrame()
            logger.warning("No invoices to fetch details for")
        
        logger.info(f"Sales data pulled: {len(self.data['sales_invoices'])} invoices, {len(self.data.get('sales_details', pd.DataFrame()))} detail records")
    
    def pull_purchase_data(self):
        """Pull purchase data including purchase order details"""
        logger.info("Pulling purchase data...")
        
        # Purchase orders - try without filter first, then filter in Python
        try:
            pos = self.client.fetch_all_pages(
                '/api/purchase-order/list.do',
                params={
                    'fields': 'id,number,transDate,vendorId,totalAmount'
                },
                max_pages=50
            )
            
            if pos:
                pos_df = pd.DataFrame(pos)
                # Filter by date range in Python if transDate column exists
                if 'transDate' in pos_df.columns and not pos_df.empty:
                    try:
                        pos_df['transDate'] = pd.to_datetime(pos_df['transDate'], errors='coerce')
                        start_dt = pd.to_datetime(self.start_date, format='%d/%m/%Y', errors='coerce')
                        end_dt = pd.to_datetime(self.end_date, format='%d/%m/%Y', errors='coerce')
                        
                        if pd.notna(start_dt) and pd.notna(end_dt):
                            mask = (pos_df['transDate'] >= start_dt) & (pos_df['transDate'] <= end_dt)
                            pos_df = pos_df[mask]
                            logger.info(f"Filtered {len(pos_df)} purchase orders in date range {self.start_date} to {self.end_date}")
                    except Exception as e:
                        logger.warning(f"Could not filter by date: {str(e)}")
                
                self.data['purchase_orders'] = pos_df
            else:
                self.data['purchase_orders'] = pd.DataFrame()
        except Exception as e:
            logger.warning(f"Error pulling purchase orders: {str(e)}")
            self.data['purchase_orders'] = pd.DataFrame()
        
        logger.info(f"Purchase orders pulled: {len(self.data['purchase_orders'])} purchase orders")
        
        # ✅ PULL PURCHASE ORDER DETAILS (if available)
        if not self.data['purchase_orders'].empty:
            logger.info(f"Pulling purchase order details for {len(self.data['purchase_orders'])} POs...")
            po_details_list = []
            pos_df = self.data['purchase_orders']
            
            for idx, po in pos_df.iterrows():
                po_id = po.get('id')
                if not po_id:
                    continue
                
                # Show progress every 20 POs
                if (idx + 1) % 20 == 0 or idx == 0:
                    logger.info(f"   Progress: {idx + 1}/{len(pos_df)} purchase orders...")
                
                # Rate limiting
                if idx > 0 and idx % 10 == 0:
                    time.sleep(0.5)
                
                try:
                    # Fetch PO detail
                    detail_response = self.client.request_api(
                        '/api/purchase-order/detail.do',
                        params={'id': po_id}
                    )
                    
                    if detail_response and detail_response.get('s'):
                        detail_data = detail_response.get('d', {})
                        
                        # Extract items from detail
                        items_key = None
                        for key in ['detailItem', 'items', 'detail', 'detailItems']:
                            if key in detail_data and detail_data[key] is not None:
                                items_key = key
                                break
                        
                        if items_key and detail_data[items_key]:
                            for item in detail_data[items_key]:
                                po_details_list.append({
                                    'purchase_order_id': po_id,
                                    'purchase_order_number': po.get('number', ''),
                                    'transaction_date': po.get('transDate', ''),
                                    'vendor_id': po.get('vendorId'),
                                    'product_id': item.get('itemId') or item.get('id') or item.get('item_id'),
                                    'product_code': item.get('itemNo') or item.get('no'),
                                    'product_name': item.get('itemName') or item.get('name'),
                                    'quantity': float(item.get('quantity', 0) or 0),
                                    'unit_price': float(item.get('unitPrice', 0) or 0),
                                    'total_amount': float(item.get('amount', 0) or item.get('totalAmount', 0) or 0)
                                })
                except Exception as e:
                    logger.warning(f"Error fetching detail for PO {po_id}: {str(e)}")
                    continue
            
            # Create purchase_order_details DataFrame
            if po_details_list:
                self.data['purchase_order_details'] = pd.DataFrame(po_details_list)
                logger.info(f"✓ Pulled {len(po_details_list)} purchase order detail records")
            else:
                self.data['purchase_order_details'] = pd.DataFrame()
        else:
            self.data['purchase_order_details'] = pd.DataFrame()
        
        logger.info(f"Purchase data pulled: {len(self.data['purchase_orders'])} purchase orders, {len(self.data.get('purchase_order_details', pd.DataFrame()))} detail records")
    
    def calculate_comprehensive_metrics(self):
        """Calculate metrics"""
        logger.info("Calculating metrics...")
        # Placeholder for metric calculations
        # This would contain the actual metric calculation logic
        pass
    
    def enrich_all_dataframes(self):
        """Enrich dataframes with mappings"""
        logger.info("Enriching dataframes...")
        # Placeholder for enrichment logic
        pass
    
    def generate_optimization_insights(self):
        """Generate optimization insights"""
        logger.info("Generating insights...")
        # Placeholder for insights generation
        pass


# ============================================================================
# NEW: PIPELINE ORCHESTRATOR WRAPPER
# ============================================================================

class PipelineDataPuller:
    """
    Streamlined Data Puller using run_full_pipeline.py
    
    This class wraps the comprehensive pipeline orchestrator to provide
    a simple interface for Streamlit real-time data refresh.
    """
    
    def __init__(self, start_date: str = None, end_date: str = None):
        """
        Initialize pipeline puller
        
        Args:
            start_date: Start date in DD/MM/YYYY format (default: 90 days ago)
            end_date: End date in DD/MM/YYYY format (default: today)
        """
        from datetime import datetime, timedelta
        
        if end_date is None:
            end_date = datetime.now().strftime('%d/%m/%Y')
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=90)).strftime('%d/%m/%Y')
        
        self.start_date = start_date
        self.end_date = end_date
        self.base_dir = Path(__file__).parent.parent  # Project root
        self.output_dir = self.base_dir / "data" / "new_base_dataset_project1"
    
    def run_full_pipeline(self, skip_stage1: bool = False, resume_step: int = None) -> bool:
        """
        Execute the full data pipeline using run_full_pipeline.py
        
        Args:
            skip_stage1: If True, skip API pulling and only run feature engineering
            resume_step: Resume from specific data preparation step (1-4)
        
        Returns:
            bool: True if successful, False otherwise
        """
        import subprocess
        import sys
        
        cmd = [
            sys.executable,  # Use current Python interpreter
            str(self.base_dir / "run_full_pipeline.py"),
            "--start-date", self.start_date,
            "--end-date", self.end_date
        ]
        
        if skip_stage1:
            cmd.append("--skip-stage1")
        
        if resume_step is not None:
            cmd.extend(["--resume-step", str(resume_step)])
        
        logger.info(f"Running pipeline: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.base_dir),
                capture_output=True,
                text=True,
                timeout=None  # No timeout for long-running pipeline
            )
            
            if result.returncode == 0:
                logger.info("Pipeline completed successfully")
                return True
            else:
                logger.error(f"Pipeline failed with code {result.returncode}")
                logger.error(f"STDERR: {result.stderr[:500] if result.stderr else 'N/A'}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Pipeline timed out")
            return False
        except Exception as e:
            logger.error(f"Pipeline error: {str(e)}")
            return False
    
    def run_feature_engineering_only(self) -> bool:
        """
        Run only Stage 2: Feature Engineering (skip API pulling)
        Useful when base datasets are already up-to-date.
        """
        return self.run_full_pipeline(skip_stage1=True)
    
    def get_last_refresh_time(self) -> Optional[datetime]:
        """Get the last data refresh timestamp"""
        feature_set_path = self.output_dir / "Master_Inventory_Feature_Set.csv"
        if feature_set_path.exists():
            import os
            mtime = os.path.getmtime(feature_set_path)
            return datetime.fromtimestamp(mtime)
        return None
    
    def is_data_stale(self, max_age_hours: int = 24) -> bool:
        """Check if data needs refresh"""
        last_refresh = self.get_last_refresh_time()
        if last_refresh is None:
            return True
        
        from datetime import timedelta
        return (datetime.now() - last_refresh) > timedelta(hours=max_age_hours)


# Import Path at module level for PipelineDataPuller
from pathlib import Path
