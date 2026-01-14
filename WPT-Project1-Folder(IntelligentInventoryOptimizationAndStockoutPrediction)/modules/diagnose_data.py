import pandas as pd

print('=== CHECKING MODULE OUTPUTS ===')

# 1. Check forecasts
print('\n1. FORECAST DATA:')
fc = pd.read_csv('../data/forecasts/forecast_summary.csv')
print('Max forecast 30d:', fc['next_30_days_avg'].max())
print('Mean forecast 30d:', round(fc['next_30_days_avg'].mean(), 2))

# 2. Check reorder optimization
print('\n2. REORDER DATA:')
ro = pd.read_csv('../data/reorder/reorder_optimization.csv')
print('Columns:', ro.columns.tolist())
if 'safety_stock_optimized' in ro.columns:
    print('Safety stock - Min:', ro['safety_stock_optimized'].min())
    print('Safety stock - Max:', ro['safety_stock_optimized'].max())
    print('Safety stock - Zero count:', (ro['safety_stock_optimized'] == 0).sum())

# 3. Check features ABC class
print('\n3. ABC CLASS:')
mf = pd.read_csv('../data/features/master_features.csv')
if 'abc_class' in mf.columns:
    print(mf['abc_class'].value_counts())

# 4. Check demand values
print('\n4. DEMAND VALUES:')
demand_cols = [c for c in mf.columns if 'demand' in c.lower()]
print('Demand columns:', demand_cols)
for col in demand_cols:
    vals = pd.to_numeric(mf[col], errors='coerce')
    print(f'  {col}: max={vals.max()}, mean={round(vals.mean(), 2)}')

# 5. Check turnover
print('\n5. TURNOVER VALUES:')
if 'turnover_ratio' in mf.columns:
    print('turnover_ratio: min=', mf['turnover_ratio'].min(), 'max=', mf['turnover_ratio'].max())

# 6. Check problematic groups
print('\n6. PROBLEMATIC GROUPS:')
h_groups = mf[mf['no'].str.startswith('H', na=False)]['no'].str.split('-').str[0].value_counts()
print('Groups starting with H:')
print(h_groups)
print()
print('Numeric-only no values:')
numeric = mf[mf['no'].str.match(r'^\d+', na=False)]['no'].head(20).tolist()
print(numeric)
