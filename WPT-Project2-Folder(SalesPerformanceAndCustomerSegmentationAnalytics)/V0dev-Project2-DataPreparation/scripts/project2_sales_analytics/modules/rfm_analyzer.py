"""
==========================================================================
PROJECT 2: SALES PERFORMANCE & CUSTOMER SEGMENTATION ANALYTICS
==========================================================================
File: modules/rfm_analyzer.py
Purpose: RFM (Recency, Frequency, Monetary) Analysis for customer segmentation
==========================================================================

OVERVIEW:
---------
Performs RFM analysis to segment customers based on:
- Recency: How recently a customer made a purchase
- Frequency: How often a customer makes purchases
- Monetary: How much money a customer spends

USAGE:
------
    from modules.rfm_analyzer import RFMAnalyzer
    
    analyzer = RFMAnalyzer(sales_by_customer_df)
    rfm_df = analyzer.calculate_rfm_scores()
    segmented_df = analyzer.segment_customers()
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple, List
from datetime import datetime

import sys
sys.path.append('..')
from config.constants import RFM_CONFIG, CUSTOMER_VALUE_CONFIG


class RFMAnalyzer:
    """
    RFM Analyzer for Customer Segmentation.
    
    Implements Recency-Frequency-Monetary analysis with configurable
    scoring and segmentation rules.
    
    Features:
    ---------
    - Quintile-based RFM scoring (1-5 scale)
    - Configurable segment definitions
    - Customer lifetime value estimation
    - Segment recommendations
    
    Attributes:
    -----------
    data : pd.DataFrame
        Customer-level sales data
    rfm_df : pd.DataFrame
        Processed RFM scores and segments
    reference_date : pd.Timestamp
        Date used for recency calculation
    """
    
    def __init__(
        self, 
        customer_data: pd.DataFrame,
        reference_date: Optional[datetime] = None
    ):
        """
        Initialize RFM Analyzer.
        
        Args:
            customer_data: DataFrame with customer sales aggregations
                Required columns: customer_id, recency_days, frequency, monetary
            reference_date: Date for recency calculation (default: today)
        """
        self.data = customer_data.copy()
        self.reference_date = reference_date or pd.Timestamp.now()
        self.rfm_df: Optional[pd.DataFrame] = None
        
        self._validate_data()
    
    def _validate_data(self) -> None:
        """Validate input data has required columns."""
        required_columns = ['customer_id', 'recency_days', 'frequency', 'monetary']
        
        missing = [col for col in required_columns if col not in self.data.columns]
        
        if missing:
            # Try to calculate missing columns
            if 'recency_days' in missing and 'last_purchase_date' in self.data.columns:
                self.data['recency_days'] = (
                    self.reference_date - pd.to_datetime(self.data['last_purchase_date'])
                ).dt.days
            
            if 'frequency' in missing and 'total_orders' in self.data.columns:
                self.data['frequency'] = self.data['total_orders']
            
            if 'monetary' in missing and 'total_amount' in self.data.columns:
                self.data['monetary'] = self.data['total_amount']
        
        # Re-check
        still_missing = [
            col for col in required_columns 
            if col not in self.data.columns
        ]
        
        if still_missing:
            raise ValueError(f"Missing required columns: {still_missing}")
    
    def calculate_rfm_scores(
        self,
        r_bins: int = 5,
        f_bins: int = 5,
        m_bins: int = 5
    ) -> pd.DataFrame:
        """
        Calculate RFM scores using quintile binning.
        
        Args:
            r_bins: Number of bins for Recency (default 5)
            f_bins: Number of bins for Frequency (default 5)
            m_bins: Number of bins for Monetary (default 5)
            
        Returns:
            DataFrame with RFM scores added
        """
        print("\n" + "=" * 60)
        print("📊 CALCULATING RFM SCORES")
        print("=" * 60)
        
        df = self.data.copy()
        
        # Handle edge cases
        df['recency_days'] = df['recency_days'].fillna(9999).astype(float)
        df['frequency'] = df['frequency'].fillna(0).astype(float)
        df['monetary'] = df['monetary'].fillna(0).astype(float)
        
        # Calculate R score (lower recency = higher score)
        df['r_score'] = self._calculate_quintile_score(
            df['recency_days'], 
            bins=r_bins, 
            reverse=True  # Lower recency gets higher score
        )
        
        # Calculate F score (higher frequency = higher score)
        df['f_score'] = self._calculate_quintile_score(
            df['frequency'], 
            bins=f_bins, 
            reverse=False
        )
        
        # Calculate M score (higher monetary = higher score)
        df['m_score'] = self._calculate_quintile_score(
            df['monetary'], 
            bins=m_bins, 
            reverse=False
        )
        
        # Combined RFM score
        df['rfm_score'] = (
            df['r_score'].astype(str) + 
            df['f_score'].astype(str) + 
            df['m_score'].astype(str)
        )
        
        # Numeric RFM score (for sorting)
        df['rfm_score_numeric'] = df['r_score'] + df['f_score'] + df['m_score']
        
        self.rfm_df = df
        
        print(f"✓ Calculated RFM scores for {len(df):,} customers")
        print(f"   • R Score range: {df['r_score'].min()} - {df['r_score'].max()}")
        print(f"   • F Score range: {df['f_score'].min()} - {df['f_score'].max()}")
        print(f"   • M Score range: {df['m_score'].min()} - {df['m_score'].max()}")
        
        return self.rfm_df
    
    def _calculate_quintile_score(
        self, 
        series: pd.Series, 
        bins: int = 5, 
        reverse: bool = False
    ) -> pd.Series:
        """
        Calculate quintile-based score for a series.
        
        Args:
            series: Numeric series to score
            bins: Number of bins (1-5 default)
            reverse: If True, lower values get higher scores
            
        Returns:
            Series with integer scores (1-5)
        """
        try:
            # Use qcut for quantile-based binning
            labels = list(range(1, bins + 1))
            
            if reverse:
                labels = labels[::-1]
            
            scores = pd.qcut(
                series.rank(method='first'), 
                q=bins, 
                labels=labels,
                duplicates='drop'
            )
            
            return scores.astype(int)
            
        except Exception as e:
            # Fallback for edge cases (e.g., all same values)
            print(f"   ⚠️ Quintile calculation issue: {e}")
            return pd.Series([3] * len(series), index=series.index)
    
    def segment_customers(self) -> pd.DataFrame:
        """
        Segment customers based on RFM scores.
        
        Returns:
            DataFrame with segment assignments
        """
        print("\n📋 Segmenting Customers...")
        
        if self.rfm_df is None:
            self.calculate_rfm_scores()
        
        df = self.rfm_df.copy()
        
        # Apply segmentation rules
        df['segment'] = df.apply(self._assign_segment, axis=1)
        
        # Add recommended actions
        df['recommended_action'] = df['segment'].map(
            RFM_CONFIG['SEGMENT_ACTIONS']
        )
        
        # Add segment priority
        df['segment_priority'] = df['segment'].map(
            RFM_CONFIG['SEGMENT_PRIORITY']
        )
        
        self.rfm_df = df
        
        # Print segment distribution
        segment_counts = df['segment'].value_counts()
        print(f"\n✓ Customer Segments:")
        for segment, count in segment_counts.items():
            pct = count / len(df) * 100
            print(f"   • {segment}: {count:,} ({pct:.1f}%)")
        
        return self.rfm_df
    
    def _assign_segment(self, row: pd.Series) -> str:
        """
        Assign segment based on R, F, M scores.
        
        Args:
            row: DataFrame row with r_score, f_score, m_score
            
        Returns:
            Segment name string
        """
        r = row['r_score']
        f = row['f_score']
        m = row['m_score']
        
        for segment_name, rules in RFM_CONFIG['SEGMENTS'].items():
            r_range = rules['R']
            f_range = rules['F']
            m_range = rules['M']
            
            if (r_range[0] <= r <= r_range[1] and
                f_range[0] <= f <= f_range[1] and
                m_range[0] <= m <= m_range[1]):
                return segment_name
        
        # Default segment
        return 'Other'
    
    def calculate_segment_metrics(self) -> pd.DataFrame:
        """
        Calculate aggregate metrics per segment.
        
        Returns:
            DataFrame with segment-level metrics
        """
        print("\n📈 Calculating Segment Metrics...")
        
        if self.rfm_df is None or 'segment' not in self.rfm_df.columns:
            self.segment_customers()
        
        df = self.rfm_df
        
        segment_metrics = df.groupby('segment').agg({
            'customer_id': 'count',
            'recency_days': 'mean',
            'frequency': 'mean',
            'monetary': ['sum', 'mean'],
        }).round(2)
        
        # Flatten columns
        segment_metrics.columns = [
            'customer_count',
            'avg_recency_days',
            'avg_frequency',
            'total_revenue',
            'avg_monetary',
        ]
        
        segment_metrics = segment_metrics.reset_index()
        
        # Add percentages
        total_customers = segment_metrics['customer_count'].sum()
        total_revenue = segment_metrics['total_revenue'].sum()
        
        segment_metrics['customer_pct'] = (
            segment_metrics['customer_count'] / total_customers * 100
        ).round(1)
        
        segment_metrics['revenue_pct'] = (
            segment_metrics['total_revenue'] / total_revenue * 100
        ).round(1)
        
        # Sort by priority
        segment_metrics['priority'] = segment_metrics['segment'].map(
            RFM_CONFIG['SEGMENT_PRIORITY']
        )
        segment_metrics = segment_metrics.sort_values(
            'priority', 
            ascending=False
        ).drop('priority', axis=1)
        
        print(f"✓ Calculated metrics for {len(segment_metrics)} segments")
        
        return segment_metrics
    
    def get_segment_recommendations(self) -> Dict[str, Dict]:
        """
        Get detailed recommendations for each segment.
        
        Returns:
            Dictionary with segment recommendations
        """
        if self.rfm_df is None or 'segment' not in self.rfm_df.columns:
            self.segment_customers()
        
        recommendations = {}
        
        for segment in self.rfm_df['segment'].unique():
            segment_data = self.rfm_df[self.rfm_df['segment'] == segment]
            
            recommendations[segment] = {
                'customer_count': len(segment_data),
                'total_revenue': segment_data['monetary'].sum(),
                'avg_recency': segment_data['recency_days'].mean(),
                'avg_frequency': segment_data['frequency'].mean(),
                'avg_monetary': segment_data['monetary'].mean(),
                'action': RFM_CONFIG['SEGMENT_ACTIONS'].get(segment, 'Review individually'),
                'priority': RFM_CONFIG['SEGMENT_PRIORITY'].get(segment, 0),
                'color': RFM_CONFIG['SEGMENT_COLORS'].get(segment, '#9E9E9E'),
            }
        
        return recommendations
    
    def identify_at_risk_customers(
        self, 
        recency_threshold: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Identify customers at risk of churning.
        
        Args:
            recency_threshold: Days since last purchase to consider at-risk
            
        Returns:
            DataFrame of at-risk customers
        """
        if recency_threshold is None:
            recency_threshold = CUSTOMER_VALUE_CONFIG['AT_RISK_THRESHOLD_DAYS']
        
        if self.rfm_df is None:
            self.calculate_rfm_scores()
        
        df = self.rfm_df
        
        # At risk: High value customers who haven't purchased recently
        at_risk = df[
            (df['recency_days'] >= recency_threshold) &
            (df['monetary'] >= df['monetary'].median()) &
            (df['frequency'] >= df['frequency'].median())
        ].copy()
        
        at_risk = at_risk.sort_values('monetary', ascending=False)
        
        print(f"\n⚠️ Identified {len(at_risk):,} at-risk high-value customers")
        
        return at_risk
    
    def get_rfm_results(self) -> pd.DataFrame:
        """
        Get complete RFM analysis results.
        
        Returns:
            DataFrame with all RFM data and segments
        """
        if self.rfm_df is None:
            self.calculate_rfm_scores()
        
        if 'segment' not in self.rfm_df.columns:
            self.segment_customers()
        
        return self.rfm_df
    
    def export_summary(self) -> Dict:
        """
        Export RFM analysis summary.
        
        Returns:
            Dictionary with analysis summary
        """
        if self.rfm_df is None or 'segment' not in self.rfm_df.columns:
            self.segment_customers()
        
        df = self.rfm_df
        
        return {
            'total_customers': len(df),
            'total_revenue': df['monetary'].sum(),
            'avg_recency': df['recency_days'].mean(),
            'avg_frequency': df['frequency'].mean(),
            'avg_monetary': df['monetary'].mean(),
            'segment_distribution': df['segment'].value_counts().to_dict(),
            'top_segment': df['segment'].value_counts().idxmax(),
            'at_risk_count': len(df[df['segment'].isin(['At Risk', 'Cannot Lose Them'])]),
            'champion_count': len(df[df['segment'] == 'Champions']),
            'reference_date': str(self.reference_date),
        }
