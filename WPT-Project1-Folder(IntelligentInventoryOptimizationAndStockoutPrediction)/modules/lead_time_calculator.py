"""
Lead Time Calculator - Per Product
===================================

Calculate actual lead times per product from:
- Purchase Order date (trans_date from purchase_details)
- Receipt Invoice date (transactionDate from stock_mutations where transactionType='RI')

Formula: lead_time = receipt_date - po_date (in days)

Author: AI Assistant
Date: January 2026
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import logging
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def calculate_lead_times_per_product():
    """Calculate actual lead times per product from PO and RI data"""
    
    logger.info("=" * 60)
    logger.info("LEAD TIME CALCULATION - PER PRODUCT")
    logger.info("=" * 60)
    
    # Load data
    logger.info("\n[PHASE 1] Loading Data")
    
    pd_path = Path("../data/pulled/purchase_details.csv")
    mutations_path = Path("../data/pulled/stock_mutations.csv")
    
    if not pd_path.exists() or not mutations_path.exists():
        logger.error("Required files not found")
        return None
    
    purchase_details = pd.read_csv(pd_path, encoding='utf-8-sig')
    mutations = pd.read_csv(mutations_path, encoding='utf-8-sig')
    
    logger.info(f"  Purchase Details: {len(purchase_details)} records")
    logger.info(f"  Stock Mutations: {len(mutations)} records")
    
    # Get PO data with item_id and date
    logger.info("\n[PHASE 2] Extracting PO Dates")
    
    po_df = purchase_details[['item_id', 'trans_date']].copy()
    po_df['trans_date'] = pd.to_datetime(po_df['trans_date'], format='%d/%m/%Y', errors='coerce')
    po_df = po_df.dropna(subset=['item_id', 'trans_date'])
    po_df['item_id'] = po_df['item_id'].astype(int)
    
    logger.info(f"  Valid PO records: {len(po_df)}")
    logger.info(f"  PO date range: {po_df['trans_date'].min().date()} to {po_df['trans_date'].max().date()}")
    
    # Get RI (Receipt Invoice) data
    logger.info("\n[PHASE 3] Extracting RI (Receipt) Dates")
    
    ri_df = mutations[mutations['transactionType'] == 'RI'][['product_id', 'transactionDate']].copy()
    ri_df['transactionDate'] = pd.to_datetime(ri_df['transactionDate'], format='%d/%m/%Y', errors='coerce')
    ri_df = ri_df.dropna(subset=['product_id', 'transactionDate'])
    ri_df['product_id'] = ri_df['product_id'].astype(int)
    
    logger.info(f"  Valid RI records: {len(ri_df)}")
    logger.info(f"  RI date range: {ri_df['transactionDate'].min().date()} to {ri_df['transactionDate'].max().date()}")
    
    # Calculate lead times per product
    logger.info("\n[PHASE 4] Calculating Lead Times per Product")
    
    lead_time_records = []
    
    # Get common items
    common_items = set(po_df['item_id'].unique()) & set(ri_df['product_id'].unique())
    logger.info(f"  Common items (PO & RI): {len(common_items)}")
    
    for item_id in common_items:
        # Get all PO dates for this item
        item_po_dates = po_df[po_df['item_id'] == item_id]['trans_date'].sort_values()
        
        # Get all RI dates for this item
        item_ri_dates = ri_df[ri_df['product_id'] == item_id]['transactionDate'].sort_values()
        
        item_lead_times = []
        
        # For each RI, find the closest preceding PO
        for ri_date in item_ri_dates:
            preceding_po = item_po_dates[item_po_dates <= ri_date]
            
            if not preceding_po.empty:
                closest_po_date = preceding_po.max()
                lt_days = (ri_date - closest_po_date).days
                
                # Valid lead time: 1-180 days
                if 1 <= lt_days <= 180:
                    item_lead_times.append(lt_days)
        
        if item_lead_times:
            lead_time_records.append({
                'item_id': int(item_id),
                'lead_time_mean': round(np.mean(item_lead_times), 1),
                'lead_time_median': round(np.median(item_lead_times), 1),
                'lead_time_std': round(np.std(item_lead_times), 1) if len(item_lead_times) > 1 else 0,
                'lead_time_min': int(min(item_lead_times)),
                'lead_time_max': int(max(item_lead_times)),
                'sample_count': len(item_lead_times)
            })
    
    # Create DataFrame
    lt_df = pd.DataFrame(lead_time_records)
    
    if lt_df.empty:
        logger.warning("  No lead times calculated!")
        return None
    
    logger.info(f"  Calculated lead times for {len(lt_df)} products")
    
    # Overall statistics
    logger.info("\n[PHASE 5] Overall Statistics")
    
    all_mean = lt_df['lead_time_mean'].mean()
    all_median = lt_df['lead_time_median'].median()
    
    stats = {
        'total_products_with_lead_time': len(lt_df),
        'overall_mean': round(all_mean, 1),
        'overall_median': round(all_median, 1),
        'products_lt_7_days': int((lt_df['lead_time_median'] <= 7).sum()),
        'products_7_14_days': int(((lt_df['lead_time_median'] > 7) & (lt_df['lead_time_median'] <= 14)).sum()),
        'products_14_30_days': int(((lt_df['lead_time_median'] > 14) & (lt_df['lead_time_median'] <= 30)).sum()),
        'products_30_60_days': int(((lt_df['lead_time_median'] > 30) & (lt_df['lead_time_median'] <= 60)).sum()),
        'products_60plus_days': int((lt_df['lead_time_median'] > 60).sum())
    }
    
    logger.info(f"  Overall Mean: {stats['overall_mean']} days")
    logger.info(f"  Overall Median: {stats['overall_median']} days")
    logger.info(f"  Distribution:")
    logger.info(f"    <= 7 days: {stats['products_lt_7_days']} products")
    logger.info(f"    7-14 days: {stats['products_7_14_days']} products")
    logger.info(f"    14-30 days: {stats['products_14_30_days']} products")
    logger.info(f"    30-60 days: {stats['products_30_60_days']} products")
    logger.info(f"    > 60 days: {stats['products_60plus_days']} products")
    
    # Save results
    logger.info("\n[PHASE 6] Saving Results")
    
    output_dir = Path("../data/features")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save per-product lead times
    lt_df.to_csv(output_dir / 'product_lead_times.csv', index=False, encoding='utf-8-sig')
    logger.info(f"  Saved product_lead_times.csv ({len(lt_df)} products)")
    
    # Save statistics
    with open(output_dir / 'lead_time_stats.json', 'w') as f:
        json.dump({
            'calculated_at': datetime.now().isoformat(),
            'statistics': stats,
            'default_lead_time_recommendation': int(round(all_median)),
            'safe_lead_time_recommendation': int(round(all_mean + 1.65 * lt_df['lead_time_std'].mean())),
            'data_source': 'Calculated from purchase_details.trans_date to stock_mutations.transactionDate (RI)'
        }, f, indent=2)
    logger.info(f"  Saved lead_time_stats.json")
    
    logger.info("\n" + "=" * 60)
    logger.info("LEAD TIME CALCULATION COMPLETE")
    logger.info("=" * 60)
    
    return lt_df, stats


if __name__ == '__main__':
    result = calculate_lead_times_per_product()
    
    if result:
        lt_df, stats = result
        print(f"\nProducts with lead time data: {len(lt_df)}")
        print(f"Default lead time (median): {stats['overall_median']} days")
