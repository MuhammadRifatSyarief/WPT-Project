# PROMPT MODULE 8: Slow-Moving Analysis
## Project 1 - Intelligent Inventory Optimization

---

## Overview

| Attribute | Value |
|-----------|-------|
| File | `modules/slow_moving_analysis.py` |
| Lines | ~470 |
| Input | `data/features/`, `data/prepared/` |
| Output | `data/slow_moving/` |

---

## Components

| Component | Function |
|-----------|----------|
| **SlowMovingClassifier** | Classify items by movement velocity |
| **AgingAnalyzer** | Analyze inventory aging |
| **SlowMovingRecommendationEngine** | Generate action recommendations |
| **FinancialImpactCalculator** | Calculate holding cost waste |

---

## Movement Classification

| Class | Criteria |
|-------|----------|
| **Dead Stock** | No sales in 180+ days |
| **Slow Moving** | No sales in 90+ days OR turnover < 1x/year |
| **Normal** | Regular movement |
| **Fast Moving** | Turnover >= 12x/year |

---

## Aging Buckets

| Bucket | Days |
|--------|------|
| Fresh | 0-30 days |
| Recent | 31-60 days |
| Aging | 61-90 days |
| Old | 91-180 days |
| Very Old | 181-365 days |
| Ancient | 365+ days |

---

## Markdown Rates

| Age | Discount |
|-----|----------|
| 30-60 days | 10% |
| 60-90 days | 20% |
| 90-180 days | 35% |
| 180-365 days | 50% |
| 365+ days | 70% (clearance) |

---

## Recommendations

| Condition | Recommendation |
|-----------|----------------|
| Dead Stock > 365 days | Dispose/Write-off |
| Dead Stock < 365 days | Clearance Sale (70% off) |
| Slow Moving > 180 days | Deep Discount (50% off) |
| Slow Moving 90-180 days | Markdown (35% off) |
| Slow Moving < 90 days | Promotional Sale (20% off) |
| Fast Moving | No Action |

---

## Usage

```bash
cd modules
python slow_moving_analysis.py
```

---

## Output

```
data/slow_moving/
├── slow_moving_analysis.csv   # Full analysis per item
├── action_items.csv           # Items needing action (sorted by priority)
└── analysis_summary.json      # Summary and financial impact
```

### slow_moving_analysis.csv Schema

| Column | Type | Description |
|--------|------|-------------|
| id | int | Item ID |
| days_since_last_sale | float | Days since last sale |
| movement_class | str | Dead Stock/Slow Moving/Normal/Fast |
| aging_bucket | str | Aging category |
| recommendation | str | Action recommendation |
| markdown_rate | float | Suggested discount |
| suggested_price | float | Price after markdown |
| priority_score | float | Action priority (0-100) |

---

## Financial Impact Output

```json
{
  "total_slow_moving_items": 500,
  "total_slow_moving_stock_value": 50000000,
  "annual_holding_cost_waste": 10000000,
  "dead_stock_value": 20000000,
  "slow_moving_value": 30000000,
  "potential_recovery": 15000000
}
```

---

## Next: Dashboard Integration

Output dari semua modules siap untuk:
1. Full dashboard integration
2. Executive reporting
3. Automated alerts
