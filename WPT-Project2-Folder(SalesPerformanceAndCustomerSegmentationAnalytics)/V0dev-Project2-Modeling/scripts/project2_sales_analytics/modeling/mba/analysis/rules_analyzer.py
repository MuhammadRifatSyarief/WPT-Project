"""
MBA Rules Analyzer Module
=========================

Analyzes association rules and generates actionable insights
for business decision making.

Author: Project 2 - Sales Analytics
Version: 1.0.0
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


class RulesAnalyzer:
    """
    Analyzer for association rules with business context.
    
    Provides:
    - Rule categorization and ranking
    - Product affinity analysis
    - Bundle recommendations
    - Rule quality assessment
    
    Example:
        >>> analyzer = RulesAnalyzer(rules_df, config)
        >>> top_rules = analyzer.get_top_rules(n=20)
        >>> bundles = analyzer.identify_bundles()
    """
    
    def __init__(self, rules: pd.DataFrame, config):
        """
        Initialize rules analyzer.
        
        Args:
            rules: DataFrame with association rules
            config: MBAConfig instance
        """
        self.rules = rules.copy()
        self.config = config
        self.analysis_results: Dict[str, Any] = {}
        
    def analyze(self) -> Dict[str, Any]:
        """
        Run comprehensive rules analysis.
        
        Returns:
            Dictionary with analysis results
        """
        logger.info("Starting rules analysis...")
        
        if len(self.rules) == 0:
            logger.warning("No rules to analyze")
            return {'status': 'no_rules'}
        
        self.analysis_results = {
            'summary': self._generate_summary(),
            'quality_metrics': self._assess_rule_quality(),
            'product_analysis': self._analyze_products(),
            'rule_categories': self._categorize_rules(),
            'actionable_insights': self._generate_insights()
        }
        
        logger.info("Analysis complete")
        return self.analysis_results
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate summary statistics for rules."""
        df = self.rules
        
        summary = {
            'total_rules': len(df),
            'unique_antecedents': df['antecedents'].nunique(),
            'unique_consequents': df['consequents'].nunique(),
            'support': {
                'min': df['support'].min(),
                'max': df['support'].max(),
                'mean': df['support'].mean(),
                'median': df['support'].median()
            },
            'confidence': {
                'min': df['confidence'].min(),
                'max': df['confidence'].max(),
                'mean': df['confidence'].mean(),
                'median': df['confidence'].median()
            },
            'lift': {
                'min': df['lift'].min(),
                'max': df['lift'].max(),
                'mean': df['lift'].mean(),
                'median': df['lift'].median()
            }
        }
        
        # Distribution by rule size
        if 'rule_size' in df.columns:
            summary['size_distribution'] = df['rule_size'].value_counts().to_dict()
        
        return summary
    
    def _assess_rule_quality(self) -> pd.DataFrame:
        """
        Assess quality of each rule using multiple metrics.
        
        Returns:
            DataFrame with quality scores
        """
        df = self.rules.copy()
        
        # Normalize metrics to 0-1 scale
        for col in ['support', 'confidence', 'lift']:
            if col in df.columns:
                min_val = df[col].min()
                max_val = df[col].max()
                if max_val > min_val:
                    df[f'{col}_normalized'] = (df[col] - min_val) / (max_val - min_val)
                else:
                    df[f'{col}_normalized'] = 0.5
        
        # Calculate composite quality score
        # Weights: lift (40%), confidence (35%), support (25%)
        df['quality_score'] = (
            df.get('lift_normalized', 0) * 0.40 +
            df.get('confidence_normalized', 0) * 0.35 +
            df.get('support_normalized', 0) * 0.25
        )
        
        # Assign quality tier
        df['quality_tier'] = pd.cut(
            df['quality_score'],
            bins=[0, 0.33, 0.66, 1.0],
            labels=['Low', 'Medium', 'High'],
            include_lowest=True
        )
        
        return df[['rule_str', 'support', 'confidence', 'lift', 'quality_score', 'quality_tier']]
    
    def _analyze_products(self) -> Dict[str, pd.DataFrame]:
        """
        Analyze product appearances in rules.
        
        Returns:
            Dictionary with product analysis DataFrames
        """
        df = self.rules
        
        # Count product appearances as antecedent
        antecedent_counts = defaultdict(int)
        for _, row in df.iterrows():
            for item in row['antecedents']:
                antecedent_counts[item] += 1
        
        # Count product appearances as consequent
        consequent_counts = defaultdict(int)
        for _, row in df.iterrows():
            for item in row['consequents']:
                consequent_counts[item] += 1
        
        # Create summary DataFrames
        antecedent_df = pd.DataFrame([
            {'product': k, 'antecedent_count': v}
            for k, v in antecedent_counts.items()
        ]).sort_values('antecedent_count', ascending=False)
        
        consequent_df = pd.DataFrame([
            {'product': k, 'consequent_count': v}
            for k, v in consequent_counts.items()
        ]).sort_values('consequent_count', ascending=False)
        
        # Merge for complete view
        if len(antecedent_df) > 0 and len(consequent_df) > 0:
            product_summary = antecedent_df.merge(
                consequent_df,
                on='product',
                how='outer'
            ).fillna(0)
            product_summary['total_appearances'] = (
                product_summary['antecedent_count'] + 
                product_summary['consequent_count']
            )
            product_summary = product_summary.sort_values(
                'total_appearances', 
                ascending=False
            )
        else:
            product_summary = pd.DataFrame()
        
        return {
            'antecedent_frequency': antecedent_df,
            'consequent_frequency': consequent_df,
            'product_summary': product_summary
        }
    
    def _categorize_rules(self) -> Dict[str, pd.DataFrame]:
        """
        Categorize rules by characteristics.
        
        Returns:
            Dictionary with categorized rules
        """
        df = self.rules.copy()
        categories = {}
        
        # High lift rules (strong positive association)
        lift_threshold = df['lift'].quantile(0.75)
        categories['high_lift'] = df[df['lift'] >= lift_threshold]
        
        # High confidence rules (reliable predictions)
        conf_threshold = df['confidence'].quantile(0.75)
        categories['high_confidence'] = df[df['confidence'] >= conf_threshold]
        
        # High support rules (frequent patterns)
        support_threshold = df['support'].quantile(0.75)
        categories['high_support'] = df[df['support'] >= support_threshold]
        
        # Golden rules (high in all metrics)
        categories['golden_rules'] = df[
            (df['lift'] >= lift_threshold) &
            (df['confidence'] >= conf_threshold) &
            (df['support'] >= support_threshold)
        ]
        
        # Single antecedent rules (simpler, more actionable)
        if 'antecedent_size' in df.columns:
            categories['simple_rules'] = df[df['antecedent_size'] == 1]
        
        return categories
    
    def _generate_insights(self) -> List[Dict[str, Any]]:
        """
        Generate actionable business insights from rules.
        
        Returns:
            List of insight dictionaries
        """
        insights = []
        df = self.rules
        
        if len(df) == 0:
            return insights
        
        # Insight 1: Top cross-sell opportunities
        top_lift = df.nlargest(5, 'lift')
        for _, row in top_lift.iterrows():
            insights.append({
                'type': 'cross_sell',
                'priority': 'high',
                'title': f"Cross-sell opportunity: {row.get('rule_str', 'N/A')}",
                'description': f"Customers buying {row.get('antecedents_str', 'N/A')} "
                             f"are {row['lift']:.1f}x more likely to buy "
                             f"{row.get('consequents_str', 'N/A')}",
                'confidence': row['confidence'],
                'lift': row['lift']
            })
        
        # Insight 2: Bundle suggestions
        high_confidence = df[df['confidence'] >= 0.5]
        if len(high_confidence) > 0:
            bundle_candidates = high_confidence.nlargest(3, 'support')
            for _, row in bundle_candidates.iterrows():
                insights.append({
                    'type': 'bundle',
                    'priority': 'medium',
                    'title': f"Bundle suggestion: {row.get('rule_str', 'N/A')}",
                    'description': f"{row['confidence']*100:.0f}% of customers who buy "
                                 f"{row.get('antecedents_str', 'N/A')} also buy "
                                 f"{row.get('consequents_str', 'N/A')}",
                    'support': row['support'],
                    'confidence': row['confidence']
                })
        
        # Insight 3: Most influential products
        product_analysis = self._analyze_products()
        if 'product_summary' in product_analysis and len(product_analysis['product_summary']) > 0:
            top_product = product_analysis['product_summary'].iloc[0]
            insights.append({
                'type': 'product_influence',
                'priority': 'medium',
                'title': f"Key product: {top_product['product']}",
                'description': f"Appears in {int(top_product['total_appearances'])} rules "
                             f"({int(top_product['antecedent_count'])} as trigger, "
                             f"{int(top_product['consequent_count'])} as target)",
                'product': top_product['product']
            })
        
        return insights
    
    def get_top_rules(
        self, 
        n: int = 20, 
        sort_by: str = 'lift'
    ) -> pd.DataFrame:
        """
        Get top N rules sorted by specified metric.
        
        Args:
            n: Number of rules to return
            sort_by: Metric to sort by ('lift', 'confidence', 'support')
            
        Returns:
            DataFrame with top rules
        """
        return self.rules.nlargest(n, sort_by)
    
    def get_rules_for_product(
        self, 
        product: str, 
        as_antecedent: bool = True,
        top_n: int = 10
    ) -> pd.DataFrame:
        """
        Get rules involving a specific product.
        
        Args:
            product: Product name/ID
            as_antecedent: Search as antecedent (True) or consequent (False)
            top_n: Maximum rules to return
            
        Returns:
            DataFrame with matching rules
        """
        if as_antecedent:
            mask = self.rules['antecedents'].apply(lambda x: product in x)
        else:
            mask = self.rules['consequents'].apply(lambda x: product in x)
        
        return self.rules[mask].head(top_n)
    
    def identify_bundles(
        self, 
        min_confidence: float = 0.4,
        min_support: float = 0.01
    ) -> pd.DataFrame:
        """
        Identify product bundles from rules.
        
        Bundles are bidirectional associations where
        A -> B and B -> A both exist with high confidence.
        
        Args:
            min_confidence: Minimum confidence for both directions
            min_support: Minimum support threshold
            
        Returns:
            DataFrame with bundle suggestions
        """
        df = self.rules[
            (self.rules['confidence'] >= min_confidence) &
            (self.rules['support'] >= min_support)
        ]
        
        bundles = []
        seen = set()
        
        for _, rule1 in df.iterrows():
            ant1 = frozenset(rule1['antecedents'])
            cons1 = frozenset(rule1['consequents'])
            
            # Look for reverse rule
            reverse_mask = (
                df['antecedents'].apply(lambda x: frozenset(x) == cons1) &
                df['consequents'].apply(lambda x: frozenset(x) == ant1)
            )
            
            reverse_rules = df[reverse_mask]
            
            if len(reverse_rules) > 0:
                bundle_key = tuple(sorted([str(ant1), str(cons1)]))
                
                if bundle_key not in seen:
                    seen.add(bundle_key)
                    reverse_rule = reverse_rules.iloc[0]
                    
                    bundles.append({
                        'item_set_1': rule1.get('antecedents_str', str(ant1)),
                        'item_set_2': rule1.get('consequents_str', str(cons1)),
                        'confidence_1_to_2': rule1['confidence'],
                        'confidence_2_to_1': reverse_rule['confidence'],
                        'avg_confidence': (rule1['confidence'] + reverse_rule['confidence']) / 2,
                        'support': rule1['support'],
                        'lift': rule1['lift']
                    })
        
        return pd.DataFrame(bundles).sort_values('avg_confidence', ascending=False)
    
    def print_summary(self) -> None:
        """Print analysis summary to console."""
        if not self.analysis_results:
            self.analyze()
        
        summary = self.analysis_results.get('summary', {})
        
        print("\n" + "=" * 60)
        print("ASSOCIATION RULES ANALYSIS SUMMARY")
        print("=" * 60)
        
        print(f"\nTotal Rules: {summary.get('total_rules', 0):,}")
        print(f"Unique Antecedents: {summary.get('unique_antecedents', 0):,}")
        print(f"Unique Consequents: {summary.get('unique_consequents', 0):,}")
        
        print("\n--- Metric Ranges ---")
        for metric in ['support', 'confidence', 'lift']:
            if metric in summary:
                m = summary[metric]
                print(f"{metric.capitalize():12} Min: {m['min']:.4f}  Max: {m['max']:.4f}  "
                      f"Mean: {m['mean']:.4f}  Median: {m['median']:.4f}")
        
        # Print top insights
        insights = self.analysis_results.get('actionable_insights', [])
        if insights:
            print("\n--- Top Insights ---")
            for i, insight in enumerate(insights[:5], 1):
                print(f"{i}. [{insight['type'].upper()}] {insight['title']}")
