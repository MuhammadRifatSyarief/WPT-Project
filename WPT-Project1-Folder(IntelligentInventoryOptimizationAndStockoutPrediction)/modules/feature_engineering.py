"""
Module 3: Feature Engineering
==============================

Project 1 - Intelligent Inventory Optimization & Stockout Prediction

Key Features:
1. Demand Metrics - avg daily demand, CV, trend
2. Inventory Metrics - turnover, days in inventory, coverage
3. Financial Metrics - gross margin, holding cost
4. Risk Metrics - days until stockout, stockout probability
5. ABC Classification - by value and velocity
6. Seasonality Detection - weekly/monthly patterns

Author: AI Assistant
Date: January 2026
Version: 1.0.0
"""

import os
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any, Tuple
from dataclasses import dataclass
import warnings

warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
from scipy import stats

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
class FeatureConfig:
    """Configuration for feature engineering"""
    # Input/Output
    input_dir: str = "../data/prepared"
    output_dir: str = "../data/features"
    
    # Date range for analysis
    analysis_days: int = 365  # Use 1 year of data for analysis
    
    # Business constraints (REALISTIC BOUNDS)
    min_turnover_ratio: float = 0.5      # 0.5x per year minimum
    max_turnover_ratio: float = 52.0     # 52x per year (weekly turnover) max
    min_days_inventory: float = 7.0      # 1 week minimum
    max_days_inventory: float = 365.0    # 1 year maximum
    min_stock_coverage: float = 0.0      # 0 days
    max_stock_coverage: float = 180.0    # 6 months max
    
    # Financial assumptions
    holding_cost_rate: float = 0.20      # 20% per year
    ordering_cost: float = 100000.0      # Rp 100k per order
    
    # ABC Classification thresholds
    abc_a_threshold: float = 0.80        # Top 80% of value
    abc_b_threshold: float = 0.95        # Next 15%
    
    # Risk thresholds
    stockout_critical_days: int = 7      # Critical if < 7 days
    stockout_warning_days: int = 14      # Warning if < 14 days
    
    # Seasonality
    min_history_weeks: int = 12          # Need 12 weeks for seasonality


# =============================================================================
# DATA LOADER
# =============================================================================

class FeatureDataLoader:
    """Load prepared data for feature engineering"""
    
    def __init__(self, input_dir: str):
        self.input_dir = Path(input_dir)
        self.data: Dict[str, pd.DataFrame] = {}
    
    def load_all(self) -> Dict[str, pd.DataFrame]:
        """Load all required datasets"""
        required_files = [
            'items', 'current_stock', 'sales_details', 
            'purchase_details', 'stock_mutations'
        ]
        
        logger.info(f"📂 Loading prepared data from {self.input_dir}...")
        
        for name in required_files:
            file_path = self.input_dir / f"{name}.csv"
            if file_path.exists():
                df = pd.read_csv(file_path, encoding='utf-8-sig')
                self.data[name] = df
                logger.info(f"  ✓ {name}: {len(df):,} records")
            else:
                logger.warning(f"  ✗ {name}.csv not found")
                self.data[name] = pd.DataFrame()
        
        return self.data


# =============================================================================
# DEMAND FEATURES
# =============================================================================

class DemandFeatureGenerator:
    """Generate demand-related features"""
    
    def __init__(self, config: FeatureConfig):
        self.config = config
    
    def calculate_daily_demand(
        self,
        sales_df: pd.DataFrame,
        mutations_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Calculate average daily demand per item
        
        Sources:
        1. sales_details.qty aggregated by date
        2. mutations with transactionType = 'SI' (Sales Invoice)
        """
        logger.info("  📊 Calculating daily demand...")
        
        demand_records = []
        
        # Source 1: From sales_details
        if not sales_df.empty and 'item_id' in sales_df.columns:
            # Parse dates
            if 'trans_date' in sales_df.columns:
                sales_df['trans_date'] = pd.to_datetime(sales_df['trans_date'], errors='coerce')
            
            # Group by item and date
            daily_sales = sales_df.groupby(['item_id', sales_df['trans_date'].dt.date]).agg({
                'qty': 'sum'
            }).reset_index()
            daily_sales.columns = ['item_id', 'date', 'daily_qty']
            
            # Calculate stats per item
            for item_id, group in daily_sales.groupby('item_id'):
                if len(group) >= 7:  # Need at least 7 days of data
                    demand_records.append({
                        'item_id': item_id,
                        'total_qty_sold': group['daily_qty'].sum(),
                        'days_with_sales': len(group),
                        'avg_daily_demand': group['daily_qty'].mean(),
                        'demand_std': group['daily_qty'].std(),
                        'demand_cv': group['daily_qty'].std() / group['daily_qty'].mean() if group['daily_qty'].mean() > 0 else 0,
                        'max_daily_demand': group['daily_qty'].max(),
                        'demand_source': 'sales_details'
                    })
        
        # Source 2: From mutations (SI = Sales Invoice = outgoing)
        if not mutations_df.empty and 'product_id' in mutations_df.columns:
            # Filter sales transactions (negative mutations or SI type)
            if 'transactionType' in mutations_df.columns:
                sales_mutations = mutations_df[mutations_df['transactionType'] == 'SI'].copy()
            else:
                sales_mutations = mutations_df[mutations_df['mutation'] < 0].copy()
            
            if not sales_mutations.empty:
                if 'transactionDate' in sales_mutations.columns:
                    sales_mutations['transactionDate'] = pd.to_datetime(
                        sales_mutations['transactionDate'], errors='coerce'
                    )
                
                # For items not in sales_details
                existing_items = set(r['item_id'] for r in demand_records)
                
                for product_id, group in sales_mutations.groupby('product_id'):
                    if product_id not in existing_items and len(group) >= 7:
                        daily_qty = abs(group['mutation']).sum()
                        days = len(group['transactionDate'].dt.date.unique())
                        
                        demand_records.append({
                            'item_id': product_id,
                            'total_qty_sold': daily_qty,
                            'days_with_sales': days,
                            'avg_daily_demand': daily_qty / max(days, 1),
                            'demand_std': abs(group['mutation']).std(),
                            'demand_cv': abs(group['mutation']).std() / abs(group['mutation']).mean() if abs(group['mutation']).mean() > 0 else 0,
                            'max_daily_demand': abs(group['mutation']).max(),
                            'demand_source': 'mutations'
                        })
        
        demand_df = pd.DataFrame(demand_records)
        
        if not demand_df.empty:
            # Apply reasonable bounds
            demand_df['avg_daily_demand'] = demand_df['avg_daily_demand'].clip(lower=0.01)
            demand_df['demand_cv'] = demand_df['demand_cv'].clip(lower=0.1, upper=3.0)
            
            logger.info(f"    ✓ Calculated demand for {len(demand_df)} items")
        
        return demand_df
    
    def calculate_demand_trend(
        self,
        sales_df: pd.DataFrame,
        window_weeks: int = 4
    ) -> pd.DataFrame:
        """
        Calculate demand trend (growing/stable/declining)
        Compare recent weeks vs previous weeks
        """
        logger.info("  📈 Calculating demand trends...")
        
        if sales_df.empty:
            return pd.DataFrame()
        
        trend_records = []
        
        # Parse dates
        if 'trans_date' in sales_df.columns:
            sales_df = sales_df.copy()
            sales_df['trans_date'] = pd.to_datetime(sales_df['trans_date'], errors='coerce')
            sales_df = sales_df.dropna(subset=['trans_date'])
            
            if sales_df.empty:
                return pd.DataFrame()
            
            # Get date range
            max_date = sales_df['trans_date'].max()
            cutoff_date = max_date - timedelta(weeks=window_weeks)
            previous_cutoff = cutoff_date - timedelta(weeks=window_weeks)
            
            for item_id, group in sales_df.groupby('item_id'):
                recent = group[group['trans_date'] >= cutoff_date]['qty'].sum()
                previous = group[
                    (group['trans_date'] >= previous_cutoff) & 
                    (group['trans_date'] < cutoff_date)
                ]['qty'].sum()
                
                if previous > 0:
                    trend_pct = (recent - previous) / previous
                elif recent > 0:
                    trend_pct = 1.0  # New demand
                else:
                    trend_pct = 0.0
                
                # Classify trend
                if trend_pct > 0.1:
                    trend_class = 'growing'
                elif trend_pct < -0.1:
                    trend_class = 'declining'
                else:
                    trend_class = 'stable'
                
                trend_records.append({
                    'item_id': item_id,
                    'demand_trend': trend_pct,
                    'trend_class': trend_class,
                    'recent_qty': recent,
                    'previous_qty': previous
                })
        
        trend_df = pd.DataFrame(trend_records)
        
        if not trend_df.empty:
            # Apply bounds
            trend_df['demand_trend'] = trend_df['demand_trend'].clip(lower=-0.5, upper=1.0)
            logger.info(f"    ✓ Calculated trends for {len(trend_df)} items")
        
        return trend_df


# =============================================================================
# INVENTORY FEATURES
# =============================================================================

class InventoryFeatureGenerator:
    """Generate inventory-related features"""
    
    def __init__(self, config: FeatureConfig):
        self.config = config
    
    def calculate_turnover(
        self,
        items_df: pd.DataFrame,
        stock_df: pd.DataFrame,
        demand_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Calculate inventory turnover ratio
        
        Formula: Annual Sales (units) / Average Inventory
        
        REALISTIC BOUNDS: 0.5x - 52x per year
        """
        logger.info("  🔄 Calculating inventory turnover...")
        
        turnover_records = []
        
        for _, item in items_df.iterrows():
            item_id = item['id']
            
            # Get demand
            demand_row = demand_df[demand_df['item_id'] == item_id]
            if demand_row.empty:
                annual_sales = 0
            else:
                avg_daily = demand_row['avg_daily_demand'].values[0]
                annual_sales = avg_daily * 365
            
            # Get current stock
            stock_row = stock_df[stock_df['product_id'] == item_id]
            if stock_row.empty:
                current_stock = 0
            else:
                current_stock = stock_row['quantity'].values[0]
            
            # Calculate turnover
            if current_stock > 0:
                turnover_ratio = annual_sales / current_stock
            elif annual_sales > 0:
                turnover_ratio = self.config.max_turnover_ratio  # High turnover, no stock
            else:
                turnover_ratio = 0  # No sales, no stock
            
            # Apply realistic bounds
            turnover_ratio = min(max(turnover_ratio, self.config.min_turnover_ratio), 
                                self.config.max_turnover_ratio)
            
            # Calculate days in inventory
            if turnover_ratio > 0:
                days_in_inventory = 365 / turnover_ratio
            else:
                days_in_inventory = self.config.max_days_inventory
            
            days_in_inventory = min(max(days_in_inventory, self.config.min_days_inventory),
                                   self.config.max_days_inventory)
            
            turnover_records.append({
                'item_id': item_id,
                'annual_sales_qty': annual_sales,
                'current_stock': current_stock,
                'turnover_ratio': round(turnover_ratio, 2),
                'days_in_inventory': round(days_in_inventory, 1)
            })
        
        turnover_df = pd.DataFrame(turnover_records)
        logger.info(f"    ✓ Calculated turnover for {len(turnover_df)} items")
        
        return turnover_df
    
    def calculate_stock_coverage(
        self,
        stock_df: pd.DataFrame,
        demand_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Calculate days of stock coverage
        
        Formula: Current Stock / Avg Daily Demand
        
        REALISTIC BOUNDS: 0 - 180 days
        """
        logger.info("  📦 Calculating stock coverage...")
        
        coverage_records = []
        
        for _, stock in stock_df.iterrows():
            product_id = stock['product_id']
            current_qty = stock.get('quantity', 0)
            
            # Get demand
            demand_row = demand_df[demand_df['item_id'] == product_id]
            if demand_row.empty or demand_row['avg_daily_demand'].values[0] == 0:
                avg_daily = 0.01  # Minimum to avoid division by zero
            else:
                avg_daily = demand_row['avg_daily_demand'].values[0]
            
            # Calculate coverage days
            if avg_daily > 0:
                coverage_days = current_qty / avg_daily
            else:
                coverage_days = self.config.max_stock_coverage
            
            # Apply bounds
            coverage_days = min(max(coverage_days, 0), self.config.max_stock_coverage)
            
            coverage_records.append({
                'item_id': product_id,
                'stock_coverage_days': round(coverage_days, 1),
                'avg_daily_demand': round(avg_daily, 3)
            })
        
        coverage_df = pd.DataFrame(coverage_records)
        logger.info(f"    ✓ Calculated coverage for {len(coverage_df)} items")
        
        return coverage_df


# =============================================================================
# FINANCIAL FEATURES
# =============================================================================

class FinancialFeatureGenerator:
    """Generate financial features"""
    
    def __init__(self, config: FeatureConfig):
        self.config = config
    
    def calculate_margins(self, items_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate gross margin and profit metrics
        
        Formula: (Selling Price - Cost) / Selling Price
        
        REALISTIC BOUNDS: 5% - 80%
        """
        logger.info("  💰 Calculating margins...")
        
        items_df = items_df.copy()
        
        # Ensure numeric
        items_df['unitPrice'] = pd.to_numeric(items_df['unitPrice'], errors='coerce').fillna(0)
        items_df['avgCost'] = pd.to_numeric(items_df['avgCost'], errors='coerce').fillna(0)
        
        # Calculate gross margin
        mask = items_df['unitPrice'] > 0
        items_df.loc[mask, 'gross_margin'] = (
            (items_df.loc[mask, 'unitPrice'] - items_df.loc[mask, 'avgCost']) / 
            items_df.loc[mask, 'unitPrice']
        )
        items_df.loc[~mask, 'gross_margin'] = 0
        
        # Apply realistic bounds (5% - 80%)
        items_df['gross_margin'] = items_df['gross_margin'].clip(lower=0.05, upper=0.80)
        
        # Calculate holding cost per unit per year
        items_df['holding_cost_per_unit'] = items_df['avgCost'] * self.config.holding_cost_rate
        
        logger.info(f"    ✓ Calculated margins for {len(items_df)} items")
        
        return items_df[['id', 'unitPrice', 'avgCost', 'gross_margin', 'holding_cost_per_unit']]


# =============================================================================
# RISK FEATURES
# =============================================================================

class RiskFeatureGenerator:
    """Generate stockout risk features"""
    
    def __init__(self, config: FeatureConfig):
        self.config = config
    
    def calculate_stockout_risk(
        self,
        stock_df: pd.DataFrame,
        demand_df: pd.DataFrame,
        coverage_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Calculate stockout risk metrics
        
        REALISTIC BOUNDS:
        - days_until_stockout: 0 - 365
        - stockout_probability: 0 - 1
        """
        logger.info("  ⚠️ Calculating stockout risk...")
        
        risk_records = []
        
        for _, stock in stock_df.iterrows():
            product_id = stock['product_id']
            current_qty = stock.get('quantity', 0)
            
            # Get coverage
            coverage_row = coverage_df[coverage_df['item_id'] == product_id]
            if coverage_row.empty:
                coverage_days = 0
            else:
                coverage_days = coverage_row['stock_coverage_days'].values[0]
            
            # Get demand variability
            demand_row = demand_df[demand_df['item_id'] == product_id]
            if demand_row.empty:
                demand_cv = 0.5  # Default moderate variability
            else:
                demand_cv = demand_row['demand_cv'].values[0]
            
            # Calculate days until stockout (same as coverage)
            days_until_stockout = coverage_days
            
            # Calculate stockout probability (simplified model)
            # Higher CV = higher risk, lower coverage = higher risk
            if coverage_days <= 0:
                stockout_probability = 1.0
            elif coverage_days >= 90:
                stockout_probability = 0.05  # Very safe
            else:
                # Probability increases with CV and decreases with coverage
                base_prob = max(0, 1 - (coverage_days / 30))  # 30 days as reference
                cv_factor = min(demand_cv, 2.0) / 2.0  # CV contribution
                stockout_probability = min(base_prob + cv_factor * 0.3, 1.0)
            
            # Risk classification
            if days_until_stockout <= self.config.stockout_critical_days:
                risk_level = 'critical'
            elif days_until_stockout <= self.config.stockout_warning_days:
                risk_level = 'high'
            elif days_until_stockout <= 30:
                risk_level = 'medium'
            else:
                risk_level = 'low'
            
            risk_records.append({
                'item_id': product_id,
                'days_until_stockout': round(days_until_stockout, 1),
                'stockout_probability': round(stockout_probability, 3),
                'risk_level': risk_level
            })
        
        risk_df = pd.DataFrame(risk_records)
        logger.info(f"    ✓ Calculated risk for {len(risk_df)} items")
        
        # Summary
        if not risk_df.empty:
            critical = (risk_df['risk_level'] == 'critical').sum()
            high = (risk_df['risk_level'] == 'high').sum()
            logger.info(f"    📊 Risk summary: {critical} critical, {high} high risk items")
        
        return risk_df


# =============================================================================
# ABC CLASSIFICATION
# =============================================================================

class ABCClassifier:
    """ABC Classification for inventory"""
    
    def __init__(self, config: FeatureConfig):
        self.config = config
    
    def classify_by_value(
        self,
        items_df: pd.DataFrame,
        demand_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        ABC Classification by annual sales value
        
        A: Top 80% of value
        B: Next 15%
        C: Bottom 5%
        """
        logger.info("  🏷️ ABC Classification...")
        
        # Calculate annual value per item
        merged = items_df.merge(
            demand_df[['item_id', 'total_qty_sold']],
            left_on='id',
            right_on='item_id',
            how='left'
        )
        merged['total_qty_sold'] = merged['total_qty_sold'].fillna(0)
        merged['annual_value'] = merged['total_qty_sold'] * merged['unitPrice']
        
        # Sort by value descending
        merged = merged.sort_values('annual_value', ascending=False)
        
        # Calculate cumulative percentage
        total_value = merged['annual_value'].sum()
        if total_value > 0:
            merged['cumulative_pct'] = merged['annual_value'].cumsum() / total_value
        else:
            merged['cumulative_pct'] = 0
        
        # Classify
        def classify(pct):
            if pct <= self.config.abc_a_threshold:
                return 'A'
            elif pct <= self.config.abc_b_threshold:
                return 'B'
            else:
                return 'C'
        
        merged['abc_class'] = merged['cumulative_pct'].apply(classify)
        
        # Summary
        a_count = (merged['abc_class'] == 'A').sum()
        b_count = (merged['abc_class'] == 'B').sum()
        c_count = (merged['abc_class'] == 'C').sum()
        logger.info(f"    ✓ ABC: A={a_count}, B={b_count}, C={c_count}")
        
        return merged[['id', 'annual_value', 'abc_class']]


# =============================================================================
# EOQ CALCULATION
# =============================================================================

class EOQCalculator:
    """Economic Order Quantity calculator"""
    
    def __init__(self, config: FeatureConfig):
        self.config = config
    
    def calculate_eoq(
        self,
        items_df: pd.DataFrame,
        demand_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Calculate Economic Order Quantity
        
        Formula: sqrt(2 * D * S / H)
        where:
            D = Annual demand
            S = Ordering cost per order
            H = Holding cost per unit per year
            
        REALISTIC BOUNDS: 1 - 10,000 units
        """
        logger.info("  📐 Calculating EOQ...")
        
        eoq_records = []
        
        for _, item in items_df.iterrows():
            item_id = item['id']
            unit_cost = item.get('avgCost', 0)
            
            if unit_cost <= 0:
                unit_cost = 1000  # Default minimum
            
            # Get annual demand
            demand_row = demand_df[demand_df['item_id'] == item_id]
            if demand_row.empty:
                annual_demand = 0
            else:
                # Annual demand = avg daily × 365
                annual_demand = demand_row['avg_daily_demand'].values[0] * 365
            
            # Calculate holding cost
            H = unit_cost * self.config.holding_cost_rate
            S = self.config.ordering_cost
            
            # Calculate EOQ
            if annual_demand > 0 and H > 0:
                eoq = np.sqrt(2 * annual_demand * S / H)
            else:
                eoq = 1  # Minimum
            
            # Apply realistic bounds
            eoq = int(min(max(eoq, 1), 10000))
            
            # Calculate reorder point (ROP)
            # ROP = (Lead time demand) + (Safety stock)
            # Assuming 7 days lead time and 1.65 × std for 95% service level
            if not demand_row.empty:
                avg_daily = demand_row['avg_daily_demand'].values[0]
                demand_std = demand_row.get('demand_std', pd.Series([avg_daily * 0.3])).values[0]
                lead_time = 7  # days
                
                lead_time_demand = avg_daily * lead_time
                safety_stock = 1.65 * demand_std * np.sqrt(lead_time)
                rop = lead_time_demand + safety_stock
            else:
                rop = 5  # Default minimum
            
            rop = int(min(max(rop, 1), 10000))
            
            eoq_records.append({
                'item_id': item_id,
                'eoq': eoq,
                'reorder_point': rop,
                'annual_demand': round(annual_demand, 0)
            })
        
        eoq_df = pd.DataFrame(eoq_records)
        logger.info(f"    ✓ Calculated EOQ for {len(eoq_df)} items")
        
        return eoq_df


# =============================================================================
# MAIN PROCESSOR
# =============================================================================

class FeatureEngineeringProcessor:
    """Main orchestrator for feature engineering"""
    
    def __init__(self, config: Optional[FeatureConfig] = None):
        self.config = config or FeatureConfig()
        self.loader = FeatureDataLoader(self.config.input_dir)
        
        # Feature generators
        self.demand_gen = DemandFeatureGenerator(self.config)
        self.inventory_gen = InventoryFeatureGenerator(self.config)
        self.financial_gen = FinancialFeatureGenerator(self.config)
        self.risk_gen = RiskFeatureGenerator(self.config)
        self.abc_classifier = ABCClassifier(self.config)
        self.eoq_calc = EOQCalculator(self.config)
        
        self.data: Dict[str, pd.DataFrame] = {}
        self.features: Dict[str, pd.DataFrame] = {}
    
    def run(self) -> pd.DataFrame:
        """Run full feature engineering pipeline"""
        logger.info("=" * 60)
        logger.info("STARTING FEATURE ENGINEERING")
        logger.info("=" * 60)
        
        # Phase 1: Load data
        logger.info("\n📂 PHASE 1: Loading Data")
        self.data = self.loader.load_all()
        
        # Phase 2: Calculate demand features
        logger.info("\n📊 PHASE 2: Demand Features")
        self.features['demand'] = self.demand_gen.calculate_daily_demand(
            self.data.get('sales_details', pd.DataFrame()),
            self.data.get('stock_mutations', pd.DataFrame())
        )
        self.features['trend'] = self.demand_gen.calculate_demand_trend(
            self.data.get('sales_details', pd.DataFrame())
        )
        
        # Phase 3: Calculate inventory features
        logger.info("\n📦 PHASE 3: Inventory Features")
        self.features['turnover'] = self.inventory_gen.calculate_turnover(
            self.data.get('items', pd.DataFrame()),
            self.data.get('current_stock', pd.DataFrame()),
            self.features['demand']
        )
        self.features['coverage'] = self.inventory_gen.calculate_stock_coverage(
            self.data.get('current_stock', pd.DataFrame()),
            self.features['demand']
        )
        
        # Phase 4: Financial features
        logger.info("\n💰 PHASE 4: Financial Features")
        self.features['margins'] = self.financial_gen.calculate_margins(
            self.data.get('items', pd.DataFrame())
        )
        
        # Phase 5: Risk features
        logger.info("\n⚠️ PHASE 5: Risk Features")
        self.features['risk'] = self.risk_gen.calculate_stockout_risk(
            self.data.get('current_stock', pd.DataFrame()),
            self.features['demand'],
            self.features['coverage']
        )
        
        # Phase 6: ABC Classification
        logger.info("\n🏷️ PHASE 6: ABC Classification")
        self.features['abc'] = self.abc_classifier.classify_by_value(
            self.data.get('items', pd.DataFrame()),
            self.features['demand']
        )
        
        # Phase 7: EOQ Calculation
        logger.info("\n📐 PHASE 7: EOQ & Reorder Points")
        self.features['eoq'] = self.eoq_calc.calculate_eoq(
            self.data.get('items', pd.DataFrame()),
            self.features['demand']
        )
        
        # Phase 8: Merge all features
        logger.info("\n🔗 PHASE 8: Merging Features")
        master_features = self._merge_all_features()
        
        # Phase 9: Save
        logger.info("\n💾 PHASE 9: Saving Features")
        self._save_features(master_features)
        
        logger.info("\n" + "=" * 60)
        logger.info("FEATURE ENGINEERING COMPLETE")
        logger.info("=" * 60)
        
        return master_features
    
    def _merge_all_features(self) -> pd.DataFrame:
        """Merge all feature dataframes into master"""
        items_df = self.data.get('items', pd.DataFrame())
        
        if items_df.empty:
            return pd.DataFrame()
        
        # Start with items - use available columns
        base_cols = ['id']
        if 'no' in items_df.columns:
            base_cols.append('no')
        if 'name' in items_df.columns:
            base_cols.append('name')
        
        # Category column may have different names
        category_col = None
        for col_name in ['itemCategoryName', 'category', 'categoryName']:
            if col_name in items_df.columns:
                category_col = col_name
                break
        
        if category_col:
            base_cols.append(category_col)
        
        master = items_df[base_cols].copy()
        
        # Rename category column if needed
        if category_col and category_col != 'category':
            master = master.rename(columns={category_col: 'category'})
        
        # Merge demand features
        if not self.features['demand'].empty:
            master = master.merge(
                self.features['demand'],
                left_on='id', right_on='item_id',
                how='left'
            ).drop(columns=['item_id'], errors='ignore')
        
        # Merge trend
        if not self.features['trend'].empty:
            master = master.merge(
                self.features['trend'][['item_id', 'demand_trend', 'trend_class']],
                left_on='id', right_on='item_id',
                how='left'
            ).drop(columns=['item_id'], errors='ignore')
        
        # Merge turnover
        if not self.features['turnover'].empty:
            master = master.merge(
                self.features['turnover'],
                left_on='id', right_on='item_id',
                how='left'
            ).drop(columns=['item_id'], errors='ignore')
        
        # Merge coverage
        if not self.features['coverage'].empty:
            master = master.merge(
                self.features['coverage'],
                left_on='id', right_on='item_id',
                how='left'
            ).drop(columns=['item_id'], errors='ignore')
        
        # Merge margins
        if not self.features['margins'].empty:
            master = master.merge(
                self.features['margins'],
                on='id',
                how='left'
            )
        
        # Merge risk
        if not self.features['risk'].empty:
            master = master.merge(
                self.features['risk'],
                left_on='id', right_on='item_id',
                how='left'
            ).drop(columns=['item_id'], errors='ignore')
        
        # Merge ABC
        if not self.features['abc'].empty:
            master = master.merge(
                self.features['abc'],
                on='id',
                how='left'
            )
        
        # Merge EOQ
        if not self.features['eoq'].empty:
            master = master.merge(
                self.features['eoq'],
                left_on='id', right_on='item_id',
                how='left'
            ).drop(columns=['item_id'], errors='ignore')
        
        # ==== UNIFY DUPLICATE COLUMNS FROM MERGES ====
        # Handle avg_daily_demand_x and avg_daily_demand_y
        if 'avg_daily_demand_x' in master.columns and 'avg_daily_demand_y' in master.columns:
            # Prefer _y (from coverage) as it's more complete, fallback to _x
            master['avg_daily_demand'] = master['avg_daily_demand_y'].fillna(master['avg_daily_demand_x'])
            master = master.drop(columns=['avg_daily_demand_x', 'avg_daily_demand_y'], errors='ignore')
        elif 'avg_daily_demand_x' in master.columns:
            master['avg_daily_demand'] = master['avg_daily_demand_x']
            master = master.drop(columns=['avg_daily_demand_x'], errors='ignore')
        elif 'avg_daily_demand_y' in master.columns:
            master['avg_daily_demand'] = master['avg_daily_demand_y']
            master = master.drop(columns=['avg_daily_demand_y'], errors='ignore')
        
        # Calculate demand_std from demand_cv if missing
        if 'demand_std' not in master.columns and 'avg_daily_demand' in master.columns:
            master['demand_std'] = master['avg_daily_demand'] * master.get('demand_cv', 0.3).fillna(0.3)
        
        # ==== FIX ABC CLASSIFICATION FOR OUTLIERS ====
        # Recalculate ABC excluding extreme outliers (top 0.1% by value)
        if 'annual_value' in master.columns:
            # Cap annual_value at 99.9th percentile to prevent outlier domination
            cap_value = master['annual_value'].quantile(0.999)
            master['annual_value_capped'] = master['annual_value'].clip(upper=cap_value)
            
            # Recalculate cumulative percentage
            master = master.sort_values('annual_value_capped', ascending=False)
            total_value = master['annual_value_capped'].sum()
            if total_value > 0:
                master['cumulative_pct'] = master['annual_value_capped'].cumsum() / total_value
                
                # Reclassify ABC
                def classify_abc(pct):
                    if pct <= 0.80:
                        return 'A'
                    elif pct <= 0.95:
                        return 'B'
                    else:
                        return 'C'
                
                master['abc_class'] = master['cumulative_pct'].apply(classify_abc)
                master = master.drop(columns=['annual_value_capped', 'cumulative_pct'], errors='ignore')
                
                # Log ABC distribution
                a_count = (master['abc_class'] == 'A').sum()
                b_count = (master['abc_class'] == 'B').sum()
                c_count = (master['abc_class'] == 'C').sum()
                logger.info(f"  ✓ ABC Recalculated: A={a_count}, B={b_count}, C={c_count}")
        
        # Fill NaN with defaults
        master = master.fillna({
            'avg_daily_demand': 0.01,  # Small default instead of 0
            'demand_std': 0.01,
            'demand_cv': 0.5,
            'demand_trend': 0,
            'trend_class': 'stable',
            'turnover_ratio': 1.0,
            'days_in_inventory': 365,
            'stock_coverage_days': 0,
            'gross_margin': 0.3,
            'days_until_stockout': 0,
            'stockout_probability': 1.0,
            'risk_level': 'unknown',
            'abc_class': 'C',
            'eoq': 1,
            'reorder_point': 5
        })
        
        logger.info(f"  ✓ Master features: {len(master)} items, {len(master.columns)} columns")
        
        return master
    
    def _save_features(self, master_df: pd.DataFrame):
        """Save all feature datasets"""
        output_path = Path(self.config.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save master features
        master_df.to_csv(output_path / 'master_features.csv', index=False, encoding='utf-8-sig')
        logger.info(f"  ✓ master_features.csv ({len(master_df):,} records)")
        
        # Save individual feature sets
        for name, df in self.features.items():
            if isinstance(df, pd.DataFrame) and not df.empty:
                df.to_csv(output_path / f'{name}_features.csv', index=False, encoding='utf-8-sig')
                logger.info(f"  ✓ {name}_features.csv ({len(df):,} records)")
        
        logger.info(f"\n✓ Saved to {output_path.absolute()}")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main entry point"""
    config = FeatureConfig(
        input_dir="../data/prepared",
        output_dir="../data/features"
    )
    
    processor = FeatureEngineeringProcessor(config)
    
    try:
        features = processor.run()
        
        # Print summary
        print("\n📊 FEATURE SUMMARY:")
        print("-" * 40)
        print(f"Total items: {len(features)}")
        print(f"Total features: {len(features.columns)}")
        print(f"\nKey columns: {list(features.columns[:15])}")
        
    except FileNotFoundError as e:
        logger.error(f"Data not found: {e}")
        logger.info("Please run data_preparation.py first")
    except Exception as e:
        logger.error(f"Feature engineering failed: {e}")
        raise


if __name__ == '__main__':
    main()
