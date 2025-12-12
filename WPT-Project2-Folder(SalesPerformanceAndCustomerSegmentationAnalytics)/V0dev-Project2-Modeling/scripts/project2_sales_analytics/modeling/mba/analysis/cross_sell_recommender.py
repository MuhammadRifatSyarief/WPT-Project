"""
MBA Cross-Sell Recommender Module
=================================

Generates cross-sell and up-sell recommendations based on
association rules analysis.

Author: Project 2 - Sales Analytics
Version: 1.2.0 - Robust Error Handling
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)


class CrossSellRecommender:
    """
    Cross-sell recommendation engine based on association rules.
    """
    
    def __init__(self, rules: pd.DataFrame, config=None):
        """
        Initialize cross-sell recommender.
        
        Args:
            rules: DataFrame with association rules
            config: Optional MBAConfig instance
        """
        self.rules = rules.copy()
        self.config = config
        self.product_data: Optional[pd.DataFrame] = None
        self.rfm_data: Optional[pd.DataFrame] = None
        self._build_lookup_index()
        
        if config:
            self._load_enrichment_data()
    
    def _load_enrichment_data(self) -> None:
        """Load product and RFM data for enrichment with robust error handling."""
        if self.config is None:
            return
        
        try:
            # Try attribute first (new style)
            product_path_str = getattr(self.config, 'sales_by_product_path', None)
            if product_path_str is None:
                # Fallback to method (old style)
                product_path_str = str(self.config.get_sales_by_product_path())
            
            product_path = Path(product_path_str)
            if product_path.exists():
                self.product_data = pd.read_csv(product_path)
                logger.info(f"Loaded product data for enrichment: {len(self.product_data)} products")
            else:
                logger.warning(f"Product data file not found: {product_path}. Enrichment will be skipped.")
        except Exception as e:
            logger.warning(f"Could not load product data: {e}. Enrichment will be skipped.")
        
        try:
            rfm_path_str = getattr(self.config, 'rfm_features_path', None)
            if rfm_path_str is None:
                rfm_path_str = str(self.config.get_rfm_features_path())
            
            rfm_path = Path(rfm_path_str)
            if rfm_path.exists():
                self.rfm_data = pd.read_csv(rfm_path)
                logger.info(f"Loaded RFM data for enrichment: {len(self.rfm_data)} customers")
            else:
                logger.warning(f"RFM data file not found: {rfm_path}. Segment filtering will be skipped.")
        except Exception as e:
            logger.warning(f"Could not load RFM data: {e}. Segment filtering will be skipped.")
        
    def _build_lookup_index(self) -> None:
        """Build index for fast rule lookup."""
        self.antecedent_index: Dict[str, List[int]] = defaultdict(list)
        self.consequent_index: Dict[str, List[int]] = defaultdict(list)
        
        if len(self.rules) == 0:
            logger.warning("No rules provided for indexing")
            return
        
        for idx, row in self.rules.iterrows():
            antecedents = row.get('antecedents', set())
            consequents = row.get('consequents', set())
            
            # Convert to iterable if needed
            if isinstance(antecedents, frozenset):
                antecedents = list(antecedents)
            elif isinstance(antecedents, str):
                antecedents = [antecedents]
            elif not hasattr(antecedents, '__iter__'):
                antecedents = [antecedents]
                
            if isinstance(consequents, frozenset):
                consequents = list(consequents)
            elif isinstance(consequents, str):
                consequents = [consequents]
            elif not hasattr(consequents, '__iter__'):
                consequents = [consequents]
            
            for item in antecedents:
                self.antecedent_index[str(item)].append(idx)
            for item in consequents:
                self.consequent_index[str(item)].append(idx)
        
        logger.info(f"Built index for {len(self.antecedent_index)} antecedent items")
    
    def recommend(
        self,
        basket: List[str],
        n: int = 5,
        exclude_basket: bool = True,
        min_confidence: float = 0.0
    ) -> pd.DataFrame:
        """
        Get recommendations based on current basket items.
        """
        if len(self.rules) == 0:
            logger.warning("No rules available for recommendations")
            return pd.DataFrame()
        
        basket_set = set(str(item) for item in basket)
        recommendations: Dict[str, Dict[str, Any]] = {}
        
        for item in basket:
            # Find rules where this item is in the antecedent
            rule_indices = self.antecedent_index.get(str(item), [])
            
            for idx in rule_indices:
                try:
                    rule = self.rules.loc[idx]
                except KeyError:
                    continue
                
                antecedents = rule.get('antecedents', set())
                if isinstance(antecedents, frozenset):
                    antecedent_set = set(str(i) for i in antecedents)
                else:
                    antecedent_set = {str(antecedents)}
                
                if not antecedent_set.issubset(basket_set):
                    continue
                
                confidence = rule.get('confidence', 0)
                if confidence < min_confidence:
                    continue
                
                consequents = rule.get('consequents', set())
                if isinstance(consequents, frozenset):
                    cons_items = list(consequents)
                else:
                    cons_items = [consequents]
                
                lift = rule.get('lift', 1.0)
                support = rule.get('support', 0)
                
                for cons_item in cons_items:
                    cons_str = str(cons_item)
                    
                    if exclude_basket and cons_str in basket_set:
                        continue
                    
                    score = lift * confidence
                    
                    if cons_str not in recommendations:
                        recommendations[cons_str] = {
                            'product': cons_str,
                            'score': score,
                            'confidence': confidence,
                            'lift': lift,
                            'support': support,
                            'triggered_by': [str(antecedent_set)],
                            'rule_count': 1
                        }
                    else:
                        rec = recommendations[cons_str]
                        rec['score'] = max(rec['score'], score)
                        rec['confidence'] = max(rec['confidence'], confidence)
                        rec['lift'] = max(rec['lift'], lift)
                        rec['triggered_by'].append(str(antecedent_set))
                        rec['rule_count'] += 1
        
        if recommendations:
            rec_df = pd.DataFrame(list(recommendations.values()))
            rec_df = rec_df.sort_values('score', ascending=False).head(n)
            rec_df['rank'] = range(1, len(rec_df) + 1)
            rec_df = self._enrich_recommendations(rec_df)
            return rec_df
        
        return pd.DataFrame()
    
    def _enrich_recommendations(self, rec_df: pd.DataFrame) -> pd.DataFrame:
        """Enrich recommendations with product metrics."""
        if self.product_data is None or self.config is None or len(rec_df) == 0:
            return rec_df
        
        try:
            product_name_col = getattr(self.config, 'product_name_col', 'product_name')
            
            if product_name_col in self.product_data.columns:
                enrichment_cols = [product_name_col]
                
                metric_cols = ['total_revenue', 'total_quantity_sold', 'revenue_contribution_pct', 'order_count']
                for col in metric_cols:
                    if col in self.product_data.columns:
                        enrichment_cols.append(col)
                
                if len(enrichment_cols) > 1:
                    rec_df = rec_df.merge(
                        self.product_data[enrichment_cols],
                        left_on='product',
                        right_on=product_name_col,
                        how='left'
                    )
                    
                    if product_name_col in rec_df.columns and product_name_col != 'product':
                        rec_df = rec_df.drop(columns=[product_name_col])
        except Exception as e:
            logger.warning(f"Could not enrich recommendations: {e}")
        
        return rec_df
    
    def get_cross_sells(
        self,
        product: str,
        n: int = 10,
        min_lift: float = 1.0
    ) -> pd.DataFrame:
        """Get cross-sell recommendations for a specific product."""
        if len(self.rules) == 0:
            return pd.DataFrame()
        
        product_str = str(product)
        rule_indices = self.antecedent_index.get(product_str, [])
        
        if not rule_indices:
            logger.info(f"No rules found for product: {product}")
            return pd.DataFrame()
        
        cross_sells = []
        
        for idx in rule_indices:
            try:
                rule = self.rules.loc[idx]
            except KeyError:
                continue
            
            lift = rule.get('lift', 0)
            if lift < min_lift:
                continue
            
            consequents = rule.get('consequents', set())
            if isinstance(consequents, frozenset):
                cons_items = list(consequents)
            else:
                cons_items = [consequents]
            
            for cons_item in cons_items:
                cross_sells.append({
                    'trigger_product': product,
                    'recommended_product': str(cons_item),
                    'confidence': rule.get('confidence', 0),
                    'lift': lift,
                    'support': rule.get('support', 0),
                    'rule': rule.get('rule_str', f"{product} -> {cons_item}")
                })
        
        if cross_sells:
            df = pd.DataFrame(cross_sells)
            df = df.sort_values('lift', ascending=False).drop_duplicates(
                subset=['recommended_product']
            ).head(n)
            df = self._enrich_cross_sells(df)
            return df
        
        return pd.DataFrame()
    
    def _enrich_cross_sells(self, df: pd.DataFrame) -> pd.DataFrame:
        """Enrich cross-sell DataFrame with product metrics."""
        if self.product_data is None or self.config is None or len(df) == 0:
            return df
        
        try:
            product_name_col = getattr(self.config, 'product_name_col', 'product_name')
            
            if product_name_col in self.product_data.columns:
                metric_cols = ['total_revenue', 'revenue_contribution_pct']
                available_cols = [c for c in metric_cols if c in self.product_data.columns]
                
                if available_cols:
                    merge_cols = [product_name_col] + available_cols
                    df = df.merge(
                        self.product_data[merge_cols],
                        left_on='recommended_product',
                        right_on=product_name_col,
                        how='left'
                    )
                    if product_name_col != 'recommended_product':
                        df = df.drop(columns=[product_name_col], errors='ignore')
        except Exception as e:
            logger.warning(f"Could not enrich cross-sells: {e}")
        
        return df
    
    def recommend_for_segment(
        self,
        segment: str,
        basket: List[str],
        n: int = 5
    ) -> pd.DataFrame:
        """Get recommendations tailored for a specific RFM segment."""
        recs = self.recommend(basket, n=n*2)
        
        if len(recs) == 0:
            return recs
        
        segment_weights = {
            'Champions': {'lift': 1.2, 'confidence': 1.0},
            'Loyal': {'lift': 1.1, 'confidence': 1.1},
            'Potential Loyalists': {'lift': 1.0, 'confidence': 1.2},
            'New Customers': {'lift': 0.9, 'confidence': 1.3},
            'At Risk': {'lift': 1.1, 'confidence': 1.0},
            'Hibernating': {'lift': 1.0, 'confidence': 1.1},
            'Lost': {'lift': 0.8, 'confidence': 1.2}
        }
        
        weights = segment_weights.get(segment, {'lift': 1.0, 'confidence': 1.0})
        
        recs['adjusted_score'] = (
            recs['lift'] * weights['lift'] * 
            recs['confidence'] * weights['confidence']
        )
        
        recs = recs.sort_values('adjusted_score', ascending=False).head(n)
        recs['rank'] = range(1, len(recs) + 1)
        recs['target_segment'] = segment
        
        return recs
    
    def generate_cross_sell_report(self) -> pd.DataFrame:
        """Generate comprehensive cross-sell report."""
        if len(self.rules) == 0:
            return pd.DataFrame()
        
        all_products = set()
        for _, row in self.rules.iterrows():
            antecedents = row.get('antecedents', set())
            if isinstance(antecedents, frozenset):
                all_products.update(str(i) for i in antecedents)
            else:
                all_products.add(str(antecedents))
        
        report_data = []
        
        for product in all_products:
            cross_sells = self.get_cross_sells(product, n=5)
            
            if len(cross_sells) > 0:
                top_rec = cross_sells.iloc[0]
                report_data.append({
                    'product': product,
                    'top_recommendation': top_rec['recommended_product'],
                    'top_lift': top_rec['lift'],
                    'top_confidence': top_rec['confidence'],
                    'total_cross_sell_options': len(cross_sells),
                    'recommendations': ', '.join(cross_sells['recommended_product'].tolist())
                })
        
        if not report_data:
            return pd.DataFrame()
        
        report_df = pd.DataFrame(report_data).sort_values('top_lift', ascending=False)
        
        # Enrich with product data
        if self.product_data is not None and self.config is not None:
            try:
                product_name_col = getattr(self.config, 'product_name_col', 'product_name')
                if product_name_col in self.product_data.columns:
                    revenue_cols = [product_name_col]
                    if 'total_revenue' in self.product_data.columns:
                        revenue_cols.append('total_revenue')
                    if 'revenue_contribution_pct' in self.product_data.columns:
                        revenue_cols.append('revenue_contribution_pct')
                    
                    if len(revenue_cols) > 1:
                        report_df = report_df.merge(
                            self.product_data[revenue_cols],
                            left_on='product',
                            right_on=product_name_col,
                            how='left'
                        )
            except Exception as e:
                logger.warning(f"Could not enrich report: {e}")
        
        return report_df
