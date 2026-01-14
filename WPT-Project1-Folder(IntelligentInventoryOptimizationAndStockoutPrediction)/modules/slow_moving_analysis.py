"""
Module 8: Slow-Moving Analysis
===============================

Project 1 - Intelligent Inventory Optimization & Stockout Prediction

Features:
1. Dead stock identification
2. Slow-moving item classification
3. Aging analysis
4. Disposal recommendations
5. Markdown pricing suggestions
6. Holding cost impact analysis

Author: AI Assistant
Date: January 2026
Version: 1.0.0
"""

import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any, Tuple
from dataclasses import dataclass
import json

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
class SlowMovingConfig:
    """Configuration for slow-moving analysis"""
    # Input/Output
    features_dir: str = "../data/features"
    prepared_dir: str = "../data/prepared"
    output_dir: str = "../data/slow_moving"
    
    # Thresholds for classification
    dead_stock_days: int = 180          # No sales in 180 days = dead stock
    slow_moving_days: int = 90          # No sales in 90 days = slow moving
    slow_turnover_threshold: float = 1.0  # Turnover < 1x per year
    
    # Aging buckets (days)
    aging_buckets: List[int] = None     # Will be set in __post_init__
    
    # Financial parameters
    holding_cost_rate: float = 0.20     # 20% per year
    markdown_rates: Dict[str, float] = None  # Will be set in __post_init__
    
    # Disposal thresholds
    disposal_threshold_days: int = 365  # Recommend disposal if > 365 days old
    
    def __post_init__(self):
        if self.aging_buckets is None:
            self.aging_buckets = [30, 60, 90, 180, 365]
        if self.markdown_rates is None:
            self.markdown_rates = {
                '30-60': 0.10,    # 10% discount
                '60-90': 0.20,    # 20% discount
                '90-180': 0.35,   # 35% discount
                '180-365': 0.50,  # 50% discount
                '365+': 0.70      # 70% discount (clearance)
            }


# =============================================================================
# SLOW-MOVING CLASSIFIER
# =============================================================================

class SlowMovingClassifier:
    """Classify items based on movement velocity"""
    
    def __init__(self, config: SlowMovingConfig):
        self.config = config
    
    def classify_items(
        self,
        features_df: pd.DataFrame,
        sales_df: pd.DataFrame = None
    ) -> pd.DataFrame:
        """
        Classify items into categories:
        - Dead Stock: No sales in X days
        - Slow Moving: Low turnover
        - Normal: Regular movement
        - Fast Moving: High turnover
        """
        logger.info("  Classifying items by movement velocity...")
        
        df = features_df.copy()
        
        # Calculate days since last sale
        df['days_since_last_sale'] = self._calculate_days_since_sale(df, sales_df)
        
        # Classify by movement
        df['movement_class'] = df.apply(self._classify_movement, axis=1)
        
        # Count by class
        class_counts = df['movement_class'].value_counts()
        logger.info(f"  Classification results: {class_counts.to_dict()}")
        
        return df
    
    def _calculate_days_since_sale(
        self,
        features_df: pd.DataFrame,
        sales_df: pd.DataFrame = None
    ) -> pd.Series:
        """Calculate days since last sale for each item"""
        today = datetime.now()
        
        if sales_df is not None and not sales_df.empty and 'trans_date' in sales_df.columns:
            # Calculate from actual sales data
            sales_df['trans_date'] = pd.to_datetime(sales_df['trans_date'], errors='coerce')
            
            last_sale = sales_df.groupby('item_id')['trans_date'].max().reset_index()
            last_sale.columns = ['id', 'last_sale_date']
            
            merged = features_df.merge(last_sale, on='id', how='left')
            
            days_since = (today - merged['last_sale_date']).dt.days
            days_since = days_since.fillna(365)  # Assume 365 days if no sales
            
            return days_since
        else:
            # Estimate from turnover ratio
            if 'turnover_ratio' in features_df.columns:
                # Low turnover = more days since last sale
                turnover = features_df['turnover_ratio'].fillna(0.1).clip(lower=0.1)
                days_since = (365 / turnover).clip(upper=365)
                return days_since
            else:
                return pd.Series([180] * len(features_df))  # Default 180 days
    
    def _classify_movement(self, row) -> str:
        """Classify a single item based on turnover and history"""
        turnover = row.get('turnover_ratio', 0)
        coverage = row.get('stock_coverage_days', 0)
        days = row.get('days_since_last_sale', 180)
        
        # Dead stock: Very low turnover AND high coverage (sitting too long)
        if turnover < 0.5 and coverage > 90:
            return 'Dead Stock'
        
        # Dead stock: No sales for extended period
        if days >= self.config.dead_stock_days:
            return 'Dead Stock'
        
        # Fast moving: High turnover (monthly or more)
        if turnover >= 12.0:
            return 'Fast Moving'
        
        # Normal: Good turnover (2-12x per year)
        if turnover >= 2.0:
            return 'Normal'
        
        # Slow moving: Low turnover or long time since last sale
        if turnover < 2.0 or days >= self.config.slow_moving_days:
            return 'Slow Moving'
        
        return 'Normal'


# =============================================================================
# AGING ANALYZER
# =============================================================================

class AgingAnalyzer:
    """Analyze inventory aging"""
    
    def __init__(self, config: SlowMovingConfig):
        self.config = config
    
    def analyze_aging(self, df: pd.DataFrame) -> pd.DataFrame:
        """Categorize items by age buckets"""
        logger.info("  Analyzing inventory aging...")
        
        df = df.copy()
        
        # Create aging bucket
        df['aging_bucket'] = df['days_since_last_sale'].apply(self._get_aging_bucket)
        
        # Calculate aging distribution
        aging_dist = df.groupby('aging_bucket').agg({
            'id': 'count',
            'current_stock': 'sum'
        }).reset_index()
        aging_dist.columns = ['aging_bucket', 'item_count', 'total_stock']
        
        logger.info(f"  Aging distribution:")
        for _, row in aging_dist.iterrows():
            logger.info(f"    {row['aging_bucket']}: {row['item_count']} items, {row['total_stock']:.0f} units")
        
        return df
    
    def _get_aging_bucket(self, days: float) -> str:
        """Assign aging bucket based on days"""
        if days <= 30:
            return '0-30 days'
        elif days <= 60:
            return '31-60 days'
        elif days <= 90:
            return '61-90 days'
        elif days <= 180:
            return '91-180 days'
        elif days <= 365:
            return '181-365 days'
        else:
            return '365+ days'


# =============================================================================
# RECOMMENDATION ENGINE
# =============================================================================

class SlowMovingRecommendationEngine:
    """Generate recommendations for slow-moving items"""
    
    def __init__(self, config: SlowMovingConfig):
        self.config = config
    
    def generate_recommendations(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate action recommendations for each item"""
        logger.info("  Generating recommendations...")
        
        df = df.copy()
        
        # Generate recommendations
        df['recommendation'] = df.apply(self._get_recommendation, axis=1)
        df['markdown_rate'] = df.apply(self._get_markdown_rate, axis=1)
        df['suggested_price'] = self._calculate_suggested_price(df)
        df['priority_score'] = self._calculate_priority_score(df)
        
        # Count recommendations
        rec_counts = df['recommendation'].value_counts()
        logger.info(f"  Recommendations: {rec_counts.to_dict()}")
        
        return df
    
    def _get_recommendation(self, row) -> str:
        """Get recommendation for single item"""
        movement = row.get('movement_class', 'Normal')
        days = row.get('days_since_last_sale', 0)
        stock = row.get('current_stock', 0)
        
        if stock == 0:
            return 'No Action (No Stock)'
        
        if movement == 'Dead Stock':
            if days >= self.config.disposal_threshold_days:
                return 'Dispose/Write-off'
            else:
                return 'Clearance Sale (70% off)'
        
        if movement == 'Slow Moving':
            if days >= 180:
                return 'Deep Discount (50% off)'
            elif days >= 90:
                return 'Markdown (35% off)'
            else:
                return 'Promotional Sale (20% off)'
        
        if movement == 'Fast Moving':
            return 'No Action (Fast Moving)'
        
        return 'Monitor'
    
    def _get_markdown_rate(self, row) -> float:
        """Get markdown rate based on aging"""
        days = row.get('days_since_last_sale', 0)
        
        if days <= 30:
            return 0.0
        elif days <= 60:
            return self.config.markdown_rates.get('30-60', 0.10)
        elif days <= 90:
            return self.config.markdown_rates.get('60-90', 0.20)
        elif days <= 180:
            return self.config.markdown_rates.get('90-180', 0.35)
        elif days <= 365:
            return self.config.markdown_rates.get('180-365', 0.50)
        else:
            return self.config.markdown_rates.get('365+', 0.70)
    
    def _calculate_suggested_price(self, df: pd.DataFrame) -> pd.Series:
        """Calculate suggested price after markdown"""
        selling_price = df.get('unitPrice', df.get('avgCost', 0) * 1.3)
        selling_price = selling_price.fillna(0)
        markdown_rate = df['markdown_rate']
        
        suggested_price = selling_price * (1 - markdown_rate)
        return suggested_price.round(0)
    
    def _calculate_priority_score(self, df: pd.DataFrame) -> pd.Series:
        """Calculate priority score for action (higher = more urgent)"""
        # Factors: days since sale, stock value, holding cost
        days = df['days_since_last_sale'].fillna(0)
        stock = df.get('current_stock', 0).fillna(0)
        cost = df.get('avgCost', 1000).fillna(1000)
        
        stock_value = stock * cost
        days_factor = (days / 365).clip(0, 1)  # Normalize to 0-1
        value_factor = (stock_value / stock_value.max()).clip(0, 1) if stock_value.max() > 0 else 0
        
        # Priority = weighted combination
        priority = (days_factor * 0.6 + value_factor * 0.4) * 100
        return priority.round(1)


# =============================================================================
# FINANCIAL IMPACT CALCULATOR
# =============================================================================

class FinancialImpactCalculator:
    """Calculate financial impact of slow-moving inventory"""
    
    def __init__(self, config: SlowMovingConfig):
        self.config = config
    
    def calculate_impact(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate financial metrics"""
        logger.info("  Calculating financial impact...")
        
        # Filter slow-moving items
        slow_items = df[df['movement_class'].isin(['Dead Stock', 'Slow Moving'])]
        
        # Calculate metrics
        stock = slow_items.get('current_stock', 0).fillna(0)
        cost = slow_items.get('avgCost', 1000).fillna(1000)
        
        total_stock_value = (stock * cost).sum()
        annual_holding_cost = total_stock_value * self.config.holding_cost_rate
        
        # By category
        dead_stock_value = (df[df['movement_class'] == 'Dead Stock'].get('current_stock', 0).fillna(0) * 
                          df[df['movement_class'] == 'Dead Stock'].get('avgCost', 1000).fillna(1000)).sum()
        
        slow_moving_value = (df[df['movement_class'] == 'Slow Moving'].get('current_stock', 0).fillna(0) * 
                           df[df['movement_class'] == 'Slow Moving'].get('avgCost', 1000).fillna(1000)).sum()
        
        impact = {
            'total_slow_moving_items': len(slow_items),
            'total_slow_moving_stock_value': round(total_stock_value, 0),
            'annual_holding_cost_waste': round(annual_holding_cost, 0),
            'dead_stock_value': round(dead_stock_value, 0),
            'slow_moving_value': round(slow_moving_value, 0),
            'potential_recovery': round(total_stock_value * 0.3, 0)  # Assume 30% recovery through sales
        }
        
        logger.info(f"  Total slow-moving value: Rp {impact['total_slow_moving_stock_value']:,.0f}")
        logger.info(f"  Annual holding cost waste: Rp {impact['annual_holding_cost_waste']:,.0f}")
        
        return impact


# =============================================================================
# MAIN PROCESSOR
# =============================================================================

class SlowMovingAnalysisProcessor:
    """Main orchestrator for slow-moving analysis"""
    
    def __init__(self, config: Optional[SlowMovingConfig] = None):
        self.config = config or SlowMovingConfig()
        self.classifier = SlowMovingClassifier(self.config)
        self.aging_analyzer = AgingAnalyzer(self.config)
        self.recommender = SlowMovingRecommendationEngine(self.config)
        self.financial_calc = FinancialImpactCalculator(self.config)
        
        self.analysis_results = pd.DataFrame()
        self.financial_impact = {}
    
    def run(self) -> pd.DataFrame:
        """Run slow-moving analysis pipeline"""
        logger.info("=" * 60)
        logger.info("STARTING SLOW-MOVING ANALYSIS")
        logger.info("=" * 60)
        
        # Phase 1: Load data
        logger.info("\n[PHASE 1] Loading Data")
        features_df, sales_df = self._load_data()
        
        if features_df.empty:
            logger.error("No features data available")
            return pd.DataFrame()
        
        # Phase 2: Classify items
        logger.info("\n[PHASE 2] Classifying Items")
        classified_df = self.classifier.classify_items(features_df, sales_df)
        
        # Phase 3: Analyze aging
        logger.info("\n[PHASE 3] Analyzing Aging")
        aged_df = self.aging_analyzer.analyze_aging(classified_df)
        
        # Phase 4: Generate recommendations
        logger.info("\n[PHASE 4] Generating Recommendations")
        recommended_df = self.recommender.generate_recommendations(aged_df)
        
        # Phase 5: Calculate financial impact
        logger.info("\n[PHASE 5] Calculating Financial Impact")
        self.financial_impact = self.financial_calc.calculate_impact(recommended_df)
        
        # Phase 6: Save results
        logger.info("\n[PHASE 6] Saving Results")
        self._save_results(recommended_df)
        
        self.analysis_results = recommended_df
        
        logger.info("\n" + "=" * 60)
        logger.info("SLOW-MOVING ANALYSIS COMPLETE")
        logger.info("=" * 60)
        
        return recommended_df
    
    def _load_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load features and sales data"""
        features_path = Path(self.config.features_dir) / "master_features.csv"
        sales_path = Path(self.config.prepared_dir) / "sales_details.csv"
        
        features_df = pd.DataFrame()
        sales_df = pd.DataFrame()
        
        if features_path.exists():
            features_df = pd.read_csv(features_path, encoding='utf-8-sig')
            logger.info(f"  Loaded features: {len(features_df)} items")
        
        if sales_path.exists():
            sales_df = pd.read_csv(sales_path, encoding='utf-8-sig', low_memory=False)
            logger.info(f"  Loaded sales: {len(sales_df)} records")
        
        return features_df, sales_df
    
    def _save_results(self, results_df: pd.DataFrame):
        """Save analysis results"""
        output_path = Path(self.config.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save full results
        results_df.to_csv(
            output_path / 'slow_moving_analysis.csv',
            index=False,
            encoding='utf-8-sig'
        )
        logger.info(f"  Saved slow_moving_analysis.csv ({len(results_df)} items)")
        
        # Save action items (slow-moving only)
        action_items = results_df[results_df['movement_class'].isin(['Dead Stock', 'Slow Moving'])]
        action_items = action_items.sort_values('priority_score', ascending=False)
        
        action_items.to_csv(
            output_path / 'action_items.csv',
            index=False,
            encoding='utf-8-sig'
        )
        logger.info(f"  Saved action_items.csv ({len(action_items)} items)")
        
        # Save summary report
        summary = {
            'generated_at': datetime.now().isoformat(),
            'total_items_analyzed': len(results_df),
            'classification_summary': results_df['movement_class'].value_counts().to_dict(),
            'aging_summary': results_df['aging_bucket'].value_counts().to_dict(),
            'recommendation_summary': results_df['recommendation'].value_counts().to_dict(),
            'financial_impact': self.financial_impact,
            'top_priority_items': action_items.head(20)[['id', 'no', 'name', 'movement_class', 'priority_score', 'recommendation']].to_dict('records') if 'name' in action_items.columns else []
        }
        
        with open(output_path / 'analysis_summary.json', 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        logger.info(f"  Saved analysis_summary.json")
        
        logger.info(f"\n  Output saved to: {output_path.absolute()}")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main entry point"""
    config = SlowMovingConfig(
        features_dir="../data/features",
        prepared_dir="../data/prepared",
        output_dir="../data/slow_moving"
    )
    
    processor = SlowMovingAnalysisProcessor(config)
    
    try:
        results_df = processor.run()
        
        # Print summary
        print("\n" + "=" * 40)
        print("SLOW-MOVING ANALYSIS SUMMARY")
        print("=" * 40)
        print(f"Total items analyzed: {len(results_df)}")
        
        if 'movement_class' in results_df.columns:
            print("\nMovement Classification:")
            print(results_df['movement_class'].value_counts().to_string())
        
        print(f"\nFinancial Impact:")
        print(f"  Dead Stock Value: Rp {processor.financial_impact.get('dead_stock_value', 0):,.0f}")
        print(f"  Annual Holding Cost Waste: Rp {processor.financial_impact.get('annual_holding_cost_waste', 0):,.0f}")
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise


if __name__ == '__main__':
    main()
