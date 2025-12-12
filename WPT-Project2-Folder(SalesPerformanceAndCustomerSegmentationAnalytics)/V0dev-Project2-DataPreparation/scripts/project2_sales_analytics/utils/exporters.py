"""
==========================================================================
PROJECT 2: SALES PERFORMANCE & CUSTOMER SEGMENTATION ANALYTICS
==========================================================================
File: utils/exporters.py
Purpose: Data export utilities for Excel and CSV
Author: v0
Created: 2025
==========================================================================

OVERVIEW:
---------
Handles exporting analysis results to various formats:
- Excel with multiple sheets
- CSV files
- Summary reports

USAGE:
------
    from utils.exporters import ExcelExporter
    
    exporter = ExcelExporter()
    exporter.export_analysis_results(data_dict, 'output.xlsx')
"""

import os
import pandas as pd
from typing import Dict, Optional, List, Any
from datetime import datetime

import sys
sys.path.append('..')
from config.constants import EXPORT_CONFIG, FILE_PATHS


class ExcelExporter:
    """
    Excel Exporter for analysis results.
    
    Handles multi-sheet Excel exports with proper formatting.
    """
    
    def __init__(self):
        """Initialize Excel Exporter."""
        self.sheets_exported = 0
    
    def export_analysis_results(
        self,
        rfm_results: Optional[pd.DataFrame] = None,
        segment_metrics: Optional[pd.DataFrame] = None,
        market_basket_rules: Optional[pd.DataFrame] = None,
        product_pairs: Optional[pd.DataFrame] = None,
        sales_by_customer: Optional[pd.DataFrame] = None,
        sales_by_product: Optional[pd.DataFrame] = None,
        sales_details: Optional[pd.DataFrame] = None,  # Added sales_details parameter
        customers: Optional[pd.DataFrame] = None,
        items: Optional[pd.DataFrame] = None,
        summary_stats: Optional[Dict] = None,
        filename: Optional[str] = None
    ) -> bool:
        """
        Export all analysis results to Excel.
        
        Args:
            rfm_results: RFM analysis results
            segment_metrics: Segment-level metrics
            market_basket_rules: Association rules
            product_pairs: Frequently bought together pairs
            sales_by_customer: Customer sales aggregations
            sales_by_product: Product sales aggregations
            sales_details: Raw sales details data
            customers: Customer master data
            items: Item master data
            summary_stats: Summary statistics dictionary
            filename: Output filename
            
        Returns:
            True if export successful
        """
        if filename is None:
            filename = FILE_PATHS['OUTPUT_EXCEL']
        
        print("\n" + "=" * 60)
        print("EXPORTING ANALYSIS RESULTS")
        print("=" * 60)
        
        try:
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                self.sheets_exported = 0
                
                # 1. RFM Analysis
                if rfm_results is not None and not rfm_results.empty:
                    self._write_sheet(
                        writer, 
                        rfm_results, 
                        EXPORT_CONFIG['SHEETS']['rfm_analysis']
                    )
                
                # 2. Segment Metrics
                if segment_metrics is not None and not segment_metrics.empty:
                    self._write_sheet(
                        writer, 
                        segment_metrics, 
                        EXPORT_CONFIG['SHEETS']['customer_segments']
                    )
                
                # 3. Market Basket Rules
                if market_basket_rules is not None and not market_basket_rules.empty:
                    # Drop frozenset columns for Excel
                    export_df = market_basket_rules.copy()
                    cols_to_drop = ['antecedent', 'consequent']
                    export_df = export_df.drop(
                        columns=[c for c in cols_to_drop if c in export_df.columns], 
                        errors='ignore'
                    )
                    self._write_sheet(
                        writer, 
                        export_df, 
                        EXPORT_CONFIG['SHEETS']['market_basket']
                    )
                
                # 4. Product Associations (Frequently Bought Together)
                if product_pairs is not None and not product_pairs.empty:
                    self._write_sheet(
                        writer, 
                        product_pairs, 
                        EXPORT_CONFIG['SHEETS']['product_associations']
                    )
                
                if sales_details is not None and not sales_details.empty:
                    # Limit to 100k rows for Excel performance
                    export_df = sales_details.head(100000)
                    self._write_sheet(
                        writer, 
                        export_df, 
                        EXPORT_CONFIG['SHEETS']['sales_details']
                    )
                    if len(sales_details) > 100000:
                        print(f"      (truncated from {len(sales_details):,} rows)")
                
                # 6. Sales by Customer
                if sales_by_customer is not None and not sales_by_customer.empty:
                    self._write_sheet(
                        writer, 
                        sales_by_customer, 
                        EXPORT_CONFIG['SHEETS']['sales_by_customer']
                    )
                
                # 7. Sales by Product
                if sales_by_product is not None and not sales_by_product.empty:
                    self._write_sheet(
                        writer, 
                        sales_by_product, 
                        EXPORT_CONFIG['SHEETS']['sales_by_product']
                    )
                
                # 8. Customer Master
                if customers is not None and not customers.empty:
                    self._write_sheet(
                        writer, 
                        customers, 
                        EXPORT_CONFIG['SHEETS']['customer_master']
                    )
                
                # 9. Item Master
                if items is not None and not items.empty:
                    self._write_sheet(
                        writer, 
                        items, 
                        EXPORT_CONFIG['SHEETS']['item_master']
                    )
                
                # 10. Summary Statistics
                if summary_stats:
                    summary_df = self._dict_to_dataframe(summary_stats)
                    self._write_sheet(
                        writer, 
                        summary_df, 
                        EXPORT_CONFIG['SHEETS']['summary_stats']
                    )
            
            if self.sheets_exported > 0:
                print(f"\n[OK] Exported {self.sheets_exported} sheets to: {filename}")
                return True
            else:
                print("[FAIL] No data to export")
                return False
                
        except Exception as e:
            print(f"[ERROR] Export error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _write_sheet(
        self, 
        writer: pd.ExcelWriter, 
        df: pd.DataFrame, 
        sheet_name: str
    ) -> None:
        """Write DataFrame to Excel sheet."""
        safe_name = sheet_name[:31]
        
        export_df = df.copy()
        for col in export_df.columns:
            if export_df[col].dtype == 'datetime64[ns]':
                export_df[col] = export_df[col].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        export_df.to_excel(writer, sheet_name=safe_name, index=False)
        print(f"   [OK] {sheet_name}: {len(df):,} rows")
        self.sheets_exported += 1
    
    def _dict_to_dataframe(self, data: Dict[str, Any]) -> pd.DataFrame:
        """
        Convert dictionary to DataFrame for export.
        
        Handles nested dictionaries and various data types.
        """
        rows = []
        
        def flatten_dict(d: Dict, prefix: str = ''):
            """Recursively flatten nested dictionaries."""
            for key, value in d.items():
                full_key = f"{prefix}{key}" if not prefix else f"{prefix}.{key}"
                
                if isinstance(value, dict):
                    flatten_dict(value, full_key)
                elif isinstance(value, (list, tuple)):
                    rows.append({
                        'Metric': full_key,
                        'Value': str(value)
                    })
                else:
                    # Format numbers nicely
                    if isinstance(value, float):
                        if value > 1000000:
                            formatted = f"{value:,.0f}"
                        elif value > 1:
                            formatted = f"{value:,.2f}"
                        else:
                            formatted = f"{value:.4f}"
                        rows.append({'Metric': full_key, 'Value': formatted})
                    else:
                        rows.append({'Metric': full_key, 'Value': value})
        
        flatten_dict(data)
        
        if rows:
            return pd.DataFrame(rows)
        return pd.DataFrame(columns=['Metric', 'Value'])

    def export_to_csv(
        self,
        data: Dict[str, pd.DataFrame],
        output_folder: Optional[str] = None
    ) -> bool:
        """
        Export all DataFrames to CSV files.
        
        Args:
            data: Dictionary of DataFrames
            output_folder: Output folder path
            
        Returns:
            True if export successful
        """
        if output_folder is None:
            output_folder = FILE_PATHS['OUTPUT_CSV_FOLDER']
        
        print(f"\n📁 Exporting CSVs to: {output_folder}")
        
        try:
            os.makedirs(output_folder, exist_ok=True)
            
            files_exported = 0
            for name, df in data.items():
                if isinstance(df, pd.DataFrame) and not df.empty:
                    filepath = os.path.join(output_folder, f"{name}.csv")
                    df.to_csv(filepath, index=False)
                    print(f"   ✓ {name}.csv: {len(df):,} rows")
                    files_exported += 1
            
            print(f"✅ Exported {files_exported} CSV files")
            return True
            
        except Exception as e:
            print(f"❌ CSV export error: {e}")
            return False
