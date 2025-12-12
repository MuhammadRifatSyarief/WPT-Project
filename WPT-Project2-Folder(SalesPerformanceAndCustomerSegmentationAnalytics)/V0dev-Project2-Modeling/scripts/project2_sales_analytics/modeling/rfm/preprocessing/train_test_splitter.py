"""
Train Test Splitter Module

Module untuk splitting data menjadi train dan test set
dengan berbagai strategi.
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional, Dict
from sklearn.model_selection import train_test_split, StratifiedKFold, KFold


class TrainTestSplitter:
    """
    Train/Test splitter dengan berbagai strategi:
    - Simple random split
    - Stratified split (untuk classification)
    - K-Fold cross validation
    """
    
    def __init__(
        self,
        test_size: float = 0.2,
        random_state: int = 42,
        verbose: bool = True
    ):
        """
        Initialize splitter
        
        Args:
            test_size: Proporsi test set (0-1)
            random_state: Random seed untuk reproducibility
            verbose: Print progress messages
        """
        self.test_size = test_size
        self.random_state = random_state
        self.verbose = verbose
        self.split_info: Dict = {}
    
    def split(
        self,
        X: pd.DataFrame,
        y: Optional[pd.Series] = None,
        stratify: bool = False
    ) -> Tuple[pd.DataFrame, pd.DataFrame, Optional[pd.Series], Optional[pd.Series]]:
        """
        Split data menjadi train dan test set
        
        Args:
            X: Features DataFrame
            y: Optional target Series
            stratify: Use stratified split (untuk classification)
            
        Returns:
            Tuple of (X_train, X_test, y_train, y_test)
        """
        stratify_col = y if stratify and y is not None else None
        
        if y is not None:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y,
                test_size=self.test_size,
                random_state=self.random_state,
                stratify=stratify_col
            )
        else:
            X_train, X_test = train_test_split(
                X,
                test_size=self.test_size,
                random_state=self.random_state
            )
            y_train, y_test = None, None
        
        # Store split info
        self.split_info = {
            "train_size": len(X_train),
            "test_size": len(X_test),
            "train_pct": len(X_train) / len(X) * 100,
            "test_pct": len(X_test) / len(X) * 100,
            "stratified": stratify
        }
        
        if y is not None and stratify:
            self.split_info["train_class_dist"] = y_train.value_counts(normalize=True).to_dict()
            self.split_info["test_class_dist"] = y_test.value_counts(normalize=True).to_dict()
        
        if self.verbose:
            print(f"[TrainTestSplitter] Split: Train={len(X_train)} ({self.split_info['train_pct']:.1f}%), Test={len(X_test)} ({self.split_info['test_pct']:.1f}%)")
            if stratify and y is not None:
                print(f"[TrainTestSplitter] Stratified split maintained class distribution")
        
        return X_train, X_test, y_train, y_test
    
    def get_kfold_splits(
        self,
        X: pd.DataFrame,
        y: Optional[pd.Series] = None,
        n_splits: int = 5,
        stratified: bool = False
    ) -> list:
        """
        Get K-Fold cross validation splits
        
        Args:
            X: Features DataFrame
            y: Optional target Series
            n_splits: Number of folds
            stratified: Use stratified K-Fold
            
        Returns:
            List of (train_idx, test_idx) tuples
        """
        if stratified and y is not None:
            kfold = StratifiedKFold(
                n_splits=n_splits,
                shuffle=True,
                random_state=self.random_state
            )
            splits = list(kfold.split(X, y))
        else:
            kfold = KFold(
                n_splits=n_splits,
                shuffle=True,
                random_state=self.random_state
            )
            splits = list(kfold.split(X))
        
        if self.verbose:
            print(f"[TrainTestSplitter] Created {n_splits}-fold CV splits (stratified={stratified})")
        
        return splits
    
    def get_split_summary(self) -> Dict:
        """Get summary dari last split operation"""
        return self.split_info
    
    def validate_split(
        self,
        X_train: pd.DataFrame,
        X_test: pd.DataFrame,
        y_train: Optional[pd.Series] = None,
        y_test: Optional[pd.Series] = None
    ) -> Dict:
        """
        Validate split dengan berbagai checks
        
        Args:
            X_train, X_test: Train/test features
            y_train, y_test: Train/test targets
            
        Returns:
            Dictionary dengan validation results
        """
        validation = {
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "features": len(X_train.columns),
            "train_missing_values": X_train.isna().sum().sum(),
            "test_missing_values": X_test.isna().sum().sum(),
            "feature_names_match": list(X_train.columns) == list(X_test.columns)
        }
        
        # Check for data leakage (same indices)
        common_indices = set(X_train.index) & set(X_test.index)
        validation["data_leakage"] = len(common_indices) > 0
        validation["common_indices_count"] = len(common_indices)
        
        # Target distribution check
        if y_train is not None and y_test is not None:
            validation["train_target_dist"] = y_train.value_counts(normalize=True).to_dict()
            validation["test_target_dist"] = y_test.value_counts(normalize=True).to_dict()
        
        if self.verbose:
            print(f"[TrainTestSplitter] Validation: Features match={validation['feature_names_match']}, Data leakage={validation['data_leakage']}")
        
        return validation
