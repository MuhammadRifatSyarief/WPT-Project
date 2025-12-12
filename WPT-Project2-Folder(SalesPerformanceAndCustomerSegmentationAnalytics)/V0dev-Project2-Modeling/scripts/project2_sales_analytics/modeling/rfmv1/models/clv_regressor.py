"""
Customer Lifetime Value (CLV) Regression Model

Module untuk memprediksi CLV menggunakan:
- Linear Regression
- Random Forest Regressor
- Gradient Boosting Regressor

Output: Predicted CLV value dan CLV segments
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.metrics import (
    mean_squared_error, mean_absolute_error, r2_score,
    mean_absolute_percentage_error
)
from sklearn.model_selection import cross_val_score
import joblib
from pathlib import Path

from config.rfm_config import CLVConfig
from utils.helpers import print_section_header, print_subsection_header, print_model_metrics, format_currency


class CLVRegressor:
    """
    Customer Lifetime Value Prediction with log transformation for skewed data
    
    Memprediksi nilai total yang akan dihasilkan customer
    selama periode tertentu berdasarkan:
    - RFM metrics
    - Purchase behavior
    - Customer tenure
    """
    
    MODEL_TYPES = {
        "linear": LinearRegression,
        "ridge": Ridge,
        "lasso": Lasso,
        "random_forest": RandomForestRegressor,
        "gradient_boosting": GradientBoostingRegressor
    }
    
    def __init__(self, config: CLVConfig, verbose: bool = True):
        """
        Initialize CLV regressor
        
        Args:
            config: CLVConfig dengan parameters
            verbose: Print progress messages
        """
        self.config = config
        self.verbose = verbose
        self.model = None
        self.is_fitted = False
        self.feature_names: List[str] = []
        self.feature_importances: Dict[str, float] = {}
        self.metrics: Dict[str, float] = {}
        self.cv_scores: List[float] = []
        self.clv_stats: Dict[str, float] = {}
        self.use_log_transform = True
        self.log_shift = 1.0
        
    def _create_model(self):
        """Create regression model based on config"""
        if self.config.model_type == "random_forest":
            self.model = RandomForestRegressor(
                n_estimators=self.config.rf_n_estimators,
                max_depth=self.config.rf_max_depth,
                random_state=self.config.random_state,
                n_jobs=-1
            )
        elif self.config.model_type == "gradient_boosting":
            self.model = GradientBoostingRegressor(
                n_estimators=self.config.gb_n_estimators,
                max_depth=self.config.gb_max_depth,
                learning_rate=self.config.gb_learning_rate,
                random_state=self.config.random_state
            )
        elif self.config.model_type == "linear":
            self.model = LinearRegression()
        elif self.config.model_type == "ridge":
            self.model = Ridge(random_state=self.config.random_state)
        elif self.config.model_type == "lasso":
            self.model = Lasso(random_state=self.config.random_state)
        else:
            raise ValueError(f"Unknown model type: {self.config.model_type}")
        
        if self.verbose:
            print(f"[CLVRegressor] Created {self.config.model_type} model")
    
    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series
    ) -> "CLVRegressor":
        """
        Fit regression model with log transformation for skewed targets
        
        Args:
            X_train: Training features
            y_train: Training target (CLV values)
            
        Returns:
            self untuk chaining
        """
        self._create_model()
        self.feature_names = list(X_train.columns)
        
        skewness = y_train.skew()
        
        if self.verbose:
            print(f"[CLVRegressor] Training on {len(X_train)} samples with {len(self.feature_names)} features")
            print(f"[CLVRegressor] Target stats: mean={y_train.mean():.2f}, std={y_train.std():.2f}, skew={skewness:.2f}")
        
        y_train_transformed = y_train.copy()
        if abs(skewness) > 2.0:
            self.use_log_transform = True
            # Ensure positive values
            min_val = y_train.min()
            if min_val <= 0:
                self.log_shift = abs(min_val) + 1.0
            else:
                self.log_shift = 1.0
            
            y_train_transformed = np.log(y_train + self.log_shift)
            
            if self.verbose:
                new_skew = y_train_transformed.skew()
                print(f"[CLVRegressor] Applied log transform (skewness: {skewness:.2f} → {new_skew:.2f})")
        else:
            self.use_log_transform = False
            if self.verbose:
                print(f"[CLVRegressor] Skewness acceptable, no log transform needed")
        
        # Fit model
        self.model.fit(X_train, y_train_transformed)
        self.is_fitted = True
        
        # Store CLV statistics
        self.clv_stats = {
            "train_mean": y_train.mean(),
            "train_std": y_train.std(),
            "train_min": y_train.min(),
            "train_max": y_train.max(),
            "train_median": y_train.median(),
            "train_skewness": skewness,
            "log_transformed": self.use_log_transform,
            "log_shift": self.log_shift if self.use_log_transform else None
        }
        
        # Extract feature importances
        self._extract_feature_importances()
        
        return self
    
    def _extract_feature_importances(self):
        """Extract and sort feature importances"""
        if hasattr(self.model, "feature_importances_"):
            importances = self.model.feature_importances_
        elif hasattr(self.model, "coef_"):
            importances = np.abs(self.model.coef_)
        else:
            importances = np.zeros(len(self.feature_names))
        
        self.feature_importances = dict(zip(self.feature_names, importances))
        self.feature_importances = dict(
            sorted(self.feature_importances.items(), key=lambda x: x[1], reverse=True)
        )
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict CLV values with inverse log transform if needed
        
        Args:
            X: Features DataFrame
            
        Returns:
            Array of CLV predictions
        """
        if not self.is_fitted:
            raise ValueError("Model belum di-fit.")
        
        predictions = self.model.predict(X)
        
        if self.use_log_transform:
            predictions = np.exp(predictions) - self.log_shift
        
        # Ensure non-negative predictions
        predictions = np.maximum(predictions, 0)
        
        return predictions
    
    def predict_with_segments(
        self,
        X: pd.DataFrame,
        customer_ids: pd.Series
    ) -> pd.DataFrame:
        """
        Predict CLV dengan segmentasi
        
        Args:
            X: Features DataFrame
            customer_ids: Customer ID series
            
        Returns:
            DataFrame dengan predictions dan segments
        """
        predictions = self.predict(X)
        
        # Calculate percentiles untuk segmentasi
        p25 = np.percentile(predictions, 25)
        p50 = np.percentile(predictions, 50)
        p75 = np.percentile(predictions, 75)
        
        # Assign segments
        def assign_segment(clv):
            if clv >= p75:
                return "Platinum"
            elif clv >= p50:
                return "Gold"
            elif clv >= p25:
                return "Silver"
            else:
                return "Bronze"
        
        result_df = pd.DataFrame({
            "customer_id": customer_ids,
            "predicted_clv": predictions,
            "clv_segment": [assign_segment(clv) for clv in predictions]
        })
        
        # Add percentile rank
        result_df["clv_percentile"] = result_df["predicted_clv"].rank(pct=True) * 100
        
        return result_df
    
    def evaluate(
        self,
        X_test: pd.DataFrame,
        y_test: pd.Series
    ) -> Dict[str, float]:
        """
        Evaluate model performance with safe MAPE calculation
        
        Args:
            X_test: Test features
            y_test: Test target
            
        Returns:
            Dictionary dengan metrics
        """
        y_pred = self.predict(X_test)
        
        def safe_mape(y_true, y_pred):
            """Calculate MAPE with protection against division by zero"""
            # Filter out zero values
            mask = y_true != 0
            if mask.sum() == 0:
                return 0.0  # No valid values
            
            mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100
            # Cap MAPE at reasonable maximum
            return min(mape, 1000.0)
        
        self.metrics = {
            "mse": mean_squared_error(y_test, y_pred),
            "rmse": np.sqrt(mean_squared_error(y_test, y_pred)),
            "mae": mean_absolute_error(y_test, y_pred),
            "r2_score": r2_score(y_test, y_pred),
            "mape": safe_mape(y_test.values, y_pred)  # Use safe MAPE
        }
        
        # Additional metrics
        self.metrics["explained_variance"] = 1 - (np.var(y_test - y_pred) / np.var(y_test))
        
        # Prediction error statistics
        errors = y_test - y_pred
        self.metrics["mean_error"] = errors.mean()
        self.metrics["error_std"] = errors.std()
        
        if self.verbose:
            print_model_metrics({
                "R2 Score": self.metrics["r2_score"],
                "RMSE": self.metrics["rmse"],
                "MAE": self.metrics["mae"],
                "MAPE": f"{self.metrics['mape']:.2f}%"
            }, title="CLV Regressor Metrics")
        
        return self.metrics
    
    def cross_validate(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        cv: int = 5
    ) -> Dict[str, Any]:
        """
        Perform cross-validation
        
        Args:
            X: Features
            y: Target
            cv: Number of folds
            
        Returns:
            Dictionary dengan CV results
        """
        if self.model is None:
            self._create_model()
        
        if self.verbose:
            print(f"[CLVRegressor] Running {cv}-fold cross-validation...")
        
        # Use negative MSE karena sklearn convention
        cv_scores_mse = cross_val_score(self.model, X, y, cv=cv, scoring="neg_mean_squared_error")
        cv_scores_r2 = cross_val_score(self.model, X, y, cv=cv, scoring="r2")
        
        self.cv_scores = np.sqrt(-cv_scores_mse)  # Convert to RMSE
        
        cv_results = {
            "cv_rmse_scores": self.cv_scores.tolist(),
            "mean_rmse": self.cv_scores.mean(),
            "std_rmse": self.cv_scores.std(),
            "cv_r2_scores": cv_scores_r2.tolist(),
            "mean_r2": cv_scores_r2.mean(),
            "std_r2": cv_scores_r2.std()
        }
        
        if self.verbose:
            print(f"[CLVRegressor] CV RMSE: {cv_results['mean_rmse']:.2f} (+/- {cv_results['std_rmse']*2:.2f})")
            print(f"[CLVRegressor] CV R2: {cv_results['mean_r2']:.4f} (+/- {cv_results['std_r2']*2:.4f})")
        
        return cv_results
    
    def calculate_simple_clv(
        self,
        df: pd.DataFrame,
        avg_order_value_col: str = "avg_transaction_value",
        purchase_frequency_col: str = "frequency",
        customer_lifespan_months: int = 12
    ) -> pd.DataFrame:
        """
        Calculate simple CLV using formula:
        CLV = Avg Order Value × Purchase Frequency × Customer Lifespan
        
        Args:
            df: DataFrame dengan customer data
            avg_order_value_col: Column name untuk average order value
            purchase_frequency_col: Column name untuk purchase frequency
            customer_lifespan_months: Expected customer lifespan dalam bulan
            
        Returns:
            DataFrame dengan calculated CLV
        """
        result = df.copy()
        
        # Simple CLV calculation
        result["simple_clv"] = (
            result[avg_order_value_col] * 
            result[purchase_frequency_col] * 
            (customer_lifespan_months / 12)  # Annualized
        )
        
        # Discounted CLV (present value)
        discount_rate = self.config.discount_rate
        result["discounted_clv"] = result["simple_clv"] / (1 + discount_rate)
        
        if self.verbose:
            print(f"[CLVRegressor] Calculated simple CLV for {len(result)} customers")
            print(f"[CLVRegressor] CLV range: {format_currency(result['simple_clv'].min())} - {format_currency(result['simple_clv'].max())}")
        
        return result
    
    def get_top_value_customers(
        self,
        X: pd.DataFrame,
        customer_ids: pd.Series,
        top_n: int = 100
    ) -> pd.DataFrame:
        """
        Identifikasi top value customers
        
        Args:
            X: Features
            customer_ids: Customer ID series
            top_n: Number of top customers
            
        Returns:
            DataFrame dengan top customers
        """
        predictions = self.predict(X)
        
        top_df = pd.DataFrame({
            "customer_id": customer_ids,
            "predicted_clv": predictions
        })
        
        top_df = top_df.nlargest(top_n, "predicted_clv")
        top_df["rank"] = range(1, len(top_df) + 1)
        top_df["cumulative_clv"] = top_df["predicted_clv"].cumsum()
        top_df["cumulative_pct"] = top_df["cumulative_clv"] / predictions.sum() * 100
        
        if self.verbose:
            print(f"[CLVRegressor] Top {top_n} customers contribute {top_df['cumulative_pct'].iloc[-1]:.1f}% of total predicted CLV")
        
        return top_df
    
    def get_clv_distribution_analysis(
        self,
        X: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Analyze CLV distribution
        
        Args:
            X: Features
            
        Returns:
            Dictionary dengan distribution analysis
        """
        predictions = self.predict(X)
        
        analysis = {
            "total_customers": len(predictions),
            "total_predicted_clv": predictions.sum(),
            "mean_clv": predictions.mean(),
            "median_clv": np.median(predictions),
            "std_clv": predictions.std(),
            "min_clv": predictions.min(),
            "max_clv": predictions.max(),
            "percentiles": {
                "p10": np.percentile(predictions, 10),
                "p25": np.percentile(predictions, 25),
                "p50": np.percentile(predictions, 50),
                "p75": np.percentile(predictions, 75),
                "p90": np.percentile(predictions, 90),
                "p99": np.percentile(predictions, 99)
            },
            "segment_distribution": {
                "Bronze (0-25%)": (predictions < np.percentile(predictions, 25)).sum(),
                "Silver (25-50%)": ((predictions >= np.percentile(predictions, 25)) & 
                                   (predictions < np.percentile(predictions, 50))).sum(),
                "Gold (50-75%)": ((predictions >= np.percentile(predictions, 50)) & 
                                 (predictions < np.percentile(predictions, 75))).sum(),
                "Platinum (75-100%)": (predictions >= np.percentile(predictions, 75)).sum()
            }
        }
        
        # Pareto analysis (80/20 rule)
        sorted_clv = np.sort(predictions)[::-1]
        cumsum = np.cumsum(sorted_clv)
        total = predictions.sum()
        
        # Find top X% that contributes to 80% of CLV
        idx_80 = np.searchsorted(cumsum, total * 0.8)
        analysis["pareto"] = {
            "top_pct_for_80_revenue": (idx_80 / len(predictions)) * 100,
            "top_20_pct_revenue_share": cumsum[int(len(predictions) * 0.2)] / total * 100
        }
        
        return analysis
    
    def get_clv_insights(self) -> Dict[str, Any]:
        """
        Generate business insights dari CLV analysis
        
        Returns:
            Dictionary dengan insights
        """
        # Top CLV drivers
        top_drivers = list(self.feature_importances.items())[:5]
        
        insights = {
            "top_clv_drivers": [
                {"feature": f, "importance": round(imp, 4)}
                for f, imp in top_drivers
            ],
            "model_performance": {
                "r2_score": self.metrics.get("r2_score", 0),
                "rmse": self.metrics.get("rmse", 0),
                "mape": self.metrics.get("mape", 0)
            },
            "recommendations": {
                "Platinum": [
                    "VIP treatment dan dedicated account manager",
                    "Exclusive early access ke produk baru",
                    "Personalized offers berdasarkan purchase history",
                    "High priority customer service"
                ],
                "Gold": [
                    "Loyalty program dengan benefits premium",
                    "Targeted upselling campaigns",
                    "Invitation ke exclusive events",
                    "Personalized product recommendations"
                ],
                "Silver": [
                    "Nurturing campaigns untuk meningkatkan engagement",
                    "Bundle offers untuk meningkatkan basket size",
                    "Referral incentives",
                    "Educational content tentang product value"
                ],
                "Bronze": [
                    "Re-engagement campaigns",
                    "Entry-level product promotions",
                    "Survey untuk understand barriers",
                    "Cost-effective service channels"
                ]
            },
            "interpretation": self._interpret_clv_drivers()
        }
        
        return insights
    
    def _interpret_clv_drivers(self) -> List[str]:
        """Generate natural language interpretations"""
        interpretations = []
        
        for feature, importance in list(self.feature_importances.items())[:3]:
            if importance > 0.3:
                interpretations.append(
                    f"{feature} adalah DRIVER UTAMA CLV (importance: {importance:.2%})"
                )
            elif importance > 0.15:
                interpretations.append(
                    f"{feature} memiliki PENGARUH SIGNIFIKAN pada CLV (importance: {importance:.2%})"
                )
            else:
                interpretations.append(
                    f"{feature} berkontribusi pada CLV prediction (importance: {importance:.2%})"
                )
        
        return interpretations
    
    def save(self, filepath: str):
        """Save model ke file"""
        save_data = {
            "model": self.model,
            "config": self.config,
            "feature_names": self.feature_names,
            "feature_importances": self.feature_importances,
            "metrics": self.metrics,
            "clv_stats": self.clv_stats,
            "is_fitted": self.is_fitted
        }
        
        joblib.dump(save_data, filepath)
        
        if self.verbose:
            print(f"[CLVRegressor] Model saved to {filepath}")
    
    @classmethod
    def load(cls, filepath: str) -> "CLVRegressor":
        """Load model dari file"""
        save_data = joblib.load(filepath)
        
        instance = cls(config=save_data["config"], verbose=False)
        instance.model = save_data["model"]
        instance.feature_names = save_data["feature_names"]
        instance.feature_importances = save_data["feature_importances"]
        instance.metrics = save_data["metrics"]
        instance.clv_stats = save_data["clv_stats"]
        instance.is_fitted = save_data["is_fitted"]
        
        return instance
