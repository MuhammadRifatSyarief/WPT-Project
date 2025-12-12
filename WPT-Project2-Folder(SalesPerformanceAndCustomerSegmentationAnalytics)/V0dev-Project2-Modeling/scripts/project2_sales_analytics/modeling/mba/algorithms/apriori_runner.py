"""
MBA Apriori Algorithm Runner
============================

Implementation of Apriori algorithm for frequent itemset mining
and association rule generation.

Author: Project 2 - Sales Analytics
Version: 1.0.0
"""

import pandas as pd
import numpy as np
import logging
from typing import Optional
from mlxtend.frequent_patterns import apriori, association_rules

from .base_runner import BaseAlgorithmRunner

logger = logging.getLogger(__name__)


class AprioriRunner(BaseAlgorithmRunner):
    """
    Apriori algorithm implementation for Market Basket Analysis.
    
    The Apriori algorithm works by:
    1. Finding all itemsets with support >= min_support
    2. Using downward closure property to prune candidates
    3. Generating rules from frequent itemsets
    
    Pros:
    - Well-understood, widely used
    - Good for sparse datasets
    
    Cons:
    - Multiple database scans
    - Can be slow for large datasets
    - Memory intensive for low support
    
    Example:
        >>> runner = AprioriRunner(config)
        >>> itemsets, rules = runner.run(basket_matrix)
        >>> runner.print_summary()
    """
    
    def __init__(self, config):
        """
        Initialize Apriori runner.
        
        Args:
            config: MBAConfig instance
        """
        super().__init__(config)
        self.algorithm_name = "apriori"
        
    def _run_frequent_itemsets(self, basket_matrix: pd.DataFrame) -> pd.DataFrame:
        """
        Run Apriori algorithm to find frequent itemsets.
        
        Args:
            basket_matrix: Binary encoded transaction matrix
            
        Returns:
            DataFrame with columns: ['support', 'itemsets']
        """
        try:
            # Run Apriori
            frequent_itemsets = apriori(
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
            logger.error(f"Apriori failed: {str(e)}")
            raise
    
    def _generate_rules(self, frequent_itemsets: pd.DataFrame) -> pd.DataFrame:
        """
        Generate association rules from frequent itemsets.
        
        Args:
            frequent_itemsets: DataFrame from Apriori
            
        Returns:
            DataFrame with association rules and metrics
        """
        if len(frequent_itemsets) == 0:
            logger.warning("No frequent itemsets found, cannot generate rules")
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
    
    def run_with_multiple_supports(
        self, 
        basket_matrix: pd.DataFrame,
        support_values: list = [0.005, 0.01, 0.02, 0.05]
    ) -> pd.DataFrame:
        """
        Run Apriori with multiple support thresholds for comparison.
        
        Args:
            basket_matrix: Binary encoded transaction matrix
            support_values: List of support thresholds to try
            
        Returns:
            DataFrame comparing results across thresholds
        """
        results = []
        
        for support in support_values:
            try:
                # Update config temporarily
                original_support = self.config.min_support
                self.config.min_support = support
                
                # Run algorithm
                itemsets, rules = self.run(basket_matrix)
                
                results.append({
                    'min_support': support,
                    'frequent_itemsets': len(itemsets),
                    'association_rules': len(rules),
                    'max_lift': rules['lift'].max() if len(rules) > 0 else 0,
                    'avg_confidence': rules['confidence'].mean() if len(rules) > 0 else 0
                })
                
                # Restore original config
                self.config.min_support = original_support
                
            except Exception as e:
                logger.warning(f"Failed for support={support}: {str(e)}")
                results.append({
                    'min_support': support,
                    'frequent_itemsets': 0,
                    'association_rules': 0,
                    'max_lift': 0,
                    'avg_confidence': 0
                })
        
        return pd.DataFrame(results)
