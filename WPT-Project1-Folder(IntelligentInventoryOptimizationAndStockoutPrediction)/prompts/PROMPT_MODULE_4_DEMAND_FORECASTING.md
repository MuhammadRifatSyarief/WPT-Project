# PROMPT MODULE 4: Demand Forecasting
## Project 1 - Intelligent Inventory Optimization

---

## Overview

| Attribute | Value |
|-----------|-------|
| File | `modules/demand_forecasting.py` |
| Lines | ~550 |
| Input | `data/prepared/`, `data/features/` |
| Output | `data/forecasts/` |

---

## Models

| Model | Use Case | Speed |
|-------|----------|-------|
| **Prophet** | Top 50 items (A class) | Slow (~2s/item) |
| **Exponential Smoothing** | Remaining items | Fast |
| **Moving Average** | Fallback | Very Fast |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│               DEMAND FORECASTING                         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  TimeSeriesDataPreparator ────────────────────────────→│
│  ├─ Load sales_details + stock_mutations                │
│  ├─ Aggregate to daily time series per item             │
│  └─ Fill missing dates with 0                           │
│                    ↓                                    │
│  Item Prioritization ─────────────────────────────────→│
│  └─ ABC class (A first) + demand volume                 │
│                    ↓                                    │
│  ProphetForecaster (top N items) ─────────────────────→│
│  ├─ Train/test split (80/20)                            │
│  ├─ Weekly seasonality                                  │
│  └─ MAPE/RMSE metrics                                   │
│                    ↓                                    │
│  StatisticalForecaster (remaining) ───────────────────→│
│  ├─ Exponential smoothing (alpha=0.3)                   │
│  └─ Trend factor decay                                  │
│                    ↓                                    │
│  Business Constraints ────────────────────────────────→│
│  ├─ min_forecast = 0                                    │
│  └─ max_forecast = 5x historical max                    │
└─────────────────────────────────────────────────────────┘
```

---

## Configuration

```python
@dataclass
class ForecastConfig:
    forecast_horizon: int = 30      # Days to forecast
    min_history_days: int = 30      # Minimum data required
    train_test_split: float = 0.8   # 80% train
    
    # Prophet settings
    prophet_weekly_seasonality: bool = True
    prophet_items_limit: int = 50   # Use Prophet for top 50 only
    
    # Statistical settings
    moving_avg_window: int = 7
    exp_smoothing_alpha: float = 0.3
    
    # Business constraints
    min_forecast: float = 0.0
    max_forecast_multiplier: float = 5.0
```

---

## Usage

```bash
cd modules
python demand_forecasting.py
```

### Install Prophet (optional)
```bash
pip install prophet
```

---

## Output

```
data/forecasts/
├── forecast_summary.csv      # Summary per item
├── daily_forecasts.csv       # Detailed daily forecasts
└── detailed_forecasts.json   # Full JSON with all data
```

### forecast_summary.csv Schema

| Column | Type | Description |
|--------|------|-------------|
| item_id | int | Item ID |
| model | str | prophet/exponential_smoothing/moving_average |
| next_7_days_avg | float | Average forecast next 7 days |
| next_30_days_avg | float | Average forecast next 30 days |
| mape | float | Mean Absolute % Error (Prophet only) |
| rmse | float | Root Mean Square Error |

### daily_forecasts.csv Schema

| Column | Type | Description |
|--------|------|-------------|
| item_id | int | Item ID |
| date | str | Forecast date |
| forecast | float | Predicted demand |
| lower | float | Lower bound (70%) |
| upper | float | Upper bound (130%) |
| model | str | Model used |

---

## Key Features

1. **ABC Prioritization** - Forecast A-class items first
2. **Hybrid Approach** - Prophet for top items, statistical for rest
3. **Business Constraints** - No negative/unrealistic forecasts
4. **Confidence Intervals** - Lower/upper bounds included
5. **Performance Metrics** - MAPE/RMSE for Prophet models

---

## Next Steps: Module 5 (Stockout Prediction)

Output dari Module 4 siap untuk:
1. Stockout probability calculation
2. Reorder timing recommendations
3. Dashboard integration
