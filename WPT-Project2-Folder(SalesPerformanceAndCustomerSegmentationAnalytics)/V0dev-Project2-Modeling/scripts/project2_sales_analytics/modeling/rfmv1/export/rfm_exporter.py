"""
RFM Exporter Module

Module untuk export hasil RFM modeling ke berbagai format:
- CSV untuk data tabular
- PKL untuk models dan objects
- JSON untuk metadata dan configurations
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from pathlib import Path
import joblib
import json
from datetime import datetime


class RFMExporter:
    """
    Exporter untuk RFM modeling results
    
    Exports:
    - Customer clusters with labels
    - Churn predictions with probabilities
    - CLV predictions with segments
    - Models untuk deployment
    - Metadata dan configurations
    """
    
    def __init__(self, output_path: str, verbose: bool = True):
        """
        Initialize exporter
        
        Args:
            output_path: Base directory untuk output
            verbose: Print progress messages
        """
        self.output_path = Path(output_path)
        self.verbose = verbose
        self.export_history: List[Dict] = []
        
        # Create output directories
        self._create_directories()
    
    def _create_directories(self):
        """Create output directory structure"""
        subdirs = ["csv", "pkl", "json", "models", "visualizations", "reports"]
        
        for subdir in subdirs:
            (self.output_path / subdir).mkdir(parents=True, exist_ok=True)
        
        if self.verbose:
            print(f"[RFMExporter] Output directories created at {self.output_path}")
    
    def export_clustering_results(
        self,
        customer_ids: pd.Series,
        labels: np.ndarray,
        cluster_labels: Dict[int, str],
        cluster_profiles: pd.DataFrame,
        features: pd.DataFrame,
        model: Any,
        metrics: Dict[str, float]
    ) -> Dict[str, str]:
        """
        Export clustering results
        
        Returns:
            Dictionary dengan paths ke exported files
        """
        exports = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. Customer cluster assignments (CSV)
        cluster_df = pd.DataFrame({
            "customer_id": customer_ids,
            "cluster_id": labels,
            "cluster_label": [cluster_labels.get(l, f"Cluster {l}") for l in labels]
        })
        
        # Add original features
        cluster_df = pd.concat([cluster_df.reset_index(drop=True), features.reset_index(drop=True)], axis=1)
        
        csv_path = self.output_path / "csv" / "customer_clusters.csv"
        cluster_df.to_csv(csv_path, index=False)
        exports["customer_clusters_csv"] = str(csv_path)
        
        # 2. Cluster profiles (CSV)
        profiles_path = self.output_path / "csv" / "cluster_profiles.csv"
        cluster_profiles.to_csv(profiles_path, index=False)
        exports["cluster_profiles_csv"] = str(profiles_path)
        
        # 3. Model (PKL)
        model_path = self.output_path / "models" / "clustering_model.pkl"
        joblib.dump(model, model_path)
        exports["clustering_model_pkl"] = str(model_path)
        
        # 4. Metadata (JSON)
        metadata = {
            "export_timestamp": timestamp,
            "n_customers": len(customer_ids),
            "n_clusters": len(cluster_labels),
            "cluster_labels": cluster_labels,
            "metrics": metrics,
            "cluster_distribution": {
                cluster_labels.get(k, f"Cluster {k}"): int(v) 
                for k, v in zip(*np.unique(labels, return_counts=True))
            }
        }
        
        json_path = self.output_path / "json" / "clustering_metadata.json"
        with open(json_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        exports["clustering_metadata_json"] = str(json_path)
        
        # 5. Streamlit-ready package (PKL)
        streamlit_data = {
            "customer_clusters": cluster_df,
            "cluster_profiles": cluster_profiles,
            "cluster_labels": cluster_labels,
            "metrics": metrics,
            "features_used": list(features.columns)
        }
        
        streamlit_path = self.output_path / "pkl" / "clustering_streamlit_data.pkl"
        joblib.dump(streamlit_data, streamlit_path)
        exports["clustering_streamlit_pkl"] = str(streamlit_path)
        
        self._log_export("clustering", exports)
        
        if self.verbose:
            print(f"[RFMExporter] Clustering results exported:")
            for key, path in exports.items():
                print(f"  - {key}: {path}")
        
        return exports
    
    def export_churn_results(
        self,
        customer_ids: pd.Series,
        predictions: np.ndarray,
        probabilities: np.ndarray,
        features: pd.DataFrame,
        model: Any,
        metrics: Dict[str, float],
        feature_importances: Dict[str, float]
    ) -> Dict[str, str]:
        """
        Export churn prediction results
        """
        exports = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. Churn predictions (CSV)
        churn_df = pd.DataFrame({
            "customer_id": customer_ids,
            "churn_prediction": predictions,
            "churn_probability": probabilities,
            "risk_level": pd.cut(
                probabilities,
                bins=[0, 0.3, 0.5, 0.7, 1.0],
                labels=["Low", "Medium", "High", "Critical"]
            )
        })
        
        csv_path = self.output_path / "csv" / "churn_predictions.csv"
        churn_df.to_csv(csv_path, index=False)
        exports["churn_predictions_csv"] = str(csv_path)
        
        # 2. High-risk customers (CSV)
        high_risk_df = churn_df[churn_df["churn_probability"] >= 0.5].sort_values(
            "churn_probability", ascending=False
        )
        
        high_risk_path = self.output_path / "csv" / "high_risk_customers.csv"
        high_risk_df.to_csv(high_risk_path, index=False)
        exports["high_risk_customers_csv"] = str(high_risk_path)
        
        # 3. Feature importances (CSV)
        importance_df = pd.DataFrame([
            {"feature": k, "importance": v}
            for k, v in feature_importances.items()
        ]).sort_values("importance", ascending=False)
        
        importance_path = self.output_path / "csv" / "churn_feature_importances.csv"
        importance_df.to_csv(importance_path, index=False)
        exports["churn_feature_importances_csv"] = str(importance_path)
        
        # 4. Model (PKL)
        model_path = self.output_path / "models" / "churn_classifier.pkl"
        joblib.dump(model, model_path)
        exports["churn_model_pkl"] = str(model_path)
        
        # 5. Metadata (JSON)
        metadata = {
            "export_timestamp": timestamp,
            "n_customers": len(customer_ids),
            "n_churned": int(predictions.sum()),
            "churn_rate": float(predictions.mean()),
            "high_risk_count": len(high_risk_df),
            "metrics": metrics,
            "top_features": dict(list(feature_importances.items())[:10])
        }
        
        json_path = self.output_path / "json" / "churn_metadata.json"
        with open(json_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        exports["churn_metadata_json"] = str(json_path)
        
        # 6. Streamlit-ready package (PKL)
        streamlit_data = {
            "churn_predictions": churn_df,
            "high_risk_customers": high_risk_df,
            "feature_importances": feature_importances,
            "metrics": metrics,
            "threshold": 0.5
        }
        
        streamlit_path = self.output_path / "pkl" / "churn_streamlit_data.pkl"
        joblib.dump(streamlit_data, streamlit_path)
        exports["churn_streamlit_pkl"] = str(streamlit_path)
        
        self._log_export("churn", exports)
        
        if self.verbose:
            print(f"[RFMExporter] Churn results exported:")
            for key, path in exports.items():
                print(f"  - {key}: {path}")
        
        return exports
    
    def export_clv_results(
        self,
        customer_ids: pd.Series,
        predictions: np.ndarray,
        segments: pd.Series,
        features: pd.DataFrame,
        model: Any,
        metrics: Dict[str, float],
        feature_importances: Dict[str, float],
        distribution_analysis: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Export CLV prediction results
        """
        exports = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. CLV predictions (CSV)
        clv_df = pd.DataFrame({
            "customer_id": customer_ids,
            "predicted_clv": predictions,
            "clv_segment": segments,
            "clv_percentile": pd.Series(predictions).rank(pct=True) * 100
        })
        
        csv_path = self.output_path / "csv" / "clv_predictions.csv"
        clv_df.to_csv(csv_path, index=False)
        exports["clv_predictions_csv"] = str(csv_path)
        
        # 2. Top customers (CSV)
        top_customers = clv_df.nlargest(100, "predicted_clv")
        top_path = self.output_path / "csv" / "top_clv_customers.csv"
        top_customers.to_csv(top_path, index=False)
        exports["top_clv_customers_csv"] = str(top_path)
        
        # 3. Segment summary (CSV)
        segment_summary = clv_df.groupby("clv_segment").agg({
            "customer_id": "count",
            "predicted_clv": ["sum", "mean", "median"]
        }).round(2)
        segment_summary.columns = ["customer_count", "total_clv", "avg_clv", "median_clv"]
        
        segment_path = self.output_path / "csv" / "clv_segment_summary.csv"
        segment_summary.to_csv(segment_path)
        exports["clv_segment_summary_csv"] = str(segment_path)
        
        # 4. Feature importances (CSV)
        importance_df = pd.DataFrame([
            {"feature": k, "importance": v}
            for k, v in feature_importances.items()
        ]).sort_values("importance", ascending=False)
        
        importance_path = self.output_path / "csv" / "clv_feature_importances.csv"
        importance_df.to_csv(importance_path, index=False)
        exports["clv_feature_importances_csv"] = str(importance_path)
        
        # 5. Model (PKL)
        model_path = self.output_path / "models" / "clv_regressor.pkl"
        joblib.dump(model, model_path)
        exports["clv_model_pkl"] = str(model_path)
        
        # 6. Metadata (JSON)
        metadata = {
            "export_timestamp": timestamp,
            "n_customers": len(customer_ids),
            "total_predicted_clv": float(predictions.sum()),
            "avg_clv": float(predictions.mean()),
            "median_clv": float(np.median(predictions)),
            "metrics": metrics,
            "distribution": {
                "min": float(predictions.min()),
                "max": float(predictions.max()),
                "std": float(predictions.std())
            },
            "pareto_analysis": distribution_analysis.get("pareto", {}),
            "top_features": dict(list(feature_importances.items())[:10])
        }
        
        json_path = self.output_path / "json" / "clv_metadata.json"
        with open(json_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        exports["clv_metadata_json"] = str(json_path)
        
        # 7. Streamlit-ready package (PKL)
        streamlit_data = {
            "clv_predictions": clv_df,
            "segment_summary": segment_summary,
            "top_customers": top_customers,
            "feature_importances": feature_importances,
            "metrics": metrics,
            "distribution_analysis": distribution_analysis
        }
        
        streamlit_path = self.output_path / "pkl" / "clv_streamlit_data.pkl"
        joblib.dump(streamlit_data, streamlit_path)
        exports["clv_streamlit_pkl"] = str(streamlit_path)
        
        self._log_export("clv", exports)
        
        if self.verbose:
            print(f"[RFMExporter] CLV results exported:")
            for key, path in exports.items():
                print(f"  - {key}: {path}")
        
        return exports
    
    def export_master_customer_data(
        self,
        cluster_df: pd.DataFrame,
        churn_df: pd.DataFrame,
        clv_df: pd.DataFrame
    ) -> str:
        """
        Export master customer data dengan semua predictions
        """
        # Merge all predictions
        master_df = cluster_df.merge(
            churn_df[["customer_id", "churn_prediction", "churn_probability", "risk_level"]],
            on="customer_id",
            how="left"
        ).merge(
            clv_df[["customer_id", "predicted_clv", "clv_segment", "clv_percentile"]],
            on="customer_id",
            how="left"
        )
        
        csv_path = self.output_path / "csv" / "master_customer_analytics.csv"
        master_df.to_csv(csv_path, index=False)
        
        # Also save as PKL untuk Streamlit
        pkl_path = self.output_path / "pkl" / "master_customer_analytics.pkl"
        joblib.dump(master_df, pkl_path)
        
        if self.verbose:
            print(f"[RFMExporter] Master customer data exported:")
            print(f"  - CSV: {csv_path}")
            print(f"  - PKL: {pkl_path}")
        
        return str(csv_path)
    
    def export_insights_report(self, executive_summary: str) -> str:
        """
        Export executive summary report
        """
        report_path = self.output_path / "reports" / "rfm_modeling_report.txt"
        
        with open(report_path, 'w') as f:
            f.write(executive_summary)
        
        if self.verbose:
            print(f"[RFMExporter] Report exported: {report_path}")
        
        return str(report_path)
    
    def _log_export(self, export_type: str, paths: Dict[str, str]):
        """Log export untuk tracking"""
        self.export_history.append({
            "type": export_type,
            "timestamp": datetime.now().isoformat(),
            "files": paths
        })
    
    def get_export_summary(self) -> Dict[str, Any]:
        """Get summary dari semua exports"""
        return {
            "output_path": str(self.output_path),
            "total_exports": len(self.export_history),
            "export_history": self.export_history
        }
