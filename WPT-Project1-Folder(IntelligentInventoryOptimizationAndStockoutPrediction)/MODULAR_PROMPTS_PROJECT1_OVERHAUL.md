# MODULAR PROMPTS: Project 1 Complete Overhaul
## Intelligent Inventory Optimization & Stockout Prediction
## Version 2.0 - With Data Preparation & Cross-Endpoint Enrichment

================================================================================
## RINGKASAN EKSEKUTIF
================================================================================

### Tujuan
Merobak keseluruhan flow Project 1 dari pulling data hingga modeling dengan:
1. Menggunakan CUDA GPU untuk data processing
2. Mengganti metode statistik dengan ML models yang sensitif
3. Memperbaiki nilai output yang tidak realistis
4. Mempertahankan logic yang masih valid

### Dashboard Pages yang Akan Diperbaiki
1. Dashboard Overview
2. Demand Forecasting
3. Inventory Health
4. Stockout Alerts
5. Reorder Optimization
6. Slow-Moving Analysis

================================================================================
## BAGIAN A: LESSONS LEARNED (Kegagalan yang Harus Dihindari)
================================================================================

### A1. Masalah API Data (dari debug_field_mapping.py)

**Bukti Masalah:**
```
- Selling Price: 70% return false/null dari /api/item/get-selling-price.do
- Contact Fields: 80%+ null untuk email, mobilePhone
- customerId: Tidak tersedia di list endpoint, harus double API call
- Field naming inconsistent: detailItem vs items vs detail
```

**Solusi yang HARUS Diterapkan:**
1. Multiple fallback strategy untuk price data
2. Data enrichment dari berbagai sumber
3. Caching untuk mengurangi API calls
4. Validasi data sebelum processing

---

### A2. Masalah Kalkulasi yang Tidak Realistis

**Contoh Output Bermasalah (Saat Ini):**
```python
# Turnover Ratio terlalu tinggi
annualized_turnover = weighted_avg_turnover_90d * (365 / 90)  # Bisa > 100x

# Days until stockout bisa infinity
days_until_stockout = current_stock / (avg_daily_demand + 0.01)  # 0.01 terlalu kecil

# EOQ dengan nilai ekstrem
EOQ = sqrt(2 * D * S / H)  # Jika H ~ 0, EOQ = infinity
```

**Perbaikan yang Dibutuhkan:**
```python
# 1. Cap turnover dengan nilai realistis
annualized_turnover = min(weighted_avg_turnover_90d * (365 / 90), 52)  # Max 52x/tahun

# 2. Minimum demand untuk mencegah division issues
min_demand = max(avg_daily_demand, 0.1)  # Minimal 0.1 unit/hari

# 3. EOQ dengan safety bounds
H = max(holding_cost, unit_cost * 0.20)  # Minimal 20% dari unit cost
EOQ = min(max(calculated_eoq, 1), max_order_qty)
```

---

### A3. Logic yang HARUS Dipertahankan

**1. Rate Limiting (dari data_puller_project1.py):**
```python
def rate_limit(self):
    current_time = time.time()
    elapsed = current_time - self.last_request_time
    if elapsed < self.min_request_interval:
        time.sleep(self.min_request_interval - elapsed)
    self.last_request_time = time.time()
```

**2. HMAC Authentication:**
```python
def get_headers(self):
    ts = datetime.now(wib).strftime('%d/%m/%Y %H:%M:%S')
    signature = base64.b64encode(
        hmac.new(self.signature_secret.encode(), ts.encode(), hashlib.sha256).digest()
    ).decode()
    return {
        'Authorization': f'Bearer {self.api_token}',
        'X-Api-Timestamp': ts,
        'X-Api-Signature': signature
    }
```

**3. Pagination Handler:**
```python
def fetch_all_pages(self, endpoint, params=None, max_pages=50):
    # Keep this logic - it works well
```

================================================================================
## BAGIAN B: MODULAR PROMPTS UNTUK REBUILD
================================================================================

### PROMPT MODULE 1: Data Puller dengan GPU Support

```
CONTEXT:
Anda akan membuat data puller baru untuk Project 1 yang menggunakan CUDA GPU 
untuk processing. Data akan diambil dari API Accurate dengan authentication 
HMAC-SHA256.

REQUIREMENTS:
1. Gunakan cuDF (rapids) untuk DataFrame operations jika GPU tersedia
2. Fallback ke pandas jika GPU tidak tersedia
3. Implementasi rate limiting: max 3 requests/second
4. Retry mechanism dengan exponential backoff
5. Checkpoint system untuk resume dari kegagalan

API ENDPOINTS YANG DIGUNAKAN:
- /api/item/list.do (Master Items)
- /api/item/list-stock.do (Current Stock)
- /api/item/stock-mutation-history.do (Stock Mutations)
- /api/sales-invoice/list.do + detail.do (Sales)
- /api/purchase-order/list.do + detail.do (Purchases)
- /api/item/get-selling-price.do (Prices - 70% return null, need fallback)

KNOWN ISSUES TO HANDLE:
- get-selling-price.do returns {"s": false, "d": null} for 70% items
- customerId not in sales-invoice/list.do, must use detail endpoint
- Field names inconsistent between endpoints

OUTPUT FORMAT:
- Python module dengan class DataPullerGPU
- Methods untuk setiap data category
- Logging untuk monitoring progress
- Error handling yang comprehensive
```

---

### PROMPT MODULE 2: Feature Engineering dengan Realistic Constraints

```
CONTEXT:
Feature engineering untuk inventory optimization harus menghasilkan nilai 
yang REALISTIS untuk bisnis. Nilai ekstrem (terlalu besar/kecil) harus 
dibatasi dengan business constraints.

FEATURES YANG DIBUTUHKAN:

1. DEMAND METRICS (Realistic bounds):
   - avg_daily_demand: min=0.01, max=1000 units/day
   - demand_variability: CV between 0.1 - 3.0
   - demand_trend: -50% to +100% growth rate

2. INVENTORY METRICS (Realistic bounds):
   - turnover_ratio: 0.5x - 52x per year
   - days_in_inventory: 7 - 365 days
   - stock_coverage: 0 - 180 days

3. FINANCIAL METRICS:
   - unit_cost: Must be > 0 (use selling_price * 0.6 as fallback)
   - holding_cost: 15-30% of unit_cost per year
   - ordering_cost: Rp 50,000 - Rp 500,000 per order

4. STOCKOUT METRICS:
   - days_until_stockout: 0 - 365 (cap at 365)
   - stockout_probability: 0% - 100%
   - service_level: 50% - 99.9%

VALIDATION RULES:
- All metrics must pass sanity check before use
- Outliers > 3 std dev should be capped, not removed
- Missing values should use category median, not global
```

---

### PROMPT MODULE 3: ML Models untuk Demand Forecasting

```
CONTEXT:
Ganti metode statistik dengan ML models yang lebih sensitif terhadap patterns.

MODELS YANG DIIMPLEMENTASI:

1. TIME SERIES FORECASTING:
   - Prophet (untuk seasonal patterns)
   - LSTM (untuk complex patterns)
   - Ensemble average of both

2. STOCKOUT PREDICTION (Classification):
   - Random Forest Classifier
   - XGBoost Classifier
   - Threshold: P(stockout) > 0.3 = Warning, > 0.6 = Critical

3. DEMAND CLUSTERING:
   - K-Means untuk segmentasi demand patterns
   - Features: avg_demand, variability, trend, seasonality

TRAINING REQUIREMENTS:
- Minimum 30 days history per item
- Use last 7 days for validation
- Cross-validation untuk hyperparameter tuning
- Model persistence dengan joblib

HANDLING SPARSE DATA:
- Items dengan < 30 days history: Gunakan statistical fallback
- Items dengan zero sales: Flag sebagai "new/dormant"
- Seasonal items: Detect dan adjust forecast
```

---

### PROMPT MODULE 4: Reorder Optimization dengan EOQ Enhancement

```
CONTEXT:
EOQ calculation saat ini menghasilkan nilai tidak realistis. Perlu 
enhancement dengan business constraints.

CURRENT ISSUE:
```python
# EOQ standard - dapat menghasilkan nilai infinity
EOQ = sqrt(2 * D * S / H)
```

ENHANCED EOQ:
```python
def calculate_realistic_eoq(
    annual_demand: float,
    ordering_cost: float,
    holding_cost_rate: float,
    unit_cost: float,
    min_order: int = 1,
    max_order: int = 10000,
    lead_time_days: int = 14
) -> dict:
    
    # Validate inputs
    annual_demand = max(annual_demand, 1)  # Min 1 unit/year
    ordering_cost = max(ordering_cost, 50000)  # Min Rp 50k
    holding_cost_rate = max(holding_cost_rate, 0.15)  # Min 15%
    unit_cost = max(unit_cost, 1000)  # Min Rp 1k
    
    # Calculate holding cost per unit
    H = unit_cost * holding_cost_rate
    
    # Calculate EOQ
    eoq_raw = sqrt(2 * annual_demand * ordering_cost / H)
    
    # Apply bounds
    eoq = int(min(max(eoq_raw, min_order), max_order))
    
    # Calculate reorder point
    daily_demand = annual_demand / 365
    safety_stock = daily_demand * lead_time_days * 0.5  # 50% buffer
    reorder_point = (daily_demand * lead_time_days) + safety_stock
    
    return {
        'eoq': eoq,
        'reorder_point': int(reorder_point),
        'safety_stock': int(safety_stock),
        'annual_orders': int(annual_demand / eoq),
        'total_annual_cost': (annual_demand / eoq) * ordering_cost + (eoq / 2) * H
    }
```

ADDITIONAL OPTIMIZATIONS:
1. Multi-item joint replenishment 
2. Quantity discount consideration
3. Supplier lead time variability
4. Demand uncertainty buffer
```

---

### PROMPT MODULE 5: Stockout Alert System dengan ML

```
CONTEXT:
Stockout alerts saat ini hanya berdasarkan threshold statis. Perlu 
enhancement dengan ML prediction.

CURRENT LOGIC (Statis):
```python
if days_until_stockout < 7:
    alert = "Critical"
elif days_until_stockout < 14:
    alert = "High"
```

ENHANCED LOGIC (ML-based):
```python
def predict_stockout_risk(
    item_features: dict,
    model: XGBClassifier,
    thresholds: dict = {'critical': 0.7, 'high': 0.4, 'medium': 0.2}
) -> dict:
    
    features = [
        item_features['current_stock'],
        item_features['avg_daily_demand'],
        item_features['demand_variability'],
        item_features['lead_time'],
        item_features['days_since_last_order'],
        item_features['supplier_reliability'],
        item_features['is_seasonal'],
        item_features['demand_trend']
    ]
    
    # Predict probability
    prob = model.predict_proba([features])[0][1]
    
    # Dynamic threshold based on item importance
    if item_features['abc_class'] == 'A':
        thresholds = {'critical': 0.5, 'high': 0.3, 'medium': 0.15}
    
    # Determine alert level
    if prob >= thresholds['critical']:
        level = 'Critical'
    elif prob >= thresholds['high']:
        level = 'High'
    elif prob >= thresholds['medium']:
        level = 'Medium'
    else:
        level = 'Low'
    
    return {
        'probability': prob,
        'alert_level': level,
        'recommended_action': get_action(level),
        'days_to_stockout_predicted': estimate_days(item_features, model)
    }
```

TRAINING DATA:
- Historical stockout events (if available)
- Synthetic stockout scenarios from demand patterns
- Feature importance analysis untuk interpretability
```

---

### PROMPT MODULE 6: Slow-Moving Analysis dengan Segmentation

```
CONTEXT:
Slow-moving analysis perlu lebih dari sekadar turnover ratio. Perlu 
segmentasi dan root cause analysis.

ENHANCED ANALYSIS:

1. SLOW-MOVING SEGMENTATION:
   - Seasonal Slow: High sales in certain periods
   - New Products: < 90 days in inventory
   - Declining: Negative trend over 6 months
   - Dead Stock: Zero movement > 180 days
   - Overstocked: Stock > 1 year supply

2. ROOT CAUSE ANALYSIS:
   - Price sensitivity check
   - Seasonality detection
   - Product substitution effect
   - Market trend alignment

3. RECOMMENDATION ENGINE:
   - Dynamic pricing suggestions
   - Bundle opportunities
   - Liquidation thresholds
   - Phase-out timeline

METRICS:
- Days Since Last Sale (DSLS)
- Stock-to-Sales ratio
- Aging bucket distribution
- Obsolescence risk score
```

================================================================================
## BAGIAN C: ARSITEKTUR BARU
================================================================================

### Directory Structure:
```
Project1/
├── data_pipeline/
│   ├── puller_gpu.py          # GPU-enabled data puller
│   ├── puller_cpu.py          # CPU fallback
│   ├── validator.py           # Data validation
│   └── cache_manager.py       # API response caching
├── feature_engineering/
│   ├── demand_features.py     # Demand metrics
│   ├── inventory_features.py  # Inventory metrics
│   ├── financial_features.py  # Cost metrics
│   └── constraints.py         # Business constraints
├── models/
│   ├── demand_forecast/
│   │   ├── prophet_model.py
│   │   ├── lstm_model.py
│   │   └── ensemble.py
│   ├── stockout_prediction/
│   │   ├── rf_classifier.py
│   │   ├── xgb_classifier.py
│   │   └── threshold_optimizer.py
│   └── clustering/
│       └── demand_segments.py
├── optimization/
│   ├── eoq_calculator.py
│   ├── reorder_optimizer.py
│   └── safety_stock.py
├── dashboard/
│   ├── pages/
│   │   ├── overview.py
│   │   ├── forecasting.py
│   │   ├── health.py
│   │   ├── alerts.py
│   │   ├── reorder.py
│   │   └── slow_moving.py
│   └── components/
│       ├── metrics.py
│       ├── charts.py
│       └── tables.py
└── app.py                     # Main Streamlit app
```

### Data Flow:
```
API Accurate
    ↓
Data Puller (GPU/CPU)
    ↓
Data Validator → Cache
    ↓
Feature Engineering (with constraints)
    ↓
ML Models (Prophet/LSTM/XGB)
    ↓
Business Logic (EOQ/Reorder/Alerts)
    ↓
Dashboard Display
```

================================================================================
## BAGIAN D: IMPLEMENTATION SEQUENCE
================================================================================

### Week 1: Data Pipeline
1. Refactor data puller dengan GPU support
2. Implement data validation layer
3. Create caching mechanism
4. Test dengan real API

### Week 2: Feature Engineering
1. Implement realistic constraints
2. Fix calculation formulas
3. Add outlier handling
4. Validate output ranges

### Week 3: ML Models
1. Implement Prophet forecasting
2. Add LSTM model
3. Create stockout classification
4. Train dan tune models

### Week 4: Dashboard Integration
1. Update all 6 pages
2. Replace static calculations with ML predictions
3. Add model performance monitoring
4. Final testing dan validation

================================================================================
## BAGIAN E: VALIDATION CHECKLIST
================================================================================

### Business Realism Check:
- [ ] Turnover ratio between 0.5x - 52x/year
- [ ] Days in inventory between 7 - 365 days
- [ ] EOQ between 1 - 10,000 units
- [ ] Stockout days prediction between 0 - 365
- [ ] Service level between 50% - 99.9%
- [ ] Holding cost between 15% - 30% of unit cost

### Data Quality Check:
- [ ] No infinite values
- [ ] No negative values where inappropriate
- [ ] All required fields populated
- [ ] Outliers capped, not removed

### Model Performance Check:
- [ ] Forecast MAPE < 30%
- [ ] Classification F1 > 0.7
- [ ] No catastrophic predictions
- [ ] Graceful degradation for sparse data

================================================================================
