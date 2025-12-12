"""
RFM Modeling Pipeline Runner

Main entry point untuk menjalankan complete RFM modeling pipeline:
1. Customer Clustering (K-Means)
2. Churn Prediction (Classification)
3. CLV Prediction (Regression)

Usage:
    # Default (data di scripts/project2_sales_analytics/output/features/csv/)
    python run_rfm_pipeline.py
    
    # Dengan absolute path
    python run_rfm_pipeline.py --input "D:/path/to/features/csv"
    
    # Dengan custom parameters
    python run_rfm_pipeline.py --n-clusters 3 --churn-model random_forest

Output: CSV, PKL, visualizations, dan insights
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
import warnings
import traceback

warnings.filterwarnings('ignore')

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="RFM Modeling Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
DATA LOCATION:
  Taruh file feature engineering di:
    scripts/project2_sales_analytics/output/features/csv/
    ├── rfm_features.csv
    ├── behavioral_features.csv
    ├── customer_features.csv
    └── ...
  
  Atau gunakan --input dengan absolute path:
    python run_rfm_pipeline.py --input "D:/path/to/features/csv"
        """
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        default=None,
        help="Input directory dengan feature engineering output"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output directory untuk results"
    )
    
    parser.add_argument(
        "--n-clusters", "-k",
        type=int,
        default=3,
        help="Number of clusters untuk K-Means (default: 3)"
    )
    
    parser.add_argument(
        "--churn-model",
        type=str,
        choices=["random_forest", "xgboost", "logistic"],
        default="random_forest",
        help="Model type untuk churn prediction"
    )
    
    parser.add_argument(
        "--clv-model",
        type=str,
        choices=["linear", "random_forest", "gradient_boosting"],
        default="random_forest",
        help="Model type untuk CLV prediction"
    )
    
    parser.add_argument(
        "--churn-threshold",
        type=int,
        default=90,
        help="Days threshold untuk churn definition"
    )
    
    parser.add_argument(
        "--no-viz",
        action="store_true",
        help="Skip visualizations"
    )
    
    parser.add_argument(
        "--show-guide",
        action="store_true",
        help="Show data location guide and exit"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=True,
        help="Enable verbose output"
    )
    
    return parser.parse_args()


def print_section_header(title: str):
    """Print formatted section header."""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def safe_import_modules():
    """Safely import all required modules with error handling"""
    modules = {}
    
    try:
        from config.rfm_config import RFMModelConfig
        modules['RFMModelConfig'] = RFMModelConfig
    except ImportError as e:
        print(f"[ERROR] Cannot import RFMModelConfig: {e}")
        return None
    
    try:
        from data.data_loader import RFMDataLoader
        modules['RFMDataLoader'] = RFMDataLoader
    except ImportError as e:
        print(f"[ERROR] Cannot import RFMDataLoader: {e}")
        return None
    
    try:
        from visualization.rfm_visualizer import RFMVisualizer
        modules['RFMVisualizer'] = RFMVisualizer
    except ImportError as e:
        print(f"[WARNING] Cannot import RFMVisualizer: {e}")
        modules['RFMVisualizer'] = None
    
    try:
        from analysis.insight_generator import RFMInsightGenerator
        modules['RFMInsightGenerator'] = RFMInsightGenerator
    except ImportError as e:
        print(f"[WARNING] Cannot import RFMInsightGenerator: {e}")
        modules['RFMInsightGenerator'] = None
    
    try:
        from export.rfm_exporter import RFMExporter
        modules['RFMExporter'] = RFMExporter
    except ImportError as e:
        print(f"[WARNING] Cannot import RFMExporter: {e}")
        modules['RFMExporter'] = None
    
    try:
        from models.clustering_model import CustomerClusteringModel
        modules['CustomerClusteringModel'] = CustomerClusteringModel
    except ImportError as e:
        print(f"[ERROR] Cannot import CustomerClusteringModel: {e}")
        return None
    
    try:
        from models.churn_classifier import ChurnClassifier
        modules['ChurnClassifier'] = ChurnClassifier
    except ImportError as e:
        print(f"[ERROR] Cannot import ChurnClassifier: {e}")
        return None
    
    try:
        from models.clv_regressor import CLVRegressor
        modules['CLVRegressor'] = CLVRegressor
    except ImportError as e:
        print(f"[ERROR] Cannot import CLVRegressor: {e}")
        return None
    
    try:
        from preprocessing.train_test_splitter import TrainTestSplitter
        modules['TrainTestSplitter'] = TrainTestSplitter
    except ImportError as e:
        print(f"[ERROR] Cannot import TrainTestSplitter: {e}")
        return None
    
    return modules


def run_clustering_pipeline(config, data_loader, visualizer, exporter, modules) -> dict:
    """Run customer clustering pipeline"""
    print_section_header("CUSTOMER CLUSTERING (K-MEANS)")
    
    CustomerClusteringModel = modules['CustomerClusteringModel']
    
    try:
        # Prepare data
        features_df, customer_ids = data_loader.prepare_clustering_data()
        print(f"Data prepared: {len(features_df)} customers, {len(features_df.columns)} features")
        
        # Initialize model
        clustering_model = CustomerClusteringModel(config.clustering, verbose=True)
        
        # Find optimal K
        print("\n[Step 1] Finding optimal number of clusters...")
        optimal_k_results = clustering_model.find_optimal_k(features_df, k_range=range(2, 8))
        
        # Visualize elbow curve
        if visualizer:
            visualizer.plot_elbow_curve(
                k_values=optimal_k_results["k_values"],
                inertias=optimal_k_results["inertia"],
                silhouettes=optimal_k_results["silhouette"],
                optimal_k=optimal_k_results["optimal_k"]
            )
        
        # Fit model
        print(f"\n[Step 2] Fitting K-Means with K={config.clustering.n_clusters}...")
        labels = clustering_model.fit_predict(features_df)
        
        # Evaluate
        print("\n[Step 3] Evaluating clustering quality...")
        metrics = clustering_model.evaluate(features_df, labels)
        
        # Assign labels
        print("\n[Step 4] Assigning cluster labels...")
        cluster_labels = clustering_model.assign_cluster_labels(features_df, labels)
        
        # Get profiles
        print("\n[Step 5] Generating cluster profiles...")
        cluster_profiles = clustering_model.get_cluster_profiles(features_df, labels)
        
        # Visualizations
        if visualizer:
            print("\n[Step 6] Creating visualizations...")
            visualizer.plot_cluster_distribution(labels, cluster_labels)
            
            if "recency" in features_df.columns and "monetary" in features_df.columns:
                visualizer.plot_cluster_scatter_2d(
                    features_df, labels, cluster_labels,
                    x_col="recency", y_col="monetary"
                )
            
            if all(col in features_df.columns for col in ["recency", "frequency", "monetary"]):
                visualizer.plot_cluster_scatter_3d(features_df, labels, cluster_labels)
            
            visualizer.plot_cluster_profiles(cluster_profiles)
        
        # Export
        export_paths = {}
        if exporter:
            print("\n[Step 7] Exporting results...")
            export_paths = exporter.export_clustering_results(
                customer_ids=customer_ids,
                labels=labels,
                cluster_labels=cluster_labels,
                cluster_profiles=cluster_profiles,
                features=features_df,
                model=clustering_model,
                metrics=metrics
            )
        
        # Recommendations
        print("\n[Step 8] Generating business recommendations...")
        recommendations = clustering_model.get_cluster_recommendations()
        for segment, rec in recommendations.items():
            print(f"\n{segment}:")
            print(f"  Strategy: {rec['strategy']}")
            print(f"  Priority: {rec['priority']}")
        
        return {
            "model": clustering_model,
            "labels": labels,
            "cluster_labels": cluster_labels,
            "cluster_profiles": cluster_profiles,
            "metrics": metrics,
            "customer_ids": customer_ids,
            "features": features_df,
            "export_paths": export_paths,
            "status": "success"
        }
        
    except Exception as e:
        print(f"\n[ERROR] Clustering pipeline failed: {e}")
        traceback.print_exc()
        return {"status": "failed", "error": str(e)}


def run_churn_pipeline(config, data_loader, visualizer, exporter, modules) -> dict:
    """Run churn prediction pipeline"""
    print_section_header("CHURN PREDICTION (CLASSIFICATION)")
    
    ChurnClassifier = modules['ChurnClassifier']
    TrainTestSplitter = modules['TrainTestSplitter']
    import numpy as np
    
    try:
        # Prepare data
        features_df, target, customer_ids = data_loader.prepare_churn_data()
        print(f"Data prepared: {len(features_df)} customers, {len(features_df.columns)} features")
        print(f"Target distribution: {target.value_counts().to_dict()}")
        
        # Split
        print("\n[Step 1] Splitting data...")
        splitter = TrainTestSplitter(test_size=config.churn.test_size, random_state=config.churn.random_state)
        X_train, X_test, y_train, y_test = splitter.split(features_df, target, stratify=True)
        
        # Train
        print(f"\n[Step 2] Training {config.churn.model_type} classifier...")
        churn_model = ChurnClassifier(config.churn, verbose=True)
        cv_results = churn_model.cross_validate(features_df, target, cv=5)
        churn_model.fit(X_train, y_train)
        
        # Evaluate
        print("\n[Step 3] Evaluating model...")
        metrics = churn_model.evaluate(X_test, y_test)
        
        print("\n[Step 4] Classification Report:")
        print(churn_model.get_classification_report(X_test, y_test))
        
        # Threshold
        print("\n[Step 5] Finding optimal threshold...")
        threshold_results = churn_model.find_optimal_threshold(X_test, y_test, metric="f1")
        
        # Predict
        predictions = churn_model.predict(features_df)
        probabilities = churn_model.predict_proba(features_df)
        
        # Visualizations
        if visualizer:
            print("\n[Step 6] Creating visualizations...")
            cm = metrics.get("confusion_matrix", [[0, 0], [0, 0]])
            visualizer.plot_confusion_matrix(np.array(cm))
            
            roc_data = churn_model.get_roc_curve_data(X_test, y_test)
            visualizer.plot_roc_curve(roc_data["fpr"], roc_data["tpr"], roc_data["auc"])
            visualizer.plot_feature_importance(churn_model.feature_importances, title="Churn Prediction - Feature Importance")
            visualizer.plot_churn_risk_distribution(probabilities, threshold=churn_model.threshold)
        
        # High-risk customers
        print("\n[Step 7] Identifying high-risk customers...")
        high_risk_df = churn_model.get_high_risk_customers(features_df, customer_ids, threshold=0.5)
        print(f"High-risk customers: {len(high_risk_df)}")
        
        # Export
        export_paths = {}
        if exporter:
            print("\n[Step 8] Exporting results...")
            export_paths = exporter.export_churn_results(
                customer_ids=customer_ids,
                predictions=predictions,
                probabilities=probabilities,
                features=features_df,
                model=churn_model,
                metrics=metrics,
                feature_importances=churn_model.feature_importances
            )
        
        # Insights
        print("\n[Step 9] Generating business insights...")
        insights = churn_model.get_churn_insights()
        print("\nTop Risk Factors:")
        for factor in insights["top_risk_factors"][:3]:
            print(f"  - {factor['feature']}: {factor['importance']:.4f}")
        
        return {
            "model": churn_model,
            "predictions": predictions,
            "probabilities": probabilities,
            "metrics": metrics,
            "feature_importances": churn_model.feature_importances,
            "high_risk_customers": high_risk_df,
            "customer_ids": customer_ids,
            "export_paths": export_paths,
            "status": "success"
        }
        
    except Exception as e:
        print(f"\n[ERROR] Churn pipeline failed: {e}")
        traceback.print_exc()
        return {"status": "failed", "error": str(e)}


def run_clv_pipeline(config, data_loader, visualizer, exporter, modules) -> dict:
    """Run CLV prediction pipeline"""
    print_section_header("CUSTOMER LIFETIME VALUE (REGRESSION)")
    
    CLVRegressor = modules['CLVRegressor']
    TrainTestSplitter = modules['TrainTestSplitter']
    import pandas as pd
    
    try:
        # Prepare data
        features_df, target, customer_ids = data_loader.prepare_clv_data()
        print(f"Data prepared: {len(features_df)} customers, {len(features_df.columns)} features")
        print(f"Target stats: mean={target.mean():.2f}, median={target.median():.2f}")
        
        # Split
        print("\n[Step 1] Splitting data...")
        splitter = TrainTestSplitter(test_size=config.clv.test_size, random_state=config.clv.random_state)
        X_train, X_test, y_train, y_test = splitter.split(features_df, target)
        
        # Train
        print(f"\n[Step 2] Training {config.clv.model_type} regressor...")
        clv_model = CLVRegressor(config.clv, verbose=True)
        cv_results = clv_model.cross_validate(features_df, target, cv=5)
        clv_model.fit(X_train, y_train)
        
        # Evaluate
        print("\n[Step 3] Evaluating model...")
        metrics = clv_model.evaluate(X_test, y_test)
        
        # Predict with segments
        print("\n[Step 4] Generating predictions with segments...")
        predictions_df = clv_model.predict_with_segments(features_df, customer_ids)
        predictions = predictions_df["predicted_clv"].values
        segments = predictions_df["clv_segment"]
        
        # Distribution analysis
        print("\n[Step 5] Analyzing CLV distribution...")
        distribution_analysis = clv_model.get_clv_distribution_analysis(features_df)
        print(f"Total Predicted CLV: {distribution_analysis['total_predicted_clv']:,.0f}")
        print(f"Pareto Analysis: Top 20% = {distribution_analysis['pareto']['top_20_pct_revenue_share']:.1f}% revenue")
        
        # Visualizations
        if visualizer:
            print("\n[Step 6] Creating visualizations...")
            visualizer.plot_clv_distribution(predictions)
            
            segment_counts = segments.value_counts().to_dict()
            segment_values = predictions_df.groupby("clv_segment")["predicted_clv"].sum().to_dict()
            visualizer.plot_clv_segments(segment_counts, segment_values)
            visualizer.plot_pareto_analysis(predictions)
            visualizer.plot_feature_importance(clv_model.feature_importances, title="CLV Prediction - Feature Importance")
        
        # Top customers
        print("\n[Step 7] Identifying top value customers...")
        top_customers = clv_model.get_top_value_customers(features_df, customer_ids, top_n=50)
        
        # Export
        export_paths = {}
        if exporter:
            print("\n[Step 8] Exporting results...")
            export_paths = exporter.export_clv_results(
                customer_ids=customer_ids,
                predictions=predictions,
                segments=segments,
                features=features_df,
                model=clv_model,
                metrics=metrics,
                feature_importances=clv_model.feature_importances,
                distribution_analysis=distribution_analysis
            )
        
        # Insights
        print("\n[Step 9] Generating business insights...")
        insights = clv_model.get_clv_insights()
        print("\nTop CLV Drivers:")
        for driver in insights["top_drivers"][:3]:
            print(f"  - {driver['feature']}: {driver['importance']:.4f}")
        
        return {
            "model": clv_model,
            "predictions": predictions,
            "segments": segments,
            "predictions_df": predictions_df,
            "metrics": metrics,
            "feature_importances": clv_model.feature_importances,
            "distribution_analysis": distribution_analysis,
            "top_customers": top_customers,
            "customer_ids": customer_ids,
            "export_paths": export_paths,
            "status": "success"
        }
        
    except Exception as e:
        print(f"\n[ERROR] CLV pipeline failed: {e}")
        traceback.print_exc()
        return {"status": "failed", "error": str(e)}


def run_complete_pipeline(config, modules) -> dict:
    """Run complete RFM modeling pipeline"""
    import pandas as pd
    import numpy as np
    
    RFMDataLoader = modules['RFMDataLoader']
    RFMVisualizer = modules.get('RFMVisualizer')
    RFMInsightGenerator = modules.get('RFMInsightGenerator')
    RFMExporter = modules.get('RFMExporter')
    
    print("\n" + "=" * 70)
    print(" RFM MODELING PIPELINE")
    print(f" Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print(f"\nInput Directory: {config.base_input_path}")
    print(f"Output Directory: {config.base_output_path}")
    
    # Validate input files
    file_status = config.validate_input_files()
    missing_files = [f for f, exists in file_status.items() if not exists]
    
    # Only customer_features is required
    if not file_status.get("customer_features", False):
        print(f"\n[ERROR] Required file 'customer_features.csv' not found!")
        config.print_data_location_guide()
        return None
    
    if missing_files:
        print(f"\n[WARNING] Some optional files are missing: {missing_files}")
        print("Pipeline will continue with available files.")
    
    # Initialize components
    data_loader = RFMDataLoader(config)
    
    visualizer = None
    if RFMVisualizer:
        try:
            visualizer = RFMVisualizer(
                figsize=config.figure_size,
                save_path=config.get_output_path("visualizations"),
                verbose=config.verbose
            )
        except Exception as e:
            print(f"[WARNING] Could not initialize visualizer: {e}")
    
    exporter = None
    if RFMExporter:
        try:
            exporter = RFMExporter(
                output_path=config.base_output_path,
                verbose=config.verbose
            )
        except Exception as e:
            print(f"[WARNING] Could not initialize exporter: {e}")
    
    insight_generator = None
    if RFMInsightGenerator:
        try:
            insight_generator = RFMInsightGenerator(verbose=config.verbose)
        except Exception as e:
            print(f"[WARNING] Could not initialize insight generator: {e}")
    
    results = {}
    
    # Run clustering
    print("\n" + "-" * 70)
    clustering_results = run_clustering_pipeline(config, data_loader, visualizer, exporter, modules)
    results["clustering"] = clustering_results
    
    # Run churn prediction
    print("\n" + "-" * 70)
    churn_results = run_churn_pipeline(config, data_loader, visualizer, exporter, modules)
    results["churn"] = churn_results
    
    # Run CLV prediction
    print("\n" + "-" * 70)
    clv_results = run_clv_pipeline(config, data_loader, visualizer, exporter, modules)
    results["clv"] = clv_results
    
    # Generate insights (if all pipelines succeeded)
    if insight_generator and all(r.get("status") == "success" for r in [clustering_results, churn_results, clv_results]):
        print_section_header("GENERATING COMPREHENSIVE INSIGHTS")
        
        insight_generator.generate_clustering_insights(
            cluster_profiles=clustering_results["cluster_profiles"],
            cluster_labels=clustering_results["cluster_labels"],
            metrics=clustering_results["metrics"]
        )
        
        insight_generator.generate_churn_insights(
            metrics=churn_results["metrics"],
            feature_importances=churn_results["feature_importances"],
            high_risk_count=len(churn_results["high_risk_customers"]),
            total_customers=len(churn_results["customer_ids"])
        )
        
        insight_generator.generate_clv_insights(
            metrics=clv_results["metrics"],
            distribution_analysis=clv_results["distribution_analysis"],
            feature_importances=clv_results["feature_importances"]
        )
        
        executive_summary = insight_generator.generate_executive_summary()
        print(executive_summary)
        
        if exporter:
            exporter.export_insights_report(executive_summary)
    
    # Export master data
    if exporter and all(r.get("status") == "success" for r in [clustering_results, churn_results, clv_results]):
        print_section_header("EXPORTING MASTER CUSTOMER DATA")
        
        cluster_df = pd.DataFrame({
            "customer_id": clustering_results["customer_ids"],
            "cluster_id": clustering_results["labels"],
            "cluster_label": [clustering_results["cluster_labels"].get(l, f"Cluster {l}") 
                            for l in clustering_results["labels"]]
        })
        
        churn_df = pd.DataFrame({
            "customer_id": churn_results["customer_ids"],
            "churn_prediction": churn_results["predictions"],
            "churn_probability": churn_results["probabilities"],
            "risk_level": pd.cut(
                churn_results["probabilities"],
                bins=[0, 0.3, 0.5, 0.7, 1.0],
                labels=["Low", "Medium", "High", "Critical"]
            )
        })
        
        exporter.export_master_customer_data(
            cluster_df=cluster_df,
            churn_df=churn_df,
            clv_df=clv_results["predictions_df"]
        )
    
    # Summary dashboard
    if visualizer and all(r.get("status") == "success" for r in [clustering_results, churn_results, clv_results]):
        print_section_header("CREATING SUMMARY DASHBOARD")
        
        import numpy as np
        
        visualizer.plot_rfm_summary_dashboard(
            cluster_data={
                "cluster_counts": {
                    clustering_results["cluster_labels"].get(k, f"Cluster {k}"): int(v)
                    for k, v in zip(*np.unique(clustering_results["labels"], return_counts=True))
                },
                "metrics": clustering_results["metrics"],
                "n_clusters": len(clustering_results["cluster_labels"])
            },
            churn_data={
                "metrics": churn_results["metrics"],
                "feature_importances": churn_results["feature_importances"],
                "high_risk_count": len(churn_results["high_risk_customers"])
            },
            clv_data={
                "clv_values": clv_results["predictions"],
                "segment_distribution": clv_results["distribution_analysis"].get("segment_distribution", {}),
                "total_clv": clv_results["distribution_analysis"].get("total_predicted_clv", 0),
                "pareto_20_pct": clv_results["distribution_analysis"].get("pareto", {}).get("top_20_pct_revenue_share", 0)
            }
        )
    
    # Show visualizations
    print("\n" + "=" * 70)
    print(" PIPELINE COMPLETED")
    print(f" Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Summary
    success_count = sum(1 for r in [clustering_results, churn_results, clv_results] if r.get("status") == "success")
    print(f"\nPipelines completed: {success_count}/3")
    
    if clustering_results.get("status") == "success":
        print(f"  - Clustering: SUCCESS ({len(clustering_results['cluster_labels'])} clusters)")
    else:
        print(f"  - Clustering: FAILED ({clustering_results.get('error', 'unknown')})")
    
    if churn_results.get("status") == "success":
        print(f"  - Churn: SUCCESS (Accuracy: {churn_results['metrics'].get('accuracy', 0):.2%})")
    else:
        print(f"  - Churn: FAILED ({churn_results.get('error', 'unknown')})")
    
    if clv_results.get("status") == "success":
        print(f"  - CLV: SUCCESS (R2: {clv_results['metrics'].get('r2_score', 0):.4f})")
    else:
        print(f"  - CLV: FAILED ({clv_results.get('error', 'unknown')})")
    
    print(f"\nOutput files saved to: {config.base_output_path}")
    
    if visualizer and config.save_figures:
        print("\nDisplaying visualizations...")
        try:
            visualizer.show_all()
        except Exception as e:
            print(f"[WARNING] Could not display visualizations: {e}")
    
    return results


def main():
    """Main entry point"""
    args = parse_arguments()
    
    # Import modules
    modules = safe_import_modules()
    if modules is None:
        print("\n[ERROR] Failed to import required modules. Exiting.")
        sys.exit(1)
    
    RFMModelConfig = modules['RFMModelConfig']
    
    # Create config
    config = RFMModelConfig()
    
    if args.input:
        config.base_input_path = str(Path(args.input).resolve())
    if args.output:
        config.base_output_path = str(Path(args.output).resolve())
    
    if args.show_guide:
        config.print_data_location_guide()
        return
    
    config.clustering.n_clusters = args.n_clusters
    config.churn.model_type = args.churn_model
    config.churn.churn_threshold_days = args.churn_threshold
    config.clv.model_type = args.clv_model
    config.save_figures = not args.no_viz
    config.verbose = args.verbose
    
    # Run pipeline
    try:
        results = run_complete_pipeline(config, modules)
        
        if results:
            print("\n[OK] Pipeline completed!")
        else:
            print("\n[WARNING] Pipeline exited early due to missing files.")
            
    except FileNotFoundError as e:
        print(f"\n[ERROR] File not found: {e}")
        print("   Use --show-guide to see expected data locations.")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n[ERROR] Pipeline failed: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
