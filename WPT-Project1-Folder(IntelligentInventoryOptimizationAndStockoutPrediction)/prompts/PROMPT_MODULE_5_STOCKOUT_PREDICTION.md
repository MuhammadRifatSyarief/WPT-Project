# PROMPT MODULE 5: Stockout Prediction
## Project 1 - Intelligent Inventory Optimization

---

## Overview

| Attribute | Value |
|-----------|-------|
| File | `modules/stockout_prediction.py` |
| Lines | ~500 |
| Input | `data/features/`, `data/forecasts/` |
| Output | `data/predictions/` |

---

## Models

| Model | Use Case | Library |
|-------|----------|---------|
| **Random Forest** | ML classification | scikit-learn |
| **Rule-based** | Fallback | Built-in |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│               STOCKOUT PREDICTION                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  StockoutClassifier ──────────────────────────────────→│
│  ├─ Prepare training data (features + labels)          │
│  ├─ Train Random Forest (balanced classes)              │
│  └─ Predict stockout probability                        │
│                    ↓                                    │
│  RiskCalculator ──────────────────────────────────────→│
│  ├─ Combined risk score formula                         │
│  ├─ Risk classification (critical/high/medium/low)     │
│  └─ Reorder recommendations                             │
│                    ↓                                    │
│  AlertGenerator ──────────────────────────────────────→│
│  ├─ Filter high-risk items                              │
│  └─ Prioritize by ABC class and risk score              │
└─────────────────────────────────────────────────────────┘
```

---

## Risk Score Formula

```
risk_score = (coverage_risk × 0.4) + 
             (demand_risk × 0.3) + 
             (ml_risk × 0.2) + 
             (abc_weight × 0.1)
```

| Component | Weight | Source |
|-----------|--------|--------|
| Coverage Risk | 40% | stock_coverage_days |
| Demand Risk | 30% | demand_cv (variability) |
| ML Risk | 20% | Random Forest probability |
| ABC Weight | 10% | ABC classification |

---

## Risk Classification

| Class | Score Range | Action |
|-------|-------------|--------|
| **Critical** | >= 0.7 | Immediate reorder |
| **High** | 0.5 - 0.7 | Order soon |
| **Medium** | 0.3 - 0.5 | Plan order |
| **Low** | < 0.3 | Monitor |

---

## Reorder Urgency

| Urgency | Condition |
|---------|-----------|
| **Immediate** | coverage < lead_time (7 days) |
| **Soon** | coverage < warning (14 days) |
| **Planned** | coverage < safe (30 days) |
| **Not Needed** | coverage >= 30 days |

---

## Usage

```bash
cd modules
python stockout_prediction.py
```

---

## Output

```
data/predictions/
├── stockout_predictions.csv    # Full predictions
├── stockout_alerts.json        # Prioritized alerts
├── model_metrics.json          # ML model performance
└── prediction_summary.json     # Summary stats
```

### stockout_predictions.csv Schema

| Column | Type | Description |
|--------|------|-------------|
| id | int | Item ID |
| risk_score | float | 0-1 combined risk |
| risk_class | str | critical/high/medium/low |
| reorder_urgency | str | immediate/soon/planned/not_needed |
| recommended_qty | int | Order quantity |
| expected_stockout_date | str | Predicted stockout date |

### stockout_alerts.json Schema

```json
{
  "generated_at": "2026-01-14T10:00:00",
  "total_alerts": 50,
  "critical_count": 10,
  "high_count": 40,
  "alerts": [
    {
      "item_id": 123,
      "item_name": "Product A",
      "risk_class": "critical",
      "risk_score": 0.85,
      "coverage_days": 3,
      "recommended_qty": 100
    }
  ]
}
```

---

## ML Model Features

| Feature | Description |
|---------|-------------|
| avg_daily_demand | Average daily sales |
| demand_cv | Coefficient of variation |
| turnover_ratio | Inventory turnover |
| days_in_inventory | Stock duration |
| stock_coverage_days | Days until stockout |
| gross_margin | Profit margin |
| next_7_days_avg | Forecasted demand |
| next_30_days_avg | Forecasted demand |

---

## Project 1 Modules Complete!

| Module | Status | Description |
|--------|--------|-------------|
| Module 1 | DONE | Data Puller |
| Module 2 | DONE | Data Preparation |
| Module 3 | DONE | Feature Engineering |
| Module 4 | DONE | Demand Forecasting |
| Module 5 | DONE | Stockout Prediction |
