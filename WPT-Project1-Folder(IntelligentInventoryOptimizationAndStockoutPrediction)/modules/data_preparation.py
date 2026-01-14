"""
Module 2: Data Preparation & Enrichment
========================================

Project 1 - Intelligent Inventory Optimization & Stockout Prediction

Key Features:
1. Data Cleansing - standardize formats, remove duplicates
2. Cross-Endpoint Enrichment - fill null values using related data
3. Data Validation - quality scoring and completeness checks
4. Imputation - smart filling of remaining nulls

Author: AI Assistant
Date: January 2026
Version: 1.0.0
"""

import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List, Any, Tuple
from dataclasses import dataclass, field
import warnings

warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class PreparationConfig:
    """Configuration for data preparation"""
    # Input/Output
    input_dir: str = "../data/pulled"
    output_dir: str = "../data/prepared"
    
    # Enrichment settings
    price_margin_estimate: float = 0.6  # avgCost = sellingPrice * 0.6
    min_selling_price: float = 1000.0   # Minimum Rp 1,000
    min_avg_cost: float = 500.0         # Minimum Rp 500
    
    # Validation thresholds
    min_quality_score: float = 70.0     # Minimum acceptable quality score
    max_null_ratio: float = 0.3         # Max 30% null values per column
    
    # Category defaults
    default_category: str = "Uncategorized"
    default_minimum_stock: int = 5


# =============================================================================
# DATA LOADER
# =============================================================================

class DataLoader:
    """Load CSV data from pulled directory"""
    
    def __init__(self, input_dir: str):
        self.input_dir = Path(input_dir)
        self.data: Dict[str, pd.DataFrame] = {}
    
    def load_all(self) -> Dict[str, pd.DataFrame]:
        """Load all CSV files from input directory"""
        if not self.input_dir.exists():
            raise FileNotFoundError(f"Input directory not found: {self.input_dir}")
        
        logger.info(f"📂 Loading data from {self.input_dir.absolute()}...")
        
        csv_files = list(self.input_dir.glob("*.csv"))
        if not csv_files:
            raise FileNotFoundError(f"No CSV files found in {self.input_dir}")
        
        for csv_file in csv_files:
            name = csv_file.stem
            try:
                df = pd.read_csv(csv_file, encoding='utf-8-sig')
                self.data[name] = df
                logger.info(f"  ✓ {name}: {len(df):,} records, {len(df.columns)} columns")
            except Exception as e:
                logger.error(f"  ✗ Failed to load {name}: {e}")
        
        return self.data
    
    def get(self, name: str) -> pd.DataFrame:
        """Get specific DataFrame by name"""
        return self.data.get(name, pd.DataFrame())


# =============================================================================
# DATA CLEANSER
# =============================================================================

class DataCleanser:
    """Clean and standardize data"""
    
    def __init__(self, config: PreparationConfig):
        self.config = config
        self.cleaning_stats = {}
    
    def clean_items(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean items master data"""
        original_count = len(df)
        
        # Remove duplicates by ID
        df = df.drop_duplicates(subset=['id'], keep='first')
        
        # Standardize text fields
        if 'name' in df.columns:
            df['name'] = df['name'].fillna('').str.strip()
        
        if 'no' in df.columns:
            df['no'] = df['no'].fillna('').str.strip().str.upper()
        
        # Fill missing category
        if 'itemCategoryName' in df.columns:
            df['itemCategoryName'] = df['itemCategoryName'].fillna(self.config.default_category)
            df.loc[df['itemCategoryName'] == '', 'itemCategoryName'] = self.config.default_category
        
        # Ensure numeric fields are numeric
        numeric_cols = ['unitPrice', 'avgCost', 'minimumStock']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        self.cleaning_stats['items'] = {
            'original': original_count,
            'cleaned': len(df),
            'duplicates_removed': original_count - len(df)
        }
        
        logger.info(f"  [Items] Cleaned: {original_count} → {len(df)} records")
        return df
    
    def clean_stock(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean current stock data"""
        original_count = len(df)
        
        # Remove duplicates by product_id + warehouseId
        if 'product_id' in df.columns and 'warehouseId' in df.columns:
            df = df.drop_duplicates(subset=['product_id', 'warehouseId'], keep='first')
        
        # Ensure quantity is numeric and non-negative
        for col in ['quantity', 'quantity_available']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                df[col] = df[col].clip(lower=0)
        
        self.cleaning_stats['current_stock'] = {
            'original': original_count,
            'cleaned': len(df)
        }
        
        logger.info(f"  [Stock] Cleaned: {original_count} → {len(df)} records")
        return df
    
    def clean_sales_details(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean sales details data"""
        original_count = len(df)
        
        # Ensure numeric fields
        for col in ['unit_price', 'qty']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Remove records with zero quantity
        if 'qty' in df.columns:
            df = df[df['qty'] > 0]
        
        # Parse dates
        if 'trans_date' in df.columns:
            df['trans_date'] = pd.to_datetime(df['trans_date'], format='%d/%m/%Y', errors='coerce')
        
        self.cleaning_stats['sales_details'] = {
            'original': original_count,
            'cleaned': len(df),
            'zero_qty_removed': original_count - len(df)
        }
        
        logger.info(f"  [Sales Details] Cleaned: {original_count} → {len(df)} records")
        return df
    
    def clean_purchase_details(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean purchase details data"""
        original_count = len(df)
        
        # Ensure numeric fields
        for col in ['unit_price', 'qty']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Remove records with zero quantity
        if 'qty' in df.columns:
            df = df[df['qty'] > 0]
        
        # Parse dates
        if 'trans_date' in df.columns:
            df['trans_date'] = pd.to_datetime(df['trans_date'], format='%d/%m/%Y', errors='coerce')
        
        self.cleaning_stats['purchase_details'] = {
            'original': original_count,
            'cleaned': len(df)
        }
        
        logger.info(f"  [Purchase Details] Cleaned: {original_count} → {len(df)} records")
        return df
    
    def clean_mutations(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean stock mutations data"""
        original_count = len(df)
        
        # Ensure numeric fields
        if 'mutation' in df.columns:
            df['mutation'] = pd.to_numeric(df['mutation'], errors='coerce').fillna(0)
        
        if 'itemCost' in df.columns:
            df['itemCost'] = pd.to_numeric(df['itemCost'], errors='coerce').fillna(0)
        
        # Parse dates
        if 'transactionDate' in df.columns:
            df['transactionDate'] = pd.to_datetime(df['transactionDate'], format='%d/%m/%Y', errors='coerce')
        
        self.cleaning_stats['stock_mutations'] = {
            'original': original_count,
            'cleaned': len(df)
        }
        
        logger.info(f"  [Mutations] Cleaned: {original_count} → {len(df)} records")
        return df


# =============================================================================
# CROSS-ENDPOINT ENRICHMENT (KEY MODULE!)
# =============================================================================

class DataEnricher:
    """
    Enrich null values using cross-endpoint relations
    
    This is the CRITICAL module that fills missing data using related endpoints
    """
    
    def __init__(self, config: PreparationConfig):
        self.config = config
        self.enrichment_stats = {}
    
    def enrich_selling_price(
        self,
        items_df: pd.DataFrame,
        sales_details_df: pd.DataFrame,
        selling_prices_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Enrich selling price with fallback chain:
        1. selling_prices.selling_price (from API)
        2. sales_details.unit_price (average per item)
        3. items.unitPrice (from master)
        """
        logger.info("  🔄 Enriching selling prices...")
        
        items_df = items_df.copy()
        original_null = (items_df['unitPrice'].isna() | (items_df['unitPrice'] == 0)).sum()
        
        # Step 1: Map from selling_prices table
        if not selling_prices_df.empty and 'selling_price' in selling_prices_df.columns:
            price_map = selling_prices_df.set_index('item_id')['selling_price'].to_dict()
            
            mask = (items_df['unitPrice'].isna()) | (items_df['unitPrice'] == 0)
            items_df.loc[mask, 'unitPrice'] = items_df.loc[mask, 'id'].map(price_map)
            
            step1_filled = original_null - ((items_df['unitPrice'].isna()) | (items_df['unitPrice'] == 0)).sum()
            logger.info(f"    Step 1 (selling_prices): Filled {step1_filled} items")
        
        # Step 2: Calculate average from sales_details
        if not sales_details_df.empty and 'unit_price' in sales_details_df.columns:
            # Filter only positive prices
            valid_sales = sales_details_df[sales_details_df['unit_price'] > 0]
            avg_sales_prices = valid_sales.groupby('item_id')['unit_price'].mean()
            
            mask = (items_df['unitPrice'].isna()) | (items_df['unitPrice'] == 0)
            items_df.loc[mask, 'unitPrice'] = items_df.loc[mask, 'id'].map(avg_sales_prices)
            
            current_null = ((items_df['unitPrice'].isna()) | (items_df['unitPrice'] == 0)).sum()
            step2_filled = original_null - step1_filled - (original_null - current_null)
            logger.info(f"    Step 2 (sales_details avg): Filled additional items")
        
        # Step 3: Use category median as final fallback
        mask = (items_df['unitPrice'].isna()) | (items_df['unitPrice'] == 0)
        remaining_null = mask.sum()
        
        if remaining_null > 0 and 'itemCategoryName' in items_df.columns:
            category_medians = items_df[items_df['unitPrice'] > 0].groupby('itemCategoryName')['unitPrice'].median()
            items_df.loc[mask, 'unitPrice'] = items_df.loc[mask, 'itemCategoryName'].map(category_medians)
            
            step3_filled = remaining_null - ((items_df['unitPrice'].isna()) | (items_df['unitPrice'] == 0)).sum()
            logger.info(f"    Step 3 (category median): Filled {step3_filled} items")
        
        # Apply minimum price
        items_df['unitPrice'] = items_df['unitPrice'].clip(lower=self.config.min_selling_price)
        
        final_null = ((items_df['unitPrice'].isna()) | (items_df['unitPrice'] == 0)).sum()
        self.enrichment_stats['unitPrice'] = {
            'original_null': original_null,
            'final_null': final_null,
            'enriched': original_null - final_null
        }
        
        logger.info(f"    ✓ Selling Price: {original_null} → {final_null} null ({original_null - final_null} enriched)")
        return items_df
    
    def enrich_avg_cost(
        self,
        items_df: pd.DataFrame,
        purchase_details_df: pd.DataFrame,
        mutations_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Enrich avgCost with fallback chain:
        1. purchase_details.unit_price (average per item)
        2. mutations.itemCost (average per item)
        3. items.unitPrice * margin_estimate
        """
        logger.info("  🔄 Enriching average cost...")
        
        items_df = items_df.copy()
        
        # Initialize avgCost if not exists
        if 'avgCost' not in items_df.columns:
            items_df['avgCost'] = 0.0
        
        original_null = (items_df['avgCost'].isna() | (items_df['avgCost'] == 0)).sum()
        
        # Step 1: Calculate average from purchase_details
        if not purchase_details_df.empty and 'unit_price' in purchase_details_df.columns:
            valid_purchases = purchase_details_df[purchase_details_df['unit_price'] > 0]
            avg_purchase_costs = valid_purchases.groupby('item_id')['unit_price'].mean()
            
            mask = (items_df['avgCost'].isna()) | (items_df['avgCost'] == 0)
            items_df.loc[mask, 'avgCost'] = items_df.loc[mask, 'id'].map(avg_purchase_costs)
            
            step1_filled = original_null - ((items_df['avgCost'].isna()) | (items_df['avgCost'] == 0)).sum()
            logger.info(f"    Step 1 (purchase_details avg): Filled {step1_filled} items")
        
        # Step 2: Calculate from mutations.itemCost
        if not mutations_df.empty and 'itemCost' in mutations_df.columns:
            valid_mutations = mutations_df[mutations_df['itemCost'] > 0]
            avg_mutation_costs = valid_mutations.groupby('product_id')['itemCost'].mean()
            
            mask = (items_df['avgCost'].isna()) | (items_df['avgCost'] == 0)
            items_df.loc[mask, 'avgCost'] = items_df.loc[mask, 'id'].map(avg_mutation_costs)
            
            step2_filled = original_null - ((items_df['avgCost'].isna()) | (items_df['avgCost'] == 0)).sum() - step1_filled
            logger.info(f"    Step 2 (mutations itemCost avg): Filled {step2_filled} items")
        
        # Step 3: Derive from selling price with margin estimate
        mask = (items_df['avgCost'].isna()) | (items_df['avgCost'] == 0)
        remaining_null = mask.sum()
        
        if remaining_null > 0 and 'unitPrice' in items_df.columns:
            items_df.loc[mask, 'avgCost'] = items_df.loc[mask, 'unitPrice'] * self.config.price_margin_estimate
            
            step3_filled = remaining_null - ((items_df['avgCost'].isna()) | (items_df['avgCost'] == 0)).sum()
            logger.info(f"    Step 3 (derived from price × {self.config.price_margin_estimate}): Filled {step3_filled} items")
        
        # Apply minimum cost
        items_df['avgCost'] = items_df['avgCost'].clip(lower=self.config.min_avg_cost)
        
        final_null = ((items_df['avgCost'].isna()) | (items_df['avgCost'] == 0)).sum()
        self.enrichment_stats['avgCost'] = {
            'original_null': original_null,
            'final_null': final_null,
            'enriched': original_null - final_null
        }
        
        logger.info(f"    ✓ Avg Cost: {original_null} → {final_null} null ({original_null - final_null} enriched)")
        return items_df
    
    def enrich_minimum_stock(self, items_df: pd.DataFrame) -> pd.DataFrame:
        """
        Enrich minimumStock with default value
        """
        logger.info("  🔄 Enriching minimum stock...")
        
        items_df = items_df.copy()
        
        if 'minimumStock' not in items_df.columns:
            items_df['minimumStock'] = self.config.default_minimum_stock
        else:
            mask = (items_df['minimumStock'].isna()) | (items_df['minimumStock'] == 0)
            original_null = mask.sum()
            items_df.loc[mask, 'minimumStock'] = self.config.default_minimum_stock
            
            logger.info(f"    ✓ Minimum Stock: {original_null} items set to default ({self.config.default_minimum_stock})")
        
        return items_df
    
    def verify_stock_with_mutations(
        self,
        stock_df: pd.DataFrame,
        mutations_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Verify current stock against mutation history
        Add reliability flag
        """
        logger.info("  🔄 Verifying stock against mutations...")
        
        stock_df = stock_df.copy()
        
        if mutations_df.empty or 'mutation' not in mutations_df.columns:
            stock_df['stock_reliable'] = True
            return stock_df
        
        # Calculate expected stock from mutations
        calculated_stock = mutations_df.groupby('product_id')['mutation'].sum()
        
        if 'product_id' in stock_df.columns:
            stock_df['calculated_stock'] = stock_df['product_id'].map(calculated_stock).fillna(0)
            
            # Calculate discrepancy
            stock_df['stock_discrepancy'] = abs(
                stock_df['quantity'].fillna(0) - stock_df['calculated_stock']
            )
            
            # Flag as reliable if discrepancy < 10% of max value
            max_val = stock_df[['quantity', 'calculated_stock']].max(axis=1)
            stock_df['stock_reliable'] = stock_df['stock_discrepancy'] <= (max_val * 0.1 + 1)
            
            reliable_count = stock_df['stock_reliable'].sum()
            logger.info(f"    ✓ Stock verification: {reliable_count}/{len(stock_df)} reliable ({reliable_count/len(stock_df)*100:.1f}%)")
        else:
            stock_df['stock_reliable'] = True
        
        return stock_df


# =============================================================================
# DATA VALIDATOR
# =============================================================================

class DataValidator:
    """Validate data quality and generate reports"""
    
    def __init__(self, config: PreparationConfig):
        self.config = config
        self.validation_results = {}
    
    def calculate_quality_score(self, df: pd.DataFrame, critical_columns: List[str]) -> float:
        """Calculate quality score based on completeness of critical columns"""
        if df.empty:
            return 0.0
        
        scores = []
        for col in critical_columns:
            if col in df.columns:
                non_null = df[col].notna() & (df[col] != 0) & (df[col] != '')
                completeness = non_null.sum() / len(df)
                scores.append(completeness)
        
        return round(sum(scores) / len(scores) * 100, 2) if scores else 0.0
    
    def validate_items(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate items data"""
        critical_cols = ['id', 'name', 'unitPrice', 'avgCost']
        quality_score = self.calculate_quality_score(df, critical_cols)
        
        result = {
            'total_records': len(df),
            'quality_score': quality_score,
            'passed': quality_score >= self.config.min_quality_score,
            'columns': {}
        }
        
        for col in critical_cols:
            if col in df.columns:
                null_count = df[col].isna().sum()
                zero_count = (df[col] == 0).sum() if df[col].dtype in ['int64', 'float64'] else 0
                result['columns'][col] = {
                    'null_count': int(null_count),
                    'zero_count': int(zero_count),
                    'completeness': round((len(df) - null_count - zero_count) / len(df) * 100, 2)
                }
        
        self.validation_results['items'] = result
        status = "✓ PASSED" if result['passed'] else "✗ FAILED"
        logger.info(f"  [Items] Quality Score: {quality_score:.1f}% {status}")
        
        return result
    
    def validate_stock(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate current stock data"""
        result = {
            'total_records': len(df),
            'zero_quantity': int((df['quantity'] == 0).sum()) if 'quantity' in df.columns else 0,
            'reliable_count': int(df['stock_reliable'].sum()) if 'stock_reliable' in df.columns else len(df),
            'reliability_ratio': round(df['stock_reliable'].mean() * 100, 2) if 'stock_reliable' in df.columns else 100.0
        }
        
        self.validation_results['current_stock'] = result
        logger.info(f"  [Stock] Reliability: {result['reliability_ratio']:.1f}%")
        
        return result
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report"""
        return {
            'timestamp': datetime.now().isoformat(),
            'validation_results': self.validation_results,
            'overall_passed': all(
                r.get('passed', True) for r in self.validation_results.values()
                if isinstance(r, dict) and 'passed' in r
            )
        }


# =============================================================================
# MAIN PROCESSOR
# =============================================================================

class DataPreparationProcessor:
    """Main orchestrator for data preparation"""
    
    def __init__(self, config: Optional[PreparationConfig] = None):
        self.config = config or PreparationConfig()
        self.loader = DataLoader(self.config.input_dir)
        self.cleanser = DataCleanser(self.config)
        self.enricher = DataEnricher(self.config)
        self.validator = DataValidator(self.config)
        
        self.data: Dict[str, pd.DataFrame] = {}
        self.prepared_data: Dict[str, pd.DataFrame] = {}
    
    def run(self) -> Dict[str, pd.DataFrame]:
        """Run full data preparation pipeline"""
        logger.info("=" * 60)
        logger.info("STARTING DATA PREPARATION")
        logger.info("=" * 60)
        
        # Phase 1: Load data
        logger.info("\n📂 PHASE 1: Loading Data")
        self.data = self.loader.load_all()
        
        # Phase 2: Clean data
        logger.info("\n🧹 PHASE 2: Cleaning Data")
        self._clean_all()
        
        # Phase 3: Enrich data
        logger.info("\n🔗 PHASE 3: Cross-Endpoint Enrichment")
        self._enrich_all()
        
        # Phase 4: Validate data
        logger.info("\n✅ PHASE 4: Validation")
        self._validate_all()
        
        # Phase 5: Save prepared data
        logger.info("\n💾 PHASE 5: Saving Prepared Data")
        self._save_all()
        
        logger.info("\n" + "=" * 60)
        logger.info("DATA PREPARATION COMPLETE")
        logger.info("=" * 60)
        
        return self.prepared_data
    
    def _clean_all(self):
        """Clean all datasets"""
        if 'items' in self.data:
            self.prepared_data['items'] = self.cleanser.clean_items(self.data['items'])
        
        if 'current_stock' in self.data:
            self.prepared_data['current_stock'] = self.cleanser.clean_stock(self.data['current_stock'])
        
        if 'sales_details' in self.data:
            self.prepared_data['sales_details'] = self.cleanser.clean_sales_details(self.data['sales_details'])
        
        if 'purchase_details' in self.data:
            self.prepared_data['purchase_details'] = self.cleanser.clean_purchase_details(self.data['purchase_details'])
        
        if 'stock_mutations' in self.data:
            self.prepared_data['stock_mutations'] = self.cleanser.clean_mutations(self.data['stock_mutations'])
        
        # Copy other datasets without modification
        for name in ['warehouses', 'customers', 'vendors', 'selling_prices', 
                     'sales_invoices', 'purchase_orders']:
            if name in self.data:
                self.prepared_data[name] = self.data[name].copy()
    
    def _enrich_all(self):
        """Enrich all datasets"""
        items_df = self.prepared_data.get('items', pd.DataFrame())
        
        if not items_df.empty:
            # Enrich selling price
            items_df = self.enricher.enrich_selling_price(
                items_df,
                self.prepared_data.get('sales_details', pd.DataFrame()),
                self.prepared_data.get('selling_prices', pd.DataFrame())
            )
            
            # Enrich avgCost
            items_df = self.enricher.enrich_avg_cost(
                items_df,
                self.prepared_data.get('purchase_details', pd.DataFrame()),
                self.prepared_data.get('stock_mutations', pd.DataFrame())
            )
            
            # Enrich minimum stock
            items_df = self.enricher.enrich_minimum_stock(items_df)
            
            self.prepared_data['items'] = items_df
        
        # Verify stock with mutations
        stock_df = self.prepared_data.get('current_stock', pd.DataFrame())
        if not stock_df.empty:
            self.prepared_data['current_stock'] = self.enricher.verify_stock_with_mutations(
                stock_df,
                self.prepared_data.get('stock_mutations', pd.DataFrame())
            )
    
    def _validate_all(self):
        """Validate all datasets"""
        if 'items' in self.prepared_data:
            self.validator.validate_items(self.prepared_data['items'])
        
        if 'current_stock' in self.prepared_data:
            self.validator.validate_stock(self.prepared_data['current_stock'])
        
        # Generate and save report
        report = self.validator.generate_report()
        
        import json
        output_path = Path(self.config.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        with open(output_path / 'validation_report.json', 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"  Validation report saved to {output_path / 'validation_report.json'}")
    
    def _save_all(self):
        """Save all prepared data"""
        output_path = Path(self.config.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for name, df in self.prepared_data.items():
            if isinstance(df, pd.DataFrame) and not df.empty:
                file_path = output_path / f"{name}.csv"
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
                logger.info(f"  ✓ {name}.csv ({len(df):,} records)")
        
        logger.info(f"\n✓ Saved {len(self.prepared_data)} files to {output_path.absolute()}")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main entry point"""
    config = PreparationConfig(
        input_dir="../data/pulled",
        output_dir="../data/prepared"
    )
    
    processor = DataPreparationProcessor(config)
    
    try:
        prepared_data = processor.run()
        
        # Print summary
        print("\n📊 SUMMARY:")
        print("-" * 40)
        for name, df in prepared_data.items():
            if isinstance(df, pd.DataFrame):
                print(f"  {name}: {len(df):,} records")
        
    except FileNotFoundError as e:
        logger.error(f"Data not found: {e}")
        logger.info("Please run data_puller_v2.py first to pull data from API")
    except Exception as e:
        logger.error(f"Preparation failed: {e}")
        raise


if __name__ == '__main__':
    main()
