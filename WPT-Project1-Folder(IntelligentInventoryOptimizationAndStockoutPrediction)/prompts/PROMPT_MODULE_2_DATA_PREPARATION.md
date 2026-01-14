# PROMPT MODULE 2: Data Preparation & Enrichment
## Project 1 - Intelligent Inventory Optimization

---

## Overview

| Attribute | Value |
|-----------|-------|
| File | `modules/data_preparation.py` |
| Lines | ~600 |
| Input | `data/pulled/*.csv` |
| Output | `data/prepared/*.csv` |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 DATA PREPARATION                         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  DataLoader ───────────────────────────────────────────→│
│  (load CSVs)                                             │
│                    ↓                                    │
│  DataCleanser ────────────────────────────────────────→│
│  ├─ Remove duplicates                                   │
│  ├─ Standardize formats                                 │
│  ├─ Parse dates                                         │
│  └─ Ensure numeric types                                │
│                    ↓                                    │
│  DataEnricher ────────────────────────────────────────→│
│  ├─ enrich_selling_price()                              │
│  ├─ enrich_avg_cost()                                   │
│  ├─ enrich_minimum_stock()                              │
│  └─ verify_stock_with_mutations()                       │
│                    ↓                                    │
│  DataValidator ───────────────────────────────────────→│
│  ├─ Quality score calculation                           │
│  └─ Validation report                                   │
│                    ↓                                    │
│  Save to data/prepared/                                │
└─────────────────────────────────────────────────────────┘
```

---

## Cross-Endpoint Enrichment Logic

### Selling Price Fallback Chain
```
1. selling_prices.selling_price (from API)
           ↓ if null
2. sales_details.unit_price (average per item)
           ↓ if null
3. items.itemCategoryName → category median
           ↓ if null
4. Apply minimum: Rp 1,000
```

### Average Cost Fallback Chain
```
1. purchase_details.unit_price (average per item)
           ↓ if null
2. stock_mutations.itemCost (average per item)
           ↓ if null
3. items.unitPrice × 0.6 (40% margin estimate)
           ↓ if null
4. Apply minimum: Rp 500
```

---

## Usage

```bash
cd modules
python data_preparation.py
```

### Output
```
data/prepared/
├── items.csv (enriched with prices)
├── current_stock.csv (with reliability flag)
├── sales_details.csv (cleaned)
├── purchase_details.csv (cleaned)
├── stock_mutations.csv (cleaned)
├── ... (other datasets)
└── validation_report.json
```

---

## Key Methods

| Method | Description |
|--------|-------------|
| `DataCleanser.clean_items()` | Remove duplicates, standardize text |
| `DataEnricher.enrich_selling_price()` | 3-level fallback for price |
| `DataEnricher.enrich_avg_cost()` | 3-level fallback for cost |
| `DataEnricher.verify_stock_with_mutations()` | Add reliability flag |
| `DataValidator.calculate_quality_score()` | Score 0-100% |

---

## Configuration

```python
@dataclass
class PreparationConfig:
    input_dir: str = "../data/pulled"
    output_dir: str = "../data/prepared"
    price_margin_estimate: float = 0.6   # avgCost = price × 0.6
    min_selling_price: float = 1000.0    # Minimum Rp 1,000
    min_avg_cost: float = 500.0          # Minimum Rp 500
    min_quality_score: float = 70.0      # Quality threshold
    default_category: str = "Uncategorized"
    default_minimum_stock: int = 5
```

---

## Next Steps: Module 3 (Feature Engineering)

Output dari Module 2 siap untuk:
1. Perhitungan demand metrics
2. Inventory turnover calculation
3. ML feature generation
