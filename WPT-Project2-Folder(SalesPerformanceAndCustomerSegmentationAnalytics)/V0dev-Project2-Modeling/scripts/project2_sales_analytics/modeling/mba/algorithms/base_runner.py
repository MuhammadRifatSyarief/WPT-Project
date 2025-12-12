"""
MBA Base Algorithm Runner
=========================

Abstract base class for MBA algorithm implementations.
Provides common interface and utilities.

Author: Project 2 - Sales Analytics
Version: 1.0.0
"""

import pandas as pd
import numpy as np
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseAlgorithmRunner(ABC):
    """
    Abstract base class for association rule mining algorithms.
    
    Provides common interface for:
    - Running frequent itemset mining
    - Generating association rules
    - Tracking performance metrics
    
    Subclasses must implement:
    - _run_frequent_itemsets()
    - _generate_rules()
    """
    
    def __init__(self, config):
        """
        Initialize algorithm runner.
        
        Args:
            config: MBAConfig instance with algorithm parameters
        """
        self.config = config
        self.frequent_itemsets: Optional[pd.DataFrame] = None
        self.rules: Optional[pd.DataFrame] = None
        self.performance_metrics: Dict[str, Any] = {}
        self.algorithm_name: str = "base"
        
    @abstractmethod
    def _run_frequent_itemsets(self, basket_matrix: pd.DataFrame) -> pd.DataFrame:
        """
        Run frequent itemset mining algorithm.
        
        Args:
            basket_matrix: Binary encoded transaction matrix
            
        Returns:
            DataFrame with frequent itemsets and support values
        """
        pass
    
    @abstractmethod
    def _generate_rules(self, frequent_itemsets: pd.DataFrame) -> pd.DataFrame:
        """
        Generate association rules from frequent itemsets.
        
        Args:
            frequent_itemsets: DataFrame from frequent itemset mining
            
        Returns:
            DataFrame with association rules
        """
        pass
    
    def run(
        self, 
        basket_matrix: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Execute complete association rule mining pipeline.
        
        Args:
            basket_matrix: Binary encoded transaction matrix
            
        Returns:
            Tuple of (frequent_itemsets, association_rules)
        """
        logger.info(f"Running {self.algorithm_name} algorithm...")
        start_time = datetime.now()
        
        # Step 1: Find frequent itemsets
        logger.info("   Step 1: Finding frequent itemsets...")
        itemset_start = datetime.now()
        
        self.frequent_itemsets = self._run_frequent_itemsets(basket_matrix)
        
        itemset_time = (datetime.now() - itemset_start).total_seconds()
        logger.info(f"   Found {len(self.frequent_itemsets):,} frequent itemsets in {itemset_time:.2f}s")
        
        # Step 2: Generate association rules
        logger.info("   Step 2: Generating association rules...")
        rules_start = datetime.now()
        
        self.rules = self._generate_rules(self.frequent_itemsets)
        
        rules_time = (datetime.now() - rules_start).total_seconds()
        logger.info(f"   Generated {len(self.rules):,} rules in {rules_time:.2f}s")
        
        # Calculate performance metrics
        total_time = (datetime.now() - start_time).total_seconds()
        self._calculate_performance_metrics(
            basket_matrix, 
            itemset_time, 
            rules_time, 
            total_time
        )
        
        return self.frequent_itemsets, self.rules
    
    def _calculate_performance_metrics(
        self,
        basket_matrix: pd.DataFrame,
        itemset_time: float,
        rules_time: float,
        total_time: float
    ) -> None:
        """Calculate and store performance metrics."""
        self.performance_metrics = {
            'algorithm': self.algorithm_name,
            'parameters': {
                'min_support': self.config.min_support,
                'min_confidence': self.config.min_confidence,
                'min_lift': self.config.min_lift,
                'max_length': self.config.max_length
            },
            'input': {
                'transactions': len(basket_matrix),
                'products': len(basket_matrix.columns),
                'matrix_density': basket_matrix.values.mean()
            },
            'output': {
                'frequent_itemsets': len(self.frequent_itemsets) if self.frequent_itemsets is not None else 0,
                'association_rules': len(self.rules) if self.rules is not None else 0
            },
            'timing': {
                'itemset_mining_seconds': itemset_time,
                'rule_generation_seconds': rules_time,
                'total_seconds': total_time
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def get_frequent_itemsets(self) -> pd.DataFrame:
        """Return frequent itemsets DataFrame."""
        if self.frequent_itemsets is None:
            raise ValueError("No frequent itemsets found. Run algorithm first.")
        return self.frequent_itemsets
    
    def get_rules(self) -> pd.DataFrame:
        """Return association rules DataFrame."""
        if self.rules is None:
            raise ValueError("No rules generated. Run algorithm first.")
        return self.rules
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Return performance metrics."""
        return self.performance_metrics
    
    def print_summary(self) -> None:
        """Print algorithm execution summary."""
        print("\n" + "=" * 60)
        print(f"{self.algorithm_name.upper()} ALGORITHM SUMMARY")
        print("=" * 60)
        
        if not self.performance_metrics:
            print("No results available. Run algorithm first.")
            return
        
        params = self.performance_metrics['parameters']
        output = self.performance_metrics['output']
        timing = self.performance_metrics['timing']
        
        print(f"\nParameters:")
        print(f"  Min Support:     {params['min_support']}")
        print(f"  Min Confidence:  {params['min_confidence']}")
        print(f"  Min Lift:        {params['min_lift']}")
        print(f"  Max Length:      {params['max_length']}")
        
        print(f"\nResults:")
        print(f"  Frequent Itemsets: {output['frequent_itemsets']:,}")
        print(f"  Association Rules: {output['association_rules']:,}")
        
        print(f"\nTiming:")
        print(f"  Itemset Mining:    {timing['itemset_mining_seconds']:.2f}s")
        print(f"  Rule Generation:   {timing['rule_generation_seconds']:.2f}s")
        print(f"  Total Time:        {timing['total_seconds']:.2f}s")
    
    def get_itemsets_by_length(self) -> Dict[int, pd.DataFrame]:
        """
        Group frequent itemsets by length.
        
        Returns:
            Dictionary mapping itemset length to DataFrame
        """
        if self.frequent_itemsets is None:
            raise ValueError("No frequent itemsets found. Run algorithm first.")
        
        df = self.frequent_itemsets.copy()
        df['length'] = df['itemsets'].apply(len)
        
        return {
            length: group.drop('length', axis=1)
            for length, group in df.groupby('length')
        }
    
    def get_top_itemsets(self, n: int = 20) -> pd.DataFrame:
        """
        Get top N frequent itemsets by support.
        
        Args:
            n: Number of itemsets to return
            
        Returns:
            DataFrame with top itemsets
        """
        if self.frequent_itemsets is None:
            raise ValueError("No frequent itemsets found. Run algorithm first.")
        
        return self.frequent_itemsets.nlargest(n, 'support')
