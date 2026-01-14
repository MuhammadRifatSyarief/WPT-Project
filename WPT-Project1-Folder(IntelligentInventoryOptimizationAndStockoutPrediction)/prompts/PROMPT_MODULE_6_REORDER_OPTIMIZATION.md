# PROMPT MODULE 6: Reorder Optimization
## Project 1 - Intelligent Inventory Optimization

---

## Overview

| Attribute | Value |
|-----------|-------|
| File | `modules/reorder_optimization.py` |
| Lines | ~550 |
| Input | `data/features/`, `data/predictions/` |
| Output | `data/reorder/` |

---

## Components

| Component | Function |
|-----------|----------|
| **EnhancedEOQCalculator** | EOQ with cost breakdown |
| **SafetyStockCalculator** | Dynamic safety stock |
| **OrderScheduler** | Order schedule generation |
| **CostAnalyzer** | Savings analysis |

---

## Key Formulas

### EOQ (Economic Order Quantity)
```
EOQ = sqrt(2 × D × S / H)

where:
  D = Annual demand (units)
  S = Ordering cost (Rp 150,000)
  H = Holding cost (20% × unit cost)
```

### Safety Stock
```
SS = Z × σ_d × √L

where:
  Z = 1.65 (95% service level)
  σ_d = Demand standard deviation
  L = Lead time (7 days default)
```

### Reorder Point
```
ROP = (Lead Time × Avg Daily Demand) + Safety Stock
```

---

## Configuration

```python
@dataclass
class ReorderConfig:
    default_ordering_cost: float = 150000.0   # Rp 150k
    default_holding_rate: float = 0.20        # 20% per year
    default_lead_time: int = 7                # 7 days
    target_service_level: float = 0.95        # 95%
    
    min_order_qty: int = 1
    max_order_qty: int = 10000
    min_safety_stock: int = 0
    max_safety_stock: int = 1000
```

---

## Usage

```bash
cd modules
python reorder_optimization.py
```

---

## Output

```
data/reorder/
├── reorder_optimization.csv    # Optimized parameters per item
├── order_schedule.csv          # 90-day order schedule
└── optimization_analysis.json  # Cost analysis & savings
```

### reorder_optimization.csv Schema

| Column | Type | Description |
|--------|------|-------------|
| id | int | Item ID |
| eoq_optimized | int | Optimal order quantity |
| safety_stock_optimized | int | Safety stock level |
| reorder_point_optimized | int | When to reorder |
| annual_inventory_cost | float | Total inventory cost |
| achieved_service_level | float | Actual service level |

### order_schedule.csv Schema

| Column | Type | Description |
|--------|------|-------------|
| item_id | int | Item ID |
| order_date | str | When to place order |
| order_qty | int | Quantity to order |
| expected_delivery | str | Delivery date |

---

## Cost Analysis Output

```json
{
  "savings_analysis": {
    "current_annual_cost": 500000000,
    "optimized_annual_cost": 350000000,
    "potential_savings": 150000000,
    "savings_percentage": 30.0
  }
}
```

---

## Architecture Flow

```
┌─────────────────────────────────────────────────────────┐
│               REORDER OPTIMIZATION                       │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Load Features + Predictions                             │
│            ↓                                            │
│  EnhancedEOQCalculator                                  │
│  ├─ EOQ per item                                        │
│  ├─ Annual ordering cost                                │
│  └─ Annual holding cost                                 │
│            ↓                                            │
│  SafetyStockCalculator                                  │
│  ├─ Safety stock (95% SL)                               │
│  └─ Service level achieved                              │
│            ↓                                            │
│  OrderScheduler                                         │
│  ├─ Simulate 90-day inventory                           │
│  └─ Generate order dates                                │
│            ↓                                            │
│  CostAnalyzer                                           │
│  ├─ Current holding costs                               │
│  └─ Potential savings                                   │
└─────────────────────────────────────────────────────────┘
```

---

## Next: Module 7 (Dashboard/Reporting)

Output dari Module 6 siap untuk:
1. Executive dashboard
2. Automated reorder alerts
3. Vendor communication
