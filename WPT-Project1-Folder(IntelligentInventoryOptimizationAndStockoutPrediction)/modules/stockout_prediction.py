"""
Module 5: Stockout Prediction
==============================

Project 1 - Intelligent Inventory Optimization & Stockout Prediction

Features:
1. ML Classification - predict stockout probability
2. Rule-based fallback for items without history
3. Risk scoring and prioritization
4. Reorder recommendations

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

# ML libraries
try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, accuracy_score, f1_score
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

# Configure logging
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
class StockoutConfig:
    """Configuration for stockout prediction"""
    # Input/Output
    features_dir: str = "../data/features"
    forecasts_dir: str = "../data/forecasts"
    output_dir: str = "../data/predictions"
    
    # Stockout thresholds
    critical_days: int = 7          # Critical if stock < 7 days
    warning_days: int = 14          # Warning if stock < 14 days
    safe_days: int = 30             # Safe if stock >= 30 days
    
    # ML settings
    test_size: float = 0.2
    random_state: int = 42
    
    # Risk weights
    weight_abc_a: float = 3.0       # A-class items weighted 3x
    weight_abc_b: float = 2.0       # B-class items weighted 2x
    weight_abc_c: float = 1.0       # C-class items weighted 1x
    
    # Business rules
    lead_time_days: int = 7         # Default lead time
    service_level: float = 0.95     # 95% service level target


# =============================================================================
# STOCKOUT CLASSIFIER
# =============================================================================

class StockoutClassifier:
    """ML-based stockout classification"""
    
    def __init__(self, config: StockoutConfig):
        self.config = config
        self.model = None
        self.scaler = StandardScaler() if SKLEARN_AVAILABLE else None
        self.feature_columns = []
        self.metrics = {}
    
    def prepare_training_data(
        self,
        features_df: pd.DataFrame,
        forecasts_df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prepare features and labels for training
        
        Label: 1 = stockout risk (coverage < warning_days)
               0 = safe
        """
        logger.info("  Preparing training data...")
        
        # Merge features with forecasts
        df = features_df.copy()
        
        if not forecasts_df.empty and 'item_id' in forecasts_df.columns:
            forecast_agg = forecasts_df.groupby('item_id').agg({
                'next_7_days_avg': 'first',
                'next_30_days_avg': 'first'
            }).reset_index()
            
            df = df.merge(forecast_agg, left_on='id', right_on='item_id', how='left')
        
        # Fill missing values
        df['next_7_days_avg'] = df.get('next_7_days_avg', df.get('avg_daily_demand', 0)).fillna(0)
        df['next_30_days_avg'] = df.get('next_30_days_avg', df.get('avg_daily_demand', 0)).fillna(0)
        
        # Create label based on coverage days
        if 'stock_coverage_days' in df.columns:
            df['stockout_risk'] = (df['stock_coverage_days'] < self.config.warning_days).astype(int)
        elif 'days_until_stockout' in df.columns:
            df['stockout_risk'] = (df['days_until_stockout'] < self.config.warning_days).astype(int)
        else:
            # Fallback: if current_stock / demand < warning_days
            if 'current_stock' in df.columns and 'avg_daily_demand' in df.columns:
                coverage = df['current_stock'] / (df['avg_daily_demand'] + 0.01)
                df['stockout_risk'] = (coverage < self.config.warning_days).astype(int)
            else:
                df['stockout_risk'] = 0
        
        # Select features for ML
        self.feature_columns = [
            'avg_daily_demand', 'demand_cv', 'turnover_ratio', 
            'days_in_inventory', 'stock_coverage_days', 'gross_margin',
            'next_7_days_avg', 'next_30_days_avg'
        ]
        
        # Only use available columns
        available_features = [c for c in self.feature_columns if c in df.columns]
        self.feature_columns = available_features
        
        if not available_features:
            logger.warning("  No features available for ML")
            return pd.DataFrame(), pd.Series()
        
        # Prepare X and y
        X = df[available_features].fillna(0)
        y = df['stockout_risk']
        
        logger.info(f"  Training data: {len(X)} samples, {len(available_features)} features")
        logger.info(f"  Class distribution: {y.value_counts().to_dict()}")
        
        return X, y
    
    def train(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, Any]:
        """Train stockout prediction model"""
        if not SKLEARN_AVAILABLE:
            logger.warning("  scikit-learn not available, using rule-based approach")
            return {}
        
        if len(X) < 20:
            logger.warning("  Insufficient data for ML training")
            return {}
        
        logger.info("  Training ML model...")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=self.config.test_size, 
            random_state=self.config.random_state,
            stratify=y if y.nunique() > 1 else None
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train Random Forest
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=self.config.random_state,
            class_weight='balanced'
        )
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate
        y_pred = self.model.predict(X_test_scaled)
        
        self.metrics = {
            'accuracy': round(accuracy_score(y_test, y_pred), 4),
            'f1_score': round(f1_score(y_test, y_pred, average='weighted'), 4),
            'feature_importance': dict(zip(
                self.feature_columns,
                [round(x, 4) for x in self.model.feature_importances_]
            ))
        }
        
        logger.info(f"  Model trained: Accuracy={self.metrics['accuracy']:.2%}, F1={self.metrics['f1_score']:.2%}")
        
        return self.metrics
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predict stockout probability"""
        if self.model is None or not SKLEARN_AVAILABLE:
            # Rule-based fallback
            if 'stock_coverage_days' in X.columns:
                return (X['stock_coverage_days'] < self.config.warning_days).astype(int).values
            return np.zeros(len(X))
        
        X_scaled = self.scaler.transform(X.fillna(0))
        return self.model.predict_proba(X_scaled)[:, 1] if hasattr(self.model, 'predict_proba') else self.model.predict(X_scaled)


# =============================================================================
# RISK CALCULATOR
# =============================================================================

class RiskCalculator:
    """Calculate comprehensive stockout risk scores"""
    
    def __init__(self, config: StockoutConfig):
        self.config = config
    
    def calculate_risk_score(
        self,
        features_df: pd.DataFrame,
        ml_probabilities: np.ndarray = None
    ) -> pd.DataFrame:
        """
        Calculate risk score combining multiple factors
        
        Formula:
        risk_score = (coverage_risk × 0.4) + (demand_risk × 0.3) + 
                     (ml_risk × 0.2) + (abc_weight × 0.1)
        """
        logger.info("  Calculating risk scores...")
        
        df = features_df.copy()
        
        # Coverage risk (0-1 scale)
        if 'stock_coverage_days' in df.columns:
            df['coverage_risk'] = 1 - (df['stock_coverage_days'] / self.config.safe_days).clip(0, 1)
        else:
            df['coverage_risk'] = 0.5
        
        # Demand volatility risk (high CV = high risk)
        if 'demand_cv' in df.columns:
            df['demand_risk'] = (df['demand_cv'] / 2.0).clip(0, 1)  # Normalize CV to 0-1
        else:
            df['demand_risk'] = 0.3
        
        # ML probability risk
        if ml_probabilities is not None:
            df['ml_risk'] = ml_probabilities
        else:
            df['ml_risk'] = df['coverage_risk']  # Fallback to coverage
        
        # ABC weight
        if 'abc_class' in df.columns:
            abc_map = {
                'A': self.config.weight_abc_a / 3.0,  # Normalize to 0-1
                'B': self.config.weight_abc_b / 3.0,
                'C': self.config.weight_abc_c / 3.0
            }
            df['abc_weight'] = df['abc_class'].map(abc_map).fillna(0.33)
        else:
            df['abc_weight'] = 0.5
        
        # Combined risk score
        df['risk_score'] = (
            df['coverage_risk'] * 0.4 +
            df['demand_risk'] * 0.3 +
            df['ml_risk'] * 0.2 +
            df['abc_weight'] * 0.1
        ).clip(0, 1)
        
        # Risk classification
        def classify_risk(score):
            if score >= 0.7:
                return 'critical'
            elif score >= 0.5:
                return 'high'
            elif score >= 0.3:
                return 'medium'
            else:
                return 'low'
        
        df['risk_class'] = df['risk_score'].apply(classify_risk)
        
        # Summary
        risk_counts = df['risk_class'].value_counts()
        logger.info(f"  Risk distribution: {risk_counts.to_dict()}")
        
        return df
    
    def calculate_reorder_recommendations(
        self,
        df: pd.DataFrame,
        forecasts_df: pd.DataFrame = None
    ) -> pd.DataFrame:
        """Generate reorder recommendations"""
        logger.info("  Generating reorder recommendations...")
        
        df = df.copy()
        
        # Get forecast demand
        if forecasts_df is not None and not forecasts_df.empty:
            forecast_map = forecasts_df.set_index('item_id')['next_30_days_avg'].to_dict()
            df['forecast_demand'] = df['id'].map(forecast_map).fillna(df.get('avg_daily_demand', 0))
        else:
            df['forecast_demand'] = df.get('avg_daily_demand', 0)
        
        # Reorder urgency
        if 'stock_coverage_days' in df.columns:
            df['reorder_urgency'] = np.where(
                df['stock_coverage_days'] <= self.config.lead_time_days,
                'immediate',
                np.where(
                    df['stock_coverage_days'] <= self.config.warning_days,
                    'soon',
                    np.where(
                        df['stock_coverage_days'] <= self.config.safe_days,
                        'planned',
                        'not_needed'
                    )
                )
            )
        else:
            df['reorder_urgency'] = 'unknown'
        
        # Recommended order quantity (EOQ or demand-based)
        if 'eoq' in df.columns:
            df['recommended_qty'] = df['eoq']
        else:
            # Order for 30 days of demand
            df['recommended_qty'] = (df['forecast_demand'] * 30).clip(lower=1).astype(int)
        
        # Expected stockout date
        if 'stock_coverage_days' in df.columns:
            df['expected_stockout_date'] = pd.Timestamp.now() + pd.to_timedelta(
                df['stock_coverage_days'].fillna(0), unit='D'
            )
            df['expected_stockout_date'] = df['expected_stockout_date'].dt.strftime('%Y-%m-%d')
        
        return df


# =============================================================================
# ALERT GENERATOR
# =============================================================================

class AlertGenerator:
    """Generate stockout alerts"""
    
    def __init__(self, config: StockoutConfig):
        self.config = config
    
    def generate_alerts(self, predictions_df: pd.DataFrame) -> List[Dict]:
        """Generate prioritized alert list"""
        logger.info("  Generating alerts...")
        
        alerts = []
        
        # Filter items needing attention
        critical_items = predictions_df[predictions_df['risk_class'].isin(['critical', 'high'])]
        
        for _, row in critical_items.iterrows():
            alert = {
                'item_id': row.get('id'),
                'item_name': row.get('name', 'Unknown'),
                'item_code': row.get('no', ''),
                'risk_class': row.get('risk_class'),
                'risk_score': round(row.get('risk_score', 0), 3),
                'current_stock': row.get('current_stock', 0),
                'coverage_days': round(row.get('stock_coverage_days', 0), 1),
                'reorder_urgency': row.get('reorder_urgency', 'unknown'),
                'recommended_qty': row.get('recommended_qty', 0),
                'expected_stockout': row.get('expected_stockout_date', ''),
                'abc_class': row.get('abc_class', 'C')
            }
            alerts.append(alert)
        
        # Sort by risk score (highest first) and ABC class
        alerts = sorted(alerts, key=lambda x: (-x['risk_score'], x['abc_class']))
        
        logger.info(f"  Generated {len(alerts)} alerts ({len([a for a in alerts if a['risk_class'] == 'critical'])} critical)")
        
        return alerts


# =============================================================================
# MAIN PROCESSOR
# =============================================================================

class StockoutPredictionProcessor:
    """Main orchestrator for stockout prediction"""
    
    def __init__(self, config: Optional[StockoutConfig] = None):
        self.config = config or StockoutConfig()
        self.classifier = StockoutClassifier(self.config)
        self.risk_calc = RiskCalculator(self.config)
        self.alert_gen = AlertGenerator(self.config)
        
        self.predictions_df = pd.DataFrame()
        self.alerts = []
    
    def run(self) -> pd.DataFrame:
        """Run stockout prediction pipeline"""
        logger.info("=" * 60)
        logger.info("STARTING STOCKOUT PREDICTION")
        logger.info("=" * 60)
        
        # Phase 1: Load data
        logger.info("\n[PHASE 1] Loading Data")
        features_df, forecasts_df = self._load_data()
        
        if features_df.empty:
            logger.error("No features data available")
            return pd.DataFrame()
        
        # Phase 2: Prepare and train ML model
        logger.info("\n[PHASE 2] Training ML Model")
        X, y = self.classifier.prepare_training_data(features_df, forecasts_df)
        
        if not X.empty:
            self.classifier.train(X, y)
        
        # Phase 3: Generate predictions
        logger.info("\n[PHASE 3] Generating Predictions")
        if not X.empty:
            ml_probs = self.classifier.predict(X)
        else:
            ml_probs = None
        
        # Phase 4: Calculate risk scores
        logger.info("\n[PHASE 4] Calculating Risk Scores")
        predictions_df = self.risk_calc.calculate_risk_score(features_df, ml_probs)
        
        # Phase 5: Generate reorder recommendations
        logger.info("\n[PHASE 5] Generating Recommendations")
        predictions_df = self.risk_calc.calculate_reorder_recommendations(predictions_df, forecasts_df)
        
        # Phase 6: Generate alerts
        logger.info("\n[PHASE 6] Generating Alerts")
        self.alerts = self.alert_gen.generate_alerts(predictions_df)
        
        # Phase 7: Save results
        logger.info("\n[PHASE 7] Saving Results")
        self._save_results(predictions_df)
        
        self.predictions_df = predictions_df
        
        logger.info("\n" + "=" * 60)
        logger.info("STOCKOUT PREDICTION COMPLETE")
        logger.info("=" * 60)
        
        return predictions_df
    
    def _load_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load features and forecasts"""
        features_path = Path(self.config.features_dir) / "master_features.csv"
        forecasts_path = Path(self.config.forecasts_dir) / "forecast_summary.csv"
        
        features_df = pd.DataFrame()
        forecasts_df = pd.DataFrame()
        
        if features_path.exists():
            features_df = pd.read_csv(features_path, encoding='utf-8-sig')
            logger.info(f"  Loaded features: {len(features_df)} items")
        else:
            logger.warning(f"  Features file not found: {features_path}")
        
        if forecasts_path.exists():
            forecasts_df = pd.read_csv(forecasts_path, encoding='utf-8-sig')
            logger.info(f"  Loaded forecasts: {len(forecasts_df)} items")
        
        return features_df, forecasts_df
    
    def _save_results(self, predictions_df: pd.DataFrame):
        """Save prediction results"""
        output_path = Path(self.config.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save predictions
        predictions_df.to_csv(
            output_path / 'stockout_predictions.csv', 
            index=False, 
            encoding='utf-8-sig'
        )
        logger.info(f"  Saved stockout_predictions.csv ({len(predictions_df)} items)")
        
        # Save alerts
        with open(output_path / 'stockout_alerts.json', 'w') as f:
            json.dump({
                'generated_at': datetime.now().isoformat(),
                'total_alerts': len(self.alerts),
                'critical_count': len([a for a in self.alerts if a['risk_class'] == 'critical']),
                'high_count': len([a for a in self.alerts if a['risk_class'] == 'high']),
                'alerts': self.alerts
            }, f, indent=2, default=str)
        logger.info(f"  Saved stockout_alerts.json ({len(self.alerts)} alerts)")
        
        # Save model metrics
        if self.classifier.metrics:
            with open(output_path / 'model_metrics.json', 'w') as f:
                json.dump(self.classifier.metrics, f, indent=2)
            logger.info(f"  Saved model_metrics.json")
        
        # Create summary report
        summary = {
            'generated_at': datetime.now().isoformat(),
            'total_items': len(predictions_df),
            'risk_distribution': predictions_df['risk_class'].value_counts().to_dict() if 'risk_class' in predictions_df.columns else {},
            'urgency_distribution': predictions_df['reorder_urgency'].value_counts().to_dict() if 'reorder_urgency' in predictions_df.columns else {},
            'model_metrics': self.classifier.metrics
        }
        
        with open(output_path / 'prediction_summary.json', 'w') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"  Saved prediction_summary.json")
        
        logger.info(f"\n  Output saved to: {output_path.absolute()}")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main entry point"""
    
    if not SKLEARN_AVAILABLE:
        logger.warning("scikit-learn not available - using rule-based approach only")
        logger.info("Install with: pip install scikit-learn")
    
    config = StockoutConfig(
        features_dir="../data/features",
        forecasts_dir="../data/forecasts",
        output_dir="../data/predictions"
    )
    
    processor = StockoutPredictionProcessor(config)
    
    try:
        predictions_df = processor.run()
        
        # Print summary
        print("\n" + "=" * 40)
        print("PREDICTION SUMMARY")
        print("=" * 40)
        print(f"Total items: {len(predictions_df)}")
        
        if 'risk_class' in predictions_df.columns:
            print("\nRisk Distribution:")
            print(predictions_df['risk_class'].value_counts().to_string())
        
        if processor.alerts:
            print(f"\nTotal Alerts: {len(processor.alerts)}")
            print(f"Critical: {len([a for a in processor.alerts if a['risk_class'] == 'critical'])}")
            print(f"High: {len([a for a in processor.alerts if a['risk_class'] == 'high'])}")
        
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise


if __name__ == '__main__':
    main()
