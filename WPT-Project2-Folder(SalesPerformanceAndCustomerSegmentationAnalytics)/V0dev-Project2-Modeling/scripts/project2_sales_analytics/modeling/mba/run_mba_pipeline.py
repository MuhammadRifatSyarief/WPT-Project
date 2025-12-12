"""
MBA Pipeline Runner
===================

Main entry point for running the complete Market Basket Analysis pipeline.

Author: Project 2 - Sales Analytics
Version: 1.1.0

Usage:
    # Default (data di scripts/project2_sales_analytics/output/features/csv/)
    python run_mba_pipeline.py
    
    # Dengan absolute path
    python run_mba_pipeline.py --input "D:/path/to/sales_details.csv"
    
    # Dengan custom parameters
    python run_mba_pipeline.py --min-support 0.01 --min-confidence 0.3
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Run Market Basket Analysis Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
DATA LOCATION:
  Taruh file feature engineering di:
    scripts/project2_sales_analytics/output/features/csv/sales_details.csv
  
  Atau gunakan --input dengan absolute path:
    python run_mba_pipeline.py --input "D:/path/to/sales_details.csv"
        """
    )
    
    parser.add_argument(
        '--input', '-i',
        type=str,
        default=None,  # Default None, akan dihandle oleh config
        help='Path to input transaction data (absolute or relative to project)'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,  # Default None, akan dihandle oleh config
        help='Output directory'
    )
    
    parser.add_argument(
        '--feature-dir', '-f',
        type=str,
        default=None,
        help='Directory containing feature engineering output files'
    )
    
    parser.add_argument(
        '--min-support',
        type=float,
        default=0.01,
        help='Minimum support threshold (default: 0.01)'
    )
    
    parser.add_argument(
        '--min-confidence',
        type=float,
        default=0.3,
        help='Minimum confidence threshold (default: 0.3)'
    )
    
    parser.add_argument(
        '--min-lift',
        type=float,
        default=1.0,
        help='Minimum lift threshold (default: 1.0)'
    )
    
    parser.add_argument(
        '--algorithm',
        type=str,
        choices=['apriori', 'fpgrowth'],
        default='fpgrowth',
        help='Algorithm to use (default: fpgrowth)'
    )
    
    parser.add_argument(
        '--max-length',
        type=int,
        default=4,
        help='Maximum itemset length (default: 4)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--show-guide',
        action='store_true',
        help='Show data location guide and exit'
    )
    
    return parser.parse_args()


def run_pipeline(args):
    """
    Run the complete MBA pipeline.
    
    Args:
        args: Parsed command line arguments
    """
    from config.mba_config import MBAConfig
    from data.data_loader import MBADataLoader
    from preprocessing.data_cleaner import DataCleaner
    from preprocessing.transaction_encoder import TransactionEncoder
    from algorithms.fpgrowth_runner import FPGrowthRunner
    from algorithms.apriori_runner import AprioriRunner
    from analysis.rules_analyzer import RulesAnalyzer
    from analysis.cross_sell_recommender import CrossSellRecommender
    from analysis.product_network import ProductNetwork
    from export.mba_exporter import MBAExporter
    
    config_kwargs = {
        'min_support': args.min_support,
        'min_confidence': args.min_confidence,
        'min_lift': args.min_lift,
        'max_length': args.max_length,
        'algorithm': args.algorithm,
        'verbose': args.verbose
    }
    
    # Only set paths if explicitly provided
    if args.input:
        config_kwargs['input_path'] = args.input
    if args.output:
        config_kwargs['output_dir'] = args.output
    if args.feature_dir:
        config_kwargs['feature_engineering_dir'] = args.feature_dir
    
    # Step 1: Initialize configuration
    print("\n[STEP 1] Initializing configuration...")
    config = MBAConfig(**config_kwargs)
    
    if args.show_guide:
        config.print_data_location_guide()
        return None
    
    print("\n" + "=" * 70)
    print(" MARKET BASKET ANALYSIS PIPELINE")
    print("=" * 70)
    print(f"Input: {config.input_path}")
    print(f"Output: {config.output_dir}")
    print(f"Algorithm: {args.algorithm.upper()}")
    print(f"Parameters: min_support={args.min_support}, min_confidence={args.min_confidence}, min_lift={args.min_lift}")
    print("=" * 70 + "\n")
    
    print(f"   Config initialized: {config}")
    
    input_path = Path(config.input_path)
    if not input_path.exists():
        print(f"\n[ERROR] Input file not found: {config.input_path}")
        config.print_data_location_guide()
        return None
    
    # Step 2: Load data
    print("\n[STEP 2] Loading transaction data...")
    loader = MBADataLoader(config)
    df = loader.load()
    
    is_valid, messages = loader.validate()
    if not is_valid:
        print("[ERROR] Data validation failed:")
        for msg in messages:
            print(f"   - {msg}")
        return None
    
    if args.verbose:
        loader.preview()
    
    # Step 3: Clean data
    print("\n[STEP 3] Cleaning transaction data...")
    cleaner = DataCleaner(config)
    df_clean = cleaner.clean(df)
    
    if args.verbose:
        cleaner.print_stats()
    
    # Step 4: Encode transactions
    print("\n[STEP 4] Encoding transactions to binary matrix...")
    encoder = TransactionEncoder(config)
    transactions, basket_matrix = encoder.encode(df_clean)
    
    if args.verbose:
        encoder.print_stats()
    
    # Step 5: Run association rule mining
    print(f"\n[STEP 5] Running {args.algorithm.upper()} algorithm...")
    
    if args.algorithm.lower() == 'fpgrowth':
        runner = FPGrowthRunner(config)
    else:
        runner = AprioriRunner(config)
    
    frequent_itemsets, rules = runner.run(basket_matrix)
    
    if args.verbose:
        runner.print_summary()
    
    # Check if we have rules
    if len(rules) == 0:
        print("\n[WARNING] No association rules found!")
        print("   Try lowering min_support or min_confidence thresholds.")
        return None
    
    # Step 6: Analyze rules
    print("\n[STEP 6] Analyzing association rules...")
    analyzer = RulesAnalyzer(rules, config)
    analysis_results = analyzer.analyze()
    
    if args.verbose:
        analyzer.print_summary()
    
    # Step 7: Generate cross-sell recommendations
    print("\n[STEP 7] Generating cross-sell recommendations...")
    recommender = CrossSellRecommender(rules, config)
    cross_sell_report = recommender.generate_cross_sell_report()
    
    print(f"   Generated {len(cross_sell_report)} product recommendations")
    
    # Step 8: Build product network
    print("\n[STEP 8] Building product network...")
    network = ProductNetwork(rules, config)
    network.build()
    network_data = network.export_for_visualization()
    
    print(f"   Network: {network_data['stats']['node_count']} nodes, "
          f"{network_data['stats']['edge_count']} edges")
    
    # Step 9: Export results
    print("\n[STEP 9] Exporting results...")
    exporter = MBAExporter(config)
    exported_files = exporter.export_all(
        rules=rules,
        frequent_itemsets=frequent_itemsets,
        analysis_results=analysis_results,
        cross_sell_report=cross_sell_report,
        network_data=network_data
    )
    
    # Final summary
    print("\n" + "=" * 70)
    print(" PIPELINE COMPLETE")
    print("=" * 70)
    
    print(f"\nResults Summary:")
    print(f"  - Frequent Itemsets: {len(frequent_itemsets):,}")
    print(f"  - Association Rules: {len(rules):,}")
    print(f"  - Cross-sell Products: {len(cross_sell_report):,}")
    print(f"  - Network Nodes: {network_data['stats']['node_count']:,}")
    
    print(f"\nOutput Directory: {config.output_dir}")
    print("\nStreamlit Integration:")
    print("  ------------------------------------")
    print("  import joblib")
    print(f"  data = joblib.load('{config.output_dir}/pkl/mba_streamlit_data.pkl')")
    print("  rules = data['data']['association_rules']")
    print("  cross_sell = data['data']['cross_sell_report']")
    print("  ------------------------------------")
    
    return {
        'rules': rules,
        'itemsets': frequent_itemsets,
        'analysis': analysis_results,
        'cross_sell': cross_sell_report,
        'exported_files': exported_files
    }


def main():
    """Main entry point."""
    args = parse_arguments()
    
    try:
        results = run_pipeline(args)
        
        if results:
            print("\n[OK] Pipeline completed successfully!")
        else:
            print("\n[WARNING] Pipeline completed with warnings or exited early.")
            
    except FileNotFoundError as e:
        print(f"\n[ERROR] File not found: {e}")
        print("   Make sure to run Feature Engineering pipeline first.")
        print("   Use --show-guide to see expected data locations.")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n[ERROR] Pipeline failed: {e}")
        logger.exception("Pipeline error:")
        sys.exit(1)


if __name__ == "__main__":
    main()
