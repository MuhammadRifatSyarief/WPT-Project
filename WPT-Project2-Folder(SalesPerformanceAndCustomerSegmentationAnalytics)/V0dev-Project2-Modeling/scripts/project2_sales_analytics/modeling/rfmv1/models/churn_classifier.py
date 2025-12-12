"""
Churn Classification Model

Module untuk memprediksi customer churn menggunakan:
- Random Forest Classifier
- XGBoost Classifier
- Logistic Regression
- IsolationForest for anomaly-based churn detection

Output: Probabilitas churn dan klasifikasi (Churned/Not Churned)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, IsolationForest
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report,
    roc_curve, precision_recall_curve
)
from sklearn.model_selection import cross_val_score, GridSearchCV
import joblib
from pathlib import Path

from config.rfm_config import ChurnConfig
from utils.helpers import print_section_header, print_subsection_header, print_model_metrics


class ChurnClassifier:
    """
    Churn Prediction Classifier with graceful handling for single-class scenarios
    
    Memprediksi apakah customer akan churn berdasarkan:
    - RFM metrics
    - Behavioral features
    - Temporal features
    """
    
    MODEL_TYPES = {
        "random_forest": RandomForestClassifier,
        "xgboost": GradientBoostingClassifier,
        "logistic": LogisticRegression,
        "isolation_forest": IsolationForest
    }
    
    def __init__(self, config: ChurnConfig, verbose: bool = True):
        """
        Initialize churn classifier
        
        Args:
            config: ChurnConfig dengan parameters
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
        self.threshold: float = 0.5
        self.is_single_class = False
        self.fallback_mode = "percentile"  # Use percentile-based labeling as fallback
        
    def _create_model(self):
        """Create classification model based on config"""
        if self.config.model_type == "random_forest":
            self.model = RandomForestClassifier(
                n_estimators=self.config.rf_n_estimators,
                max_depth=self.config.rf_max_depth,
                min_samples_split=self.config.rf_min_samples_split,
                min_samples_leaf=self.config.rf_min_samples_leaf,
                random_state=self.config.random_state,
                class_weight="balanced" if self.config.use_class_weight else None,
                n_jobs=-1
            )
        elif self.config.model_type == "xgboost":
            self.model = GradientBoostingClassifier(
                n_estimators=self.config.xgb_n_estimators,
                max_depth=self.config.xgb_max_depth,
                learning_rate=self.config.xgb_learning_rate,
                subsample=self.config.xgb_subsample,
                random_state=self.config.random_state
            )
        elif self.config.model_type == "logistic":
            self.model = LogisticRegression(
                max_iter=self.config.lr_max_iter,
                C=self.config.lr_C,
                random_state=self.config.random_state,
                class_weight="balanced" if self.config.use_class_weight else None
            )
        elif self.config.model_type == "isolation_forest":
            self.model = IsolationForest(
                contamination=0.1,  # Assume 10% churn rate
                random_state=self.config.random_state,
                n_jobs=-1
            )
        else:
            raise ValueError(f"Unknown model type: {self.config.model_type}")
        
        if self.verbose:
            print(f"[ChurnClassifier] Created {self.config.model_type} model")
    
    def _generate_synthetic_churn_labels(
        self,
        X_train: pd.DataFrame,
        recency_col: str = "recency",
        churn_percentile: float = 80
    ) -> pd.Series:
        """
        Generate synthetic churn labels based on recency percentile
        
        When all customers appear as "not churned", use recency to identify
        customers who haven't purchased recently as potential churners.
        
        Args:
            X_train: Training features
            recency_col: Column name for recency
            churn_percentile: Percentile threshold (customers above this = churned)
            
        Returns:
            Series of synthetic labels (0/1)
        """
        if recency_col not in X_train.columns:
            # Fallback: use first numeric column
            numeric_cols = X_train.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) == 0:
                raise ValueError("No numeric columns found for synthetic labeling")
            recency_col = numeric_cols[0]
        
        recency = X_train[recency_col]
        threshold = recency.quantile(churn_percentile / 100)
        
        synthetic_labels = (recency > threshold).astype(int)
        
        if self.verbose:
            churn_count = synthetic_labels.sum()
            churn_pct = (churn_count / len(synthetic_labels)) * 100
            print(f"[ChurnClassifier] Generated synthetic labels: {churn_count} churned ({churn_pct:.1f}%) "
                  f"using recency P{churn_percentile} threshold={threshold:.2f}")
        
        return synthetic_labels
    
    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series
    ) -> "ChurnClassifier":
        """
        Fit classification model with graceful single-class handling
        
        Args:
            X_train: Training features
            y_train: Training target (0/1)
            
        Returns:
            self untuk chaining
        """
        self._create_model()
        self.feature_names = list(X_train.columns)
        
        unique_classes = y_train.nunique()
        class_dist = y_train.value_counts().to_dict()
        
        if self.verbose:
            print(f"[ChurnClassifier] Training on {len(X_train)} samples with {len(self.feature_names)} features")
            print(f"[ChurnClassifier] Target distribution: {class_dist}")
        
        if unique_classes < 2:
            self.is_single_class = True
            if self.verbose:
                print(f"[ChurnClassifier] WARNING: Only {unique_classes} class found in target!")
                print(f"[ChurnClassifier] Switching to synthetic labeling based on {self.fallback_mode}...")
            
            y_train_synthetic = self._generate_synthetic_churn_labels(X_train)
            
            new_dist = y_train_synthetic.value_counts().to_dict()
            if self.verbose:
                print(f"[ChurnClassifier] New target distribution: {new_dist}")
            
            y_train = y_train_synthetic
        
        self.model.fit(X_train, y_train)
        self.is_fitted = True
        
        self._extract_feature_importances()
        
        return self
    
    def _extract_feature_importances(self):
        """Extract and sort feature importances"""
        if hasattr(self.model, "feature_importances_"):
            importances = self.model.feature_importances_
        elif hasattr(self.model, "coef_"):
            importances = np.abs(self.model.coef_[0])
        elif isinstance(self.model, IsolationForest):
            importances = np.zeros(len(self.feature_names))
        else:
            importances = np.zeros(len(self.feature_names))
        
        self.feature_importances = dict(zip(self.feature_names, importances))
        self.feature_importances = dict(
            sorted(self.feature_importances.items(), key=lambda x: x[1], reverse=True)
        )
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict churn labels
        
        Args:
            X: Features DataFrame
            
        Returns:
            Array of predictions (0/1)
        """
        if not self.is_fitted:
            raise ValueError("Model belum di-fit.")
        
        # Handle IsolationForest prediction
        if isinstance(self.model, IsolationForest):
            predictions = self.model.predict(X)
            return (predictions == -1).astype(int)
        
        return self.model.predict(X)
    
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict churn probabilities
        
        Args:
            X: Features DataFrame
            
        Returns:
            Array of probabilities for positive class
        """
        if not self.is_fitted:
            raise ValueError("Model belum di-fit.")
        
        # Handle IsolationForest probability prediction
        if isinstance(self.model, IsolationForest):
            scores = self.model.decision_function(X)
            return 1 / (1 + np.exp(scores))
        
        return self.model.predict_proba(X)[:, 1]
    
    def predict_with_threshold(
        self,
        X: pd.DataFrame,
        threshold: float = 0.5
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict dengan custom threshold
        
        Args:
            X: Features DataFrame
            threshold: Probability threshold untuk positive class
            
        Returns:
            Tuple of (predictions, probabilities)
        """
        probas = self.predict_proba(X)
        predictions = (probas >= threshold).astype(int)
        
        return predictions, probas
    
    def evaluate(
        self,
        X_test: pd.DataFrame,
        y_test: pd.Series
    ) -> Dict[str, float]:
        """
        Evaluate model performance with safe handling for edge cases
        
        Args:
            X_test: Test features
            y_test: Test target
            
        Returns:
            Dictionary dengan metrics
        """
        y_pred = self.predict(X_test)
        
        try:
            y_proba = self.predict_proba(X_test)
        except:
            y_proba = y_pred.astype(float)  # Fallback to binary predictions
        
        unique_test_classes = len(np.unique(y_test))
        
        self.metrics = {
            "accuracy": accuracy_score(y_test, y_pred),
            "precision": precision_score(y_test, y_pred, zero_division=0),
            "recall": recall_score(y_test, y_pred, zero_division=0),
            "f1_score": f1_score(y_test, y_pred, zero_division=0),
            "roc_auc": roc_auc_score(y_test, y_proba) if unique_test_classes > 1 else 0,
            "support_positive": int(y_test.sum()),
            "support_negative": int(len(y_test) - y_test.sum()),
            "is_single_class_scenario": self.is_single_class
        }
        
        cm = confusion_matrix(y_test, y_pred)
        self.metrics["confusion_matrix"] = cm.tolist()
        if cm.shape == (2, 2):
            self.metrics["true_negatives"] = int(cm[0, 0])
            self.metrics["false_positives"] = int(cm[0, 1])
            self.metrics["false_negatives"] = int(cm[1, 0])
            self.metrics["true_positives"] = int(cm[1, 1])
        
        if self.verbose:
            print_model_metrics({
                "Accuracy": self.metrics["accuracy"],
                "Precision": self.metrics["precision"],
                "Recall": self.metrics["recall"],
                "F1 Score": self.metrics["f1_score"],
                "ROC AUC": self.metrics["roc_auc"]
            }, title="Churn Classifier Metrics")
            
            if self.is_single_class:
                print("[ChurnClassifier] Note: Model trained with synthetic labels due to single-class data")
        
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
            print(f"[ChurnClassifier] Running {cv}-fold cross-validation...")
        
        self.cv_scores = cross_val_score(self.model, X, y, cv=cv, scoring="f1")
        
        cv_results = {
            "cv_scores": self.cv_scores.tolist(),
            "mean_score": self.cv_scores.mean(),
            "std_score": self.cv_scores.std(),
            "min_score": self.cv_scores.min(),
            "max_score": self.cv_scores.max()
        }
        
        if self.verbose:
            print(f"[ChurnClassifier] CV F1 Score: {cv_results['mean_score']:.4f} (+/- {cv_results['std_score']*2:.4f})")
        
        return cv_results
    
    def find_optimal_threshold(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        metric: str = "f1"
    ) -> Dict[str, Any]:
        """
        Find optimal probability threshold
        
        Args:
            X: Features
            y: Target
            metric: Metric to optimize ('f1', 'precision', 'recall')
            
        Returns:
            Dictionary dengan threshold analysis
        """
        y_proba = self.predict_proba(X)
        
        thresholds = np.arange(0.1, 0.9, 0.05)
        results = []
        
        for thresh in thresholds:
            y_pred = (y_proba >= thresh).astype(int)
            
            result = {
                "threshold": thresh,
                "precision": precision_score(y, y_pred, zero_division=0),
                "recall": recall_score(y, y_pred, zero_division=0),
                "f1": f1_score(y, y_pred, zero_division=0),
                "accuracy": accuracy_score(y, y_pred)
            }
            results.append(result)
        
        results_df = pd.DataFrame(results)
        
        optimal_idx = results_df[metric].idxmax()
        optimal_threshold = results_df.loc[optimal_idx, "threshold"]
        
        self.threshold = optimal_threshold
        
        if self.verbose:
            print(f"[ChurnClassifier] Optimal threshold for {metric}: {optimal_threshold:.2f}")
        
        return {
            "optimal_threshold": optimal_threshold,
            "optimal_metrics": results_df.loc[optimal_idx].to_dict(),
            "all_results": results_df
        }
    
    def get_high_risk_customers(
        self,
        X: pd.DataFrame,
        customer_ids: pd.Series,
        threshold: float = 0.7
    ) -> pd.DataFrame:
        """
        Identifikasi customers dengan high churn risk
        
        Args:
            X: Features
            customer_ids: Customer ID series
            threshold: Minimum probability untuk high risk
            
        Returns:
            DataFrame dengan high risk customers
        """
        probas = self.predict_proba(X)
        
        high_risk_df = pd.DataFrame({
            "customer_id": customer_ids,
            "churn_probability": probas,
            "risk_level": pd.cut(
                probas,
                bins=[0, 0.3, 0.5, 0.7, 1.0],
                labels=["Low", "Medium", "High", "Critical"]
            )
        })
        
        high_risk_df = high_risk_df[high_risk_df["churn_probability"] >= threshold]
        high_risk_df = high_risk_df.sort_values("churn_probability", ascending=False)
        
        if self.verbose:
            print(f"[ChurnClassifier] Found {len(high_risk_df)} high-risk customers (threshold >= {threshold})")
        
        return high_risk_df
    
    def get_churn_insights(self) -> Dict[str, Any]:
        """
        Generate business insights dari model
        
        Returns:
            Dictionary dengan insights
        """
        top_factors = list(self.feature_importances.items())[:5]
        
        insights = {
            "top_risk_factors": [
                {"feature": f, "importance": round(imp, 4)}
                for f, imp in top_factors
            ],
            "model_performance": {
                "accuracy": self.metrics.get("accuracy", 0),
                "f1_score": self.metrics.get("f1_score", 0),
                "roc_auc": self.metrics.get("roc_auc", 0)
            },
            "recommendations": {
                "high_risk": [
                    "Immediate intervention dengan personal outreach",
                    "Offer special retention discounts",
                    "Schedule account review meeting"
                ],
                "medium_risk": [
                    "Proactive engagement via email campaigns",
                    "Survey untuk understand satisfaction",
                    "Offer loyalty program enrollment"
                ],
                "low_risk": [
                    "Maintain regular communication",
                    "Cross-sell opportunities",
                    "Referral program invitation"
                ]
            },
            "interpretation": self._interpret_feature_importances()
        }
        
        return insights
    
    def _interpret_feature_importances(self) -> List[str]:
        """Generate natural language interpretations"""
        interpretations = []
        
        for feature, importance in list(self.feature_importances.items())[:3]:
            if importance > 0.2:
                interpretations.append(
                    f"{feature} adalah prediktor SANGAT KUAT untuk churn (importance: {importance:.2%})"
                )
            elif importance > 0.1:
                interpretations.append(
                    f"{feature} adalah prediktor KUAT untuk churn (importance: {importance:.2%})"
                )
            else:
                interpretations.append(
                    f"{feature} berkontribusi pada prediksi churn (importance: {importance:.2%})"
                )
        
        return interpretations
    
    def get_classification_report(
        self,
        X_test: pd.DataFrame,
        y_test: pd.Series
    ) -> str:
        """Get sklearn classification report"""
        y_pred = self.predict(X_test)
        return classification_report(
            y_test, y_pred,
            target_names=["Not Churned", "Churned"]
        )
    
    def get_roc_curve_data(
        self,
        X_test: pd.DataFrame,
        y_test: pd.Series
    ) -> Dict[str, np.ndarray]:
        """Get data untuk ROC curve plot"""
        y_proba = self.predict_proba(X_test)
        fpr, tpr, thresholds = roc_curve(y_test, y_proba)
        
        return {
            "fpr": fpr,
            "tpr": tpr,
            "thresholds": thresholds,
            "auc": roc_auc_score(y_test, y_proba)
        }
    
    def save(self, filepath: str):
        """Save model ke file"""
        save_data = {
            "model": self.model,
            "config": self.config,
            "feature_names": self.feature_names,
            "feature_importances": self.feature_importances,
            "metrics": self.metrics,
            "threshold": self.threshold,
            "is_fitted": self.is_fitted,
            "is_single_class": self.is_single_class
        }
        
        joblib.dump(save_data, filepath)
        
        if self.verbose:
            print(f"[ChurnClassifier] Model saved to {filepath}")
    
    @classmethod
    def load(cls, filepath: str) -> "ChurnClassifier":
        """Load model dari file"""
        save_data = joblib.load(filepath)
        
        instance = cls(config=save_data["config"], verbose=False)
        instance.model = save_data["model"]
        instance.feature_names = save_data["feature_names"]
        instance.feature_importances = save_data["feature_importances"]
        instance.metrics = save_data["metrics"]
        instance.threshold = save_data["threshold"]
        instance.is_fitted = save_data["is_fitted"]
        instance.is_single_class = save_data["is_single_class"]
        
        return instance
