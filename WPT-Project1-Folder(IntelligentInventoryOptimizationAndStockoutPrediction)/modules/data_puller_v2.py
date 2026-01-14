"""
Module 1: Data Puller Refactored - GPU Accelerated Version
===========================================================

Project 1 - Intelligent Inventory Optimization & Stockout Prediction

Key Improvements:
1. GPU acceleration with cuDF (fallback to pandas)
2. Robust checkpoint system for resume capability
3. Enhanced error handling and retry logic
4. Comprehensive logging and monitoring
5. Cross-endpoint data enrichment preparation
6. Rate limiting with adaptive backoff

Author: AI Assistant
Date: January 2026
Version: 2.0.0
"""

import os
import sys
import time
import json
import pickle
import hashlib
import hmac
import base64
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any, Tuple, Union
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import warnings

warnings.filterwarnings('ignore')

# Core imports
import requests
import pytz

# DataFrame engine - GPU if available, otherwise CPU
try:
    import cudf
    import cupy as cp
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False

import pandas as pd
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION & CONSTANTS
# =============================================================================

@dataclass
class PullerConfig:
    """Configuration for data puller"""
    # Rate limiting
    max_requests_per_second: int = 3
    min_request_interval: float = 0.35
    
    # Retry settings
    max_retries: int = 3
    initial_backoff: float = 2.0
    max_backoff: float = 60.0
    
    # Pagination
    page_size: int = 100
    max_pages: int = 50
    delay_between_pages: float = 0.5
    
    # Checkpoint
    checkpoint_dir: str = "checkpoints"
    checkpoint_interval: int = 100  # Save every N items
    
    # Timeouts
    request_timeout: int = 30
    connection_timeout: int = 10
    
    # GPU settings
    use_gpu: bool = True
    gpu_memory_limit: str = "8GB"


class PullStatus(Enum):
    """Status of data pulling operation"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class EndpointStats:
    """Statistics for each endpoint"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rate_limit_hits: int = 0
    total_records: int = 0
    null_values_count: int = 0
    processing_time: float = 0.0


# =============================================================================
# GPU/CPU DATAFRAME ENGINE
# =============================================================================

class DataFrameEngine:
    """Abstraction layer for GPU/CPU DataFrame operations"""
    
    def __init__(self, use_gpu: bool = True):
        self.gpu_enabled = use_gpu and GPU_AVAILABLE
        self.engine_name = "cuDF (GPU)" if self.gpu_enabled else "pandas (CPU)"
        logger.info(f"DataFrame Engine: {self.engine_name}")
    
    def create_dataframe(self, data: Union[List[Dict], Dict]) -> Any:
        """Create DataFrame from data"""
        if not data:
            return pd.DataFrame()
        
        if self.gpu_enabled:
            try:
                return cudf.DataFrame(data)
            except Exception as e:
                logger.warning(f"GPU DataFrame creation failed, falling back to CPU: {e}")
                return pd.DataFrame(data)
        return pd.DataFrame(data)
    
    def to_pandas(self, df: Any) -> pd.DataFrame:
        """Convert to pandas DataFrame"""
        if self.gpu_enabled and hasattr(df, 'to_pandas'):
            return df.to_pandas()
        return df
    
    def concat(self, dfs: List[Any], ignore_index: bool = True) -> Any:
        """Concatenate DataFrames"""
        if not dfs:
            return pd.DataFrame()
        
        if self.gpu_enabled:
            try:
                return cudf.concat(dfs, ignore_index=ignore_index)
            except Exception:
                pandas_dfs = [self.to_pandas(df) for df in dfs]
                return pd.concat(pandas_dfs, ignore_index=ignore_index)
        return pd.concat(dfs, ignore_index=ignore_index)


# =============================================================================
# CHECKPOINT SYSTEM
# =============================================================================

class CheckpointManager:
    """Manages checkpoints for resume capability"""
    
    def __init__(self, checkpoint_dir: str, session_id: str):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.session_id = session_id
        self.checkpoint_file = self.checkpoint_dir / f"checkpoint_{session_id}.pkl"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    def save(self, state: Dict[str, Any]) -> bool:
        """Save checkpoint state"""
        try:
            state['timestamp'] = datetime.now().isoformat()
            with open(self.checkpoint_file, 'wb') as f:
                pickle.dump(state, f)
            logger.debug(f"Checkpoint saved: {len(state)} keys")
            return True
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            return False
    
    def load(self) -> Optional[Dict[str, Any]]:
        """Load checkpoint state if exists"""
        if not self.checkpoint_file.exists():
            return None
        
        try:
            with open(self.checkpoint_file, 'rb') as f:
                state = pickle.load(f)
            logger.info(f"Checkpoint loaded from {state.get('timestamp', 'unknown')}")
            return state
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None
    
    def clear(self) -> None:
        """Clear checkpoint after successful completion"""
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()
            logger.info("Checkpoint cleared")


# =============================================================================
# API CLIENT - REFACTORED
# =============================================================================

class AccurateAPIClient:
    """
    Enhanced API Client for Accurate Online
    
    Features:
    - Adaptive rate limiting
    - Exponential backoff retry
    - Request/response logging
    - Comprehensive error handling
    """
    
    def __init__(
        self,
        api_token: str,
        signature_secret: str,
        config: PullerConfig = None
    ):
        self.api_token = api_token
        self.signature_secret = signature_secret
        self.config = config or PullerConfig()
        self.host: Optional[str] = None
        
        # Rate limiting state
        self._last_request_time = 0.0
        self._request_count = 0
        self._window_start = 0.0
        
        # Statistics
        self.stats: Dict[str, EndpointStats] = {}
        
        # Timezone
        self.wib = pytz.timezone('Asia/Jakarta')
    
    def _generate_signature(self, timestamp: str) -> str:
        """Generate HMAC-SHA256 signature"""
        message = timestamp.encode('utf-8')
        secret = self.signature_secret.encode('utf-8')
        signature = hmac.new(secret, message, hashlib.sha256).digest()
        return base64.b64encode(signature).decode('utf-8')
    
    def _get_headers(self) -> Dict[str, str]:
        """Generate request headers with authentication"""
        timestamp = datetime.now(self.wib).strftime('%d/%m/%Y %H:%M:%S')
        return {
            'Authorization': f'Bearer {self.api_token}',
            'X-Api-Timestamp': timestamp,
            'X-Api-Signature': self._generate_signature(timestamp),
            'Content-Type': 'application/json'
        }
    
    def _rate_limit(self) -> None:
        """Adaptive rate limiting with sliding window"""
        current_time = time.time()
        
        # Reset window every second
        if current_time - self._window_start >= 1.0:
            self._window_start = current_time
            self._request_count = 0
        
        # Check if we've exceeded rate limit
        if self._request_count >= self.config.max_requests_per_second:
            sleep_time = 1.0 - (current_time - self._window_start)
            if sleep_time > 0:
                time.sleep(sleep_time)
            self._window_start = time.time()
            self._request_count = 0
        
        # Minimum interval between requests
        elapsed = current_time - self._last_request_time
        if elapsed < self.config.min_request_interval:
            time.sleep(self.config.min_request_interval - elapsed)
        
        self._request_count += 1
        self._last_request_time = time.time()
    
    def _get_endpoint_stats(self, endpoint: str) -> EndpointStats:
        """Get or create stats for endpoint"""
        if endpoint not in self.stats:
            self.stats[endpoint] = EndpointStats()
        return self.stats[endpoint]
    
    def initialize_host(self) -> bool:
        """Initialize host URL from API token"""
        url = 'https://account.accurate.id/api/api-token.do'
        
        try:
            logger.info("Connecting to Accurate API...")
            response = requests.post(
                url,
                headers=self._get_headers(),
                timeout=(self.config.connection_timeout, self.config.request_timeout)
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('s'):
                # Handle both 'database' and 'data usaha' keys
                db_key = 'database' if 'database' in data.get('d', {}) else 'data usaha'
                self.host = data['d'][db_key]['host']
                logger.info(f"✓ Connected successfully: {self.host}")
                return True
            else:
                error_msg = data.get('d', {}).get('error', 'Unknown error')
                logger.error(f"✗ Authentication failed: {error_msg}")
                return False
                
        except requests.exceptions.Timeout:
            logger.error("✗ Connection timeout")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Connection error: {e}")
            return False
        except Exception as e:
            logger.error(f"✗ Unexpected error: {e}")
            return False
    
    def request(
        self,
        endpoint: str,
        method: str = 'GET',
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Make API request with retry mechanism
        
        Returns:
            Tuple of (success, response_data, error_message)
        """
        if not self.host:
            return False, None, "Host not initialized"
        
        stats = self._get_endpoint_stats(endpoint)
        url = f"{self.host}/accurate{endpoint}"
        
        for attempt in range(self.config.max_retries + 1):
            self._rate_limit()
            start_time = time.time()
            
            try:
                if method.upper() == 'GET':
                    response = requests.get(
                        url,
                        headers=self._get_headers(),
                        params=params,
                        timeout=self.config.request_timeout
                    )
                else:
                    response = requests.post(
                        url,
                        headers=self._get_headers(),
                        json=data,
                        timeout=self.config.request_timeout
                    )
                
                stats.total_requests += 1
                stats.processing_time += time.time() - start_time
                
                # Handle rate limiting
                if response.status_code == 429:
                    stats.rate_limit_hits += 1
                    backoff = min(
                        self.config.initial_backoff * (2 ** attempt),
                        self.config.max_backoff
                    )
                    logger.warning(f"Rate limit hit, waiting {backoff:.1f}s (attempt {attempt + 1})")
                    time.sleep(backoff)
                    continue
                
                response.raise_for_status()
                result = response.json()
                
                if result.get('s'):
                    stats.successful_requests += 1
                    return True, result, None
                else:
                    error = result.get('d', {}).get('error', 'API returned false')
                    return False, result, error
                
            except requests.exceptions.HTTPError as e:
                stats.failed_requests += 1
                if response.status_code == 429 and attempt < self.config.max_retries:
                    continue
                return False, None, str(e)
                
            except Exception as e:
                stats.failed_requests += 1
                if attempt < self.config.max_retries:
                    backoff = self.config.initial_backoff * (2 ** attempt)
                    time.sleep(backoff)
                else:
                    return False, None, str(e)
        
        return False, None, "Max retries exceeded"
    
    def fetch_paginated(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        max_pages: Optional[int] = None,
        progress_callback: Optional[callable] = None
    ) -> List[Dict]:
        """
        Fetch all pages of data from endpoint
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            max_pages: Maximum pages to fetch (None = use config)
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of all records from all pages
        """
        params = params or {}
        max_pages = max_pages or self.config.max_pages
        all_data = []
        page = 1
        
        while page <= max_pages:
            params['sp.page'] = page
            params['sp.pageSize'] = self.config.page_size
            
            success, response, error = self.request(endpoint, params=params)
            
            if not success or not response:
                if error:
                    logger.warning(f"Page {page} failed: {error}")
                break
            
            data = response.get('d', [])
            if not data:
                break
            
            all_data.extend(data)
            
            sp = response.get('sp', {})
            total_pages = sp.get('pageCount', 1)
            
            if progress_callback:
                progress_callback(page, total_pages, len(all_data))
            
            if page >= total_pages:
                break
            
            page += 1
            time.sleep(self.config.delay_between_pages)
        
        stats = self._get_endpoint_stats(endpoint)
        stats.total_records = len(all_data)
        
        logger.info(f"  → Fetched {len(all_data)} records from {page} pages")
        return all_data


# =============================================================================
# DATA PULLER - REFACTORED
# =============================================================================

class DataPullerV2:
    """
    Refactored Data Puller for Project 1
    
    Features:
    - GPU acceleration for large datasets
    - Checkpoint/resume capability
    - Comprehensive error handling
    - Cross-endpoint data enrichment preparation
    - Detailed statistics and logging
    """
    
    def __init__(
        self,
        api_token: str,
        signature_secret: str,
        start_date: str,
        end_date: str,
        config: Optional[PullerConfig] = None,
        session_id: Optional[str] = None
    ):
        self.config = config or PullerConfig()
        self.session_id = session_id or datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Initialize components
        self.client = AccurateAPIClient(api_token, signature_secret, self.config)
        self.df_engine = DataFrameEngine(use_gpu=self.config.use_gpu)
        self.checkpoint = CheckpointManager(self.config.checkpoint_dir, self.session_id)
        
        # Date range
        self.start_date = start_date
        self.end_date = end_date
        
        # Data storage
        self.data: Dict[str, pd.DataFrame] = {}
        self.status: Dict[str, PullStatus] = {}
        self.pull_stats: Dict[str, Dict] = {}
        
        # Mappings for enrichment
        self.mappings: Dict[str, Dict] = {}
    
    def _create_progress_callback(self, data_type: str):
        """Create progress callback for logging"""
        def callback(current_page: int, total_pages: int, records: int):
            if current_page % 5 == 0 or current_page == total_pages:
                logger.info(
                    f"  [{data_type}] Page {current_page}/{total_pages} "
                    f"({records:,} records)"
                )
        return callback
    
    def initialize(self) -> bool:
        """Initialize API client and check for resume checkpoint"""
        # Try to resume from checkpoint
        checkpoint_state = self.checkpoint.load()
        if checkpoint_state:
            user_choice = input("Checkpoint found. Resume? (y/n): ").lower()
            if user_choice == 'y':
                self.data = checkpoint_state.get('data', {})
                self.status = checkpoint_state.get('status', {})
                logger.info("Resumed from checkpoint")
                return self.client.host is not None or self.client.initialize_host()
        
        # Fresh start
        return self.client.initialize_host()
    
    def initialize_without_prompt(self, resume_if_exists: bool = True) -> bool:
        """Initialize without user prompt (for automated runs)"""
        if resume_if_exists:
            checkpoint_state = self.checkpoint.load()
            if checkpoint_state:
                self.data = checkpoint_state.get('data', {})
                self.status = checkpoint_state.get('status', {})
                if self.client.host or self.client.initialize_host():
                    logger.info("Resumed from checkpoint")
                    return True
        
        return self.client.initialize_host()
    
    def _save_checkpoint(self):
        """Save current state to checkpoint"""
        state = {
            'data': {k: v for k, v in self.data.items()},
            'status': self.status,
            'session_id': self.session_id
        }
        self.checkpoint.save(state)
    
    # =========================================================================
    # MASTER DATA PULLING
    # =========================================================================
    
    def pull_items(self) -> pd.DataFrame:
        """
        Pull item master data
        
        Known Issues Handled:
        - Some items have no unitPrice
        - itemCategoryName can be empty
        """
        if self.status.get('items') == PullStatus.COMPLETED:
            logger.info("Items already pulled, skipping...")
            return self.data.get('items', pd.DataFrame())
        
        logger.info("Pulling item master data...")
        self.status['items'] = PullStatus.IN_PROGRESS
        
        items = self.client.fetch_paginated(
            '/api/item/list.do',
            params={
                'fields': 'id,no,name,itemType,itemCategoryName,avgCost,unitPrice,unit1Name,minimumStock'
            },
            progress_callback=self._create_progress_callback('Items')
        )
        
        if items:
            df = self.df_engine.create_dataframe(items)
            df = self.df_engine.to_pandas(df)
            
            # Track null values for later enrichment
            self.pull_stats['items'] = {
                'total': len(df),
                'unitPrice_null': (df['unitPrice'].isna() | (df['unitPrice'] == 0)).sum() if 'unitPrice' in df.columns else len(df),
                'avgCost_null': (df['avgCost'].isna() | (df['avgCost'] == 0)).sum() if 'avgCost' in df.columns else len(df),
                'category_null': (df['itemCategoryName'].isna() | (df['itemCategoryName'] == '')).sum() if 'itemCategoryName' in df.columns else 0
            }
            
            logger.info(f"  Items stats: {self.pull_stats['items']}")
            
            self.data['items'] = df
            self.status['items'] = PullStatus.COMPLETED
            self._save_checkpoint()
            return df
        
        self.status['items'] = PullStatus.FAILED
        return pd.DataFrame()
    
    def pull_selling_prices(self) -> pd.DataFrame:
        """
        Pull selling prices for items
        
        Known Issues Handled:
        - 70% items return false/null
        - Response structure inconsistent (list, dict, number)
        - Fallback to unitPrice from item list
        """
        items_df = self.data.get('items', pd.DataFrame())
        if items_df.empty:
            logger.warning("No items data, skipping selling price fetch")
            return pd.DataFrame()
        
        if self.status.get('selling_prices') == PullStatus.COMPLETED:
            logger.info("Selling prices already pulled, skipping...")
            return self.data.get('selling_prices', pd.DataFrame())
        
        logger.info(f"Pulling selling prices for {len(items_df)} items...")
        logger.info("  ⚠️ Note: ~70% items expected to return null (API limitation)")
        self.status['selling_prices'] = PullStatus.IN_PROGRESS
        
        selling_prices = []
        success_count = 0
        fail_count = 0
        
        for idx, item in items_df.iterrows():
            item_id = item.get('id')
            if not item_id:
                continue
            
            # Progress logging
            if (idx + 1) % 200 == 0:
                logger.info(
                    f"  Progress: {idx + 1}/{len(items_df)} "
                    f"(success: {success_count}, fail: {fail_count})"
                )
            
            success, response, error = self.client.request(
                '/api/item/get-selling-price.do',
                params={'id': item_id}
            )
            
            if success and response:
                price_data = response.get('d', {})
                price = self._extract_price(price_data)
                
                if price > 0:
                    selling_prices.append({
                        'item_id': item_id,
                        'selling_price': price,
                        'source': 'api'
                    })
                    success_count += 1
                else:
                    fail_count += 1
            else:
                fail_count += 1
            
            # Checkpoint every N items
            if (idx + 1) % self.config.checkpoint_interval == 0:
                self._save_checkpoint()
        
        # Create DataFrame and merge with unitPrice fallback
        if selling_prices:
            prices_df = pd.DataFrame(selling_prices)
            
            # Merge with items to get unitPrice fallback
            merged = items_df[['id', 'unitPrice']].copy()
            merged = merged.rename(columns={'id': 'item_id', 'unitPrice': 'unit_price_fallback'})
            prices_df = prices_df.merge(merged, on='item_id', how='outer')
            
            # Fill missing selling_price with unit_price_fallback
            prices_df['selling_price'] = prices_df['selling_price'].fillna(
                pd.to_numeric(prices_df['unit_price_fallback'], errors='coerce')
            )
            prices_df.loc[prices_df['selling_price'].isna(), 'source'] = 'fallback'
            prices_df['source'] = prices_df['source'].fillna('fallback')
            
            self.data['selling_prices'] = prices_df
            
            logger.info(f"  ✓ Selling prices: {success_count} from API, {fail_count} need fallback")
        
        self.status['selling_prices'] = PullStatus.COMPLETED
        self._save_checkpoint()
        return self.data.get('selling_prices', pd.DataFrame())
    
    def _extract_price(self, price_data: Any) -> float:
        """
        Extract price from various response structures
        
        Handles:
        - List of price objects
        - Single price dict
        - Direct numeric value
        """
        if not price_data:
            return 0.0
        
        try:
            if isinstance(price_data, list) and len(price_data) > 0:
                first = price_data[0]
                if isinstance(first, dict):
                    for key in ['price', 'unitPrice', 'sellingPrice', 'unit1Price', 'amount']:
                        val = first.get(key, 0)
                        if val and float(val) > 0:
                            return float(val)
                elif isinstance(first, (int, float)):
                    return float(first)
                    
            elif isinstance(price_data, dict):
                for key in ['unit1Price', 'price', 'unitPrice', 'sellingPrice', 'amount']:
                    val = price_data.get(key, 0)
                    if val and float(val) > 0:
                        return float(val)
                # Try unit2-5 prices
                for i in range(2, 6):
                    val = price_data.get(f'unit{i}Price', 0)
                    if val and float(val) > 0:
                        return float(val)
                        
            elif isinstance(price_data, (int, float)):
                return float(price_data)
                
        except (ValueError, TypeError):
            pass
        
        return 0.0
    
    def pull_warehouses(self) -> pd.DataFrame:
        """Pull warehouse master data"""
        if self.status.get('warehouses') == PullStatus.COMPLETED:
            return self.data.get('warehouses', pd.DataFrame())
        
        logger.info("Pulling warehouses...")
        self.status['warehouses'] = PullStatus.IN_PROGRESS
        
        warehouses = self.client.fetch_paginated(
            '/api/warehouse/list.do',
            params={'fields': 'id,name,description,address,locationId'},
            max_pages=5
        )
        
        if warehouses:
            df = pd.DataFrame(warehouses)
            # Flatten address dict if present
            if 'address' in df.columns:
                df['address'] = df['address'].apply(
                    lambda x: json.dumps(x) if isinstance(x, dict) else x
                )
            self.data['warehouses'] = df
            self.status['warehouses'] = PullStatus.COMPLETED
        
        return self.data.get('warehouses', pd.DataFrame())
    
    def pull_customers(self) -> pd.DataFrame:
        """Pull customer master data"""
        if self.status.get('customers') == PullStatus.COMPLETED:
            return self.data.get('customers', pd.DataFrame())
        
        logger.info("Pulling customers...")
        self.status['customers'] = PullStatus.IN_PROGRESS
        
        customers = self.client.fetch_paginated(
            '/api/customer/list.do',
            params={'fields': 'id,name,customerNo'},
            max_pages=20
        )
        
        if customers:
            self.data['customers'] = pd.DataFrame(customers)
            self.status['customers'] = PullStatus.COMPLETED
        
        return self.data.get('customers', pd.DataFrame())
    
    def pull_vendors(self) -> pd.DataFrame:
        """Pull vendor master data"""
        if self.status.get('vendors') == PullStatus.COMPLETED:
            return self.data.get('vendors', pd.DataFrame())
        
        logger.info("Pulling vendors...")
        self.status['vendors'] = PullStatus.IN_PROGRESS
        
        vendors = self.client.fetch_paginated(
            '/api/vendor/list.do',
            params={'fields': 'id,name,vendorNo'},
            max_pages=10
        )
        
        if vendors:
            self.data['vendors'] = pd.DataFrame(vendors)
            self.status['vendors'] = PullStatus.COMPLETED
        
        return self.data.get('vendors', pd.DataFrame())
    
    # =========================================================================
    # INVENTORY DATA PULLING
    # =========================================================================
    
    def pull_current_stock(self) -> pd.DataFrame:
        """
        Pull current stock data
        
        Known Issues Handled:
        - quantity often returns 0
        - Verification via mutation history
        """
        if self.status.get('current_stock') == PullStatus.COMPLETED:
            return self.data.get('current_stock', pd.DataFrame())
        
        logger.info("Pulling current stock...")
        self.status['current_stock'] = PullStatus.IN_PROGRESS
        
        stocks = self.client.fetch_paginated(
            '/api/item/list-stock.do',
            params={
                'fields': 'id,no,name,warehouseId,warehouseName,unitName,stockAvailable,qtyStock,itemType,itemCategoryName,avgCost,unitPrice,upcNo'
            },
            progress_callback=self._create_progress_callback('Stock')
        )
        
        if stocks:
            df = pd.DataFrame(stocks)
            df = df.rename(columns={
                'id': 'product_id',
                'no': 'product_code',
                'name': 'product_name',
                'qtyStock': 'quantity',
                'stockAvailable': 'quantity_available',
                'itemCategoryName': 'category',
                'unitName': 'unit'
            })
            
            # Track stats
            self.pull_stats['current_stock'] = {
                'total': len(df),
                'zero_quantity': (df['quantity'] == 0).sum() if 'quantity' in df.columns else 0,
                'zero_available': (df['quantity_available'] == 0).sum() if 'quantity_available' in df.columns else 0
            }
            logger.info(f"  Stock stats: {self.pull_stats['current_stock']}")
            
            self.data['current_stock'] = df
            self.status['current_stock'] = PullStatus.COMPLETED
            self._save_checkpoint()
        
        return self.data.get('current_stock', pd.DataFrame())
    
    def pull_stock_mutations(self, max_items: int = None) -> pd.DataFrame:
        """
        Pull stock mutation history
        
        Known Issues Handled:
        - Per-item fetching (slow)
        - Many items return empty array
        """
        items_df = self.data.get('items', pd.DataFrame())
        if items_df.empty:
            logger.warning("No items data for mutation fetch")
            return pd.DataFrame()
        
        if self.status.get('stock_mutations') == PullStatus.COMPLETED:
            return self.data.get('stock_mutations', pd.DataFrame())
        
        # Filter inventory items only
        inventory_types = ['INVENTORY', 'GROUP']
        if 'itemType' in items_df.columns:
            items_to_fetch = items_df[items_df['itemType'].isin(inventory_types)]
        else:
            items_to_fetch = items_df
        
        if max_items:
            items_to_fetch = items_to_fetch.head(max_items)
        
        logger.info(f"Pulling stock mutations for {len(items_to_fetch)} items...")
        logger.info("  ⚠️ This may take a while (per-item API calls)")
        self.status['stock_mutations'] = PullStatus.IN_PROGRESS
        
        all_mutations = []
        items_with_data = 0
        items_empty = 0
        
        for idx, item in items_to_fetch.iterrows():
            item_id = item.get('id')
            if not item_id:
                continue
            
            if (idx + 1) % 100 == 0:
                logger.info(
                    f"  Progress: {idx + 1}/{len(items_to_fetch)} "
                    f"(with data: {items_with_data}, empty: {items_empty})"
                )
            
            success, response, error = self.client.request(
                '/api/item/stock-mutation-history.do',
                params={
                    'id': item_id,
                    'startDate': self.start_date,
                    'endDate': self.end_date
                }
            )
            
            if success and response:
                records = response.get('d', [])
                if records:
                    for rec in records:
                        rec['product_id'] = item_id
                        rec['product_code'] = item.get('no', '')
                        rec['product_name'] = item.get('name', '')
                        all_mutations.append(rec)
                    items_with_data += 1
                else:
                    items_empty += 1
            else:
                items_empty += 1
            
            # Checkpoint every N items
            if (idx + 1) % self.config.checkpoint_interval == 0:
                self.data['stock_mutations_partial'] = pd.DataFrame(all_mutations)
                self._save_checkpoint()
        
        if all_mutations:
            df = pd.DataFrame(all_mutations)
            self.data['stock_mutations'] = df
            self.pull_stats['stock_mutations'] = {
                'total_records': len(df),
                'items_with_data': items_with_data,
                'items_empty': items_empty
            }
            logger.info(f"  Mutation stats: {self.pull_stats['stock_mutations']}")
        
        self.status['stock_mutations'] = PullStatus.COMPLETED
        self._save_checkpoint()
        return self.data.get('stock_mutations', pd.DataFrame())
    
    # =========================================================================
    # SALES DATA PULLING
    # =========================================================================
    
    def pull_sales_invoices(self) -> pd.DataFrame:
        """
        Pull sales invoice list
        
        Known Issues Handled:
        - customerId often NULL in list
        - Need detail endpoint for customerId
        """
        if self.status.get('sales_invoices') == PullStatus.COMPLETED:
            return self.data.get('sales_invoices', pd.DataFrame())
        
        logger.info("Pulling sales invoices...")
        self.status['sales_invoices'] = PullStatus.IN_PROGRESS
        
        invoices = self.client.fetch_paginated(
            '/api/sales-invoice/list.do',
            params={
                'fields': 'id,number,transDate,customerId,customerName,totalAmount,invoiceDp',
                'filter.transDate.>=': self.start_date,
                'filter.transDate.<=': self.end_date
            },
            progress_callback=self._create_progress_callback('Invoices')
        )
        
        if invoices:
            df = pd.DataFrame(invoices)
            
            # Track customerId null issue
            self.pull_stats['sales_invoices'] = {
                'total': len(df),
                'customerId_null': df['customerId'].isna().sum() if 'customerId' in df.columns else len(df)
            }
            logger.info(f"  Invoice stats: {self.pull_stats['sales_invoices']}")
            
            self.data['sales_invoices'] = df
            self.status['sales_invoices'] = PullStatus.COMPLETED
            self._save_checkpoint()
        
        return self.data.get('sales_invoices', pd.DataFrame())
    
    def pull_sales_details(self, max_invoices: int = None) -> pd.DataFrame:
        """
        Pull sales invoice details
        
        Known Issues Handled:
        - Inconsistent field naming (detailItem vs items vs detail)
        - Different field names for same data
        """
        invoices_df = self.data.get('sales_invoices', pd.DataFrame())
        if invoices_df.empty:
            logger.warning("No invoices data for detail fetch")
            return pd.DataFrame()
        
        if self.status.get('sales_details') == PullStatus.COMPLETED:
            return self.data.get('sales_details', pd.DataFrame())
        
        invoices_to_fetch = invoices_df
        if max_invoices:
            invoices_to_fetch = invoices_to_fetch.head(max_invoices)
        
        logger.info(f"Pulling details for {len(invoices_to_fetch)} invoices...")
        self.status['sales_details'] = PullStatus.IN_PROGRESS
        
        all_details = []
        
        for idx, invoice in invoices_to_fetch.iterrows():
            invoice_id = invoice.get('id')
            if not invoice_id:
                continue
            
            if (idx + 1) % 100 == 0:
                logger.info(f"  Progress: {idx + 1}/{len(invoices_to_fetch)}")
            
            success, response, error = self.client.request(
                '/api/sales-invoice/detail.do',
                params={'id': invoice_id}
            )
            
            if success and response:
                detail = response.get('d', {})
                
                # Handle inconsistent naming
                items = (
                    detail.get('detailItem') or
                    detail.get('items') or
                    detail.get('detail') or
                    detail.get('detailItems') or
                    []
                )
                
                customer_id = detail.get('customerId') or invoice.get('customerId')
                
                for item in items:
                    item['invoice_id'] = invoice_id
                    item['invoice_number'] = invoice.get('number', '')
                    item['trans_date'] = invoice.get('transDate', '')
                    item['customer_id'] = customer_id
                    
                    # Standardize field names
                    item['item_id'] = item.get('itemId') or item.get('id') or item.get('item_id')
                    item['item_no'] = item.get('itemNo') or item.get('no')
                    item['item_name'] = item.get('itemName') or item.get('name')
                    item['unit_price'] = item.get('unitPrice') or item.get('price') or item.get('unit_price') or 0
                    item['qty'] = item.get('quantity') or item.get('qty') or 0
                    
                    all_details.append(item)
            
            # Checkpoint
            if (idx + 1) % self.config.checkpoint_interval == 0:
                self._save_checkpoint()
        
        if all_details:
            df = pd.DataFrame(all_details)
            self.data['sales_details'] = df
            logger.info(f"  ✓ Fetched {len(df)} sales detail records")
        
        self.status['sales_details'] = PullStatus.COMPLETED
        self._save_checkpoint()
        return self.data.get('sales_details', pd.DataFrame())
    
    # =========================================================================
    # PURCHASE DATA PULLING
    # =========================================================================
    
    def pull_purchase_orders(self) -> pd.DataFrame:
        """Pull purchase order list"""
        if self.status.get('purchase_orders') == PullStatus.COMPLETED:
            return self.data.get('purchase_orders', pd.DataFrame())
        
        logger.info("Pulling purchase orders...")
        self.status['purchase_orders'] = PullStatus.IN_PROGRESS
        
        orders = self.client.fetch_paginated(
            '/api/purchase-order/list.do',
            params={
                'fields': 'id,number,transDate,vendorId,vendorName,totalAmount,status',
                'filter.transDate.>=': self.start_date,
                'filter.transDate.<=': self.end_date
            },
            progress_callback=self._create_progress_callback('PO')
        )
        
        if orders:
            self.data['purchase_orders'] = pd.DataFrame(orders)
            self.status['purchase_orders'] = PullStatus.COMPLETED
        
        return self.data.get('purchase_orders', pd.DataFrame())
    
    def pull_purchase_details(self, max_orders: int = None) -> pd.DataFrame:
        """Pull purchase order details"""
        orders_df = self.data.get('purchase_orders', pd.DataFrame())
        if orders_df.empty:
            logger.warning("No PO data for detail fetch")
            return pd.DataFrame()
        
        if self.status.get('purchase_details') == PullStatus.COMPLETED:
            return self.data.get('purchase_details', pd.DataFrame())
        
        orders_to_fetch = orders_df
        if max_orders:
            orders_to_fetch = orders_to_fetch.head(max_orders)
        
        logger.info(f"Pulling details for {len(orders_to_fetch)} POs...")
        self.status['purchase_details'] = PullStatus.IN_PROGRESS
        
        all_details = []
        
        for idx, order in orders_to_fetch.iterrows():
            order_id = order.get('id')
            if not order_id:
                continue
            
            if (idx + 1) % 50 == 0:
                logger.info(f"  Progress: {idx + 1}/{len(orders_to_fetch)}")
            
            success, response, error = self.client.request(
                '/api/purchase-order/detail.do',
                params={'id': order_id}
            )
            
            if success and response:
                detail = response.get('d', {})
                items = detail.get('detailItem') or detail.get('items') or []
                
                for item in items:
                    item['po_id'] = order_id
                    item['po_number'] = order.get('number', '')
                    item['trans_date'] = order.get('transDate', '')
                    item['vendor_id'] = order.get('vendorId')
                    
                    # Standardize fields
                    item['item_id'] = item.get('itemId') or item.get('id')
                    item['unit_price'] = item.get('unitPrice') or item.get('price') or 0
                    item['qty'] = item.get('quantity') or item.get('qty') or 0
                    
                    all_details.append(item)
        
        if all_details:
            df = pd.DataFrame(all_details)
            self.data['purchase_details'] = df
            logger.info(f"  ✓ Fetched {len(df)} PO detail records")
        
        self.status['purchase_details'] = PullStatus.COMPLETED
        self._save_checkpoint()
        return self.data.get('purchase_details', pd.DataFrame())
    
    # =========================================================================
    # FULL PIPELINE
    # =========================================================================
    
    def run_full_pull(
        self,
        include_selling_prices: bool = True,
        include_mutations: bool = True,
        include_sales_details: bool = True,
        max_mutation_items: int = None,
        max_invoice_details: int = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Run complete data pulling pipeline
        
        Args:
            include_selling_prices: Fetch per-item selling prices (slow)
            include_mutations: Fetch stock mutations (slow)
            include_sales_details: Fetch sales invoice details
            max_mutation_items: Limit mutation fetch to N items
            max_invoice_details: Limit invoice detail fetch to N invoices
            
        Returns:
            Dictionary of all pulled DataFrames
        """
        start_time = time.time()
        logger.info("=" * 60)
        logger.info("STARTING FULL DATA PULL")
        logger.info(f"Date range: {self.start_date} to {self.end_date}")
        logger.info(f"GPU: {self.df_engine.engine_name}")
        logger.info("=" * 60)
        
        # Initialize
        if not self.initialize_without_prompt(resume_if_exists=True):
            raise Exception("Failed to initialize API client")
        
        # Master Data
        logger.info("\n📦 PHASE 1: Master Data")
        self.pull_items()
        self.pull_warehouses()
        self.pull_customers()
        self.pull_vendors()
        
        if include_selling_prices:
            self.pull_selling_prices()
        
        # Inventory Data
        logger.info("\n📊 PHASE 2: Inventory Data")
        self.pull_current_stock()
        
        if include_mutations:
            self.pull_stock_mutations(max_items=max_mutation_items)
        
        # Transaction Data
        logger.info("\n💰 PHASE 3: Transaction Data")
        self.pull_sales_invoices()
        
        if include_sales_details:
            self.pull_sales_details(max_invoices=max_invoice_details)
        
        self.pull_purchase_orders()
        self.pull_purchase_details()
        
        # Final Summary
        elapsed = time.time() - start_time
        logger.info("\n" + "=" * 60)
        logger.info("PULL COMPLETE")
        logger.info(f"Total time: {elapsed/60:.1f} minutes")
        logger.info("Data summary:")
        for name, df in self.data.items():
            if isinstance(df, pd.DataFrame) and not df.empty:
                logger.info(f"  {name}: {len(df):,} records")
        logger.info("=" * 60)
        
        # Clear checkpoint on success
        self.checkpoint.clear()
        
        return self.data
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the pull"""
        return {
            'pull_stats': self.pull_stats,
            'endpoint_stats': {k: vars(v) for k, v in self.client.stats.items()},
            'status': {k: v.value for k, v in self.status.items()},
            'data_counts': {k: len(v) for k, v in self.data.items() if isinstance(v, pd.DataFrame)}
        }
    
    def save_to_csv(self, output_dir: str = "../data/pulled") -> Dict[str, str]:
        """
        Save all pulled data to CSV files
        
        Args:
            output_dir: Directory to save CSV files (relative to modules folder)
            
        Returns:
            Dictionary of {data_name: file_path}
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        saved_files = {}
        
        logger.info(f"\n💾 Saving data to {output_path.absolute()}...")
        
        for name, df in self.data.items():
            if not isinstance(df, pd.DataFrame) or df.empty:
                continue
            
            # Skip partial data
            if 'partial' in name:
                continue
            
            file_path = output_path / f"{name}.csv"
            
            try:
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
                saved_files[name] = str(file_path)
                logger.info(f"  ✓ {name}.csv ({len(df):,} records)")
            except Exception as e:
                logger.error(f"  ✗ Failed to save {name}: {e}")
        
        logger.info(f"✓ Saved {len(saved_files)} files to {output_path.absolute()}")
        return saved_files


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main entry point for standalone execution"""
    from dotenv import load_dotenv
    
    # Load environment
    load_dotenv()
    
    api_token = os.getenv('API_TOKEN')
    signature_secret = os.getenv('SIGNATURE_SECRET')
    
    if not api_token or not signature_secret:
        logger.error("API_TOKEN and SIGNATURE_SECRET required in environment")
        return
    
    # Date range - manual input
    print("\n📅 Date Range Configuration")
    print("Format: DD/MM/YYYY (contoh: 01/10/2025)")
    print("-" * 40)
    
    start_date = input("Start Date: ").strip()
    end_date = input("End Date: ").strip()
    
    # Validate format
    try:
        datetime.strptime(start_date, '%d/%m/%Y')
        datetime.strptime(end_date, '%d/%m/%Y')
    except ValueError:
        logger.error("Format tanggal tidak valid! Gunakan DD/MM/YYYY")
        return
    
    print(f"\n✓ Date range: {start_date} to {end_date}")
    
    # Configuration
    config = PullerConfig(
        use_gpu=True,
        checkpoint_interval=50,
        max_pages=50
    )
    
    # Run
    puller = DataPullerV2(
        api_token=api_token,
        signature_secret=signature_secret,
        start_date=start_date,
        end_date=end_date,
        config=config
    )
    
    try:
        data = puller.run_full_pull(
            include_selling_prices=True,
            include_mutations=True,
            include_sales_details=True
        )
        
        # Save all data to CSV
        puller.save_to_csv("../data/pulled")
        
        # Save statistics
        stats = puller.get_statistics()
        with open('pull_statistics.json', 'w') as f:
            json.dump(stats, f, indent=2, default=str)
        
        logger.info("Statistics saved to pull_statistics.json")
        
    except Exception as e:
        logger.error(f"Pull failed: {e}")
        raise


if __name__ == '__main__':
    main()
