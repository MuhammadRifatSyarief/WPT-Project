"""
RFM Insight Generator

Module untuk generate comprehensive insights dari hasil RFM modeling.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime


class RFMInsightGenerator:
    """
    Generate actionable insights dari RFM modeling results
    """
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.insights: Dict[str, Any] = {}
    
    def generate_clustering_insights(
        self,
        cluster_profiles: pd.DataFrame,
        cluster_labels: Dict[int, str],
        metrics: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Generate insights dari clustering results
        """
        insights = {
            "summary": {},
            "segment_insights": [],
            "recommendations": [],
            "quality_assessment": ""
        }
        
        # Summary
        insights["summary"] = {
            "total_customers": cluster_profiles["customer_count"].sum(),
            "n_segments": len(cluster_profiles),
            "silhouette_score": metrics.get("silhouette_score", 0),
            "clustering_quality": self._assess_clustering_quality(metrics)
        }
        
        # Per-segment insights
        for _, row in cluster_profiles.iterrows():
            segment_name = row["cluster_label"]
            segment_insight = {
                "segment": segment_name,
                "customer_count": row["customer_count"],
                "customer_pct": row["customer_pct"],
                "characteristics": self._describe_segment(row, segment_name),
                "actions": self._get_segment_actions(segment_name)
            }
            insights["segment_insights"].append(segment_insight)
        
        # Overall recommendations
        insights["recommendations"] = self._generate_clustering_recommendations(cluster_profiles)
        
        self.insights["clustering"] = insights
        
        if self.verbose:
            self._print_clustering_insights(insights)
        
        return insights
    
    def generate_churn_insights(
        self,
        metrics: Dict[str, float],
        feature_importances: Dict[str, float],
        high_risk_count: int,
        total_customers: int
    ) -> Dict[str, Any]:
        """
        Generate insights dari churn prediction results
        """
        insights = {
            "model_performance": {},
            "risk_analysis": {},
            "top_predictors": [],
            "recommendations": []
        }
        
        # Model performance
        insights["model_performance"] = {
            "accuracy": metrics.get("accuracy", 0),
            "precision": metrics.get("precision", 0),
            "recall": metrics.get("recall", 0),
            "f1_score": metrics.get("f1_score", 0),
            "roc_auc": metrics.get("roc_auc", 0),
            "quality_rating": self._rate_model_quality(metrics)
        }
        
        # Risk analysis
        high_risk_pct = (high_risk_count / total_customers * 100) if total_customers > 0 else 0
        insights["risk_analysis"] = {
            "high_risk_customers": high_risk_count,
            "high_risk_percentage": high_risk_pct,
            "risk_level": self._assess_overall_risk(high_risk_pct),
            "potential_revenue_at_risk": "Requires CLV data for calculation"
        }
        
        # Top predictors
        for feature, importance in list(feature_importances.items())[:5]:
            insights["top_predictors"].append({
                "feature": feature,
                "importance": importance,
                "interpretation": self._interpret_churn_feature(feature, importance)
            })
        
        # Recommendations
        insights["recommendations"] = self._generate_churn_recommendations(high_risk_pct, feature_importances)
        
        self.insights["churn"] = insights
        
        if self.verbose:
            self._print_churn_insights(insights)
        
        return insights
    
    def generate_clv_insights(
        self,
        metrics: Dict[str, float],
        distribution_analysis: Dict[str, Any],
        feature_importances: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Generate insights dari CLV prediction results
        """
        insights = {
            "model_performance": {},
            "value_distribution": {},
            "pareto_analysis": {},
            "top_drivers": [],
            "recommendations": []
        }
        
        # Model performance
        insights["model_performance"] = {
            "r2_score": metrics.get("r2_score", 0),
            "rmse": metrics.get("rmse", 0),
            "mae": metrics.get("mae", 0),
            "mape": metrics.get("mape", 0),
            "quality_rating": self._rate_regression_quality(metrics)
        }
        
        # Value distribution
        insights["value_distribution"] = {
            "total_predicted_clv": distribution_analysis.get("total_predicted_clv", 0),
            "mean_clv": distribution_analysis.get("mean_clv", 0),
            "median_clv": distribution_analysis.get("median_clv", 0),
            "clv_spread": distribution_analysis.get("std_clv", 0) / distribution_analysis.get("mean_clv", 1) if distribution_analysis.get("mean_clv", 0) > 0 else 0,
            "segment_distribution": distribution_analysis.get("segment_distribution", {})
        }
        
        # Pareto analysis
        pareto = distribution_analysis.get("pareto", {})
        insights["pareto_analysis"] = {
            "top_20_revenue_share": pareto.get("top_20_pct_revenue_share", 0),
            "customers_for_80_revenue": pareto.get("top_pct_for_80_revenue", 0),
            "concentration_level": self._assess_concentration(pareto.get("top_20_pct_revenue_share", 0))
        }
        
        # Top CLV drivers
        for feature, importance in list(feature_importances.items())[:5]:
            insights["top_drivers"].append({
                "feature": feature,
                "importance": importance,
                "interpretation": self._interpret_clv_feature(feature, importance)
            })
        
        # Recommendations
        insights["recommendations"] = self._generate_clv_recommendations(insights)
        
        self.insights["clv"] = insights
        
        if self.verbose:
            self._print_clv_insights(insights)
        
        return insights
    
    def generate_executive_summary(self) -> str:
        """
        Generate executive summary dari semua insights
        """
        summary_parts = []
        summary_parts.append("=" * 70)
        summary_parts.append(" EXECUTIVE SUMMARY - RFM MODELING RESULTS")
        summary_parts.append("=" * 70)
        summary_parts.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Clustering summary
        if "clustering" in self.insights:
            c = self.insights["clustering"]
            summary_parts.append("-" * 50)
            summary_parts.append("CUSTOMER SEGMENTATION")
            summary_parts.append("-" * 50)
            summary_parts.append(f"Total Customers Analyzed: {c['summary']['total_customers']:,}")
            summary_parts.append(f"Segments Identified: {c['summary']['n_segments']}")
            summary_parts.append(f"Clustering Quality: {c['summary']['clustering_quality']}")
            summary_parts.append("")
        
        # Churn summary
        if "churn" in self.insights:
            ch = self.insights["churn"]
            summary_parts.append("-" * 50)
            summary_parts.append("CHURN PREDICTION")
            summary_parts.append("-" * 50)
            summary_parts.append(f"Model Accuracy: {ch['model_performance']['accuracy']*100:.1f}%")
            summary_parts.append(f"High-Risk Customers: {ch['risk_analysis']['high_risk_customers']:,} ({ch['risk_analysis']['high_risk_percentage']:.1f}%)")
            summary_parts.append(f"Overall Risk Level: {ch['risk_analysis']['risk_level']}")
            summary_parts.append("")
        
        # CLV summary
        if "clv" in self.insights:
            clv = self.insights["clv"]
            summary_parts.append("-" * 50)
            summary_parts.append("CUSTOMER LIFETIME VALUE")
            summary_parts.append("-" * 50)
            summary_parts.append(f"Total Predicted CLV: {clv['value_distribution']['total_predicted_clv']:,.0f}")
            summary_parts.append(f"Average CLV: {clv['value_distribution']['mean_clv']:,.0f}")
            summary_parts.append(f"Top 20% Revenue Share: {clv['pareto_analysis']['top_20_revenue_share']:.1f}%")
            summary_parts.append(f"Revenue Concentration: {clv['pareto_analysis']['concentration_level']}")
            summary_parts.append("")
        
        summary_parts.append("=" * 70)
        summary_parts.append(" KEY ACTIONS RECOMMENDED")
        summary_parts.append("=" * 70)
        
        # Compile key actions
        all_recommendations = []
        for section in ["clustering", "churn", "clv"]:
            if section in self.insights:
                all_recommendations.extend(self.insights[section].get("recommendations", [])[:2])
        
        for i, rec in enumerate(all_recommendations[:6], 1):
            summary_parts.append(f"{i}. {rec}")
        
        summary_parts.append("")
        summary_parts.append("=" * 70)
        
        return "\n".join(summary_parts)
    
    # ==================== HELPER METHODS ====================
    
    def _assess_clustering_quality(self, metrics: Dict) -> str:
        silhouette = metrics.get("silhouette_score", 0)
        if silhouette >= 0.7:
            return "EXCELLENT - Clusters sangat well-defined"
        elif silhouette >= 0.5:
            return "GOOD - Clusters reasonably separated"
        elif silhouette >= 0.25:
            return "FAIR - Some overlap between clusters"
        else:
            return "POOR - Consider different approach"
    
    def _describe_segment(self, row: pd.Series, segment_name: str) -> str:
        descriptions = {
            "High Value": "Customers dengan spending tinggi, frekuensi pembelian tinggi, dan engagement aktif",
            "Medium Value": "Customers dengan potensi growth, pembelian moderate, perlu nurturing",
            "Low Value": "Customers dengan engagement rendah, perlu re-activation strategy"
        }
        return descriptions.get(segment_name, f"Segment dengan karakteristik unik")
    
    def _get_segment_actions(self, segment_name: str) -> List[str]:
        actions = {
            "High Value": [
                "VIP treatment dan priority service",
                "Exclusive access ke produk baru",
                "Personalized loyalty rewards"
            ],
            "Medium Value": [
                "Targeted upselling campaigns",
                "Bundle offers untuk increase basket size",
                "Loyalty program enrollment"
            ],
            "Low Value": [
                "Win-back email campaigns",
                "Special re-activation offers",
                "Survey untuk understand barriers"
            ]
        }
        return actions.get(segment_name, ["Monitor dan analyze"])
    
    def _generate_clustering_recommendations(self, profiles: pd.DataFrame) -> List[str]:
        recommendations = [
            "Implementasi tiered service model berdasarkan customer segment",
            "Develop segment-specific marketing campaigns",
            "Alokasikan resource berdasarkan segment value"
        ]
        return recommendations
    
    def _rate_model_quality(self, metrics: Dict) -> str:
        f1 = metrics.get("f1_score", 0)
        if f1 >= 0.9:
            return "EXCELLENT"
        elif f1 >= 0.8:
            return "GOOD"
        elif f1 >= 0.7:
            return "FAIR"
        else:
            return "NEEDS IMPROVEMENT"
    
    def _rate_regression_quality(self, metrics: Dict) -> str:
        r2 = metrics.get("r2_score", 0)
        if r2 >= 0.9:
            return "EXCELLENT"
        elif r2 >= 0.7:
            return "GOOD"
        elif r2 >= 0.5:
            return "FAIR"
        else:
            return "NEEDS IMPROVEMENT"
    
    def _assess_overall_risk(self, high_risk_pct: float) -> str:
        if high_risk_pct >= 30:
            return "CRITICAL - Immediate action required"
        elif high_risk_pct >= 20:
            return "HIGH - Priority attention needed"
        elif high_risk_pct >= 10:
            return "MODERATE - Standard monitoring"
        else:
            return "LOW - Healthy customer base"
    
    def _assess_concentration(self, top_20_share: float) -> str:
        if top_20_share >= 80:
            return "VERY HIGH - Dependent on few customers"
        elif top_20_share >= 60:
            return "HIGH - Moderate concentration"
        elif top_20_share >= 40:
            return "MODERATE - Balanced portfolio"
        else:
            return "LOW - Well-distributed revenue"
    
    def _interpret_churn_feature(self, feature: str, importance: float) -> str:
        strength = "very strong" if importance > 0.2 else "strong" if importance > 0.1 else "moderate"
        return f"{feature} adalah {strength} predictor untuk churn"
    
    def _interpret_clv_feature(self, feature: str, importance: float) -> str:
        strength = "major" if importance > 0.3 else "significant" if importance > 0.15 else "contributing"
        return f"{feature} adalah {strength} driver untuk customer value"
    
    def _generate_churn_recommendations(self, high_risk_pct: float, features: Dict) -> List[str]:
        recommendations = []
        
        if high_risk_pct > 20:
            recommendations.append("URGENT: Implement immediate retention program untuk high-risk customers")
        
        top_feature = list(features.keys())[0] if features else "recency"
        recommendations.append(f"Focus improvement pada {top_feature} untuk reduce churn risk")
        recommendations.append("Setup automated alerts untuk customers entering high-risk zone")
        recommendations.append("Develop personalized win-back campaigns")
        
        return recommendations
    
    def _generate_clv_recommendations(self, insights: Dict) -> List[str]:
        recommendations = []
        
        pareto = insights.get("pareto_analysis", {})
        if pareto.get("top_20_revenue_share", 0) > 70:
            recommendations.append("HIGH PRIORITY: Diversify customer base - too dependent on few high-value customers")
        
        recommendations.append("Implement tiered service model berdasarkan predicted CLV")
        recommendations.append("Develop growth strategies untuk Silver segment ke Gold")
        recommendations.append("Create VIP program untuk retain Platinum customers")
        
        return recommendations
    
    def _print_clustering_insights(self, insights: Dict):
        print("\n" + "=" * 60)
        print(" CLUSTERING INSIGHTS")
        print("=" * 60)
        print(f"Total Customers: {insights['summary']['total_customers']:,}")
        print(f"Quality: {insights['summary']['clustering_quality']}")
        
        for seg in insights["segment_insights"]:
            print(f"\n[{seg['segment']}] - {seg['customer_count']:,} customers ({seg['customer_pct']:.1f}%)")
    
    def _print_churn_insights(self, insights: Dict):
        print("\n" + "=" * 60)
        print(" CHURN PREDICTION INSIGHTS")
        print("=" * 60)
        print(f"Model Quality: {insights['model_performance']['quality_rating']}")
        print(f"High-Risk Customers: {insights['risk_analysis']['high_risk_customers']:,}")
        print(f"Risk Level: {insights['risk_analysis']['risk_level']}")
    
    def _print_clv_insights(self, insights: Dict):
        print("\n" + "=" * 60)
        print(" CLV INSIGHTS")
        print("=" * 60)
        print(f"Model Quality: {insights['model_performance']['quality_rating']}")
        print(f"Total Predicted CLV: {insights['value_distribution']['total_predicted_clv']:,.0f}")
        print(f"Pareto: Top 20% = {insights['pareto_analysis']['top_20_revenue_share']:.1f}% revenue")
