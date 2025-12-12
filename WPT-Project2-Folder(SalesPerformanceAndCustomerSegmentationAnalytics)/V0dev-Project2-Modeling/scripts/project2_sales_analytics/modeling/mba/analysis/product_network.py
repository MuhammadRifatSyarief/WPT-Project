"""
MBA Product Network Module
==========================

Builds and analyzes product co-purchase networks
from association rules.

Author: Project 2 - Sales Analytics
Version: 1.0.0
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


class ProductNetwork:
    """
    Product network analysis based on association rules.
    
    Creates a graph representation of product relationships
    for network analysis and visualization.
    
    Example:
        >>> network = ProductNetwork(rules_df)
        >>> network.build()
        >>> centrality = network.get_centrality()
        >>> communities = network.detect_communities()
    """
    
    def __init__(self, rules: pd.DataFrame, config=None):
        """
        Initialize product network.
        
        Args:
            rules: DataFrame with association rules
            config: Optional MBAConfig instance
        """
        self.rules = rules.copy()
        self.config = config
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Dict[str, Any]] = []
        self.adjacency: Dict[str, Dict[str, float]] = defaultdict(dict)
        
    def build(self, weight_metric: str = 'lift') -> None:
        """
        Build product network from rules.
        
        Args:
            weight_metric: Metric to use as edge weight ('lift', 'confidence', 'support')
        """
        logger.info("Building product network...")
        
        # Extract nodes and edges from rules
        for _, rule in self.rules.iterrows():
            # Add nodes for antecedents
            for item in rule['antecedents']:
                item_str = str(item)
                if item_str not in self.nodes:
                    self.nodes[item_str] = {
                        'id': item_str,
                        'name': item_str,
                        'antecedent_count': 0,
                        'consequent_count': 0
                    }
                self.nodes[item_str]['antecedent_count'] += 1
            
            # Add nodes for consequents
            for item in rule['consequents']:
                item_str = str(item)
                if item_str not in self.nodes:
                    self.nodes[item_str] = {
                        'id': item_str,
                        'name': item_str,
                        'antecedent_count': 0,
                        'consequent_count': 0
                    }
                self.nodes[item_str]['consequent_count'] += 1
            
            # Add edges
            weight = rule[weight_metric]
            
            for ant_item in rule['antecedents']:
                ant_str = str(ant_item)
                for cons_item in rule['consequents']:
                    cons_str = str(cons_item)
                    
                    edge = {
                        'source': ant_str,
                        'target': cons_str,
                        'weight': weight,
                        'support': rule['support'],
                        'confidence': rule['confidence'],
                        'lift': rule['lift']
                    }
                    self.edges.append(edge)
                    
                    # Update adjacency
                    current_weight = self.adjacency[ant_str].get(cons_str, 0)
                    self.adjacency[ant_str][cons_str] = max(current_weight, weight)
        
        # Calculate node metrics
        self._calculate_node_metrics()
        
        logger.info(f"Built network with {len(self.nodes)} nodes and {len(self.edges)} edges")
    
    def _calculate_node_metrics(self) -> None:
        """Calculate additional metrics for each node."""
        # Degree centrality (number of connections)
        for node_id in self.nodes:
            out_degree = len(self.adjacency.get(node_id, {}))
            in_degree = sum(
                1 for adj in self.adjacency.values() 
                if node_id in adj
            )
            
            self.nodes[node_id]['out_degree'] = out_degree
            self.nodes[node_id]['in_degree'] = in_degree
            self.nodes[node_id]['total_degree'] = out_degree + in_degree
    
    def get_nodes_df(self) -> pd.DataFrame:
        """
        Get nodes as DataFrame.
        
        Returns:
            DataFrame with node information
        """
        return pd.DataFrame(list(self.nodes.values()))
    
    def get_edges_df(self) -> pd.DataFrame:
        """
        Get edges as DataFrame.
        
        Returns:
            DataFrame with edge information
        """
        return pd.DataFrame(self.edges)
    
    def get_centrality(self) -> pd.DataFrame:
        """
        Calculate node centrality measures.
        
        Returns:
            DataFrame with centrality scores
        """
        if not self.nodes:
            logger.warning("Network not built. Call build() first.")
            return pd.DataFrame()
        
        centrality_data = []
        
        total_nodes = len(self.nodes)
        max_possible_degree = (total_nodes - 1) * 2  # In + Out
        
        for node_id, node_data in self.nodes.items():
            # Degree centrality (normalized)
            degree_centrality = node_data['total_degree'] / max_possible_degree if max_possible_degree > 0 else 0
            
            # Weighted degree (sum of edge weights)
            out_weights = sum(self.adjacency.get(node_id, {}).values())
            in_weights = sum(
                adj.get(node_id, 0) 
                for adj in self.adjacency.values()
            )
            weighted_degree = out_weights + in_weights
            
            centrality_data.append({
                'product': node_id,
                'in_degree': node_data['in_degree'],
                'out_degree': node_data['out_degree'],
                'total_degree': node_data['total_degree'],
                'degree_centrality': degree_centrality,
                'weighted_degree': weighted_degree,
                'antecedent_rules': node_data['antecedent_count'],
                'consequent_rules': node_data['consequent_count']
            })
        
        df = pd.DataFrame(centrality_data)
        df = df.sort_values('weighted_degree', ascending=False)
        
        return df
    
    def get_neighbors(self, product: str) -> Dict[str, List[str]]:
        """
        Get neighboring products for a given product.
        
        Args:
            product: Product ID/name
            
        Returns:
            Dictionary with 'leads_to' and 'triggered_by' lists
        """
        product_str = str(product)
        
        # Products this one leads to
        leads_to = list(self.adjacency.get(product_str, {}).keys())
        
        # Products that lead to this one
        triggered_by = [
            source for source, targets in self.adjacency.items()
            if product_str in targets
        ]
        
        return {
            'leads_to': leads_to,
            'triggered_by': triggered_by
        }
    
    def detect_communities_simple(self) -> Dict[str, int]:
        """
        Simple community detection using connected components.
        
        Returns:
            Dictionary mapping product to community ID
        """
        # Build undirected adjacency for community detection
        undirected = defaultdict(set)
        
        for source, targets in self.adjacency.items():
            for target in targets:
                undirected[source].add(target)
                undirected[target].add(source)
        
        # Find connected components using BFS
        visited = set()
        communities = {}
        community_id = 0
        
        for node in self.nodes:
            if node in visited:
                continue
            
            # BFS
            queue = [node]
            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                
                visited.add(current)
                communities[current] = community_id
                
                for neighbor in undirected.get(current, []):
                    if neighbor not in visited:
                        queue.append(neighbor)
            
            community_id += 1
        
        return communities
    
    def get_hub_products(self, n: int = 10) -> pd.DataFrame:
        """
        Identify hub products (high connectivity).
        
        Hub products are important for cross-selling strategies.
        
        Args:
            n: Number of top hubs to return
            
        Returns:
            DataFrame with hub products
        """
        centrality = self.get_centrality()
        
        if len(centrality) == 0:
            return pd.DataFrame()
        
        # Calculate hub score (combination of in and out degree)
        centrality['hub_score'] = (
            centrality['weighted_degree'] * 0.5 +
            centrality['degree_centrality'] * 100 * 0.3 +
            centrality['antecedent_rules'] * 0.2
        )
        
        return centrality.nlargest(n, 'hub_score')
    
    def export_for_visualization(self) -> Dict[str, Any]:
        """
        Export network data for visualization tools.
        
        Returns:
            Dictionary with nodes and edges for visualization
        """
        # Format nodes
        vis_nodes = []
        for node_id, node_data in self.nodes.items():
            vis_nodes.append({
                'id': node_id,
                'label': node_id,
                'value': node_data['total_degree'],
                'title': f"Degree: {node_data['total_degree']}"
            })
        
        # Format edges
        vis_edges = []
        for edge in self.edges:
            vis_edges.append({
                'from': edge['source'],
                'to': edge['target'],
                'value': edge['weight'],
                'title': f"Lift: {edge['lift']:.2f}, Conf: {edge['confidence']:.2%}"
            })
        
        return {
            'nodes': vis_nodes,
            'edges': vis_edges,
            'stats': {
                'node_count': len(vis_nodes),
                'edge_count': len(vis_edges)
            }
        }
