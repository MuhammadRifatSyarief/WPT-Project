# PROMPT MODULE 1: Data Puller Refactored (V2)
## Project 1 - Intelligent Inventory Optimization & Stockout Prediction

---

## Overview

| Attribute | Value |
|-----------|-------|
| File | `modules/data_puller_v2.py` |
| Lines | ~1,300 |
| Status | ✅ Implemented |
| GPU Support | cuDF (fallback pandas) |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    DATA PULLER V2                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  PullerConfig ─────┬──────────────  CheckpointManager   │
│  (rate limit,      │                (save/load/resume)  │
│   retries, GPU)    │                                    │
│                    ▼                                    │
│            AccurateAPIClient                            │
│            ├─ HMAC-SHA256 auth                          │
│            ├─ Adaptive rate limiting                    │
│            ├─ Exponential backoff                       │
│            └─ Per-endpoint stats                        │
│                    │                                    │
│                    ▼                                    │
│  DataFrameEngine ──┴───────────  DataPullerV2           │
│  (cuDF or pandas)               ├─ pull_items()        │
│                                 ├─ pull_selling_prices()│
│                                 ├─ pull_current_stock() │
│                                 ├─ pull_stock_mutations()│
│                                 ├─ pull_sales_invoices()│
│                                 ├─ pull_sales_details() │
│                                 ├─ pull_purchase_orders()│
│                                 └─ pull_purchase_details()│
└─────────────────────────────────────────────────────────┘
```

---

## Key Components

### 1. PullerConfig
```python
@dataclass
class PullerConfig:
    max_requests_per_second: int = 3
    min_request_interval: float = 0.35
    max_retries: int = 3
    initial_backoff: float = 2.0
    max_backoff: float = 60.0
    page_size: int = 100
    max_pages: int = 50
    checkpoint_interval: int = 100
    use_gpu: bool = True
```

### 2. DataFrameEngine
- Auto-detect GPU availability
- Graceful fallback to pandas
- Methods: `create_dataframe()`, `to_pandas()`, `concat()`

### 3. CheckpointManager
- Save state to pickle file
- Resume from last checkpoint
- Auto-clear after success

### 4. AccurateAPIClient
- HMAC-SHA256 authentication
- Sliding window rate limiting
- Exponential backoff retry (max 60s)
- Per-endpoint statistics

### 5. DataPullerV2
Main orchestrator with full pipeline support

---

## Known Issues Handled

| Issue | Solution |
|-------|----------|
| Selling price 70% null | Fallback chain: unit1Price → price → unitPrice → sellingPrice |
| customerId missing in list | Fetch from detail endpoint |
| Inconsistent field naming | Auto-standardize: detailItem, items, detail |
| Rate limit 429 | Exponential backoff with max 60s |
| Long-running jobs fail | Checkpoint system for resume |

---

## Usage

### Basic
```python
from modules.data_puller_v2 import DataPullerV2, PullerConfig

config = PullerConfig(use_gpu=True)
puller = DataPullerV2(
    api_token='YOUR_TOKEN',
    signature_secret='YOUR_SECRET',
    start_date='01/10/2025',
    end_date='14/01/2026',
    config=config
)

data = puller.run_full_pull()
```

### With Environment Variables
```bash
# .env file
API_TOKEN=your_token_here
SIGNATURE_SECRET=your_secret_here
```

```python
# Run from command line
python data_puller_v2.py
```

### Selective Pulling
```python
puller.pull_items()
puller.pull_current_stock()
stats = puller.get_statistics()
```

---

## Output Data

| Key | Description |
|-----|-------------|
| `items` | Master items (id, no, name, avgCost, unitPrice) |
| `selling_prices` | Per-item prices with source (api/fallback) |
| `warehouses` | Gudang list |
| `customers` | Pelanggan list |
| `vendors` | Supplier list |
| `current_stock` | Current stock levels |
| `stock_mutations` | Stock movement history |
| `sales_invoices` | Sales invoice list |
| `sales_details` | Invoice line items (standardized) |
| `purchase_orders` | PO list |
| `purchase_details` | PO line items (standardized) |

---

## Statistics Tracked

```python
stats = puller.get_statistics()

# Per data type
stats['pull_stats']['items']['unitPrice_null']
stats['pull_stats']['current_stock']['zero_quantity']

# Per endpoint
stats['endpoint_stats']['/api/item/list.do']['successful_requests']
stats['endpoint_stats']['/api/item/list.do']['rate_limit_hits']
```

---

## Pipeline Phases

```
PHASE 1: Master Data
├── pull_items()
├── pull_warehouses()
├── pull_customers()
├── pull_vendors()
└── pull_selling_prices() [slow, optional]

PHASE 2: Inventory Data
├── pull_current_stock()
└── pull_stock_mutations() [slow, optional]

PHASE 3: Transaction Data
├── pull_sales_invoices()
├── pull_sales_details() [optional]
├── pull_purchase_orders()
└── pull_purchase_details()
```

---

## Next Step: Module 2 (Data Preparation)

Output dari Module 1 siap untuk:
1. Data Cleansing
2. Cross-Endpoint Enrichment
3. Validation Layer
4. Imputation

Statistik null/missing sudah di-track di `pull_stats` untuk digunakan di Module 2.
