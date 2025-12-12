"""
==========================================================================
PROJECT 2: SALES PERFORMANCE & CUSTOMER SEGMENTATION ANALYTICS
==========================================================================
File: modules/api_client.py
Purpose: API client for Accurate Online with rate limiting and retry logic
Author: v0
Created: 2025
==========================================================================

OVERVIEW:
---------
Handles all HTTP communication with Accurate Online API including:
- Authentication with Bearer token and HMAC signature
- Rate limiting to prevent 429 errors
- Exponential backoff retry mechanism
- Pagination support

USAGE:
------
    from modules.api_client import SalesAnalyticsAPIClient
    
    client = SalesAnalyticsAPIClient(api_token, signature_secret)
    if client.initialize_host():
        data = client.fetch_all_pages('/api/customer/list.do')
"""

import requests
import hashlib
import hmac
import base64
import time
import pytz
from datetime import datetime
from typing import Dict, List, Optional, Any

import sys
sys.path.append('..')
from config.constants import API_CONFIG, DATE_CONFIG


class SalesAnalyticsAPIClient:
    """
    API client specifically designed for Sales Performance & Customer Segmentation.
    
    Features:
    ---------
    - HMAC-SHA256 authentication
    - Rate limiting (3 requests/second default)
    - Automatic retry with exponential backoff
    - Pagination handling
    - Request statistics tracking
    
    Attributes:
    -----------
    api_token : str
        Bearer token for API authentication
    signature_secret : str
        Secret key for HMAC signature generation
    host : str
        Dynamic host URL obtained from API
    request_count : int
        Number of requests in current second
    total_requests : int
        Total requests made in session
    failed_requests : int
        Number of failed requests
    """
    
    def __init__(self, api_token: str, signature_secret: str):
        """
        Initialize API client.
        
        Args:
            api_token: Bearer token from Accurate Online
            signature_secret: Secret key for signature generation
        """
        self.api_token = api_token
        self.signature_secret = signature_secret
        self.host: Optional[str] = None
        
        # Rate limiting state
        self.request_count = 0
        self.last_request_time = time.time()
        
        # Statistics
        self.total_requests = 0
        self.failed_requests = 0
        
        # Timezone
        self.timezone = pytz.timezone(DATE_CONFIG['TIMEZONE'])
    
    def _rate_limit(self) -> None:
        """
        Enforce rate limiting to avoid 429 Too Many Requests.
        
        Limits to API_CONFIG['REQUESTS_PER_SECOND'] requests per second.
        """
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        # Reset counter if more than 1 second has passed
        if elapsed >= 1.0:
            self.request_count = 0
            self.last_request_time = current_time
        
        # If at limit, wait until next second
        max_requests = API_CONFIG['REQUESTS_PER_SECOND']
        if self.request_count >= max_requests:
            sleep_time = 1.2 - elapsed  # 1.2s for safety margin
            if sleep_time > 0:
                time.sleep(sleep_time)
            self.request_count = 0
            self.last_request_time = time.time()
        
        self.request_count += 1
        self.total_requests += 1
    
    def _generate_signature(self, timestamp: str) -> str:
        """
        Generate HMAC-SHA256 signature for API authentication.
        
        Args:
            timestamp: Timestamp string in DD/MM/YYYY HH:MM:SS format
            
        Returns:
            Base64 encoded signature string
        """
        message = timestamp.encode('utf-8')
        secret = self.signature_secret.encode('utf-8')
        signature = hmac.new(secret, message, hashlib.sha256).digest()
        return base64.b64encode(signature).decode('utf-8')
    
    def _get_timestamp(self) -> str:
        """
        Generate timestamp in required format (DD/MM/YYYY HH:MM:SS) for WIB timezone.
        
        Returns:
            Formatted timestamp string
        """
        now = datetime.now(self.timezone)
        return now.strftime('%d/%m/%Y %H:%M:%S')
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Generate HTTP headers with authentication.
        
        Returns:
            Dictionary of HTTP headers
        """
        timestamp = self._get_timestamp()
        signature = self._generate_signature(timestamp)
        
        return {
            'Authorization': f'Bearer {self.api_token}',
            'X-Api-Timestamp': timestamp,
            'X-Api-Signature': signature,
            'Content-Type': 'application/json'
        }
    
    def initialize_host(self) -> bool:
        """
        Initialize API host by fetching host URL from API token endpoint.
        
        Returns:
            True if successful, False otherwise
        """
        url = f"{API_CONFIG['BASE_URL_ACCOUNT']}/api/api-token.do"
        
        try:
            response = requests.post(
                url, 
                headers=self._get_headers(),
                timeout=API_CONFIG['REQUEST_TIMEOUT']
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('s'):  # Success
                # Handle different response structures
                db_key = 'database' if 'database' in data['d'] else 'data usaha'
                self.host = data['d'][db_key]['host']
                
                print(f"✓ Connection successful!")
                print(f"✓ Host: {self.host}")
                print(f"✓ Database: {data['d'][db_key].get('alias', 'N/A')}")
                return True
            else:
                print("✗ Failed to get API token information")
                print(f"  Response: {data}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"✗ Connection error: {str(e)}")
            return False
        except Exception as e:
            print(f"✗ Unexpected error: {str(e)}")
            return False
    
    def request_api(
        self, 
        endpoint: str, 
        method: str = 'GET', 
        params: Optional[Dict] = None, 
        data: Optional[Dict] = None,
        max_retries: Optional[int] = None
    ) -> Optional[Dict]:
        """
        Make API request with retry mechanism.
        
        Args:
            endpoint: API endpoint path (e.g., '/api/customer/list.do')
            method: HTTP method ('GET' or 'POST')
            params: Query parameters for GET requests
            data: JSON body for POST requests
            max_retries: Maximum retry attempts (default from config)
            
        Returns:
            Response JSON dict if successful, None otherwise
        """
        if not self.host:
            print("✗ Host not initialized. Call initialize_host() first.")
            return None
        
        if max_retries is None:
            max_retries = API_CONFIG['RETRY_MAX_ATTEMPTS']
        
        url = f"{self.host}{API_CONFIG['BASE_URL_ACCURATE']}{endpoint}"
        
        for attempt in range(max_retries + 1):
            self._rate_limit()
            headers = self._get_headers()
            
            try:
                if method.upper() == 'GET':
                    response = requests.get(
                        url, 
                        headers=headers, 
                        params=params,
                        timeout=API_CONFIG['REQUEST_TIMEOUT']
                    )
                else:
                    response = requests.post(
                        url, 
                        headers=headers, 
                        json=data,
                        timeout=API_CONFIG['REQUEST_TIMEOUT']
                    )
                
                # Handle rate limit (429)
                if response.status_code == 429:
                    wait_time = (2 ** attempt) + 5
                    print(f"   ⚠️ Rate limit hit, waiting {wait_time}s... (Attempt {attempt + 1}/{max_retries + 1})")
                    time.sleep(wait_time)
                    continue
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.HTTPError as e:
                if response.status_code == 429 and attempt < max_retries:
                    continue
                else:
                    self.failed_requests += 1
                    return None
                    
            except requests.exceptions.RequestException as e:
                self.failed_requests += 1
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                else:
                    return None
                    
            except Exception as e:
                self.failed_requests += 1
                return None
        
        return None
    
    def fetch_all_pages(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        max_pages: Optional[int] = None,
        delay_between_pages: Optional[float] = None,
        show_progress: bool = True
    ) -> List[Dict]:
        """
        Fetch all pages of paginated data.
        
        Args:
            endpoint: API endpoint path
            params: Additional query parameters
            max_pages: Maximum pages to fetch (default from config)
            delay_between_pages: Delay between page requests
            show_progress: Whether to show progress indicator
            
        Returns:
            List of all records from all pages
        """
        if params is None:
            params = {}
        
        if max_pages is None:
            max_pages = API_CONFIG['MAX_PAGES']
        
        if delay_between_pages is None:
            delay_between_pages = API_CONFIG['DELAY_BETWEEN_PAGES']
        
        all_data = []
        page = 1
        
        while True:
            params['sp.page'] = page
            params['sp.pageSize'] = API_CONFIG['DEFAULT_PAGE_SIZE']
            
            if show_progress:
                print(f"   📄 Page {page}...", end='\r')
            
            response = self.request_api(endpoint, params=params)
            
            if not response or not response.get('s'):
                break
            
            data = response.get('d', [])
            if not data:
                break
            
            all_data.extend(data)
            
            # Check pagination info
            sp = response.get('sp', {})
            page_count = sp.get('pageCount', 1)
            
            if page >= page_count or page >= max_pages:
                break
            
            page += 1
            
            if delay_between_pages > 0:
                time.sleep(delay_between_pages)
        
        if show_progress:
            print(f"   ✅ {len(all_data):,} records from {page} pages          ")
        
        return all_data
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get API request statistics.
        
        Returns:
            Dictionary with request statistics
        """
        success_rate = 0.0
        if self.total_requests > 0:
            success_rate = (self.total_requests - self.failed_requests) / self.total_requests * 100
        
        return {
            'total_requests': self.total_requests,
            'failed_requests': self.failed_requests,
            'success_rate': success_rate,
            'host': self.host,
        }
