# Market Basket Analysis (MBA) Module

## Overview

This module provides a complete pipeline for Market Basket Analysis using
Apriori and FP-Growth algorithms. It generates association rules for
cross-selling and product bundling recommendations.

## Structure

\`\`\`
mba/
├── __init__.py                    # Package exports
├── run_mba_pipeline.py            # Main entry point
├── requirements.txt               # Dependencies
├── README.md                      # This file
│
├── config/
│   └── mba_config.py              # Configuration class
│
├── data/
│   └── data_loader.py             # Data loading utilities
│
├── preprocessing/
│   ├── data_cleaner.py            # Data cleaning
│   └── transaction_encoder.py     # Binary encoding
│
├── algorithms/
│   ├── base_runner.py             # Base class
│   ├── apriori_runner.py          # Apriori implementation
│   └── fpgrowth_runner.py         # FP-Growth implementation
│
├── analysis/
│   ├── rules_analyzer.py          # Rule analysis
│   ├── cross_sell_recommender.py  # Recommendations
│   └── product_network.py         # Network analysis
│
├── export/
│   └── mba_exporter.py            # Export utilities
│
└── utils/
    └── helpers.py                 # Helper functions
\`\`\`

## Quick Start

### 1. Basic Usage

\`\`\`python
from mba.config.mba_config import MBAConfig
from mba.run_mba_pipeline import run_pipeline

# Configure
config = MBAConfig(
    input_path='output/features/csv/sales_details.csv',
    output_dir='output/mba',
    min_support=0.01,
    min_confidence=0.3,
    algorithm='fpgrowth'
)

# Run pipeline
results = run_pipeline(config)
\`\`\`

### 2. Command Line

\`\`\`bash
python run_mba_pipeline.py \
    --input output/features/csv/sales_details.csv \
    --output output/mba \
    --min-support 0.01 \
    --min-confidence 0.3 \
    --algorithm fpgrowth \
    --verbose
\`\`\`

### 3. Streamlit Integration

\`\`\`python
import joblib

# Load MBA results
data = joblib.load('output/mba/pkl/mba_streamlit_data.pkl')

# Access data
rules = data['data']['association_rules']
cross_sell = data['data']['cross_sell_report']
analysis = data['analysis']
\`\`\`

## Output Files

### CSV Files
- `association_rules.csv` - All association rules
- `top_rules.csv` - Top N rules by lift
- `frequent_itemsets.csv` - Frequent itemsets
- `cross_sell_recommendations.csv` - Cross-sell report
- `actionable_insights.csv` - Business insights
- `product_analysis.csv` - Product frequency analysis

### Pickle Files
- `association_rules.pkl` - Rules with frozensets preserved
- `frequent_itemsets.pkl` - Itemsets with frozensets
- `mba_streamlit_data.pkl` - Combined package for Streamlit

### JSON Files
- `analysis_results.json` - Analysis summary
- `product_network.json` - Network visualization data
- `mba_metadata.json` - Pipeline metadata

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| min_support | 0.01 | Minimum itemset frequency (1%) |
| min_confidence | 0.3 | Minimum rule confidence (30%) |
| min_lift | 1.0 | Minimum lift (positive association) |
| max_length | 4 | Maximum itemset size |
| algorithm | fpgrowth | Algorithm (apriori/fpgrowth) |

## Integration with Project 1

The output from this module integrates with Project 1 (Inventory Optimization)
Streamlit dashboard:

1. **MBA.py page**: Display association rules and cross-sell recommendations
2. **slow_moving.py**: Bundle slow-moving products with fast-moving ones
3. **alerts.py**: Product affinity alerts for inventory decisions

## Dependencies

- pandas >= 1.5.0
- numpy >= 1.21.0
- mlxtend >= 0.21.0
- scikit-learn >= 1.0.0
- joblib >= 1.2.0

Install with:
\`\`\`bash
pip install -r requirements.txt
