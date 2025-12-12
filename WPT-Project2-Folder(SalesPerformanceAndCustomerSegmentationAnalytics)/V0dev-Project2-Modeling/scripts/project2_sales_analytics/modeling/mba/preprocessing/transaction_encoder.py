"""
MBA Transaction Encoder Module
==============================

Converts transaction data to binary matrix format required by
Apriori and FP-Growth algorithms.

Author: Project 2 - Sales Analytics
Version: 1.0.0
"""

import pandas as pd
import numpy as np
import logging
from typing import Optional, List, Dict, Tuple
from mlxtend.preprocessing import TransactionEncoder as MLXTransactionEncoder

logger = logging.getLogger(__name__)


class TransactionEncoder:
    """
    Transaction encoder for Market Basket Analysis.
    
    Converts transaction data from long format (row per item) to:
    1. Transaction list format (list of item lists)
    2. Binary matrix format (one-hot encoded)
    
    Attributes:
        config: MBAConfig instance
        encoder: MLXtend TransactionEncoder
        product_mapping: Mapping from product IDs to names
        
    Example:
        >>> encoder = TransactionEncoder(config)
        >>> transactions, basket_matrix = encoder.encode(df)
        >>> encoder.get_product_mapping()
    """
    
    def __init__(self, config):
        """
        Initialize transaction encoder.
        
        Args:
            config: MBAConfig instance with column mappings
        """
        self.config = config
        self.encoder: Optional[MLXTransactionEncoder] = None
        self.product_mapping: Dict[str, str] = {}
        self.reverse_mapping: Dict[str, str] = {}
        self.encoding_stats: Dict[str, int] = {}
        
    def encode(
        self, 
        df: pd.DataFrame,
        use_product_names: bool = None
    ) -> Tuple[List[List[str]], pd.DataFrame]:
        """
        Encode transactions to binary matrix format.
        
        Args:
            df: Transaction DataFrame (cleaned)
            use_product_names: Use product names instead of IDs (overrides config)
            
        Returns:
            Tuple of (transaction_list, binary_matrix)
        """
        logger.info("Starting transaction encoding...")
        
        # Determine whether to use names or IDs
        use_names = use_product_names if use_product_names is not None else self.config.use_colnames
        
        # Build product mapping
        self._build_product_mapping(df, use_names)
        
        # Convert to transaction list format
        transactions = self._to_transaction_list(df, use_names)
        
        # Encode to binary matrix
        basket_matrix = self._to_binary_matrix(transactions)
        
        # Store statistics
        self._calculate_stats(transactions, basket_matrix)
        
        logger.info(f"Encoding complete: {len(transactions):,} transactions, {len(basket_matrix.columns):,} products")
        
        return transactions, basket_matrix
    
    def _build_product_mapping(self, df: pd.DataFrame, use_names: bool) -> None:
        """Build mapping between product IDs and names."""
        product_id_col = self.config.product_id_col
        product_name_col = self.config.product_name_col
        
        if use_names and product_name_col in df.columns:
            # Create ID -> Name mapping
            mapping_df = df[[product_id_col, product_name_col]].drop_duplicates()
            self.product_mapping = dict(zip(
                mapping_df[product_id_col].astype(str),
                mapping_df[product_name_col].astype(str)
            ))
            self.reverse_mapping = {v: k for k, v in self.product_mapping.items()}
        else:
            # Use product IDs as both key and value
            unique_products = df[product_id_col].unique()
            self.product_mapping = {str(p): str(p) for p in unique_products}
            self.reverse_mapping = self.product_mapping.copy()
        
        logger.info(f"   Built mapping for {len(self.product_mapping):,} products")
    
    def _to_transaction_list(
        self, 
        df: pd.DataFrame,
        use_names: bool
    ) -> List[List[str]]:
        """
        Convert DataFrame to list of transaction item lists.
        
        Args:
            df: Transaction DataFrame
            use_names: Whether to use product names
            
        Returns:
            List of item lists (one list per transaction)
        """
        product_col = self.config.product_id_col
        name_col = self.config.product_name_col
        txn_col = self.config.transaction_id_col
        
        # Determine which column to use for items
        if use_names and name_col in df.columns:
            item_col = name_col
        else:
            item_col = product_col
        
        # Group by transaction and collect items
        transactions = (
            df.groupby(txn_col)[item_col]
            .apply(lambda x: list(set(x.astype(str))))
            .tolist()
        )
        
        logger.info(f"   Converted to {len(transactions):,} transaction lists")
        
        return transactions
    
    def _to_binary_matrix(self, transactions: List[List[str]]) -> pd.DataFrame:
        """
        Convert transaction list to binary matrix.
        
        Args:
            transactions: List of item lists
            
        Returns:
            Binary DataFrame (transactions x products)
        """
        # Initialize encoder
        self.encoder = MLXTransactionEncoder()
        
        # Fit and transform
        encoded_array = self.encoder.fit_transform(transactions)
        
        # Convert to DataFrame with column names
        basket_matrix = pd.DataFrame(
            encoded_array,
            columns=self.encoder.columns_
        )
        
        # Sort columns alphabetically for consistency
        basket_matrix = basket_matrix.reindex(sorted(basket_matrix.columns), axis=1)
        
        logger.info(f"   Created binary matrix: {basket_matrix.shape[0]:,} x {basket_matrix.shape[1]:,}")
        
        return basket_matrix
    
    def _calculate_stats(
        self, 
        transactions: List[List[str]], 
        basket_matrix: pd.DataFrame
    ) -> None:
        """Calculate encoding statistics."""
        items_per_txn = [len(t) for t in transactions]
        
        self.encoding_stats = {
            'total_transactions': len(transactions),
            'total_products': len(basket_matrix.columns),
            'total_items': sum(items_per_txn),
            'avg_items_per_transaction': np.mean(items_per_txn),
            'min_items_per_transaction': min(items_per_txn),
            'max_items_per_transaction': max(items_per_txn),
            'matrix_density': basket_matrix.values.mean(),
            'memory_mb': basket_matrix.memory_usage(deep=True).sum() / 1024 / 1024
        }
    
    def get_product_mapping(self) -> Dict[str, str]:
        """Return product ID to name mapping."""
        return self.product_mapping
    
    def get_reverse_mapping(self) -> Dict[str, str]:
        """Return product name to ID mapping."""
        return self.reverse_mapping
    
    def get_stats(self) -> Dict[str, float]:
        """Return encoding statistics."""
        return self.encoding_stats
    
    def print_stats(self) -> None:
        """Print encoding statistics."""
        print("\n" + "=" * 60)
        print("TRANSACTION ENCODING SUMMARY")
        print("=" * 60)
        
        print(f"Total transactions:   {self.encoding_stats.get('total_transactions', 0):,}")
        print(f"Total products:       {self.encoding_stats.get('total_products', 0):,}")
        print(f"Total items:          {self.encoding_stats.get('total_items', 0):,}")
        print("-" * 60)
        print(f"Avg items/txn:        {self.encoding_stats.get('avg_items_per_transaction', 0):.2f}")
        print(f"Min items/txn:        {self.encoding_stats.get('min_items_per_transaction', 0):,}")
        print(f"Max items/txn:        {self.encoding_stats.get('max_items_per_transaction', 0):,}")
        print("-" * 60)
        print(f"Matrix density:       {self.encoding_stats.get('matrix_density', 0):.4f}")
        print(f"Memory usage:         {self.encoding_stats.get('memory_mb', 0):.2f} MB")
    
    def get_product_frequencies(self, basket_matrix: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate product frequencies from basket matrix.
        
        Args:
            basket_matrix: Binary encoded matrix
            
        Returns:
            DataFrame with product frequencies sorted descending
        """
        freq = basket_matrix.sum().sort_values(ascending=False)
        
        freq_df = pd.DataFrame({
            'product': freq.index,
            'frequency': freq.values,
            'support': freq.values / len(basket_matrix)
        })
        
        return freq_df
    
    def decode_itemset(self, itemset: frozenset) -> List[str]:
        """
        Decode itemset back to product IDs if using names.
        
        Args:
            itemset: Frozenset of product names/IDs
            
        Returns:
            List of product IDs
        """
        if self.reverse_mapping:
            return [self.reverse_mapping.get(str(item), str(item)) for item in itemset]
        return [str(item) for item in itemset]
