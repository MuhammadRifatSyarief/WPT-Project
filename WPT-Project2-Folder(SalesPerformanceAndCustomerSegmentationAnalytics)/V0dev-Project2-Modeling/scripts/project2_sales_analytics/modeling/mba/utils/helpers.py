"""
MBA Helper Functions
====================

Utility functions for Market Basket Analysis operations.

Author: Project 2 - Sales Analytics
Version: 1.0.0
"""

import pandas as pd
import numpy as np
from typing import List, Tuple, Dict, Any, Union, FrozenSet


def format_itemset(itemset: FrozenSet) -> str:
    """
    Format a frozenset itemset as a readable string.
    
    Args:
        itemset: FrozenSet of item names/IDs
        
    Returns:
        Formatted string representation
        
    Example:
        >>> format_itemset(frozenset(['A', 'B', 'C']))
        'A, B, C'
    """
    return ', '.join(sorted(str(item) for item in itemset))


def format_rule(antecedent: FrozenSet, consequent: FrozenSet) -> str:
    """
    Format an association rule as a readable string.
    
    Args:
        antecedent: Items on the left side of the rule
        consequent: Items on the right side of the rule
        
    Returns:
        Formatted rule string
        
    Example:
        >>> format_rule(frozenset(['A']), frozenset(['B']))
        'A -> B'
    """
    ant_str = format_itemset(antecedent)
    cons_str = format_itemset(consequent)
    return f"{ant_str} -> {cons_str}"


def calculate_metrics(
    rules_df: pd.DataFrame,
    total_transactions: int
) -> pd.DataFrame:
    """
    Calculate additional metrics for association rules.
    
    Args:
        rules_df: DataFrame with base association rules
        total_transactions: Total number of transactions
        
    Returns:
        DataFrame with additional metrics
    """
    df = rules_df.copy()
    
    # Calculate conviction
    # Conviction = (1 - consequent_support) / (1 - confidence)
    df['conviction'] = np.where(
        df['confidence'] < 1,
        (1 - df['consequent support']) / (1 - df['confidence']),
        np.inf
    )
    
    # Calculate leverage
    # Leverage = support - (antecedent_support * consequent_support)
    df['leverage'] = df['support'] - (df['antecedent support'] * df['consequent support'])
    
    # Calculate Zhang's metric
    # Zhang = (confidence - consequent_support) / max(confidence, consequent_support) * (1 - consequent_support)
    df['zhang_metric'] = np.where(
        df['confidence'] > df['consequent support'],
        (df['confidence'] - df['consequent support']) / (1 - df['consequent support']),
        (df['confidence'] - df['consequent support']) / df['consequent support']
    )
    
    # Transaction counts
    df['support_count'] = (df['support'] * total_transactions).astype(int)
    
    return df


def filter_rules(
    rules_df: pd.DataFrame,
    min_support: float = 0.01,
    min_confidence: float = 0.3,
    min_lift: float = 1.0,
    min_conviction: float = 1.0,
    max_rules: int = None
) -> pd.DataFrame:
    """
    Filter association rules based on multiple criteria.
    
    Args:
        rules_df: DataFrame with association rules
        min_support: Minimum support threshold
        min_confidence: Minimum confidence threshold
        min_lift: Minimum lift threshold
        min_conviction: Minimum conviction threshold
        max_rules: Maximum number of rules to return
        
    Returns:
        Filtered DataFrame
    """
    df = rules_df.copy()
    
    # Apply filters
    mask = (
        (df['support'] >= min_support) &
        (df['confidence'] >= min_confidence) &
        (df['lift'] >= min_lift)
    )
    
    if 'conviction' in df.columns:
        mask &= (df['conviction'] >= min_conviction)
    
    df = df[mask]
    
    # Sort by lift (descending)
    df = df.sort_values('lift', ascending=False)
    
    # Limit number of rules
    if max_rules:
        df = df.head(max_rules)
    
    return df.reset_index(drop=True)


def get_top_rules_for_product(
    rules_df: pd.DataFrame,
    product: str,
    n: int = 10,
    as_antecedent: bool = True
) -> pd.DataFrame:
    """
    Get top rules where a specific product appears.
    
    Args:
        rules_df: DataFrame with association rules
        product: Product name/ID to search for
        n: Number of top rules to return
        as_antecedent: If True, find rules where product is antecedent
                       If False, find rules where product is consequent
        
    Returns:
        DataFrame with top rules for the product
    """
    df = rules_df.copy()
    
    if as_antecedent:
        mask = df['antecedents'].apply(lambda x: product in x)
    else:
        mask = df['consequents'].apply(lambda x: product in x)
    
    filtered = df[mask].sort_values('lift', ascending=False).head(n)
    
    return filtered


def itemset_to_list(itemset: FrozenSet) -> List[str]:
    """Convert frozenset to sorted list."""
    return sorted(str(item) for item in itemset)


def calculate_rule_interestingness(rules_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate composite interestingness score for rules.
    
    Uses weighted combination of:
    - Lift (weight: 0.4)
    - Confidence (weight: 0.3)
    - Support (weight: 0.2)
    - Leverage (weight: 0.1)
    
    Returns:
        DataFrame with interestingness score
    """
    df = rules_df.copy()
    
    # Normalize metrics to 0-1 scale
    for col in ['lift', 'confidence', 'support']:
        if col in df.columns:
            min_val = df[col].min()
            max_val = df[col].max()
            if max_val > min_val:
                df[f'{col}_norm'] = (df[col] - min_val) / (max_val - min_val)
            else:
                df[f'{col}_norm'] = 0
    
    # Calculate weighted score
    weights = {
        'lift_norm': 0.4,
        'confidence_norm': 0.3,
        'support_norm': 0.2
    }
    
    df['interestingness_score'] = sum(
        df[col] * weight 
        for col, weight in weights.items() 
        if col in df.columns
    )
    
    # Add leverage if available
    if 'leverage' in df.columns:
        leverage_norm = (df['leverage'] - df['leverage'].min()) / (df['leverage'].max() - df['leverage'].min() + 1e-10)
        df['interestingness_score'] += leverage_norm * 0.1
    
    return df
