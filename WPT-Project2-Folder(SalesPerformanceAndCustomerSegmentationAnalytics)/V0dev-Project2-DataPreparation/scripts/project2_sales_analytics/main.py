"""
==========================================================================
PROJECT 2: SALES PERFORMANCE & CUSTOMER SEGMENTATION ANALYTICS
==========================================================================
File: main.py
Purpose: Main entry point for Sales Analytics Pipeline (ROBUST VERSION)
Author: v0
Created: 2025
==========================================================================
"""

import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.constants import (
    get_default_date_range,
    FILE_PATHS,
    DATE_CONFIG
)
from modules.api_client import SalesAnalyticsAPIClient
from modules.data_puller import SalesDataPuller
from modules.rfm_analyzer import RFMAnalyzer
from modules.market_basket_analyzer import MarketBasketAnalyzer
from modules.data_enricher import DataEnricher
from utils.exporters import ExcelExporter


def run_sales_analytics(
    api_token: str,
    signature_secret: str,
    start_date: str = None,
    end_date: str = None,
    output_file: str = None,
    resume_from_checkpoint: bool = True,
    debug_mode: bool = True  # Added debug mode parameter
) -> dict:
    """
    Run complete Sales Performance & Customer Segmentation Analytics pipeline.
    
    Args:
        api_token: Accurate Online API token
        signature_secret: Signature secret for HMAC authentication
        start_date: Start date (DD/MM/YYYY), defaults to 365 days ago
        end_date: End date (DD/MM/YYYY), defaults to today
        output_file: Output Excel filename
        resume_from_checkpoint: Whether to resume from checkpoint if available
        debug_mode: Enable detailed logging for troubleshooting
        
    Returns:
        Dictionary with analysis results and statistics
    """
    # ==========================================================================
    # SETUP
    # ==========================================================================
    print("=" * 70)
    print("SALES PERFORMANCE & CUSTOMER SEGMENTATION ANALYTICS")
    print("=" * 70)
    
    if start_date is None or end_date is None:
        start_date, end_date = get_default_date_range()
    
    if output_file is None:
        output_file = FILE_PATHS['OUTPUT_EXCEL']
    
    print(f"Analysis Period: {start_date} to {end_date}")
    print(f"Output File: {output_file}")
    print(f"Debug Mode: {'ON' if debug_mode else 'OFF'}")
    print("=" * 70)
    
    start_time = time.time()
    results = {
        'success': False,
        'validation_passed': False,
        'stages_completed': []
    }
    
    # ==========================================================================
    # STEP 1: INITIALIZE API CLIENT
    # ==========================================================================
    print("\n[STEP 1] Initializing API connection...")
    
    client = SalesAnalyticsAPIClient(api_token, signature_secret)
    
    if not client.initialize_host():
        print("\n[FAIL] Failed to initialize API connection. Check credentials.")
        return {'success': False, 'error': 'API connection failed'}
    
    results['stages_completed'].append('api_init')
    
    # ==========================================================================
    # STEP 2: PULL DATA
    # ==========================================================================
    print("\n[STEP 2] Pulling data from API...")
    
    puller = SalesDataPuller(client, start_date, end_date)
    puller.debug_mode = debug_mode  # Pass debug mode to puller
    
    # Check for checkpoint
    if resume_from_checkpoint and puller.load_checkpoint():
        print("[INFO] Checkpoint found!")
        resume = input("Resume from checkpoint? (y/n): ").lower().strip()
        if resume != 'y':
            print("Starting fresh...")
            puller.clear_checkpoint()
            puller.data = {}
            puller.mappings = {}
    
    # Pull data if not loaded from checkpoint
    if not puller.data or 'sales_details' not in puller.data:
        puller.pull_all_data()
    else:
        print("[OK] Using data from checkpoint")
        if 'sales_by_customer' not in puller.data or puller.data['sales_by_customer'].empty:
            print("[INFO] Re-aggregating sales data...")
            puller.aggregate_sales_by_customer()
            puller.aggregate_sales_by_product()
    
    results['stages_completed'].append('data_pull')
    
    # ==========================================================================
    # STEP 2.5: VALIDATE RAW DATA
    # ==========================================================================
    print("\n[STEP 2.5] Validating raw data...")
    
    validation_passed = _validate_raw_data(puller.data, debug_mode)
    
    if not validation_passed:
        print("\n[WARNING] Raw data validation failed!")
        print("Attempting to continue with enrichment...")
    
    # ==========================================================================
    # STEP 3: ENRICH DATA
    # ==========================================================================
    print("\n[STEP 3] Enriching data...")
    
    enricher = DataEnricher(puller.data, puller.mappings)
    puller.data = enricher.enrich_all()
    
    results['stages_completed'].append('data_enrichment')
    results['enrichment_stats'] = enricher.get_enrichment_stats()
    
    # ==========================================================================
    # STEP 3.5: VALIDATE ENRICHED DATA
    # ==========================================================================
    print("\n[STEP 3.5] Validating enriched data...")
    
    validation_passed = _validate_enriched_data(puller.data, debug_mode)
    results['validation_passed'] = validation_passed
    
    if not validation_passed:
        print("\n[WARNING] Enriched data validation has issues!")
        print("Analysis may produce incomplete results.")
    
    # ==========================================================================
    # STEP 4: RFM ANALYSIS
    # ==========================================================================
    print("\n" + "=" * 70)
    print("[STEP 4] RUNNING RFM ANALYSIS")
    print("=" * 70)
    
    rfm_results = None
    segment_metrics = None
    
    sales_by_customer = puller.data.get('sales_by_customer')
    
    if sales_by_customer is not None and not sales_by_customer.empty:
        valid_customers = sales_by_customer[sales_by_customer['monetary'] > 0]
        
        if len(valid_customers) >= 5:  # Minimum 5 customers for RFM
            print(f"   Analyzing {len(valid_customers):,} customers with purchase history...")
            
            rfm_analyzer = RFMAnalyzer(valid_customers)
            rfm_analyzer.calculate_rfm_scores()
            rfm_analyzer.segment_customers()
            
            rfm_results = rfm_analyzer.get_rfm_results()
            segment_metrics = rfm_analyzer.calculate_segment_metrics()
            
            results['rfm_summary'] = rfm_analyzer.export_summary()
            results['at_risk_customers'] = len(rfm_analyzer.identify_at_risk_customers())
            results['stages_completed'].append('rfm_analysis')
            
            print(f"   [OK] RFM Analysis complete: {len(rfm_results):,} customers segmented")
        else:
            print(f"   [SKIP] Only {len(valid_customers)} customers with monetary > 0")
            print("   Minimum 5 customers required for RFM analysis")
    else:
        print("   [SKIP] No customer data available for RFM analysis")
    
    # ==========================================================================
    # STEP 5: MARKET BASKET ANALYSIS
    # ==========================================================================
    print("\n" + "=" * 70)
    print("[STEP 5] RUNNING MARKET BASKET ANALYSIS")
    print("=" * 70)
    
    mba_rules = None
    product_pairs = None
    
    sales_details = puller.data.get('sales_details')
    
    if sales_details is not None and not sales_details.empty:
        unique_invoices = sales_details['invoice_id'].nunique()
        unique_products = sales_details['product_id'].nunique()
        
        if unique_invoices >= 10 and unique_products >= 2:
            print(f"   Analyzing {unique_invoices:,} transactions, {unique_products:,} products...")
            
            mba_analyzer = MarketBasketAnalyzer(sales_details)
            mba_analyzer.find_frequent_itemsets()
            mba_rules = mba_analyzer.generate_association_rules()
            product_pairs = mba_analyzer.get_frequently_bought_together()
            
            results['mba_summary'] = mba_analyzer.export_summary()
            results['stages_completed'].append('market_basket')
            
            if mba_rules is not None and not mba_rules.empty:
                print(f"   [OK] Found {len(mba_rules):,} association rules")
            else:
                print("   [INFO] No significant association rules found")
        else:
            print(f"   [SKIP] Insufficient data: {unique_invoices} invoices, {unique_products} products")
            print("   Minimum 10 invoices and 2 products required")
    else:
        print("   [SKIP] No sales details available for Market Basket Analysis")
    
    # ==========================================================================
    # STEP 6: EXPORT RESULTS
    # ==========================================================================
    print("\n" + "=" * 70)
    print("[STEP 6] EXPORTING RESULTS")
    print("=" * 70)
    
    exporter = ExcelExporter()
    
    export_success = exporter.export_analysis_results(
        rfm_results=rfm_results,
        segment_metrics=segment_metrics,
        market_basket_rules=mba_rules,
        product_pairs=product_pairs,
        sales_by_customer=puller.data.get('sales_by_customer'),
        sales_by_product=puller.data.get('sales_by_product'),
        sales_details=puller.data.get('sales_details'),  # Added sales_details
        customers=puller.data.get('customers'),
        items=puller.data.get('items'),
        summary_stats={
            'analysis_date': datetime.now().isoformat(),
            'period_start': start_date,
            'period_end': end_date,
            'validation_passed': validation_passed,
            **results.get('rfm_summary', {}),
            **results.get('mba_summary', {}),
        },
        filename=output_file
    )
    
    if export_success:
        results['stages_completed'].append('export')
    
    # ==========================================================================
    # SUMMARY
    # ==========================================================================
    end_time = time.time()
    duration_minutes = (end_time - start_time) / 60
    
    api_stats = client.get_statistics()
    
    print("\n" + "=" * 70)
    print("PIPELINE SUMMARY")
    print("=" * 70)
    print(f"Output: {output_file}")
    print(f"Duration: {duration_minutes:.1f} minutes")
    print(f"API Requests: {api_stats['total_requests']}")
    print(f"Success Rate: {api_stats['success_rate']:.1f}%")
    print(f"Stages Completed: {', '.join(results['stages_completed'])}")
    print(f"Validation Passed: {'Yes' if validation_passed else 'No (check warnings)'}")
    
    if rfm_results is not None:
        print(f"\nRFM Analysis:")
        print(f"   Customers analyzed: {len(rfm_results):,}")
        print(f"   Segments identified: {rfm_results['segment'].nunique()}")
    
    if mba_rules is not None and not mba_rules.empty:
        print(f"\nMarket Basket Analysis:")
        print(f"   Association rules: {len(mba_rules):,}")
        if product_pairs is not None:
            print(f"   Product pairs: {len(product_pairs):,}")
    
    # Clean up checkpoint on success
    if export_success:
        puller.clear_checkpoint()
    
    results['success'] = export_success
    results['duration_minutes'] = duration_minutes
    results['api_stats'] = api_stats
    
    return results


def _validate_raw_data(data: dict, debug_mode: bool = False) -> bool:
    """
    Validate raw pulled data before enrichment.
    
    Returns:
        True if validation passes, False otherwise
    """
    issues = []
    
    # Check sales_details
    if 'sales_details' not in data or data['sales_details'].empty:
        issues.append("sales_details is empty")
    else:
        df = data['sales_details']
        
        # Check customer_id
        valid_customer = (df['customer_id'] != '') & df['customer_id'].notna()
        if valid_customer.sum() == 0:
            issues.append("No valid customer_id in sales_details")
        elif debug_mode:
            print(f"   customer_id: {valid_customer.sum():,}/{len(df):,} valid")
        
        # Check product_id
        valid_product = (df['product_id'] != '') & df['product_id'].notna()
        if valid_product.sum() == 0:
            issues.append("No valid product_id in sales_details")
        elif debug_mode:
            print(f"   product_id: {valid_product.sum():,}/{len(df):,} valid")
        
        # Check amounts
        valid_amount = df['total_amount'] > 0
        if valid_amount.sum() == 0:
            issues.append("No valid total_amount in sales_details (all zero)")
        elif debug_mode:
            print(f"   total_amount > 0: {valid_amount.sum():,}/{len(df):,}")
    
    # Check customers master
    if 'customers' not in data or data['customers'].empty:
        issues.append("customers master is empty")
    elif debug_mode:
        print(f"   customers: {len(data['customers']):,} records")
    
    # Check items master
    if 'items' not in data or data['items'].empty:
        issues.append("items master is empty")
    elif debug_mode:
        print(f"   items: {len(data['items']):,} records")
    
    if issues:
        print("\n   [VALIDATION ISSUES]")
        for issue in issues:
            print(f"   - {issue}")
        return False
    
    print("   [OK] Raw data validation passed")
    return True


def _validate_enriched_data(data: dict, debug_mode: bool = False) -> bool:
    """
    Validate enriched data before analysis.
    
    Returns:
        True if validation passes, False otherwise
    """
    issues = []
    
    # Check sales_by_customer (critical for RFM)
    if 'sales_by_customer' not in data or data['sales_by_customer'].empty:
        issues.append("sales_by_customer is empty - RFM will fail")
    else:
        df = data['sales_by_customer']
        valid_monetary = (df['monetary'] > 0).sum()
        
        if valid_monetary == 0:
            issues.append("No customers with monetary > 0")
        elif debug_mode:
            print(f"   sales_by_customer: {len(df):,} customers, {valid_monetary:,} with revenue")
            print(f"   Total monetary: Rp {df['monetary'].sum():,.0f}")
    
    # Check sales_by_product
    if 'sales_by_product' not in data or data['sales_by_product'].empty:
        issues.append("sales_by_product is empty")
    else:
        df = data['sales_by_product']
        valid_revenue = (df['total_revenue'] > 0).sum()
        
        if valid_revenue == 0:
            issues.append("No products with revenue > 0")
        elif debug_mode:
            print(f"   sales_by_product: {len(df):,} products, {valid_revenue:,} with revenue")
            print(f"   Total revenue: Rp {df['total_revenue'].sum():,.0f}")
    
    if issues:
        print("\n   [VALIDATION ISSUES]")
        for issue in issues:
            print(f"   - {issue}")
        return False
    
    print("   [OK] Enriched data validation passed")
    return True


# ==========================================================================
# MAIN EXECUTION
# ==========================================================================
if __name__ == "__main__":
    # ==========================================================================
    # CONFIGURATION - UPDATE THESE VALUES
    # ==========================================================================
    API_TOKEN = "aat.NTA.eyJ2IjoxLCJ1IjoxMDIyNDE2LCJkIjo5NDY3OTMsImFpIjo2MDMxMiwiYWsiOiIwOGRlZmNiMC1kNjEzLTQxYjgtOGI5YS0zOWNhNjQ1OWIzOTkiLCJhbiI6IkFwbGlrYXNpIC0gRGF0YSBDb2xsZWN0aW9uIiwiYXAiOiI2NzgwZTA1YS0wNjQ3LTQ2NzktYmEyYi1jMWE4YWEyZGZjYWUiLCJ0IjoxNzYwMDkwNzI4OTcwfQ.LemzKJp8Tgp+yacEUvUM8hgTrUbb2rhCgNrpW/WsznGtvusfjeVV7AkqPShw0QvqL4bUey3k7BbifqwJVtTVAFp84BfyrC0/YwM7Xl5zycmf95dsJZV8we1yD13KRDcG5PoBCqh5Y4CY0oz39gBPM5oMcy9PZixjYKSc8/LaqfMMZLfaYMPuGjb5ppq9KbLVqFWQSbheqRc=.McqkDx7gdPa9Fzn501K/Fsfzzb8N7iF08un74VZqQaA"
    SIGNATURE_SECRET = "VdQuYB9APtdyJxgFOGr8CtSMUtjVjmeTxDRhnrnOuh9el8qft2h5RO61ftO1Zr5l"
    
    # Optional: Custom date range (default: last 365 days)
    START_DATE = "01/10/2025"
    END_DATE = "31/12/2025"
    
    # Debug mode: Set to True for detailed logging
    DEBUG_MODE = True
    
    # ==========================================================================
    # RUN ANALYTICS
    # ==========================================================================
    try:
        results = run_sales_analytics(
            api_token=API_TOKEN,
            signature_secret=SIGNATURE_SECRET,
            start_date=START_DATE,  # Uncomment to use custom dates
            end_date=END_DATE,
            debug_mode=DEBUG_MODE,
        )
        
        if results.get('success'):
            print("\n[SUCCESS] Analysis completed successfully!")
        else:
            print("\n[WARNING] Analysis completed with issues")
            if not results.get('validation_passed'):
                print("Check the validation warnings above for details")
            
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Interrupted by user")
        print("Run again to resume from checkpoint")
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
