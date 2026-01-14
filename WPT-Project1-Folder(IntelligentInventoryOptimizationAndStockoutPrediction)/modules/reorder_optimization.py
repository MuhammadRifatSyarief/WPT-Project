"""
Module 6: Reorder Optimization
===============================

Project 1 - Intelligent Inventory Optimization & Stockout Prediction

Features:
1. Enhanced EOQ with business constraints
2. Dynamic safety stock calculation
3. Lead time optimization
4. Order scheduling and batching
5. Cost optimization analysis

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
import json

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
class ReorderConfig:
    """Configuration for reorder optimization"""
    # Input/Output
    features_dir: str = "../data/features"
    predictions_dir: str = "../data/predictions"
    forecasts_dir: str = "../data/forecasts"
    output_dir: str = "../data/reorder"
    
    # Cost parameters (in Rupiah)
    default_ordering_cost: float = 150000.0      # Rp 150k per order
    default_holding_rate: float = 0.20           # 20% of item cost per year
    default_stockout_cost_rate: float = 2.0      # 2x selling price per stockout
    
    # Lead time parameters - BUSINESS ASSUMPTION
    default_lead_time: int = 31                  # 31 days (1 month) - business assumption
    lead_time_variance: float = 0.3              # 30% variance
    max_lead_time: int = 31                      # Use actual per-product, cap at 31 max
    
    # Service level
    target_service_level: float = 0.95           # 95% service level
    z_score_95: float = 1.65                     # Z-score for 95%
    z_score_99: float = 2.33                     # Z-score for 99%
    
    # NO ARTIFICIAL CAPS - Let values vary naturally from formula
    min_order_qty: int = 1
    max_order_qty: int = 99999                   # No practical limit
    min_safety_stock: int = 0
    max_safety_stock: int = 99999                # No cap - natural variation
    max_reorder_point: int = 99999               # No cap - natural variation
    
    # Demand - NO CAP, use actual values
    demand_cap_percentile: float = 1.0           # No percentile cap
    max_daily_demand: float = 99999.0            # No cap - use actual data
    
    # Batching
    order_frequency_days: int = 7                # Weekly ordering cycle
    min_order_value: float = 500000.0            # Minimum Rp 500k per order


# =============================================================================
# EOQ CALCULATOR (ENHANCED)
# =============================================================================

class EnhancedEOQCalculator:
    """Enhanced Economic Order Quantity with business constraints"""
    
    def __init__(self, config: ReorderConfig):
        self.config = config
    
    def calculate_eoq(
        self,
        annual_demand: float,
        unit_cost: float,
        ordering_cost: float = None,
        holding_rate: float = None
    ) -> Dict[str, float]:
        """
        Calculate EOQ with costs breakdown
        
        Formula: EOQ = sqrt(2 * D * S / H)
        
        Returns dict with EOQ, annual costs, and optimal order frequency
        """
        ordering_cost = ordering_cost or self.config.default_ordering_cost
        holding_rate = holding_rate or self.config.default_holding_rate
        
        # Holding cost per unit per year
        H = unit_cost * holding_rate
        
        # Validate inputs
        if annual_demand <= 0 or unit_cost <= 0 or H <= 0:
            return {
                'eoq': self.config.min_order_qty,
                'annual_ordering_cost': ordering_cost,
                'annual_holding_cost': 0,
                'total_annual_cost': ordering_cost,
                'orders_per_year': 1,
                'days_between_orders': 365
            }
        
        # Calculate EOQ
        eoq = np.sqrt((2 * annual_demand * ordering_cost) / H)
        
        # Apply constraints
        eoq = int(max(self.config.min_order_qty, min(eoq, self.config.max_order_qty)))
        
        # Calculate costs
        orders_per_year = annual_demand / eoq if eoq > 0 else 1
        annual_ordering_cost = orders_per_year * ordering_cost
        annual_holding_cost = (eoq / 2) * H  # Average inventory × holding cost
        total_annual_cost = annual_ordering_cost + annual_holding_cost
        
        return {
            'eoq': eoq,
            'annual_ordering_cost': round(annual_ordering_cost, 0),
            'annual_holding_cost': round(annual_holding_cost, 0),
            'total_annual_cost': round(total_annual_cost, 0),
            'orders_per_year': round(orders_per_year, 1),
            'days_between_orders': round(365 / orders_per_year, 0) if orders_per_year > 0 else 365
        }
    
    def calculate_eoq_with_quantity_discounts(
        self,
        annual_demand: float,
        unit_cost: float,
        discount_schedule: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        EOQ with quantity discounts consideration
        
        discount_schedule: [{'min_qty': 100, 'discount': 0.05}, ...]
        """
        if not discount_schedule:
            return self.calculate_eoq(annual_demand, unit_cost)
        
        best_total_cost = float('inf')
        best_result = None
        
        for tier in discount_schedule:
            min_qty = tier.get('min_qty', 0)
            discount = tier.get('discount', 0)
            discounted_cost = unit_cost * (1 - discount)
            
            # Calculate EOQ at this price
            eoq_result = self.calculate_eoq(annual_demand, discounted_cost)
            
            # If EOQ < min_qty for discount, use min_qty
            if eoq_result['eoq'] < min_qty:
                order_qty = min_qty
            else:
                order_qty = eoq_result['eoq']
            
            # Recalculate total cost
            H = discounted_cost * self.config.default_holding_rate
            orders_per_year = annual_demand / order_qty
            total_cost = (orders_per_year * self.config.default_ordering_cost + 
                         (order_qty / 2) * H +
                         annual_demand * discounted_cost)
            
            if total_cost < best_total_cost:
                best_total_cost = total_cost
                best_result = {
                    'eoq': order_qty,
                    'unit_cost': discounted_cost,
                    'discount_applied': discount,
                    'total_annual_cost': round(total_cost, 0)
                }
        
        return best_result or self.calculate_eoq(annual_demand, unit_cost)


# =============================================================================
# SAFETY STOCK CALCULATOR
# =============================================================================

class SafetyStockCalculator:
    """Dynamic safety stock calculation"""
    
    def __init__(self, config: ReorderConfig):
        self.config = config
    
    def calculate_safety_stock(
        self,
        avg_daily_demand: float,
        demand_std: float,
        lead_time: int = None,
        service_level: float = None
    ) -> Dict[str, float]:
        """
        Calculate safety stock
        
        Formula: SS = Z × σ_d × √L
        where:
            Z = z-score for service level
            σ_d = standard deviation of daily demand
            L = lead time in days
        """
        lead_time = lead_time or self.config.default_lead_time
        service_level = service_level or self.config.target_service_level
        
        # Get Z-score
        if service_level >= 0.99:
            z_score = self.config.z_score_99
        else:
            z_score = self.config.z_score_95
        
        # If no demand std provided, estimate from CV
        if demand_std <= 0:
            demand_std = avg_daily_demand * 0.3  # Assume 30% CV
        
        # Calculate safety stock
        safety_stock = z_score * demand_std * np.sqrt(lead_time)
        
        # Apply constraints
        safety_stock = int(max(self.config.min_safety_stock, 
                              min(safety_stock, self.config.max_safety_stock)))
        
        # Calculate service level achieved
        if demand_std > 0:
            actual_z = safety_stock / (demand_std * np.sqrt(lead_time))
            from scipy import stats
            try:
                achieved_service_level = stats.norm.cdf(actual_z)
            except:
                achieved_service_level = service_level
        else:
            achieved_service_level = 1.0
        
        return {
            'safety_stock': safety_stock,
            'service_level_target': service_level,
            'service_level_achieved': round(achieved_service_level, 4),
            'lead_time_days': lead_time
        }
    
    def calculate_reorder_point(
        self,
        avg_daily_demand: float,
        lead_time: int,
        safety_stock: int
    ) -> int:
        """
        Calculate reorder point
        
        Formula: ROP = (Lead Time × Avg Daily Demand) + Safety Stock
        """
        lead_time_demand = avg_daily_demand * lead_time
        rop = lead_time_demand + safety_stock
        
        return int(max(1, rop))


# =============================================================================
# ORDER SCHEDULER
# =============================================================================

class OrderScheduler:
    """Generate optimal order schedule"""
    
    def __init__(self, config: ReorderConfig):
        self.config = config
    
    def create_order_schedule(
        self,
        items_df: pd.DataFrame,
        planning_horizon: int = 90
    ) -> pd.DataFrame:
        """
        Create order schedule for planning horizon
        
        Returns DataFrame with order dates and quantities per item
        """
        logger.info("  Creating order schedule...")
        
        schedule_records = []
        today = datetime.now().date()
        
        for _, item in items_df.iterrows():
            item_id = item.get('id')
            current_stock = item.get('current_stock', 0)
            avg_daily_demand = item.get('avg_daily_demand', 0)
            eoq = item.get('eoq', 1)
            rop = item.get('reorder_point', 5)
            
            if avg_daily_demand <= 0:
                continue
            
            # Simulate inventory over planning horizon
            inventory = current_stock
            order_date = None
            
            for day in range(planning_horizon):
                date = today + timedelta(days=day)
                
                # Consume inventory
                inventory -= avg_daily_demand
                
                # Check if need to order
                if inventory <= rop and order_date is None:
                    order_date = date
                    order_qty = eoq
                    
                    schedule_records.append({
                        'item_id': item_id,
                        'item_name': item.get('name', ''),
                        'order_date': order_date.strftime('%Y-%m-%d'),
                        'order_qty': int(order_qty),
                        'current_stock_at_order': max(0, int(inventory)),
                        'lead_time_days': self.config.default_lead_time,
                        'expected_delivery': (order_date + timedelta(days=self.config.default_lead_time)).strftime('%Y-%m-%d')
                    })
                    
                    # Assume order arrives after lead time
                    inventory += eoq
                    order_date = None  # Reset for next order
        
        schedule_df = pd.DataFrame(schedule_records)
        
        if not schedule_df.empty:
            schedule_df = schedule_df.sort_values('order_date')
            logger.info(f"  Generated {len(schedule_df)} order entries")
        
        return schedule_df
    
    def batch_orders_by_vendor(
        self,
        schedule_df: pd.DataFrame,
        vendor_mapping: Dict[int, int] = None
    ) -> pd.DataFrame:
        """
        Consolidate orders by vendor and date
        
        Helps reduce ordering costs by combining orders
        """
        if schedule_df.empty:
            return schedule_df
        
        # For now, batch by date only (vendor mapping would need vendor data)
        batched = schedule_df.groupby('order_date').agg({
            'item_id': 'count',
            'order_qty': 'sum'
        }).reset_index()
        
        batched.columns = ['order_date', 'items_count', 'total_qty']
        
        return batched


# =============================================================================
# COST ANALYZER
# =============================================================================

class CostAnalyzer:
    """Analyze inventory costs and savings"""
    
    def __init__(self, config: ReorderConfig):
        self.config = config
    
    def analyze_holding_costs(
        self,
        items_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """Analyze current holding costs"""
        logger.info("  Analyzing holding costs...")
        
        total_holding_cost = 0
        item_costs = []
        
        for _, item in items_df.iterrows():
            current_stock = item.get('current_stock', 0)
            unit_cost = item.get('avgCost', 0) or item.get('unitPrice', 0) * 0.6
            
            # Annual holding cost for current stock level
            holding_cost = current_stock * unit_cost * self.config.default_holding_rate
            total_holding_cost += holding_cost
            
            item_costs.append({
                'item_id': item.get('id'),
                'current_stock': current_stock,
                'unit_cost': unit_cost,
                'annual_holding_cost': round(holding_cost, 0)
            })
        
        return {
            'total_annual_holding_cost': round(total_holding_cost, 0),
            'avg_holding_cost_per_item': round(total_holding_cost / max(len(items_df), 1), 0),
            'top_holding_costs': sorted(item_costs, key=lambda x: -x['annual_holding_cost'])[:10]
        }
    
    def calculate_potential_savings(
        self,
        items_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """Calculate potential savings from optimization"""
        logger.info("  Calculating potential savings...")
        
        current_total_cost = 0
        optimized_total_cost = 0
        
        for _, item in items_df.iterrows():
            current_stock = item.get('current_stock', 0)
            eoq = item.get('eoq', current_stock)
            unit_cost = item.get('avgCost', 0) or 1000
            annual_demand = item.get('avg_daily_demand', 0) * 365
            
            # Current costs (assuming suboptimal ordering)
            H = unit_cost * self.config.default_holding_rate
            current_holding = (current_stock / 2) * H
            current_ordering = (annual_demand / max(current_stock, 1)) * self.config.default_ordering_cost
            current_total = current_holding + current_ordering
            
            # Optimized costs with EOQ
            optimal_holding = (eoq / 2) * H
            optimal_ordering = (annual_demand / max(eoq, 1)) * self.config.default_ordering_cost
            optimal_total = optimal_holding + optimal_ordering
            
            current_total_cost += current_total
            optimized_total_cost += optimal_total
        
        savings = current_total_cost - optimized_total_cost
        savings_pct = (savings / current_total_cost * 100) if current_total_cost > 0 else 0
        
        return {
            'current_annual_cost': round(current_total_cost, 0),
            'optimized_annual_cost': round(optimized_total_cost, 0),
            'potential_savings': round(savings, 0),
            'savings_percentage': round(savings_pct, 2)
        }


# =============================================================================
# MAIN PROCESSOR
# =============================================================================

class ReorderOptimizationProcessor:
    """Main orchestrator for reorder optimization"""
    
    def __init__(self, config: Optional[ReorderConfig] = None):
        self.config = config or ReorderConfig()
        self.eoq_calc = EnhancedEOQCalculator(self.config)
        self.safety_calc = SafetyStockCalculator(self.config)
        self.scheduler = OrderScheduler(self.config)
        self.cost_analyzer = CostAnalyzer(self.config)
        
        self.optimization_results = pd.DataFrame()
        self.product_lead_times: Dict[int, int] = {}  # Per-product lead times
    
    def _load_product_lead_times(self) -> Dict[int, int]:
        """Load per-product lead times from actual PO-RI data"""
        lt_path = Path(self.config.features_dir) / "product_lead_times.csv"
        
        if lt_path.exists():
            lt_df = pd.read_csv(lt_path, encoding='utf-8-sig')
            # Use median lead time per product
            self.product_lead_times = dict(zip(
                lt_df['item_id'].astype(int),
                lt_df['lead_time_median'].astype(int)
            ))
            logger.info(f"  Loaded lead times for {len(self.product_lead_times)} products")
        else:
            logger.warning(f"  product_lead_times.csv not found, using default {self.config.default_lead_time} days")
        
        return self.product_lead_times
    
    def get_lead_time(self, item_id: int) -> int:
        """Get lead time for specific item (per-product or default)"""
        return self.product_lead_times.get(int(item_id), self.config.default_lead_time)
    
    def run(self) -> pd.DataFrame:
        """Run reorder optimization pipeline"""
        logger.info("=" * 60)
        logger.info("STARTING REORDER OPTIMIZATION")
        logger.info("=" * 60)
        
        # Phase 1: Load data
        logger.info("\n[PHASE 1] Loading Data")
        features_df, predictions_df = self._load_data()
        self._load_product_lead_times()  # Load per-product lead times
        
        if features_df.empty:
            logger.error("No features data available")
            return pd.DataFrame()
        
        # Phase 2: Merge with predictions
        logger.info("\n[PHASE 2] Merging Data")
        merged_df = self._merge_data(features_df, predictions_df)
        
        # Phase 3: Calculate EOQ for all items
        logger.info("\n[PHASE 3] Calculating EOQ")
        merged_df = self._calculate_all_eoq(merged_df)
        
        # Phase 4: Calculate safety stock
        logger.info("\n[PHASE 4] Calculating Safety Stock")
        merged_df = self._calculate_all_safety_stock(merged_df)
        
        # Phase 5: Calculate reorder points
        logger.info("\n[PHASE 5] Calculating Reorder Points")
        merged_df = self._calculate_reorder_points(merged_df)
        
        # Phase 6: Create order schedule
        logger.info("\n[PHASE 6] Creating Order Schedule")
        schedule_df = self.scheduler.create_order_schedule(merged_df)
        
        # Phase 7: Analyze costs
        logger.info("\n[PHASE 7] Analyzing Costs")
        holding_analysis = self.cost_analyzer.analyze_holding_costs(merged_df)
        savings_analysis = self.cost_analyzer.calculate_potential_savings(merged_df)
        
        # Phase 8: Save results
        logger.info("\n[PHASE 8] Saving Results")
        self._save_results(merged_df, schedule_df, holding_analysis, savings_analysis)
        
        self.optimization_results = merged_df
        
        logger.info("\n" + "=" * 60)
        logger.info("REORDER OPTIMIZATION COMPLETE")
        logger.info("=" * 60)
        
        return merged_df
    
    def _load_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load features and predictions"""
        features_path = Path(self.config.features_dir) / "master_features.csv"
        predictions_path = Path(self.config.predictions_dir) / "stockout_predictions.csv"
        
        features_df = pd.DataFrame()
        predictions_df = pd.DataFrame()
        
        if features_path.exists():
            features_df = pd.read_csv(features_path, encoding='utf-8-sig')
            logger.info(f"  Loaded features: {len(features_df)} items")
        
        if predictions_path.exists():
            predictions_df = pd.read_csv(predictions_path, encoding='utf-8-sig')
            logger.info(f"  Loaded predictions: {len(predictions_df)} items")
        
        return features_df, predictions_df
    
    def _merge_data(
        self,
        features_df: pd.DataFrame,
        predictions_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Merge features with predictions"""
        merged = features_df.copy()
        
        if not predictions_df.empty:
            # Select relevant columns from predictions
            pred_cols = ['id', 'risk_score', 'risk_class', 'reorder_urgency', 
                        'recommended_qty', 'expected_stockout_date']
            available_cols = [c for c in pred_cols if c in predictions_df.columns]
            
            if available_cols:
                merged = merged.merge(
                    predictions_df[available_cols],
                    on='id',
                    how='left',
                    suffixes=('', '_pred')
                )
        
        logger.info(f"  Merged data: {len(merged)} items, {len(merged.columns)} columns")
        return merged
    
    def _calculate_all_eoq(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate EOQ for all items"""
        logger.info("  Calculating EOQ for all items...")
        
        eoq_values = []
        annual_costs = []
        orders_per_year = []
        
        for _, row in df.iterrows():
            annual_demand = row.get('avg_daily_demand', 0) * 365
            unit_cost = row.get('avgCost', 0) or row.get('unitPrice', 0) * 0.6
            
            if unit_cost <= 0:
                unit_cost = 1000  # Default minimum
            
            eoq_result = self.eoq_calc.calculate_eoq(annual_demand, unit_cost)
            
            eoq_values.append(eoq_result['eoq'])
            annual_costs.append(eoq_result['total_annual_cost'])
            orders_per_year.append(eoq_result['orders_per_year'])
        
        df['eoq_optimized'] = eoq_values
        df['annual_inventory_cost'] = annual_costs
        df['optimal_orders_per_year'] = orders_per_year
        
        logger.info(f"  EOQ calculated for {len(df)} items")
        return df
    
    def _calculate_all_safety_stock(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate safety stock for all items using per-product lead times"""
        logger.info("  Calculating safety stock with per-product lead times...")
        logger.info(f"  Lead time max: {self.config.max_lead_time} days")
        
        safety_stocks = []
        service_levels = []
        lead_times_used = []
        
        for _, row in df.iterrows():
            item_id = row.get('id', 0)
            avg_demand = row.get('avg_daily_demand', 0)
            
            # USE ACTUAL DEMAND - no capping for natural variation
            demand_cv = row.get('demand_cv', 0.3)
            demand_std = avg_demand * demand_cv
            
            # Get per-product lead time, cap at business max (31 days)
            lead_time = min(self.get_lead_time(item_id), self.config.max_lead_time)
            
            ss_result = self.safety_calc.calculate_safety_stock(
                avg_demand, demand_std, lead_time=lead_time
            )
            
            safety_stocks.append(ss_result['safety_stock'])
            service_levels.append(ss_result['service_level_achieved'])
            lead_times_used.append(lead_time)
        
        df['safety_stock_optimized'] = safety_stocks
        df['achieved_service_level'] = service_levels
        df['lead_time_days'] = lead_times_used
        
        logger.info(f"  Safety stock calculated for {len(df)} items")
        logger.info(f"  Lead time range: {min(lead_times_used)}-{max(lead_times_used)} days")
        logger.info(f"  Safety stock range: {min(safety_stocks)}-{max(safety_stocks)}")
        return df
    
    def _calculate_reorder_points(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate reorder points using per-product lead times"""
        logger.info("  Calculating reorder points with per-product lead times...")
        
        reorder_points = []
        
        for _, row in df.iterrows():
            item_id = row.get('id', 0)
            avg_demand = row.get('avg_daily_demand', 0)
            safety_stock = row.get('safety_stock_optimized', 0)
            
            # USE ACTUAL DEMAND - no capping for natural variation
            
            # Get per-product lead time, cap at business max (31 days)
            lead_time = min(self.get_lead_time(item_id), self.config.max_lead_time)
            
            rop = self.safety_calc.calculate_reorder_point(
                avg_demand, 
                lead_time,
                safety_stock
            )
            
            # NO CAP - use natural calculated value
            reorder_points.append(rop)
        
        df['reorder_point_optimized'] = reorder_points
        
        logger.info(f"  Reorder points calculated for {len(df)} items")
        logger.info(f"  ROP range (raw): {min(reorder_points)}-{max(reorder_points)}")
        
        # WINSORIZATION: Compress outliers proportionally while preserving ranking
        df = self._winsorize_results(df)
        
        return df
    
    def _winsorize_results(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compress outlier values using logarithmic winsorization.
        - Values below 95th percentile: unchanged
        - Values above 95th percentile: compressed using log function
        - Preserves ranking/ordering
        - No identical values at cap
        """
        import numpy as np
        
        logger.info("  Applying logarithmic winsorization to compress outliers...")
        
        def winsorize_column(series, col_name):
            """Winsorize a single column"""
            if series.isna().all() or len(series) == 0:
                return series
            
            # Calculate 95th percentile as threshold
            p95 = series.quantile(0.95)
            
            if p95 <= 0:
                return series
            
            def compress_value(x):
                if pd.isna(x) or x <= p95:
                    return round(x) if not pd.isna(x) else x
                else:
                    # Logarithmic compression: p95 + log(1 + (x - p95) / p95) * p95
                    # This compresses values above p95 while preserving order
                    excess = x - p95
                    compressed = p95 + np.log1p(excess / p95) * p95 * 0.5
                    return round(compressed)  # Round to integer
            
            result = series.apply(compress_value)
            
            # Count how many were compressed
            compressed_count = (series > p95).sum()
            if compressed_count > 0:
                logger.info(f"    {col_name}: {compressed_count} values compressed (p95={p95:.0f})")
                logger.info(f"    {col_name}: new range {result.min():.0f}-{result.max():.0f}")
            
            return result
        
        # Winsorize safety stock
        if 'safety_stock_optimized' in df.columns:
            df['safety_stock_optimized'] = winsorize_column(
                df['safety_stock_optimized'], 'Safety Stock'
            )
        
        # Winsorize reorder point
        if 'reorder_point_optimized' in df.columns:
            df['reorder_point_optimized'] = winsorize_column(
                df['reorder_point_optimized'], 'Reorder Point'
            )
        
        # Winsorize EOQ
        if 'eoq_optimized' in df.columns:
            df['eoq_optimized'] = winsorize_column(
                df['eoq_optimized'], 'EOQ'
            )
        
        return df
    
    def _save_results(
        self,
        optimization_df: pd.DataFrame,
        schedule_df: pd.DataFrame,
        holding_analysis: Dict,
        savings_analysis: Dict
    ):
        """Save optimization results"""
        output_path = Path(self.config.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save optimization results
        optimization_df.to_csv(
            output_path / 'reorder_optimization.csv',
            index=False,
            encoding='utf-8-sig'
        )
        logger.info(f"  Saved reorder_optimization.csv ({len(optimization_df)} items)")
        
        # Save order schedule
        if not schedule_df.empty:
            schedule_df.to_csv(
                output_path / 'order_schedule.csv',
                index=False,
                encoding='utf-8-sig'
            )
            logger.info(f"  Saved order_schedule.csv ({len(schedule_df)} orders)")
        
        # Save analysis report
        analysis_report = {
            'generated_at': datetime.now().isoformat(),
            'holding_cost_analysis': holding_analysis,
            'savings_analysis': savings_analysis,
            'config': {
                'ordering_cost': self.config.default_ordering_cost,
                'holding_rate': self.config.default_holding_rate,
                'lead_time_days': self.config.default_lead_time,
                'service_level': self.config.target_service_level
            }
        }
        
        with open(output_path / 'optimization_analysis.json', 'w') as f:
            json.dump(analysis_report, f, indent=2, default=str)
        logger.info(f"  Saved optimization_analysis.json")
        
        # Print summary
        logger.info(f"\n  Potential Annual Savings: Rp {savings_analysis['potential_savings']:,.0f}")
        logger.info(f"  Savings Percentage: {savings_analysis['savings_percentage']:.1f}%")
        
        logger.info(f"\n  Output saved to: {output_path.absolute()}")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main entry point"""
    config = ReorderConfig(
        features_dir="../data/features",
        predictions_dir="../data/predictions",
        forecasts_dir="../data/forecasts",
        output_dir="../data/reorder"
    )
    
    processor = ReorderOptimizationProcessor(config)
    
    try:
        results_df = processor.run()
        
        # Print summary
        print("\n" + "=" * 40)
        print("OPTIMIZATION SUMMARY")
        print("=" * 40)
        print(f"Total items optimized: {len(results_df)}")
        
        if 'eoq_optimized' in results_df.columns:
            print(f"Average EOQ: {results_df['eoq_optimized'].mean():.0f}")
        
        if 'safety_stock_optimized' in results_df.columns:
            print(f"Average Safety Stock: {results_df['safety_stock_optimized'].mean():.0f}")
        
    except Exception as e:
        logger.error(f"Optimization failed: {e}")
        raise


if __name__ == '__main__':
    main()
