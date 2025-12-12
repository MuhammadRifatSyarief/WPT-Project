"""
MBA FP-Growth Algorithm Runner
==============================

Implementation of FP-Growth algorithm for frequent itemset mining.
Generally faster than Apriori for large datasets.

Author: Project 2 - Sales Analytics
Version: 1.0.0
"""

import pandas as pd
import numpy as np
import logging
from typing import Optional
from mlxtend.frequent_patterns import fpgrowth, association_rules

from .base_runner import BaseAlgorithmRunner

logger = logging.getLogger(__name__)


class FPGrowthRunner(BaseAlgorithmRunner):
    """
    FP-Growth algorithm implementation for Market Basket Analysis.
    
    FP-Growth works by:
    1. Building a compressed FP-tree structure
    2. Mining patterns directly from the tree
    3. No candidate generation needed
    
    Pros:
    - Faster than Apriori (only 2 database scans)
    - More memory efficient
    - Better for dense datasets
    
    Cons:
    - Tree construction can be expensive
    - May not fit in memory for very large datasets
    
    Example:
        >>> runner = FPGrowthRunner(config)
        >>> itemsets, rules = runner.run(basket_matrix)
        >>> runner.print_summary()
    """
    
    def __init__(self, config):
        """
        Initialize FP-Growth runner.
        
        Args:
            config: MBAConfig instance
        """
        super().__init__(config)
        self.algorithm_name = "fpgrowth"
        
    def _run_frequent_itemsets(self, basket_matrix: pd.DataFrame) -> pd.DataFrame:
        """
        Run FP-Growth algorithm to find frequent itemsets.
        
        Args:
            basket_matrix: Binary encoded transaction matrix
            
        Returns:
            DataFrame with columns: ['support', 'itemsets']
        """
        try:
            # Run FP-Growth
            frequent_itemsets = fpgrowth(
                basket_matrix,
                min_support=self.config.min_support,
                use_colnames=True,
                max_len=self.config.max_length,
                verbose=0
            )
            
            # Add itemset length
            frequent_itemsets['length'] = frequent_itemsets['itemsets'].apply(len)
            
            # Sort by support
            frequent_itemsets = frequent_itemsets.sort_values(
                'support', 
                ascending=False
            ).reset_index(drop=True)
            
            return frequent_itemsets
            
        except Exception as e:
            logger.error(f"FP-Growth failed: {str(e)}")
            raise
    
    def _generate_rules(self, frequent_itemsets: pd.DataFrame) -> pd.DataFrame:
        """
        Generate association rules from frequent itemsets.
        
        Args:
            frequent_itemsets: DataFrame from FP-Growth
            
        Returns:
            DataFrame with association rules and metrics
        """
        if len(frequent_itemsets) == 0:
            logger.warning("No frequent itemsets found, cannot generate rules")
            return pd.DataFrame()
        
        # Filter to itemsets with length >= 2 for rules
        itemsets_for_rules = frequent_itemsets[frequent_itemsets['length'] >= 2]
        
        if len(itemsets_for_rules) == 0:
            logger.warning("No itemsets with length >= 2, cannot generate rules")
            return pd.DataFrame()
        
        try:
            # Generate rules using confidence metric
            rules = association_rules(
                frequent_itemsets,
                metric="confidence",
                min_threshold=self.config.min_confidence,
                num_itemsets=len(frequent_itemsets)
            )
            
            # Filter by lift
            rules = rules[rules['lift'] >= self.config.min_lift]
            
            # Add formatted columns
            rules = self._add_formatted_columns(rules)
            
            # Add additional metrics
            rules = self._add_additional_metrics(rules, len(frequent_itemsets))
            
            # Sort by lift descending
            rules = rules.sort_values('lift', ascending=False).reset_index(drop=True)
            
            return rules
            
        except Exception as e:
            logger.error(f"Rule generation failed: {str(e)}")
            raise
    
    def _add_formatted_columns(self, rules: pd.DataFrame) -> pd.DataFrame:
        """Add human-readable formatted columns to rules."""
        df = rules.copy()
        
        # Format antecedents and consequents as strings
        df['antecedents_str'] = df['antecedents'].apply(
            lambda x: ', '.join(sorted(str(i) for i in x))
        )
        df['consequents_str'] = df['consequents'].apply(
            lambda x: ', '.join(sorted(str(i) for i in x))
        )
        
        # Format full rule
        df['rule_str'] = df.apply(
            lambda row: f"{row['antecedents_str']} -> {row['consequents_str']}",
            axis=1
        )
        
        # Add itemset sizes
        df['antecedent_size'] = df['antecedents'].apply(len)
        df['consequent_size'] = df['consequents'].apply(len)
        df['rule_size'] = df['antecedent_size'] + df['consequent_size']
        
        return df
    
    def _add_additional_metrics(
        self, 
        rules: pd.DataFrame, 
        total_itemsets: int
    ) -> pd.DataFrame:
        """Add additional evaluation metrics to rules."""
        df = rules.copy()
        
        # Conviction: (1 - consequent_support) / (1 - confidence)
        # High conviction = strong rule
        df['conviction'] = np.where(
            df['confidence'] < 1,
            (1 - df['consequent support']) / (1 - df['confidence']),
            np.inf
        )
        
        # Leverage: support - (antecedent_support * consequent_support)
        # Positive = more co-occurrence than expected
        df['leverage'] = (
            df['support'] - 
            (df['antecedent support'] * df['consequent support'])
        )
        
        # Kulczynski: (confidence + consequent_confidence) / 2
        # Where consequent_confidence = support / consequent_support
        df['kulczynski'] = 0.5 * (
            df['confidence'] + 
            df['support'] / df['consequent support']
        )
        
        # Imbalance Ratio
        df['imbalance_ratio'] = abs(
            df['antecedent support'] - df['consequent support']
        ) / (
            df['antecedent support'] + df['consequent support'] - df['support']
        )
        
        return df
    
    def get_rules_for_consequent(
        self, 
        consequent_item: str,
        top_n: int = 10
    ) -> pd.DataFrame:
        """
        Get top rules that lead to a specific consequent.
        
        Useful for: "What products lead customers to buy X?"
        
        Args:
            consequent_item: Product to find as consequent
            top_n: Number of rules to return
            
        Returns:
            DataFrame with filtered rules
        """
        if self.rules is None:
            raise ValueError("No rules generated. Run algorithm first.")
        
        # Filter rules where consequent contains the item
        mask = self.rules['consequents'].apply(lambda x: consequent_item in x)
        filtered = self.rules[mask].head(top_n)
        
        return filtered
    
    def get_rules_for_antecedent(
        self, 
        antecedent_item: str,
        top_n: int = 10
    ) -> pd.DataFrame:
        """
        Get top rules that start with a specific antecedent.
        
        Useful for: "What products do customers buy after X?"
        
        Args:
            antecedent_item: Product to find as antecedent
            top_n: Number of rules to return
            
        Returns:
            DataFrame with filtered rules
        """
        if self.rules is None:
            raise ValueError("No rules generated. Run algorithm first.")
        
        # Filter rules where antecedent contains the item
        mask = self.rules['antecedents'].apply(lambda x: antecedent_item in x)
        filtered = self.rules[mask].head(top_n)
        
        return filtered
    
    def compare_with_apriori(
        self, 
        basket_matrix: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Run both FP-Growth and Apriori for comparison.
        
        Args:
            basket_matrix: Binary encoded transaction matrix
            
        Returns:
            DataFrame comparing both algorithms
        """
        from .apriori_runner import AprioriRunner
        import time
        
        results = []
        
        # Run FP-Growth
        start = time.time()
        fp_itemsets, fp_rules = self.run(basket_matrix)
        fp_time = time.time() - start
        
        results.append({
            'algorithm': 'FP-Growth',
            'time_seconds': fp_time,
            'itemsets_found': len(fp_itemsets),
            'rules_generated': len(fp_rules)
        })
        
        # Run Apriori
        apriori_runner = AprioriRunner(self.config)
        start = time.time()
        ap_itemsets, ap_rules = apriori_runner.run(basket_matrix)
        ap_time = time.time() - start
        
        results.append({
            'algorithm': 'Apriori',
            'time_seconds': ap_time,
            'itemsets_found': len(ap_itemsets),
            'rules_generated': len(ap_rules)
        })
        
        comparison = pd.DataFrame(results)
        comparison['speedup'] = comparison['time_seconds'].max() / comparison['time_seconds']
        
        return comparison
