# PROMPT MODULE 3: Feature Engineering
## Project 1 - Intelligent Inventory Optimization

---

## Overview

| Attribute | Value |
|-----------|-------|
| File | `modules/feature_engineering.py` |
| Lines | ~850 |
| Input | `data/prepared/*.csv` |
| Output | `data/features/master_features.csv` |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│               FEATURE ENGINEERING                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  DemandFeatureGenerator ──────────────────────────────→│
│  ├─ avg_daily_demand                                    │
│  ├─ demand_cv (coefficient of variation)                │
│  ├─ demand_trend (growing/stable/declining)             │
│  └─ max_daily_demand                                    │
│                                                          │
│  InventoryFeatureGenerator ───────────────────────────→│
│  ├─ turnover_ratio (0.5x - 52x per year)                │
│  ├─ days_in_inventory (7 - 365 days)                    │
│  └─ stock_coverage_days (0 - 180 days)                  │
│                                                          │
│  FinancialFeatureGenerator ───────────────────────────→│
│  ├─ gross_margin (5% - 80%)                             │
│  └─ holding_cost_per_unit                               │
│                                                          │
│  RiskFeatureGenerator ────────────────────────────────→│
│  ├─ days_until_stockout                                 │
│  ├─ stockout_probability (0 - 1)                        │
│  └─ risk_level (critical/high/medium/low)               │
│                                                          │
│  ABCClassifier ───────────────────────────────────────→│
│  └─ abc_class (A/B/C by value)                          │
│                                                          │
│  EOQCalculator ───────────────────────────────────────→│
│  ├─ eoq (1 - 10,000 units)                              │
│  └─ reorder_point                                       │
└─────────────────────────────────────────────────────────┘
```

---

## Realistic Business Bounds

| Feature | Min | Max | Unit |
|---------|-----|-----|------|
| `turnover_ratio` | 0.5 | 52 | per year |
| `days_in_inventory` | 7 | 365 | days |
| `stock_coverage` | 0 | 180 | days |
| `gross_margin` | 5% | 80% | - |
| `eoq` | 1 | 10,000 | units |
| `demand_cv` | 0.1 | 3.0 | - |

---

## Key Formulas

### Inventory Turnover
```
Turnover Ratio = Annual Sales (units) / Average Inventory
Days in Inventory = 365 / Turnover Ratio
```

### Stock Coverage
```
Coverage Days = Current Stock / Avg Daily Demand
```

### Gross Margin
```
Gross Margin = (Selling Price - Cost) / Selling Price
```

### EOQ (Economic Order Quantity)
```
EOQ = √(2 × D × S / H)
where:
  D = Annual demand
  S = Ordering cost (Rp 100,000)
  H = Holding cost (20% × unit cost)
```

### Reorder Point
```
ROP = (Lead Time × Avg Daily Demand) + Safety Stock
Safety Stock = 1.65 × Demand Std × √Lead Time
```

---

## ABC Classification

| Class | Value Threshold | Typical % Items |
|-------|-----------------|-----------------|
| A | Top 80% of value | ~20% |
| B | Next 15% | ~30% |
| C | Bottom 5% | ~50% |

---

## Usage

```bash
cd modules
python feature_engineering.py
```

### Output
```
data/features/
├── master_features.csv (all features combined)
├── demand_features.csv
├── trend_features.csv
├── turnover_features.csv
├── coverage_features.csv
├── margins_features.csv
├── risk_features.csv
├── abc_features.csv
└── eoq_features.csv
```

---

## Output Schema (master_features.csv)

| Column | Type | Description |
|--------|------|-------------|
| id | int | Item ID |
| no | str | Item code |
| name | str | Item name |
| category | str | Category |
| avg_daily_demand | float | Average daily sales |
| demand_cv | float | Demand variability |
| demand_trend | float | Trend % |
| trend_class | str | growing/stable/declining |
| turnover_ratio | float | Annual turnover |
| days_in_inventory | float | Stock duration |
| stock_coverage_days | float | Days until stockout |
| gross_margin | float | Profit margin % |
| days_until_stockout | float | Risk metric |
| stockout_probability | float | 0-1 scale |
| risk_level | str | critical/high/medium/low |
| abc_class | str | A/B/C |
| eoq | int | Optimal order qty |
| reorder_point | int | When to reorder |

---

## Next Steps: Module 4-5 (ML Models)

Output dari Module 3 siap untuk:
1. **Module 4**: Demand Forecasting (Prophet/LSTM)
2. **Module 5**: Stockout Prediction (Classification ML)
