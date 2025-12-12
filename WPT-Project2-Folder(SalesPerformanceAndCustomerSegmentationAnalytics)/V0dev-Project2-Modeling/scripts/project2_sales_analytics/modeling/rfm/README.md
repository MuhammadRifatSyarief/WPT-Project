# RFM Modeling Pipeline

## Overview

Pipeline untuk advanced RFM analysis dengan:
- **Customer Clustering** (K-Means) - 3 segments: High/Medium/Low Value
- **Churn Prediction** (Classification) - Random Forest/XGBoost/Logistic Regression
- **CLV Prediction** (Regression) - Predict Customer Lifetime Value

## Project Structure

\`\`\`
rfm/
├── config/
│   └── rfm_config.py          # Konfigurasi parameter
├── data/
│   └── data_loader.py         # Load data dari feature engineering
├── preprocessing/
│   ├── data_scaler.py         # Feature scaling
│   ├── feature_selector.py    # Feature selection
│   └── train_test_splitter.py # Train/test split
├── models/
│   ├── clustering_model.py    # K-Means clustering
│   ├── churn_classifier.py    # Churn prediction
│   └── clv_regressor.py       # CLV prediction
├── visualization/
│   └── rfm_visualizer.py      # All visualizations
├── analysis/
│   └── insight_generator.py   # Business insights
├── export/
│   └── rfm_exporter.py        # Export CSV/PKL/JSON
├── utils/
│   └── helpers.py             # Helper functions
└── run_rfm_pipeline.py        # Main entry point
\`\`\`

## Prerequisites

Input files dari Feature Engineering:
- `rfm_features.csv`
- `behavioral_features.csv`
- `temporal_features.csv`
- `customer_features.csv`
- `sales_by_customer.csv`

## Usage

### Basic Usage

\`\`\`bash
python run_rfm_pipeline.py \
    --input output/features/csv \
    --output output/rfm_modeling
\`\`\`

### Custom Parameters

\`\`\`bash
python run_rfm_pipeline.py \
    --input output/features/csv \
    --output output/rfm_modeling \
    --n-clusters 3 \
    --churn-model random_forest \
    --clv-model gradient_boosting \
    --churn-threshold 90
\`\`\`

### Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--input, -i` | output/features/csv | Input directory |
| `--output, -o` | output/rfm_modeling | Output directory |
| `--n-clusters, -k` | 3 | Number of clusters |
| `--churn-model` | random_forest | Churn model type |
| `--clv-model` | random_forest | CLV model type |
| `--churn-threshold` | 90 | Churn threshold (days) |
| `--no-viz` | False | Skip visualizations |

## Output Files

### CSV Files
- `customer_clusters.csv` - Customer cluster assignments
- `cluster_profiles.csv` - Cluster statistics
- `churn_predictions.csv` - Churn predictions
- `high_risk_customers.csv` - High churn risk customers
- `clv_predictions.csv` - CLV predictions
- `top_clv_customers.csv` - Top value customers
- `master_customer_analytics.csv` - Combined analytics

### PKL Files (for Streamlit)
- `clustering_streamlit_data.pkl`
- `churn_streamlit_data.pkl`
- `clv_streamlit_data.pkl`
- `master_customer_analytics.pkl`

### Models
- `clustering_model.pkl`
- `churn_classifier.pkl`
- `clv_regressor.pkl`

### Visualizations
- Cluster scatter plots (2D, 3D)
- Elbow curve dan silhouette analysis
- Confusion matrix dan ROC curve
- Feature importance charts
- CLV distribution dan pareto analysis
- Summary dashboard

## Integration with Project 1 (Streamlit)

Load exported data di Streamlit:

\`\`\`python
import joblib

# Load clustering data
clustering_data = joblib.load("output/rfm_modeling/pkl/clustering_streamlit_data.pkl")

# Load churn data
churn_data = joblib.load("output/rfm_modeling/pkl/churn_streamlit_data.pkl")

# Load CLV data
clv_data = joblib.load("output/rfm_modeling/pkl/clv_streamlit_data.pkl")

# Load master data
master_df = joblib.load("output/rfm_modeling/pkl/master_customer_analytics.pkl")
\`\`\`

## Model Performance Benchmarks

### Clustering
- Silhouette Score: > 0.5 (Good)
- Davies-Bouldin Index: < 1.0 (Good)

### Churn Classification
- Accuracy: > 80%
- F1 Score: > 0.75
- ROC AUC: > 0.8

### CLV Regression
- R² Score: > 0.7
- MAPE: < 30%

## Author

Data Science Team - Project 2: Sales Analytics
