"""
Module 4: Demand Forecasting
=============================

Project 1 - Intelligent Inventory Optimization & Stockout Prediction

Models:
1. Prophet - Facebook's time series forecasting (primary)
2. Moving Average - Simple statistical fallback
3. Exponential Smoothing - Alternative statistical method

Author: AI Assistant
Date: January 2026
Version: 1.0.0
"""

import os
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any, Tuple
from dataclasses import dataclass
import warnings
import json

warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np

# Prophet (optional - will fallback if not available)
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False

# Configure logging - avoid emoji for Windows compatibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class ForecastConfig:
    """Configuration for demand forecasting"""
    # Input/Output
    input_dir: str = "../data/prepared"
    features_dir: str = "../data/features"
    output_dir: str = "../data/forecasts"
    
    # Forecasting parameters
    forecast_horizon: int = 30          # Days to forecast
    min_history_days: int = 30          # Minimum days of history required
    train_test_split: float = 0.8       # 80% train, 20% test
    
    # Prophet settings
    prophet_yearly_seasonality: bool = False
    prophet_weekly_seasonality: bool = True
    prophet_daily_seasonality: bool = False
    prophet_changepoint_prior: float = 0.05
    
    # Fallback settings
    moving_avg_window: int = 7          # 7-day moving average
    exp_smoothing_alpha: float = 0.3    # Exponential smoothing factor
    
    # STRICT Business constraints - prevent unrealistic forecasts
    min_forecast: float = 0.0           # No negative forecasts
    max_forecast_multiplier: float = 2.0  # Max 2x historical max
    use_median_bound: bool = True       # Use median instead of mean for safer bounds
    median_multiplier: float = 3.0      # Max 3x median (realistic)
    max_absolute_daily: float = 100.0   # Absolute max daily demand (realistic for IT equipment)
    
    # Validation thresholds
    suspicious_threshold: float = 50.0  # Flag if forecast > 50 units/day
    
    # Model selection
    use_prophet: bool = True
    prophet_items_limit: int = 100      # Limit Prophet to top N items (slow)


# =============================================================================
# DATA PREPARATION
# =============================================================================

class TimeSeriesDataPreparator:
    """Prepare time series data for forecasting"""
    
    def __init__(self, config: ForecastConfig):
        self.config = config
    
    def load_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load sales and mutation data"""
        sales_path = Path(self.config.input_dir) / "sales_details.csv"
        mutations_path = Path(self.config.input_dir) / "stock_mutations.csv"
        
        sales_df = pd.DataFrame()
        mutations_df = pd.DataFrame()
        
        if sales_path.exists():
            sales_df = pd.read_csv(sales_path, encoding='utf-8-sig')
            logger.info(f"  Loaded sales_details: {len(sales_df):,} records")
        
        if mutations_path.exists():
            mutations_df = pd.read_csv(mutations_path, encoding='utf-8-sig')
            logger.info(f"  Loaded stock_mutations: {len(mutations_df):,} records")
        
        return sales_df, mutations_df
    
    def prepare_daily_series(
        self,
        sales_df: pd.DataFrame,
        mutations_df: pd.DataFrame
    ) -> Dict[int, pd.DataFrame]:
        """
        Prepare daily time series per item
        
        Returns:
            Dict mapping item_id to DataFrame with columns [ds, y]
        """
        logger.info("  Preparing daily time series per item...")
        
        item_series = {}
        
        # Source 1: From sales_details
        if not sales_df.empty and 'item_id' in sales_df.columns:
            # Parse dates
            if 'trans_date' in sales_df.columns:
                sales_df['trans_date'] = pd.to_datetime(sales_df['trans_date'], errors='coerce')
                sales_df = sales_df.dropna(subset=['trans_date'])
            
            # Aggregate by item and date
            for item_id, group in sales_df.groupby('item_id'):
                daily = group.groupby(group['trans_date'].dt.date).agg({
                    'qty': 'sum'
                }).reset_index()
                daily.columns = ['ds', 'y']
                daily['ds'] = pd.to_datetime(daily['ds'])
                
                if len(daily) >= self.config.min_history_days:
                    item_series[item_id] = daily.sort_values('ds')
        
        # Source 2: From mutations (for items not in sales)
        if not mutations_df.empty and 'product_id' in mutations_df.columns:
            # Filter sales transactions (SI = Sales Invoice)
            if 'transactionType' in mutations_df.columns:
                sales_mutations = mutations_df[mutations_df['transactionType'] == 'SI'].copy()
            else:
                sales_mutations = mutations_df[mutations_df['mutation'] < 0].copy()
            
            if not sales_mutations.empty and 'transactionDate' in sales_mutations.columns:
                sales_mutations['transactionDate'] = pd.to_datetime(
                    sales_mutations['transactionDate'], errors='coerce'
                )
                
                for product_id, group in sales_mutations.groupby('product_id'):
                    if product_id in item_series:
                        continue  # Already have from sales_details
                    
                    daily = group.groupby(group['transactionDate'].dt.date).agg({
                        'mutation': lambda x: abs(x).sum()
                    }).reset_index()
                    daily.columns = ['ds', 'y']
                    daily['ds'] = pd.to_datetime(daily['ds'])
                    
                    if len(daily) >= self.config.min_history_days:
                        item_series[product_id] = daily.sort_values('ds')
        
        logger.info(f"  Prepared time series for {len(item_series)} items")
        return item_series
    
    def fill_missing_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fill missing dates with zero demand"""
        if df.empty:
            return df
        
        date_range = pd.date_range(start=df['ds'].min(), end=df['ds'].max(), freq='D')
        full_df = pd.DataFrame({'ds': date_range})
        merged = full_df.merge(df, on='ds', how='left')
        merged['y'] = merged['y'].fillna(0)
        
        return merged


# =============================================================================
# PROPHET FORECASTER
# =============================================================================

class ProphetForecaster:
    """Prophet-based demand forecasting"""
    
    def __init__(self, config: ForecastConfig):
        self.config = config
        self.models: Dict[int, Prophet] = {}
    
    def forecast_item(
        self,
        item_id: int,
        series_df: pd.DataFrame,
        historical_max: float
    ) -> Dict[str, Any]:
        """
        Forecast demand for single item using Prophet
        
        Returns:
            Dict with forecast, metrics, and model info
        """
        if not PROPHET_AVAILABLE:
            return self._fallback_forecast(item_id, series_df, historical_max)
        
        try:
            # Prepare data for Prophet
            df = series_df[['ds', 'y']].copy()
            
            # Train/test split
            split_idx = int(len(df) * self.config.train_test_split)
            train_df = df.iloc[:split_idx]
            test_df = df.iloc[split_idx:]
            
            # Initialize and fit Prophet
            model = Prophet(
                yearly_seasonality=self.config.prophet_yearly_seasonality,
                weekly_seasonality=self.config.prophet_weekly_seasonality,
                daily_seasonality=self.config.prophet_daily_seasonality,
                changepoint_prior_scale=self.config.prophet_changepoint_prior
            )
            model.fit(train_df)
            
            # Generate future dates
            future = model.make_future_dataframe(periods=self.config.forecast_horizon)
            forecast = model.predict(future)
            
            # Apply STRICT business constraints
            # 1. Cap at historical max * multiplier
            max_value = historical_max * self.config.max_forecast_multiplier
            # 2. Also cap at absolute maximum (realistic business limit)
            max_value = min(max_value, self.config.max_absolute_daily)
            # 3. Use median of historical data as reference
            historical_median = series_df['y'].median()
            
            forecast['yhat'] = forecast['yhat'].clip(lower=self.config.min_forecast, upper=max_value)
            forecast['yhat_lower'] = forecast['yhat_lower'].clip(lower=self.config.min_forecast)
            forecast['yhat_upper'] = forecast['yhat_upper'].clip(upper=max_value)
            
            # 4. If forecast is suspiciously high, use median-based fallback
            if self.config.use_median_bound and historical_median > 0:
                median_cap = historical_median * self.config.median_multiplier
                forecast['yhat'] = forecast['yhat'].clip(upper=max(0.1, median_cap))
            
            # Calculate metrics on test set
            if len(test_df) > 0:
                test_forecast = forecast[forecast['ds'].isin(test_df['ds'])]
                if len(test_forecast) > 0:
                    merged = test_df.merge(test_forecast[['ds', 'yhat']], on='ds')
                    mape = np.mean(np.abs((merged['y'] - merged['yhat']) / (merged['y'] + 1))) * 100
                    rmse = np.sqrt(np.mean((merged['y'] - merged['yhat'])**2))
                else:
                    mape, rmse = None, None
            else:
                mape, rmse = None, None
            
            # Get next N days forecast
            future_forecast = forecast.tail(self.config.forecast_horizon)[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]
            
            return {
                'item_id': item_id,
                'model': 'prophet',
                'forecast': future_forecast.to_dict('records'),
                'mape': round(mape, 2) if mape else None,
                'rmse': round(rmse, 2) if rmse else None,
                'next_7_days_avg': round(future_forecast.head(7)['yhat'].mean(), 2),
                'next_30_days_avg': round(future_forecast['yhat'].mean(), 2),
                'success': True
            }
            
        except Exception as e:
            logger.warning(f"    Prophet failed for item {item_id}: {str(e)[:50]}")
            return self._fallback_forecast(item_id, series_df, historical_max)
    
    def _fallback_forecast(
        self,
        item_id: int,
        series_df: pd.DataFrame,
        historical_max: float
    ) -> Dict[str, Any]:
        """Fallback to simple moving average"""
        # Use last N days average
        window = min(self.config.moving_avg_window, len(series_df))
        recent_avg = series_df.tail(window)['y'].mean()
        
        # Generate forecast dates
        last_date = series_df['ds'].max()
        future_dates = pd.date_range(
            start=last_date + timedelta(days=1),
            periods=self.config.forecast_horizon,
            freq='D'
        )
        
        # Apply STRICT bounds
        # 1. Historical max constraint
        max_from_history = historical_max * self.config.max_forecast_multiplier
        # 2. Absolute maximum
        max_absolute = self.config.max_absolute_daily
        # 3. Use median as safer reference
        historical_median = series_df['y'].median()
        median_cap = historical_median * self.config.median_multiplier  # Use config
        
        # Take the minimum of all caps (but at least 0.1 to avoid zero forecasts)
        if self.config.use_median_bound and historical_median > 0:
            effective_max = max(0.1, min(max_from_history, max_absolute, median_cap))
        else:
            effective_max = max(0.1, min(max_from_history, max_absolute))
        
        forecast_value = min(recent_avg, effective_max)
        forecast_value = max(forecast_value, self.config.min_forecast)
        
        forecast = [{
            'ds': str(d.date()),
            'yhat': round(forecast_value, 2),
            'yhat_lower': round(forecast_value * 0.7, 2),
            'yhat_upper': round(min(forecast_value * 1.3, effective_max), 2)
        } for d in future_dates]
        
        return {
            'item_id': item_id,
            'model': 'moving_average',
            'forecast': forecast,
            'mape': None,
            'rmse': None,
            'next_7_days_avg': round(forecast_value, 2),
            'next_30_days_avg': round(forecast_value, 2),
            'success': True
        }


# =============================================================================
# STATISTICAL FORECASTER (Fallback)
# =============================================================================

class StatisticalForecaster:
    """Simple statistical forecasting methods"""
    
    def __init__(self, config: ForecastConfig):
        self.config = config
    
    def exponential_smoothing(
        self,
        series: pd.Series,
        alpha: float = None
    ) -> float:
        """Simple exponential smoothing"""
        alpha = alpha or self.config.exp_smoothing_alpha
        
        result = series.iloc[0]
        for value in series.iloc[1:]:
            result = alpha * value + (1 - alpha) * result
        
        return result
    
    def forecast_item(
        self,
        item_id: int,
        series_df: pd.DataFrame,
        historical_max: float
    ) -> Dict[str, Any]:
        """Generate forecast using exponential smoothing"""
        
        # Calculate smoothed value
        smoothed_value = self.exponential_smoothing(series_df['y'])
        
        # Apply STRICT bounds
        max_from_history = historical_max * self.config.max_forecast_multiplier
        max_absolute = self.config.max_absolute_daily
        historical_median = series_df['y'].median()
        median_cap = historical_median * self.config.median_multiplier
        
        if self.config.use_median_bound and historical_median > 0:
            effective_max = max(0.1, min(max_from_history, max_absolute, median_cap))
        else:
            effective_max = max(0.1, min(max_from_history, max_absolute))
        
        forecast_value = min(smoothed_value, effective_max)
        forecast_value = max(forecast_value, self.config.min_forecast)
        
        # Generate future dates
        last_date = series_df['ds'].max()
        future_dates = pd.date_range(
            start=last_date + timedelta(days=1),
            periods=self.config.forecast_horizon,
            freq='D'
        )
        
        # Add slight trend based on recent data
        recent_trend = 0
        if len(series_df) >= 14:
            recent_week = series_df.tail(7)['y'].mean()
            previous_week = series_df.tail(14).head(7)['y'].mean()
            if previous_week > 0:
                recent_trend = (recent_week - previous_week) / previous_week
        
        forecast = []
        current_value = forecast_value
        for i, d in enumerate(future_dates):
            # Apply slight trend decay
            trend_factor = 1 + (recent_trend * (0.9 ** i))
            day_forecast = current_value * trend_factor
            day_forecast = max(self.config.min_forecast, 
                              min(day_forecast, effective_max))  # Use effective_max
            
            forecast.append({
                'ds': str(d.date()),
                'yhat': round(day_forecast, 2),
                'yhat_lower': round(day_forecast * 0.7, 2),
                'yhat_upper': round(day_forecast * 1.3, 2)
            })
        
        return {
            'item_id': item_id,
            'model': 'exponential_smoothing',
            'forecast': forecast,
            'mape': None,
            'rmse': None,
            'next_7_days_avg': round(np.mean([f['yhat'] for f in forecast[:7]]), 2),
            'next_30_days_avg': round(np.mean([f['yhat'] for f in forecast]), 2),
            'success': True
        }


# =============================================================================
# MAIN PROCESSOR
# =============================================================================

class DemandForecastProcessor:
    """Main orchestrator for demand forecasting"""
    
    def __init__(self, config: Optional[ForecastConfig] = None):
        self.config = config or ForecastConfig()
        self.data_prep = TimeSeriesDataPreparator(self.config)
        self.prophet_forecaster = ProphetForecaster(self.config)
        self.stat_forecaster = StatisticalForecaster(self.config)
        
        self.forecasts: Dict[int, Dict] = {}
        self.summary_stats: Dict[str, Any] = {}
    
    def run(self) -> pd.DataFrame:
        """Run demand forecasting pipeline"""
        logger.info("=" * 60)
        logger.info("STARTING DEMAND FORECASTING")
        logger.info("=" * 60)
        
        # Phase 1: Load data
        logger.info("\n[PHASE 1] Loading Data")
        sales_df, mutations_df = self.data_prep.load_data()
        
        # Phase 2: Prepare time series
        logger.info("\n[PHASE 2] Preparing Time Series")
        item_series = self.data_prep.prepare_daily_series(sales_df, mutations_df)
        
        if not item_series:
            logger.error("No items with sufficient history for forecasting")
            return pd.DataFrame()
        
        # Phase 3: Load features for prioritization
        logger.info("\n[PHASE 3] Loading Features for Prioritization")
        features_df = self._load_features()
        
        # Prioritize items by ABC class and demand
        priority_items = self._prioritize_items(item_series, features_df)
        
        # Phase 4: Generate forecasts
        logger.info("\n[PHASE 4] Generating Forecasts")
        prophet_count = 0
        stat_count = 0
        
        for i, item_id in enumerate(priority_items):
            if item_id not in item_series:
                continue
            
            series_df = self.data_prep.fill_missing_dates(item_series[item_id])
            historical_max = series_df['y'].max()
            
            # Use Prophet for top items if available
            if (self.config.use_prophet and 
                PROPHET_AVAILABLE and 
                prophet_count < self.config.prophet_items_limit):
                result = self.prophet_forecaster.forecast_item(item_id, series_df, historical_max)
                if result['model'] == 'prophet':
                    prophet_count += 1
            else:
                result = self.stat_forecaster.forecast_item(item_id, series_df, historical_max)
                stat_count += 1
            
            self.forecasts[item_id] = result
            
            # Progress logging
            if (i + 1) % 100 == 0:
                logger.info(f"    Progress: {i + 1}/{len(priority_items)} items")
        
        logger.info(f"  Forecasts generated: Prophet={prophet_count}, Statistical={stat_count}")
        
        # Phase 5: Create summary DataFrame
        logger.info("\n[PHASE 5] Creating Summary")
        summary_df = self._create_summary()
        
        # Phase 6: Save results
        logger.info("\n[PHASE 6] Saving Results")
        self._save_results(summary_df)
        
        logger.info("\n" + "=" * 60)
        logger.info("DEMAND FORECASTING COMPLETE")
        logger.info("=" * 60)
        
        return summary_df
    
    def _load_features(self) -> pd.DataFrame:
        """Load feature data for prioritization"""
        features_path = Path(self.config.features_dir) / "master_features.csv"
        
        if features_path.exists():
            df = pd.read_csv(features_path, encoding='utf-8-sig')
            logger.info(f"  Loaded features for {len(df)} items")
            return df
        
        return pd.DataFrame()
    
    def _prioritize_items(
        self,
        item_series: Dict,
        features_df: pd.DataFrame
    ) -> List[int]:
        """Prioritize items for forecasting (A class first, then by demand)"""
        available_items = list(item_series.keys())
        
        if features_df.empty:
            return available_items
        
        # Sort by ABC class and demand
        features_df = features_df[features_df['id'].isin(available_items)]
        
        if 'abc_class' in features_df.columns and 'avg_daily_demand' in features_df.columns:
            # A=0, B=1, C=2 for sorting
            features_df['abc_priority'] = features_df['abc_class'].map({'A': 0, 'B': 1, 'C': 2}).fillna(2)
            features_df = features_df.sort_values(
                ['abc_priority', 'avg_daily_demand'],
                ascending=[True, False]
            )
            return features_df['id'].tolist()
        
        return available_items
    
    def _create_summary(self) -> pd.DataFrame:
        """Create summary DataFrame of all forecasts"""
        records = []
        
        for item_id, forecast_data in self.forecasts.items():
            records.append({
                'item_id': item_id,
                'model': forecast_data['model'],
                'next_7_days_avg': forecast_data['next_7_days_avg'],
                'next_30_days_avg': forecast_data['next_30_days_avg'],
                'mape': forecast_data.get('mape'),
                'rmse': forecast_data.get('rmse'),
                'success': forecast_data['success']
            })
        
        df = pd.DataFrame(records)
        
        # Calculate summary stats
        self.summary_stats = {
            'total_items': len(df),
            'prophet_items': len(df[df['model'] == 'prophet']),
            'statistical_items': len(df[df['model'] != 'prophet']),
            'avg_mape': df['mape'].mean() if 'mape' in df.columns else None
        }
        
        logger.info(f"  Summary: {self.summary_stats}")
        
        return df
    
    def _save_results(self, summary_df: pd.DataFrame):
        """Save forecast results"""
        output_path = Path(self.config.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save summary
        summary_df.to_csv(output_path / 'forecast_summary.csv', index=False, encoding='utf-8-sig')
        logger.info(f"  Saved forecast_summary.csv ({len(summary_df)} items)")
        
        # Save detailed forecasts as JSON
        detailed = {
            'generated_at': datetime.now().isoformat(),
            'config': {
                'forecast_horizon': self.config.forecast_horizon,
                'min_history_days': self.config.min_history_days
            },
            'summary': self.summary_stats,
            'forecasts': self.forecasts
        }
        
        with open(output_path / 'detailed_forecasts.json', 'w') as f:
            json.dump(detailed, f, indent=2, default=str)
        logger.info(f"  Saved detailed_forecasts.json")
        
        # Save per-item forecast CSV (flattened)
        all_forecasts = []
        for item_id, data in self.forecasts.items():
            for fc in data['forecast']:
                all_forecasts.append({
                    'item_id': item_id,
                    'date': fc['ds'],
                    'forecast': fc['yhat'],
                    'lower': fc['yhat_lower'],
                    'upper': fc['yhat_upper'],
                    'model': data['model']
                })
        
        if all_forecasts:
            fc_df = pd.DataFrame(all_forecasts)
            fc_df.to_csv(output_path / 'daily_forecasts.csv', index=False, encoding='utf-8-sig')
            logger.info(f"  Saved daily_forecasts.csv ({len(fc_df)} rows)")
        
        logger.info(f"\n  Output saved to: {output_path.absolute()}")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main entry point"""
    
    # Check Prophet availability
    if PROPHET_AVAILABLE:
        logger.info("Prophet library available - will use for top items")
    else:
        logger.info("Prophet not available - using statistical methods only")
        logger.info("Install with: pip install prophet")
    
    config = ForecastConfig(
        input_dir="../data/prepared",
        features_dir="../data/features",
        output_dir="../data/forecasts",
        forecast_horizon=30,
        prophet_items_limit=50  # Limit Prophet to top 50 items (faster)
    )
    
    processor = DemandForecastProcessor(config)
    
    try:
        forecast_df = processor.run()
        
        # Print summary
        print("\n" + "=" * 40)
        print("FORECAST SUMMARY")
        print("=" * 40)
        print(f"Total items forecasted: {len(forecast_df)}")
        if 'model' in forecast_df.columns:
            print(f"Prophet models: {(forecast_df['model'] == 'prophet').sum()}")
            print(f"Statistical models: {(forecast_df['model'] != 'prophet').sum()}")
        
    except Exception as e:
        logger.error(f"Forecasting failed: {e}")
        raise


if __name__ == '__main__':
    main()
