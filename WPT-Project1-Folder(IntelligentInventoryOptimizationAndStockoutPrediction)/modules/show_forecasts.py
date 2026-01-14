import pandas as pd

forecast = pd.read_csv('../data/forecasts/forecast_summary.csv')
features = pd.read_csv('../data/features/master_features.csv')

merged = forecast.merge(features[['id', 'no', 'name']], left_on='item_id', right_on='id', how='left')
result = merged[['item_id', 'no', 'name', 'model', 'next_30_days_avg']].sort_values('next_30_days_avg', ascending=False)

result.to_csv('../data/forecasts/forecast_with_names.csv', index=False)
print('Saved to forecast_with_names.csv')
print()
print('=== ALL 53 PRODUCTS WITH FORECAST ===')
print()
for i, row in result.iterrows():
    name = str(row['name'])[:50] if pd.notna(row['name']) else 'N/A'
    no = str(row['no']) if pd.notna(row['no']) else 'N/A'
    print(f"{row['next_30_days_avg']:6.2f}/day | {no:15} | {name}")
