"""
RFM Helper Functions

Utility functions untuk formatting, printing, dan operasi umum.
"""

from typing import Dict, Any, Optional
from pathlib import Path
import numpy as np


def print_section_header(title: str, width: int = 60):
    """Print formatted section header"""
    print("\n" + "=" * width)
    print(f" {title}")
    print("=" * width)


def print_subsection_header(title: str, width: int = 50):
    """Print formatted subsection header"""
    print("\n" + "-" * width)
    print(f" {title}")
    print("-" * width)


def print_model_metrics(metrics: Dict[str, float], title: str = "Model Metrics"):
    """Print model metrics dalam format yang rapi"""
    print_subsection_header(title)
    for metric_name, value in metrics.items():
        if isinstance(value, float):
            if "accuracy" in metric_name.lower() or "score" in metric_name.lower():
                print(f"  {metric_name}: {value:.4f} ({value*100:.2f}%)")
            else:
                print(f"  {metric_name}: {value:.4f}")
        else:
            print(f"  {metric_name}: {value}")


def format_currency(value: float, currency: str = "Rp", decimal_places: int = 0) -> str:
    """Format angka sebagai currency"""
    if np.isnan(value):
        return f"{currency} -"
    return f"{currency} {value:,.{decimal_places}f}"


def format_percentage(value: float, decimal_places: int = 2) -> str:
    """Format angka sebagai percentage"""
    if np.isnan(value):
        return "-"
    return f"{value*100:.{decimal_places}f}%"


def format_number(value: float, decimal_places: int = 2) -> str:
    """Format angka dengan thousand separator"""
    if np.isnan(value):
        return "-"
    return f"{value:,.{decimal_places}f}"


def create_output_dirs(base_path: str, subdirs: list = None) -> Dict[str, Path]:
    """Create output directories"""
    base = Path(base_path)
    base.mkdir(parents=True, exist_ok=True)
    
    paths = {"base": base}
    
    default_subdirs = ["models", "visualizations", "reports", "csv", "pkl"]
    subdirs = subdirs or default_subdirs
    
    for subdir in subdirs:
        path = base / subdir
        path.mkdir(parents=True, exist_ok=True)
        paths[subdir] = path
    
    return paths


def calculate_silhouette_interpretation(score: float) -> str:
    """Interpretasi silhouette score"""
    if score >= 0.7:
        return "Strong structure (clusters are well-separated)"
    elif score >= 0.5:
        return "Reasonable structure (clusters are moderately separated)"
    elif score >= 0.25:
        return "Weak structure (clusters may be overlapping)"
    else:
        return "No substantial structure (consider different clustering)"


def calculate_model_quality(metrics: Dict[str, float], model_type: str) -> str:
    """Interpretasi kualitas model"""
    if model_type == "classification":
        accuracy = metrics.get("accuracy", 0)
        f1 = metrics.get("f1_score", 0)
        avg_score = (accuracy + f1) / 2
        
        if avg_score >= 0.9:
            return "Excellent"
        elif avg_score >= 0.8:
            return "Good"
        elif avg_score >= 0.7:
            return "Fair"
        else:
            return "Needs Improvement"
    
    elif model_type == "regression":
        r2 = metrics.get("r2_score", 0)
        
        if r2 >= 0.9:
            return "Excellent"
        elif r2 >= 0.7:
            return "Good" 
        elif r2 >= 0.5:
            return "Fair"
        else:
            return "Needs Improvement"
    
    return "Unknown"


def get_cluster_interpretation(cluster_stats: Dict, n_clusters: int = 3) -> Dict[int, str]:
    """
    Generate interpretasi untuk setiap cluster berdasarkan statistik
    
    Args:
        cluster_stats: Dictionary dengan statistik per cluster
        n_clusters: Jumlah cluster
        
    Returns:
        Dictionary mapping cluster_id ke label interpretasi
    """
    interpretations = {}
    
    # Sort clusters by monetary value
    sorted_clusters = sorted(
        cluster_stats.items(),
        key=lambda x: x[1].get("monetary_mean", 0),
        reverse=True
    )
    
    labels = ["High Value", "Medium Value", "Low Value"]
    
    for i, (cluster_id, stats) in enumerate(sorted_clusters):
        if i < len(labels):
            interpretations[cluster_id] = labels[i]
        else:
            interpretations[cluster_id] = f"Cluster {cluster_id}"
    
    return interpretations
