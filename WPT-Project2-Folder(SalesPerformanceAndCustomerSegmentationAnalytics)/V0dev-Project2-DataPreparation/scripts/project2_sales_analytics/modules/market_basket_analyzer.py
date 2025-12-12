"""
==========================================================================
PROJECT 2: SALES PERFORMANCE & CUSTOMER SEGMENTATION ANALYTICS
==========================================================================
File: modules/market_basket_analyzer.py
Purpose: Market Basket Analysis for product association discovery
Author: v0
Created: 2025
==========================================================================

OVERVIEW:
---------
Performs Market Basket Analysis to discover product associations:
- Frequent itemset mining
- Association rule generation
- Cross-selling/up-selling recommendations

USAGE:
------
    from modules.market_basket_analyzer import MarketBasketAnalyzer
    
    analyzer = MarketBasketAnalyzer(sales_details_df)
    rules = analyzer.generate_association_rules()
    recommendations = analyzer.get_product_recommendations('PROD001')
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Set
from collections import defaultdict
from itertools import combinations

import sys
sys.path.append('..')
from config.constants import MBA_CONFIG


class MarketBasketAnalyzer:
    """
    Market Basket Analyzer for Product Association Analysis.
    
    Implements the Apriori-like algorithm for finding frequent itemsets
    and generating association rules.
    
    Features:
    ---------
    - Frequent itemset mining
    - Association rule generation with support, confidence, lift
    - Product recommendation engine
    - Cross-selling opportunity identification
    
    Attributes:
    -----------
    transactions : List[Set[str]]
        List of transactions (each transaction is a set of product IDs)
    product_names : Dict[str, str]
        Mapping of product ID to product name
    itemsets : Dict[int, Dict]
        Frequent itemsets by size
    rules : List[Dict]
        Generated association rules
    """
    
    def __init__(
        self,
        sales_details: pd.DataFrame,
        product_id_col: str = 'product_id',
        product_name_col: str = 'product_name',
        transaction_col: str = 'invoice_id'
    ):
        """
        Initialize Market Basket Analyzer.
        
        Args:
            sales_details: DataFrame with transaction-level sales data
            product_id_col: Column name for product ID
            product_name_col: Column name for product name
            transaction_col: Column name for transaction/invoice ID
        """
        self.sales_details = sales_details.copy()
        self.product_id_col = product_id_col
        self.product_name_col = product_name_col
        self.transaction_col = transaction_col
        
        self.transactions: List[Set[str]] = []
        self.product_names: Dict[str, str] = {}
        self.itemsets: Dict[int, Dict] = {}
        self.rules: List[Dict] = []
        
        self._prepare_transactions()
    
    def _prepare_transactions(self) -> None:
        """Prepare transaction data from sales details."""
        print("\n" + "=" * 60)
        print("🛒 PREPARING TRANSACTION DATA")
        print("=" * 60)
        
        df = self.sales_details
        
        # Build product name mapping
        product_df = df[[self.product_id_col, self.product_name_col]].drop_duplicates()
        self.product_names = dict(zip(
            product_df[self.product_id_col].astype(str),
            product_df[self.product_name_col]
        ))
        
        # Group by transaction to get product sets
        grouped = df.groupby(self.transaction_col)[self.product_id_col].apply(
            lambda x: set(x.astype(str))
        )
        
        # Filter transactions with multiple items
        self.transactions = [
            items for items in grouped.values 
            if len(items) >= 2  # Need at least 2 items for association
        ]
        
        print(f"✓ Total transactions: {len(grouped):,}")
        print(f"✓ Multi-item transactions: {len(self.transactions):,}")
        print(f"✓ Unique products: {len(self.product_names):,}")
    
    def find_frequent_itemsets(
        self,
        min_support: Optional[float] = None,
        max_itemset_size: Optional[int] = None
    ) -> Dict[int, Dict]:
        """
        Find frequent itemsets using Apriori-like algorithm.
        
        Args:
            min_support: Minimum support threshold (0-1)
            max_itemset_size: Maximum number of items in itemset
            
        Returns:
            Dictionary of frequent itemsets by size
        """
        print("\n📊 Finding Frequent Itemsets...")
        
        if min_support is None:
            min_support = MBA_CONFIG['MIN_SUPPORT']
        
        if max_itemset_size is None:
            max_itemset_size = MBA_CONFIG['MAX_ITEMSET_SIZE']
        
        n_transactions = len(self.transactions)
        min_count = int(min_support * n_transactions)
        
        print(f"   • Min support: {min_support:.2%}")
        print(f"   • Min count: {min_count}")
        
        # Find frequent 1-itemsets
        item_counts = defaultdict(int)
        for transaction in self.transactions:
            for item in transaction:
                item_counts[item] += 1
        
        frequent_1 = {
            frozenset([item]): count
            for item, count in item_counts.items()
            if count >= min_count
        }
        
        self.itemsets[1] = frequent_1
        print(f"   ✓ Frequent 1-itemsets: {len(frequent_1)}")
        
        # Find larger itemsets
        k = 2
        prev_frequent = set(frequent_1.keys())
        
        while k <= max_itemset_size and prev_frequent:
            # Generate candidates
            candidates = self._generate_candidates(prev_frequent, k)
            
            # Count support
            itemset_counts = defaultdict(int)
            for transaction in self.transactions:
                transaction_set = frozenset(transaction)
                for candidate in candidates:
                    if candidate.issubset(transaction_set):
                        itemset_counts[candidate] += 1
            
            # Filter by min support
            frequent_k = {
                itemset: count
                for itemset, count in itemset_counts.items()
                if count >= min_count
            }
            
            if frequent_k:
                self.itemsets[k] = frequent_k
                print(f"   ✓ Frequent {k}-itemsets: {len(frequent_k)}")
                prev_frequent = set(frequent_k.keys())
            else:
                break
            
            k += 1
        
        return self.itemsets
    
    def _generate_candidates(
        self, 
        prev_itemsets: Set[frozenset], 
        k: int
    ) -> Set[frozenset]:
        """
        Generate candidate itemsets of size k.
        
        Args:
            prev_itemsets: Frequent itemsets of size k-1
            k: Target itemset size
            
        Returns:
            Set of candidate itemsets
        """
        candidates = set()
        prev_list = list(prev_itemsets)
        
        for i in range(len(prev_list)):
            for j in range(i + 1, len(prev_list)):
                union = prev_list[i] | prev_list[j]
                if len(union) == k:
                    candidates.add(union)
        
        return candidates
    
    def generate_association_rules(
        self,
        min_confidence: Optional[float] = None,
        min_lift: Optional[float] = None
    ) -> pd.DataFrame:
        """
        Generate association rules from frequent itemsets.
        
        Args:
            min_confidence: Minimum confidence threshold
            min_lift: Minimum lift threshold
            
        Returns:
            DataFrame with association rules
        """
        print("\n📋 Generating Association Rules...")
        
        if min_confidence is None:
            min_confidence = MBA_CONFIG['MIN_CONFIDENCE']
        
        if min_lift is None:
            min_lift = MBA_CONFIG['MIN_LIFT']
        
        # Find itemsets if not already done
        if not self.itemsets:
            self.find_frequent_itemsets()
        
        n_transactions = len(self.transactions)
        rules = []
        
        # Generate rules from itemsets of size >= 2
        for k in range(2, max(self.itemsets.keys()) + 1):
            if k not in self.itemsets:
                continue
            
            for itemset, support_count in self.itemsets[k].items():
                itemset_support = support_count / n_transactions
                
                # Generate all possible rules from this itemset
                for i in range(1, len(itemset)):
                    for antecedent in combinations(itemset, i):
                        antecedent = frozenset(antecedent)
                        consequent = itemset - antecedent
                        
                        # Calculate confidence
                        antecedent_support = self._get_support(antecedent)
                        if antecedent_support == 0:
                            continue
                        
                        confidence = itemset_support / antecedent_support
                        
                        if confidence < min_confidence:
                            continue
                        
                        # Calculate lift
                        consequent_support = self._get_support(consequent)
                        if consequent_support == 0:
                            continue
                        
                        lift = confidence / consequent_support
                        
                        if lift < min_lift:
                            continue
                        
                        # Create rule
                        rule = {
                            'antecedent': antecedent,
                            'consequent': consequent,
                            'antecedent_items': self._format_itemset(antecedent),
                            'consequent_items': self._format_itemset(consequent),
                            'support': itemset_support,
                            'confidence': confidence,
                            'lift': lift,
                            'support_count': support_count,
                            'lift_category': self._categorize_lift(lift),
                        }
                        rules.append(rule)
        
        # Sort by lift (descending)
        rules.sort(key=lambda x: x['lift'], reverse=True)
        
        # Limit to top N
        top_n = MBA_CONFIG['TOP_N_RULES']
        self.rules = rules[:top_n]
        
        rules_df = pd.DataFrame(self.rules)
        
        print(f"✓ Generated {len(self.rules)} association rules")
        
        if not rules_df.empty:
            print(f"   • Avg confidence: {rules_df['confidence'].mean():.2%}")
            print(f"   • Avg lift: {rules_df['lift'].mean():.2f}")
        
        return rules_df
    
    def _get_support(self, itemset: frozenset) -> float:
        """Get support for an itemset."""
        for k in range(1, max(self.itemsets.keys()) + 1):
            if k in self.itemsets and itemset in self.itemsets[k]:
                return self.itemsets[k][itemset] / len(self.transactions)
        return 0
    
    def _format_itemset(self, itemset: frozenset) -> str:
        """Format itemset as readable string with product names."""
        names = [
            self.product_names.get(item, item)[:30]
            for item in itemset
        ]
        return ' + '.join(names)
    
    def _categorize_lift(self, lift: float) -> str:
        """Categorize lift value."""
        for category, (low, high) in MBA_CONFIG['LIFT_CATEGORIES'].items():
            if low <= lift < high:
                return category
        return 'Weak'
    
    def get_product_recommendations(
        self, 
        product_id: str, 
        top_n: int = 5
    ) -> List[Dict]:
        """
        Get product recommendations based on association rules.
        
        Args:
            product_id: Product ID to get recommendations for
            top_n: Number of recommendations to return
            
        Returns:
            List of recommended products with confidence scores
        """
        if not self.rules:
            self.generate_association_rules()
        
        product_id = str(product_id)
        recommendations = []
        
        for rule in self.rules:
            if product_id in rule['antecedent']:
                for consequent_id in rule['consequent']:
                    recommendations.append({
                        'product_id': consequent_id,
                        'product_name': self.product_names.get(consequent_id, consequent_id),
                        'confidence': rule['confidence'],
                        'lift': rule['lift'],
                        'rule': f"{rule['antecedent_items']} → {rule['consequent_items']}",
                    })
        
        # Sort by confidence and deduplicate
        recommendations.sort(key=lambda x: (x['lift'], x['confidence']), reverse=True)
        
        seen = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec['product_id'] not in seen:
                seen.add(rec['product_id'])
                unique_recommendations.append(rec)
                if len(unique_recommendations) >= top_n:
                    break
        
        return unique_recommendations
    
    def get_frequently_bought_together(self, top_n: int = 20) -> pd.DataFrame:
        """
        Get top product pairs frequently bought together.
        
        Args:
            top_n: Number of pairs to return
            
        Returns:
            DataFrame with product pairs and their metrics
        """
        if 2 not in self.itemsets:
            self.find_frequent_itemsets()
        
        pairs = []
        n_transactions = len(self.transactions)
        
        for itemset, count in self.itemsets.get(2, {}).items():
            items = list(itemset)
            pairs.append({
                'product_1_id': items[0],
                'product_1_name': self.product_names.get(items[0], items[0]),
                'product_2_id': items[1],
                'product_2_name': self.product_names.get(items[1], items[1]),
                'support': count / n_transactions,
                'support_count': count,
            })
        
        pairs_df = pd.DataFrame(pairs)
        
        if not pairs_df.empty:
            pairs_df = pairs_df.sort_values('support', ascending=False).head(top_n)
        
        return pairs_df
    
    def get_cross_selling_opportunities(self) -> pd.DataFrame:
        """
        Identify cross-selling opportunities from association rules.
        
        Returns:
            DataFrame with cross-selling recommendations
        """
        if not self.rules:
            self.generate_association_rules()
        
        opportunities = []
        
        for rule in self.rules:
            if rule['lift'] >= MBA_CONFIG['LIFT_CATEGORIES']['Moderate'][0]:
                opportunities.append({
                    'if_customer_buys': rule['antecedent_items'],
                    'recommend': rule['consequent_items'],
                    'confidence': rule['confidence'],
                    'lift': rule['lift'],
                    'lift_category': rule['lift_category'],
                    'transactions': rule['support_count'],
                })
        
        return pd.DataFrame(opportunities)
    
    def export_summary(self) -> Dict:
        """
        Export Market Basket Analysis summary.
        
        Returns:
            Dictionary with analysis summary
        """
        return {
            'total_transactions': len(self.transactions) + len([
                t for t in self.sales_details[self.transaction_col].unique()
            ]) - len(self.transactions),
            'multi_item_transactions': len(self.transactions),
            'unique_products': len(self.product_names),
            'frequent_itemsets_1': len(self.itemsets.get(1, {})),
            'frequent_itemsets_2': len(self.itemsets.get(2, {})),
            'frequent_itemsets_3': len(self.itemsets.get(3, {})),
            'total_rules': len(self.rules),
            'strong_associations': len([r for r in self.rules if r['lift_category'] == 'Strong']),
            'moderate_associations': len([r for r in self.rules if r['lift_category'] == 'Moderate']),
        }
