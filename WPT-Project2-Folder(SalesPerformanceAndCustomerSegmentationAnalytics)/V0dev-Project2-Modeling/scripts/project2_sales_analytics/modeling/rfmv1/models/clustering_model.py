"""
Customer Clustering Model

Module untuk customer clustering menggunakan K-Means atau DBSCAN
dengan output 3 kategori: High Value, Medium Value, Low Value.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from sklearn.cluster import KMeans, DBSCAN
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
import joblib
from pathlib import Path

from config.rfm_config import ClusteringConfig
from preprocessing.data_scaler import DataScaler

try:
    from ..utils.helpers import print_section_header, print_subsection_header
except ImportError:
    # Fallback jika import gagal
    def print_section_header(title: str, width: int = 60):
        print("\n" + "=" * width)
        print(f" {title}")
        print("=" * width)
    
    def print_subsection_header(title: str, width: int = 50):
        print("\n" + "-" * width)
        print(f" {title}")
        print("-" * width)


class CustomerClusteringModel:
    """
    Customer Clustering dengan K-Means / DBSCAN
    
    Output: 3 cluster yang di-label sebagai:
    - High Value: Customers dengan monetary dan frequency tinggi
    - Medium Value: Customers dengan nilai moderate
    - Low Value: Customers dengan nilai rendah
    """
    
    def __init__(self, config: ClusteringConfig, verbose: bool = True):
        """
        Initialize clustering model
        
        Args:
            config: ClusteringConfig dengan parameters
            verbose: Print progress messages
        """
        self.config = config
        self.verbose = verbose
        self.model = None
        self.scaler = DataScaler(scaler_type="standard", verbose=False)
        self.is_fitted = False
        self.cluster_labels: Dict[int, str] = {}
        self.cluster_centers: Optional[np.ndarray] = None
        self.metrics: Dict[str, float] = {}
        self.feature_names: List[str] = []
        
    def _create_model(self):
        """Create clustering model based on config"""
        if self.config.algorithm == "kmeans":
            self.model = KMeans(
                n_clusters=self.config.n_clusters,
                random_state=self.config.random_state,
                max_iter=self.config.max_iter,
                n_init=self.config.n_init
            )
        elif self.config.algorithm == "dbscan":
            self.model = DBSCAN(
                eps=self.config.eps,
                min_samples=self.config.min_samples
            )
        else:
            raise ValueError(f"Unknown algorithm: {self.config.algorithm}")
        
        if self.verbose:
            print(f"[ClusteringModel] Created {self.config.algorithm.upper()} model with {self.config.n_clusters} clusters")
    
    def fit(self, X: pd.DataFrame) -> "CustomerClusteringModel":
        """
        Fit clustering model
        
        Args:
            X: DataFrame dengan features untuk clustering
            
        Returns:
            self untuk chaining
        """
        self._create_model()
        self.feature_names = list(X.columns)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        if self.verbose:
            print(f"[ClusteringModel] Fitting on {len(X)} samples with {len(self.feature_names)} features")
        
        # Fit model
        self.model.fit(X_scaled)
        
        # Store cluster centers untuk K-Means
        if self.config.algorithm == "kmeans":
            self.cluster_centers = self.model.cluster_centers_
        
        self.is_fitted = True
        
        return self
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict cluster labels
        
        Args:
            X: DataFrame dengan features
            
        Returns:
            Array of cluster labels
        """
        if not self.is_fitted:
            raise ValueError("Model belum di-fit. Panggil fit() terlebih dahulu.")
        
        X_scaled = self.scaler.transform(X)
        
        if self.config.algorithm == "kmeans":
            labels = self.model.predict(X_scaled)
        else:
            # DBSCAN tidak punya predict, gunakan fit_predict
            labels = self.model.fit_predict(X_scaled)
        
        return labels
    
    def fit_predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Fit model dan predict dalam satu langkah
        
        Args:
            X: DataFrame dengan features
            
        Returns:
            Array of cluster labels
        """
        self.fit(X)
        X_scaled = self.scaler.transform(X)
        labels = self.model.labels_
        
        return labels
    
    def evaluate(self, X: pd.DataFrame, labels: np.ndarray) -> Dict[str, float]:
        """
        Evaluate clustering quality
        
        Args:
            X: Original features DataFrame
            labels: Cluster labels
            
        Returns:
            Dictionary dengan metrics
        """
        X_scaled = self.scaler.transform(X)
        
        # Hanya hitung jika ada lebih dari 1 cluster
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        
        if n_clusters < 2:
            self.metrics = {"error": "Less than 2 clusters found"}
            return self.metrics
        
        self.metrics = {
            "n_clusters": n_clusters,
            "silhouette_score": silhouette_score(X_scaled, labels),
            "calinski_harabasz_score": calinski_harabasz_score(X_scaled, labels),
            "davies_bouldin_score": davies_bouldin_score(X_scaled, labels),
            "inertia": self.model.inertia_ if self.config.algorithm == "kmeans" else None
        }
        
        if self.verbose:
            print_subsection_header("Clustering Metrics")
            print(f"  Silhouette Score: {self.metrics['silhouette_score']:.4f}")
            print(f"  Calinski-Harabasz Score: {self.metrics['calinski_harabasz_score']:.2f}")
            print(f"  Davies-Bouldin Score: {self.metrics['davies_bouldin_score']:.4f}")
        
        return self.metrics
    
    def assign_cluster_labels(
        self,
        X: pd.DataFrame,
        labels: np.ndarray,
        sort_by: str = "monetary"
    ) -> Dict[int, str]:
        """
        Assign meaningful labels ke clusters berdasarkan karakteristik
        
        Clusters akan di-sort berdasarkan nilai feature tertentu dan
        di-label sebagai High/Medium/Low Value.
        
        Args:
            X: Original features DataFrame
            labels: Cluster labels
            sort_by: Feature untuk sorting (default: monetary)
            
        Returns:
            Dictionary mapping cluster_id ke label name
        """
        # Calculate cluster statistics
        df = X.copy()
        df["cluster"] = labels
        
        cluster_stats = df.groupby("cluster").agg({
            col: ["mean", "median", "count"] for col in X.columns
        })
        
        # Flatten column names
        cluster_stats.columns = ['_'.join(col).strip() for col in cluster_stats.columns.values]
        
        # Sort by monetary mean (descending)
        sort_col = f"{sort_by}_mean" if f"{sort_by}_mean" in cluster_stats.columns else cluster_stats.columns[0]
        cluster_stats = cluster_stats.sort_values(sort_col, ascending=False)
        
        # Assign labels based on ranking
        label_names = ["High Value", "Medium Value", "Low Value"]
        
        self.cluster_labels = {}
        for i, cluster_id in enumerate(cluster_stats.index):
            if i < len(label_names):
                self.cluster_labels[cluster_id] = label_names[i]
            else:
                self.cluster_labels[cluster_id] = f"Cluster {cluster_id}"
        
        if self.verbose:
            print_subsection_header("Cluster Label Assignment")
            for cluster_id, label in self.cluster_labels.items():
                count = cluster_stats.loc[cluster_id, f"{sort_by}_count"] if f"{sort_by}_count" in cluster_stats.columns else "N/A"
                print(f"  Cluster {cluster_id} -> {label} (n={count})")
        
        return self.cluster_labels
    
    def get_cluster_profiles(
        self,
        X: pd.DataFrame,
        labels: np.ndarray
    ) -> pd.DataFrame:
        """
        Generate detailed profile untuk setiap cluster
        
        Args:
            X: Original features DataFrame
            labels: Cluster labels
            
        Returns:
            DataFrame dengan cluster profiles
        """
        df = X.copy()
        df["cluster"] = labels
        df["cluster_label"] = df["cluster"].map(self.cluster_labels)
        
        profiles = []
        
        for cluster_id in sorted(df["cluster"].unique()):
            cluster_data = df[df["cluster"] == cluster_id]
            
            profile = {
                "cluster_id": cluster_id,
                "cluster_label": self.cluster_labels.get(cluster_id, f"Cluster {cluster_id}"),
                "customer_count": len(cluster_data),
                "customer_pct": len(cluster_data) / len(df) * 100
            }
            
            # Add mean statistics untuk setiap feature
            for col in X.columns:
                profile[f"{col}_mean"] = cluster_data[col].mean()
                profile[f"{col}_std"] = cluster_data[col].std()
                profile[f"{col}_min"] = cluster_data[col].min()
                profile[f"{col}_max"] = cluster_data[col].max()
            
            profiles.append(profile)
        
        profiles_df = pd.DataFrame(profiles)
        
        return profiles_df
    
    def find_optimal_k(
        self,
        X: pd.DataFrame,
        k_range: range = range(2, 11)
    ) -> Dict[str, Any]:
        """
        Find optimal number of clusters menggunakan Elbow Method dan Silhouette
        
        Args:
            X: Features DataFrame
            k_range: Range of k values to test
            
        Returns:
            Dictionary dengan results untuk setiap k
        """
        if self.verbose:
            print_section_header("Finding Optimal K")
        
        X_scaled = self.scaler.fit_transform(X)
        
        results = {
            "k_values": [],
            "inertia": [],
            "silhouette": [],
            "calinski_harabasz": [],
            "davies_bouldin": []
        }
        
        for k in k_range:
            kmeans = KMeans(
                n_clusters=k,
                random_state=self.config.random_state,
                n_init=self.config.n_init
            )
            labels = kmeans.fit_predict(X_scaled)
            
            results["k_values"].append(k)
            results["inertia"].append(kmeans.inertia_)
            results["silhouette"].append(silhouette_score(X_scaled, labels))
            results["calinski_harabasz"].append(calinski_harabasz_score(X_scaled, labels))
            results["davies_bouldin"].append(davies_bouldin_score(X_scaled, labels))
            
            if self.verbose:
                print(f"  k={k}: Silhouette={results['silhouette'][-1]:.4f}, Inertia={results['inertia'][-1]:.2f}")
        
        # Find optimal k (highest silhouette score)
        optimal_idx = np.argmax(results["silhouette"])
        results["optimal_k"] = results["k_values"][optimal_idx]
        results["optimal_silhouette"] = results["silhouette"][optimal_idx]
        
        if self.verbose:
            print(f"\n  Optimal K: {results['optimal_k']} (Silhouette: {results['optimal_silhouette']:.4f})")
        
        return results
    
    def get_cluster_recommendations(self) -> Dict[str, Dict]:
        """
        Generate business recommendations untuk setiap cluster
        
        Returns:
            Dictionary dengan recommendations per cluster
        """
        recommendations = {
            "High Value": {
                "description": "Customers dengan nilai transaksi dan frekuensi tinggi",
                "strategy": "Retention & VIP Treatment",
                "actions": [
                    "Program loyalty eksklusif",
                    "Personal account manager",
                    "Early access ke produk baru",
                    "Diskon khusus untuk pembelian bulk"
                ],
                "priority": "HIGHEST",
                "expected_revenue_impact": "60-70% of total revenue"
            },
            "Medium Value": {
                "description": "Customers dengan potensi growth",
                "strategy": "Growth & Upselling",
                "actions": [
                    "Cross-selling produk complementary",
                    "Bundling offers",
                    "Program referral",
                    "Email marketing targeted"
                ],
                "priority": "HIGH",
                "expected_revenue_impact": "20-30% of total revenue"
            },
            "Low Value": {
                "description": "Customers dengan engagement rendah",
                "strategy": "Re-engagement & Cost Optimization",
                "actions": [
                    "Win-back campaigns",
                    "Survey untuk feedback",
                    "Promo first-time buyer",
                    "Reduce service cost"
                ],
                "priority": "MEDIUM",
                "expected_revenue_impact": "5-10% of total revenue"
            }
        }
        
        return recommendations
    
    def save(self, filepath: str):
        """Save model ke file"""
        save_data = {
            "model": self.model,
            "scaler": self.scaler,
            "config": self.config,
            "cluster_labels": self.cluster_labels,
            "cluster_centers": self.cluster_centers,
            "metrics": self.metrics,
            "feature_names": self.feature_names,
            "is_fitted": self.is_fitted
        }
        
        joblib.dump(save_data, filepath)
        
        if self.verbose:
            print(f"[ClusteringModel] Model saved to {filepath}")
    
    @classmethod
    def load(cls, filepath: str) -> "CustomerClusteringModel":
        """Load model dari file"""
        save_data = joblib.load(filepath)
        
        instance = cls(config=save_data["config"], verbose=False)
        instance.model = save_data["model"]
        instance.scaler = save_data["scaler"]
        instance.cluster_labels = save_data["cluster_labels"]
        instance.cluster_centers = save_data["cluster_centers"]
        instance.metrics = save_data["metrics"]
        instance.feature_names = save_data["feature_names"]
        instance.is_fitted = save_data["is_fitted"]
        
        return instance
