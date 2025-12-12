"""
RFM Visualization Module

Module untuk visualisasi hasil RFM Modeling:
- Clustering visualizations
- Churn prediction visualizations
- CLV analysis visualizations
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.patches import Patch
import warnings

warnings.filterwarnings('ignore')


class RFMVisualizer:
    """
    Comprehensive visualizer untuk RFM Modeling results
    
    Generates:
    - Cluster scatter plots dan profiles
    - Churn prediction ROC curves dan confusion matrices
    - CLV distribution dan segment analysis
    - Feature importance charts
    """
    
    def __init__(
        self,
        figsize: Tuple[int, int] = (12, 8),
        style: str = "whitegrid",
        palette: str = "husl",
        save_path: Optional[str] = None,
        verbose: bool = True
    ):
        """
        Initialize visualizer
        
        Args:
            figsize: Default figure size
            style: Seaborn style
            palette: Color palette
            save_path: Directory untuk save figures
            verbose: Print progress messages
        """
        self.figsize = figsize
        self.style = style
        self.palette = palette
        self.save_path = Path(save_path) if save_path else None
        self.verbose = verbose
        
        # Set style
        sns.set_style(style)
        plt.rcParams['figure.figsize'] = figsize
        plt.rcParams['font.size'] = 10
        
        # Color maps untuk segments
        self.cluster_colors = {
            "High Value": "#2ecc71",    # Green
            "Medium Value": "#f39c12",  # Orange
            "Low Value": "#e74c3c"      # Red
        }
        
        self.clv_colors = {
            "Platinum": "#9b59b6",  # Purple
            "Gold": "#f1c40f",      # Gold
            "Silver": "#95a5a6",    # Silver
            "Bronze": "#d35400"     # Bronze
        }
        
        self.churn_colors = {
            "High": "#e74c3c",      # Red
            "Medium": "#f39c12",    # Orange
            "Low": "#2ecc71"        # Green
        }
    
    def _save_figure(self, filename: str):
        """Save figure jika save_path di-set"""
        if self.save_path:
            self.save_path.mkdir(parents=True, exist_ok=True)
            filepath = self.save_path / filename
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            if self.verbose:
                print(f"[Visualizer] Saved: {filepath}")
    
    # ==================== CLUSTERING VISUALIZATIONS ====================
    
    def plot_cluster_scatter_2d(
        self,
        X: pd.DataFrame,
        labels: np.ndarray,
        cluster_labels: Dict[int, str],
        x_col: str = "recency",
        y_col: str = "monetary",
        title: str = "Customer Clusters"
    ) -> plt.Figure:
        """
        Plot 2D scatter plot untuk clusters
        
        Args:
            X: Features DataFrame
            labels: Cluster labels
            cluster_labels: Mapping cluster_id ke label name
            x_col, y_col: Columns untuk x dan y axis
            title: Plot title
        """
        fig, ax = plt.subplots(figsize=self.figsize)
        
        df = X.copy()
        df["cluster"] = labels
        df["cluster_name"] = df["cluster"].map(cluster_labels)
        
        for cluster_name in cluster_labels.values():
            mask = df["cluster_name"] == cluster_name
            color = self.cluster_colors.get(cluster_name, "#3498db")
            ax.scatter(
                df.loc[mask, x_col],
                df.loc[mask, y_col],
                c=color,
                label=cluster_name,
                alpha=0.6,
                s=50
            )
        
        ax.set_xlabel(x_col.replace("_", " ").title())
        ax.set_ylabel(y_col.replace("_", " ").title())
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.legend(title="Cluster")
        
        plt.tight_layout()
        self._save_figure("cluster_scatter_2d.png")
        
        return fig
    
    def plot_cluster_scatter_3d(
        self,
        X: pd.DataFrame,
        labels: np.ndarray,
        cluster_labels: Dict[int, str],
        title: str = "3D Customer Clusters (R-F-M)"
    ) -> plt.Figure:
        """
        Plot 3D scatter plot untuk RFM clusters
        """
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111, projection='3d')
        
        df = X.copy()
        df["cluster"] = labels
        df["cluster_name"] = df["cluster"].map(cluster_labels)
        
        for cluster_name in cluster_labels.values():
            mask = df["cluster_name"] == cluster_name
            color = self.cluster_colors.get(cluster_name, "#3498db")
            
            ax.scatter(
                df.loc[mask, "recency"],
                df.loc[mask, "frequency"],
                df.loc[mask, "monetary"],
                c=color,
                label=cluster_name,
                alpha=0.6,
                s=50
            )
        
        ax.set_xlabel("Recency")
        ax.set_ylabel("Frequency")
        ax.set_zlabel("Monetary")
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.legend(title="Cluster")
        
        self._save_figure("cluster_scatter_3d.png")
        
        return fig
    
    def plot_cluster_profiles(
        self,
        cluster_profiles: pd.DataFrame,
        features: List[str] = None,
        title: str = "Cluster Profiles"
    ) -> plt.Figure:
        """
        Plot radar chart untuk cluster profiles
        """
        if features is None:
            features = ["recency", "frequency", "monetary"]
        
        # Filter features yang ada
        mean_cols = [f"{f}_mean" for f in features if f"{f}_mean" in cluster_profiles.columns]
        
        fig, ax = plt.subplots(figsize=self.figsize)
        
        x = np.arange(len(mean_cols))
        width = 0.25
        
        for i, (_, row) in enumerate(cluster_profiles.iterrows()):
            label = row.get("cluster_label", f"Cluster {i}")
            values = [row[col] for col in mean_cols]
            color = self.cluster_colors.get(label, f"C{i}")
            ax.bar(x + i*width, values, width, label=label, color=color, alpha=0.8)
        
        ax.set_xlabel("Features")
        ax.set_ylabel("Mean Value")
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xticks(x + width)
        ax.set_xticklabels([col.replace("_mean", "").title() for col in mean_cols], rotation=45)
        ax.legend()
        
        plt.tight_layout()
        self._save_figure("cluster_profiles.png")
        
        return fig
    
    def plot_cluster_distribution(
        self,
        labels: np.ndarray,
        cluster_labels: Dict[int, str],
        title: str = "Customer Distribution by Cluster"
    ) -> plt.Figure:
        """
        Plot pie chart untuk distribusi cluster
        """
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        
        # Count per cluster
        unique, counts = np.unique(labels, return_counts=True)
        cluster_names = [cluster_labels.get(u, f"Cluster {u}") for u in unique]
        colors = [self.cluster_colors.get(name, "#3498db") for name in cluster_names]
        
        # Pie chart
        axes[0].pie(
            counts, labels=cluster_names, autopct='%1.1f%%',
            colors=colors, startangle=90
        )
        axes[0].set_title("Distribution (%)", fontsize=12, fontweight='bold')
        
        # Bar chart
        axes[1].bar(cluster_names, counts, color=colors)
        axes[1].set_xlabel("Cluster")
        axes[1].set_ylabel("Number of Customers")
        axes[1].set_title("Distribution (Count)", fontsize=12, fontweight='bold')
        
        for i, (name, count) in enumerate(zip(cluster_names, counts)):
            axes[1].annotate(f'{count}', xy=(i, count), ha='center', va='bottom')
        
        plt.suptitle(title, fontsize=14, fontweight='bold')
        plt.tight_layout()
        self._save_figure("cluster_distribution.png")
        
        return fig
    
    def plot_elbow_curve(
        self,
        k_values: List[int],
        inertias: List[float],
        silhouettes: List[float],
        optimal_k: int,
        title: str = "Elbow Method & Silhouette Score"
    ) -> plt.Figure:
        """
        Plot elbow curve dan silhouette score
        """
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        
        # Elbow curve (Inertia)
        axes[0].plot(k_values, inertias, 'bo-', linewidth=2, markersize=8)
        axes[0].axvline(x=optimal_k, color='r', linestyle='--', label=f'Optimal K={optimal_k}')
        axes[0].set_xlabel("Number of Clusters (K)")
        axes[0].set_ylabel("Inertia (Within-cluster sum of squares)")
        axes[0].set_title("Elbow Method", fontsize=12, fontweight='bold')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # Silhouette score
        axes[1].plot(k_values, silhouettes, 'go-', linewidth=2, markersize=8)
        axes[1].axvline(x=optimal_k, color='r', linestyle='--', label=f'Optimal K={optimal_k}')
        axes[1].set_xlabel("Number of Clusters (K)")
        axes[1].set_ylabel("Silhouette Score")
        axes[1].set_title("Silhouette Analysis", fontsize=12, fontweight='bold')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        
        plt.suptitle(title, fontsize=14, fontweight='bold')
        plt.tight_layout()
        self._save_figure("elbow_silhouette.png")
        
        return fig
    
    # ==================== CHURN VISUALIZATIONS ====================
    
    def plot_confusion_matrix(
        self,
        confusion_matrix: np.ndarray,
        title: str = "Churn Prediction - Confusion Matrix"
    ) -> plt.Figure:
        """
        Plot confusion matrix heatmap
        """
        fig, ax = plt.subplots(figsize=(8, 6))
        
        sns.heatmap(
            confusion_matrix,
            annot=True,
            fmt='d',
            cmap='Blues',
            xticklabels=['Not Churned', 'Churned'],
            yticklabels=['Not Churned', 'Churned'],
            ax=ax
        )
        
        ax.set_xlabel("Predicted")
        ax.set_ylabel("Actual")
        ax.set_title(title, fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        self._save_figure("confusion_matrix.png")
        
        return fig
    
    def plot_roc_curve(
        self,
        fpr: np.ndarray,
        tpr: np.ndarray,
        auc_score: float,
        title: str = "Churn Prediction - ROC Curve"
    ) -> plt.Figure:
        """
        Plot ROC curve
        """
        fig, ax = plt.subplots(figsize=(8, 6))
        
        ax.plot(fpr, tpr, 'b-', linewidth=2, label=f'ROC Curve (AUC = {auc_score:.4f})')
        ax.plot([0, 1], [0, 1], 'r--', linewidth=1, label='Random Classifier')
        
        ax.fill_between(fpr, tpr, alpha=0.2)
        
        ax.set_xlabel("False Positive Rate")
        ax.set_ylabel("True Positive Rate")
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.legend(loc='lower right')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        self._save_figure("roc_curve.png")
        
        return fig
    
    def plot_feature_importance(
        self,
        feature_importances: Dict[str, float],
        top_n: int = 10,
        title: str = "Feature Importance"
    ) -> plt.Figure:
        """
        Plot horizontal bar chart untuk feature importance
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Sort dan ambil top N
        sorted_features = dict(sorted(feature_importances.items(), key=lambda x: x[1], reverse=True)[:top_n])
        
        features = list(sorted_features.keys())
        importances = list(sorted_features.values())
        
        colors = plt.cm.RdYlGn(np.linspace(0.2, 0.8, len(features)))[::-1]
        
        ax.barh(features[::-1], importances[::-1], color=colors)
        ax.set_xlabel("Importance")
        ax.set_title(title, fontsize=14, fontweight='bold')
        
        # Add value labels
        for i, (feat, imp) in enumerate(zip(features[::-1], importances[::-1])):
            ax.annotate(f'{imp:.4f}', xy=(imp, i), ha='left', va='center', fontsize=9)
        
        plt.tight_layout()
        self._save_figure("feature_importance.png")
        
        return fig
    
    def plot_churn_risk_distribution(
        self,
        probabilities: np.ndarray,
        threshold: float = 0.5,
        title: str = "Churn Risk Distribution"
    ) -> plt.Figure:
        """
        Plot histogram distribusi churn probability
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        
        ax.hist(probabilities, bins=50, edgecolor='black', alpha=0.7, color='steelblue')
        ax.axvline(x=threshold, color='red', linestyle='--', linewidth=2, label=f'Threshold = {threshold}')
        
        ax.set_xlabel("Churn Probability")
        ax.set_ylabel("Number of Customers")
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.legend()
        
        # Add risk zone annotations
        ax.axvspan(0, 0.3, alpha=0.1, color='green', label='Low Risk')
        ax.axvspan(0.3, 0.7, alpha=0.1, color='orange', label='Medium Risk')
        ax.axvspan(0.7, 1.0, alpha=0.1, color='red', label='High Risk')
        
        plt.tight_layout()
        self._save_figure("churn_risk_distribution.png")
        
        return fig
    
    # ==================== CLV VISUALIZATIONS ====================
    
    def plot_clv_distribution(
        self,
        clv_values: np.ndarray,
        title: str = "Customer Lifetime Value Distribution"
    ) -> plt.Figure:
        """
        Plot CLV distribution histogram
        """
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        
        # Histogram
        axes[0].hist(clv_values, bins=50, edgecolor='black', alpha=0.7, color='teal')
        axes[0].axvline(x=np.mean(clv_values), color='red', linestyle='--', linewidth=2, label=f'Mean = {np.mean(clv_values):,.0f}')
        axes[0].axvline(x=np.median(clv_values), color='orange', linestyle='--', linewidth=2, label=f'Median = {np.median(clv_values):,.0f}')
        axes[0].set_xlabel("CLV Value")
        axes[0].set_ylabel("Number of Customers")
        axes[0].set_title("CLV Distribution", fontsize=12, fontweight='bold')
        axes[0].legend()
        
        # Box plot
        axes[1].boxplot(clv_values, vert=True)
        axes[1].set_ylabel("CLV Value")
        axes[1].set_title("CLV Box Plot", fontsize=12, fontweight='bold')
        
        # Add percentile annotations
        percentiles = [25, 50, 75, 90]
        for p in percentiles:
            val = np.percentile(clv_values, p)
            axes[1].axhline(y=val, color='gray', linestyle=':', alpha=0.5)
            axes[1].annotate(f'P{p}: {val:,.0f}', xy=(1.1, val), fontsize=8)
        
        plt.suptitle(title, fontsize=14, fontweight='bold')
        plt.tight_layout()
        self._save_figure("clv_distribution.png")
        
        return fig
    
    def plot_clv_segments(
        self,
        segment_counts: Dict[str, int],
        segment_values: Dict[str, float],
        title: str = "CLV Segment Analysis"
    ) -> plt.Figure:
        """
        Plot CLV segment analysis
        """
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        
        segments = list(segment_counts.keys())
        counts = list(segment_counts.values())
        values = [segment_values.get(s, 0) for s in segments]
        colors = [self.clv_colors.get(s, "#3498db") for s in segments]
        
        # Customer count by segment
        axes[0].bar(segments, counts, color=colors)
        axes[0].set_xlabel("CLV Segment")
        axes[0].set_ylabel("Number of Customers")
        axes[0].set_title("Customer Count by Segment", fontsize=12, fontweight='bold')
        
        for i, count in enumerate(counts):
            axes[0].annotate(f'{count}', xy=(i, count), ha='center', va='bottom')
        
        # Total CLV by segment
        axes[1].bar(segments, values, color=colors)
        axes[1].set_xlabel("CLV Segment")
        axes[1].set_ylabel("Total CLV")
        axes[1].set_title("Total CLV by Segment", fontsize=12, fontweight='bold')
        
        for i, val in enumerate(values):
            axes[1].annotate(f'{val:,.0f}', xy=(i, val), ha='center', va='bottom', fontsize=8)
        
        plt.suptitle(title, fontsize=14, fontweight='bold')
        plt.tight_layout()
        self._save_figure("clv_segments.png")
        
        return fig
    
    def plot_pareto_analysis(
        self,
        clv_values: np.ndarray,
        title: str = "CLV Pareto Analysis (80/20 Rule)"
    ) -> plt.Figure:
        """
        Plot Pareto analysis untuk CLV
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Sort CLV descending
        sorted_clv = np.sort(clv_values)[::-1]
        cumsum = np.cumsum(sorted_clv)
        total = sorted_clv.sum()
        
        # Calculate percentages
        customer_pct = np.arange(1, len(sorted_clv) + 1) / len(sorted_clv) * 100
        revenue_pct = cumsum / total * 100
        
        ax.plot(customer_pct, revenue_pct, 'b-', linewidth=2, label='Cumulative Revenue %')
        ax.plot([0, 100], [0, 100], 'r--', linewidth=1, label='Perfect Equality')
        
        ax.fill_between(customer_pct, revenue_pct, alpha=0.2)
        
        # Mark 80/20 point
        idx_80 = np.searchsorted(revenue_pct, 80)
        if idx_80 < len(customer_pct):
            ax.axhline(y=80, color='green', linestyle=':', alpha=0.7)
            ax.axvline(x=customer_pct[idx_80], color='green', linestyle=':', alpha=0.7)
            ax.annotate(
                f'{customer_pct[idx_80]:.1f}% customers = 80% revenue',
                xy=(customer_pct[idx_80], 80),
                xytext=(customer_pct[idx_80]+10, 70),
                arrowprops=dict(arrowstyle='->', color='green'),
                fontsize=10
            )
        
        ax.set_xlabel("% of Customers (sorted by CLV)")
        ax.set_ylabel("% of Total Revenue")
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        self._save_figure("pareto_analysis.png")
        
        return fig
    
    # ==================== DIAGNOSTIC VISUALIZATIONS ====================
    
    def plot_distribution_comparison(
        self,
        original: pd.DataFrame,
        processed: pd.DataFrame,
        columns: Optional[List[str]] = None,
        title: str = "Distribution Before vs After Processing"
    ) -> plt.Figure:
        """
        Plot distribution comparison before and after preprocessing
        
        Args:
            original: Original DataFrame
            processed: Processed DataFrame
            columns: Columns to plot
            title: Plot title
        """
        if columns is None:
            columns = original.select_dtypes(include=[np.number]).columns[:4].tolist()
        
        n_cols = len(columns)
        fig, axes = plt.subplots(n_cols, 2, figsize=(14, 4*n_cols))
        
        if n_cols == 1:
            axes = axes.reshape(1, -1)
        
        for i, col in enumerate(columns):
            if col not in original.columns or col not in processed.columns:
                continue
            
            # Original distribution
            axes[i, 0].hist(original[col].dropna(), bins=50, edgecolor='black', alpha=0.7, color='steelblue')
            axes[i, 0].set_title(f"{col} - Original (skew: {original[col].skew():.2f})", fontsize=10)
            axes[i, 0].set_xlabel(col)
            axes[i, 0].set_ylabel("Frequency")
            
            # Processed distribution
            axes[i, 1].hist(processed[col].dropna(), bins=50, edgecolor='black', alpha=0.7, color='green')
            axes[i, 1].set_title(f"{col} - Processed (skew: {processed[col].skew():.2f})", fontsize=10)
            axes[i, 1].set_xlabel(col)
            axes[i, 1].set_ylabel("Frequency")
        
        plt.suptitle(title, fontsize=14, fontweight='bold')
        plt.tight_layout()
        self._save_figure("distribution_comparison.png")
        
        return fig
    
    def plot_outlier_detection(
        self,
        X: pd.DataFrame,
        outlier_masks: Dict[str, np.ndarray],
        columns: Optional[List[str]] = None,
        title: str = "Outlier Detection Results"
    ) -> plt.Figure:
        """
        Plot box plots showing outliers
        
        Args:
            X: DataFrame with features
            outlier_masks: Dictionary of outlier boolean masks
            columns: Columns to plot
            title: Plot title
        """
        if columns is None:
            columns = list(outlier_masks.keys())[:6]
        
        n_cols = min(len(columns), 6)
        n_rows = (n_cols + 2) // 3
        
        fig, axes = plt.subplots(n_rows, 3, figsize=(15, 4*n_rows))
        axes = axes.flatten() if n_rows > 1 else [axes]
        
        for i, col in enumerate(columns[:6]):
            if col not in X.columns or col not in outlier_masks:
                continue
            
            data = X[col].dropna()
            outliers = outlier_masks[col]
            
            axes[i].boxplot(data, vert=True)
            axes[i].scatter(
                np.ones(outliers.sum()),
                data[outliers],
                c='red',
                alpha=0.5,
                s=30,
                label=f'Outliers ({outliers.sum()})'
            )
            axes[i].set_title(f"{col}", fontsize=10)
            axes[i].set_ylabel("Value")
            axes[i].legend()
        
        # Hide unused subplots
        for i in range(len(columns), len(axes)):
            axes[i].axis('off')
        
        plt.suptitle(title, fontsize=14, fontweight='bold')
        plt.tight_layout()
        self._save_figure("outlier_detection.png")
        
        return fig
    
    # ==================== SUMMARY DASHBOARD ====================
    
    def plot_rfm_summary_dashboard(
        self,
        cluster_data: Dict,
        churn_data: Dict,
        clv_data: Dict,
        title: str = "RFM Modeling Summary Dashboard"
    ) -> plt.Figure:
        """
        Plot comprehensive summary dashboard
        """
        fig = plt.figure(figsize=(16, 12))
        
        # Layout: 3x3 grid
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
        
        # 1. Cluster distribution (top-left)
        ax1 = fig.add_subplot(gs[0, 0])
        if "cluster_counts" in cluster_data:
            labels = list(cluster_data["cluster_counts"].keys())
            sizes = list(cluster_data["cluster_counts"].values())
            colors = [self.cluster_colors.get(l, "#3498db") for l in labels]
            ax1.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors)
            ax1.set_title("Customer Clusters", fontsize=11, fontweight='bold')
        
        # 2. Cluster metrics (top-center)
        ax2 = fig.add_subplot(gs[0, 1])
        if "metrics" in cluster_data:
            metrics = cluster_data["metrics"]
            metric_names = ["Silhouette", "Calinski-H", "Davies-B"]
            metric_values = [
                metrics.get("silhouette_score", 0),
                metrics.get("calinski_harabasz_score", 0) / 1000,  # Scale down
                metrics.get("davies_bouldin_score", 0)
            ]
            ax2.bar(metric_names, metric_values, color=['#3498db', '#2ecc71', '#e74c3c'])
            ax2.set_title("Clustering Metrics", fontsize=11, fontweight='bold')
        
        # 3. Churn metrics (top-right)
        ax3 = fig.add_subplot(gs[0, 2])
        if "metrics" in churn_data:
            metrics = churn_data["metrics"]
            metric_names = ["Accuracy", "Precision", "Recall", "F1", "AUC"]
            metric_values = [
                metrics.get("accuracy", 0),
                metrics.get("precision", 0),
                metrics.get("recall", 0),
                metrics.get("f1_score", 0),
                metrics.get("roc_auc", 0)
            ]
            bars = ax3.bar(metric_names, metric_values, color='steelblue')
            ax3.set_ylim(0, 1)
            ax3.set_title("Churn Model Metrics", fontsize=11, fontweight='bold')
            for bar, val in zip(bars, metric_values):
                ax3.annotate(f'{val:.2f}', xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                           ha='center', va='bottom', fontsize=8)
        
        # 4. Feature importance - Churn (middle-left)
        ax4 = fig.add_subplot(gs[1, 0])
        if "feature_importances" in churn_data:
            top_features = dict(list(churn_data["feature_importances"].items())[:5])
            ax4.barh(list(top_features.keys())[::-1], list(top_features.values())[::-1], color='coral')
            ax4.set_title("Top Churn Predictors", fontsize=11, fontweight='bold')
        
        # 5. CLV distribution (middle-center)
        ax5 = fig.add_subplot(gs[1, 1])
        if "clv_values" in clv_data:
            ax5.hist(clv_data["clv_values"], bins=30, color='teal', alpha=0.7, edgecolor='black')
            ax5.set_title("CLV Distribution", fontsize=11, fontweight='bold')
            ax5.set_xlabel("CLV")
        
        # 6. CLV segments (middle-right)
        ax6 = fig.add_subplot(gs[1, 2])
        if "segment_distribution" in clv_data:
            segments = list(clv_data["segment_distribution"].keys())
            counts = list(clv_data["segment_distribution"].values())
            colors = [self.clv_colors.get(s.split()[0], "#3498db") for s in segments]
            ax6.bar(range(len(segments)), counts, color=colors)
            ax6.set_xticks(range(len(segments)))
            ax6.set_xticklabels([s.split()[0] for s in segments], rotation=45)
            ax6.set_title("CLV Segments", fontsize=11, fontweight='bold')
        
        # 7. Key insights (bottom - spanning full width)
        ax7 = fig.add_subplot(gs[2, :])
        ax7.axis('off')
        
        insights_text = f"""
        KEY INSIGHTS
        ═══════════════════════════════════════════════════════════════════════════════
        
        CLUSTERING: {cluster_data.get('n_clusters', 3)} customer segments identified
        • Silhouette Score: {cluster_data.get('metrics', {}).get('silhouette_score', 0):.4f}
        
        CHURN PREDICTION: Model trained with {churn_data.get('metrics', {}).get('accuracy', 0)*100:.1f}% accuracy
        • High-risk customers: {churn_data.get('high_risk_count', 'N/A')}
        
        CLV ANALYSIS: Total predicted CLV: {clv_data.get('total_clv', 0):,.0f}
        • Top 20% customers contribute {clv_data.get('pareto_20_pct', 0):.1f}% of revenue
        """
        
        ax7.text(0.5, 0.5, insights_text, transform=ax7.transAxes, fontsize=10,
                verticalalignment='center', horizontalalignment='center',
                family='monospace', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.suptitle(title, fontsize=16, fontweight='bold')
        self._save_figure("rfm_summary_dashboard.png")
        
        return fig
    
    def show_all(self):
        """Display all figures"""
        plt.show()
