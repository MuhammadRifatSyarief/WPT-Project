"""
MBA Exporter Module
===================

Exports Market Basket Analysis results to various formats
for integration with Streamlit dashboard and other systems.

Author: Project 2 - Sales Analytics
Version: 1.0.0
"""

import pandas as pd
import numpy as np
import json
import joblib
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)
class FrozensetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, frozenset):
            return list(obj)
        return super().default(obj)

class MBAExporter:
    """
    Exporter for Market Basket Analysis results.
    
    Exports to:
    - CSV files (human-readable)
    - Pickle files (for Streamlit integration)
    - JSON files (for API/web integration)
    
    Example:
        >>> exporter = MBAExporter(config)
        >>> exporter.export_all(rules, itemsets, analysis_results)
    """
    
    def __init__(self, config):
        """
        Initialize MBA exporter.
        
        Args:
            config: MBAConfig instance with output paths
        """
        self.config = config
        self.output_dir = Path(config.output_dir)
        self.export_log: List[Dict[str, Any]] = []
        
        # Ensure directories exist
        self._create_directories()
    
    def _create_directories(self) -> None:
        """Create output directories."""
        (self.output_dir / "csv").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "pkl").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "json").mkdir(parents=True, exist_ok=True)
    
    def export_all(
        self,
        rules: pd.DataFrame,
        frequent_itemsets: pd.DataFrame,
        analysis_results: Dict[str, Any],
        cross_sell_report: Optional[pd.DataFrame] = None,
        network_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Export all MBA results.
        
        Args:
            rules: Association rules DataFrame
            frequent_itemsets: Frequent itemsets DataFrame
            analysis_results: Analysis results dictionary
            cross_sell_report: Optional cross-sell report
            network_data: Optional network visualization data
            
        Returns:
            Dictionary mapping output type to file path
        """
        logger.info("Starting MBA export...")
        exported_files = {}
        
        # 1. Export association rules
        if len(rules) > 0:
            exported_files.update(self._export_rules(rules))
        
        # 2. Export frequent itemsets
        if len(frequent_itemsets) > 0:
            exported_files.update(self._export_itemsets(frequent_itemsets))
        
        # 3. Export analysis results
        if analysis_results:
            exported_files.update(self._export_analysis(analysis_results))
        
        # 4. Export cross-sell report
        if cross_sell_report is not None and len(cross_sell_report) > 0:
            exported_files.update(self._export_cross_sell(cross_sell_report))
        
        # 5. Export network data
        if network_data:
            exported_files.update(self._export_network(network_data))
        
        # 6. Create combined Streamlit data package
        exported_files.update(self._export_streamlit_package(
            rules, frequent_itemsets, analysis_results, cross_sell_report
        ))
        
        # 7. Export metadata
        exported_files.update(self._export_metadata())
        
        self._print_export_summary(exported_files)
        
        return exported_files
    
    def _export_rules(self, rules: pd.DataFrame) -> Dict[str, str]:
        """Export association rules."""
        files = {}
        
        # Prepare rules for export (convert frozensets to strings)
        export_df = self._prepare_rules_for_export(rules)
        
        # CSV
        if "csv" in self.config.export_formats:
            csv_path = self.output_dir / "csv" / "association_rules.csv"
            export_df.to_csv(csv_path, index=False)
            files['rules_csv'] = str(csv_path)
            self._log_export('association_rules.csv', 'csv', len(export_df))
        
        # Top rules (for quick access)
        if "csv" in self.config.export_formats:
            top_rules = export_df.head(self.config.top_rules_count)
            top_path = self.output_dir / "csv" / "top_rules.csv"
            top_rules.to_csv(top_path, index=False)
            files['top_rules_csv'] = str(top_path)
        
        # Pickle (preserves frozensets)
        if "pkl" in self.config.export_formats:
            pkl_path = self.output_dir / "pkl" / "association_rules.pkl"
            joblib.dump(rules, pkl_path)
            files['rules_pkl'] = str(pkl_path)
            self._log_export('association_rules.pkl', 'pkl', len(rules))
        
        return files
    
    def _prepare_rules_for_export(self, rules: pd.DataFrame) -> pd.DataFrame:
        """Prepare rules DataFrame for CSV export."""
        df = rules.copy()
        
        # Convert frozensets to strings if not already
        if 'antecedents' in df.columns:
            df['antecedents'] = df['antecedents'].apply(
                lambda x: ', '.join(sorted(str(i) for i in x)) if isinstance(x, frozenset) else str(x)
            )
        
        if 'consequents' in df.columns:
            df['consequents'] = df['consequents'].apply(
                lambda x: ', '.join(sorted(str(i) for i in x)) if isinstance(x, frozenset) else str(x)
            )
        
        # Select and order columns
        core_columns = [
            'antecedents', 'consequents', 'support', 'confidence', 'lift'
        ]
        
        additional_columns = [
            'antecedent support', 'consequent support',
            'leverage', 'conviction', 'rule_str'
        ]
        
        available_columns = [c for c in core_columns + additional_columns if c in df.columns]
        
        return df[available_columns]
    
    def _export_itemsets(self, itemsets: pd.DataFrame) -> Dict[str, str]:
        """Export frequent itemsets."""
        files = {}
        
        # Prepare for export
        export_df = itemsets.copy()
        export_df['itemsets'] = export_df['itemsets'].apply(
            lambda x: ', '.join(sorted(str(i) for i in x)) if isinstance(x, frozenset) else str(x)
        )
        
        # CSV
        if "csv" in self.config.export_formats:
            csv_path = self.output_dir / "csv" / "frequent_itemsets.csv"
            export_df.to_csv(csv_path, index=False)
            files['itemsets_csv'] = str(csv_path)
            self._log_export('frequent_itemsets.csv', 'csv', len(export_df))
        
        # Pickle
        if "pkl" in self.config.export_formats:
            pkl_path = self.output_dir / "pkl" / "frequent_itemsets.pkl"
            joblib.dump(itemsets, pkl_path)
            files['itemsets_pkl'] = str(pkl_path)
        
        return files
    
    def _export_analysis(self, analysis: Dict[str, Any]) -> Dict[str, str]:
        """Export analysis results."""
        files = {}
        
        # Export summary as JSON
        if "json" in self.config.export_formats:
            # Prepare for JSON serialization
            json_safe = self._make_json_serializable(analysis)
            
            json_path = self.output_dir / "json" / "analysis_results.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_safe, f, indent=2, ensure_ascii=False, cls=FrozensetEncoder)
            files['analysis_json'] = str(json_path)
            self._log_export('analysis_results.json', 'json', 0)
        
        # Export insights as CSV
        if 'actionable_insights' in analysis and "csv" in self.config.export_formats:
            insights_df = pd.DataFrame(analysis['actionable_insights'])
            if len(insights_df) > 0:
                insights_path = self.output_dir / "csv" / "actionable_insights.csv"
                insights_df.to_csv(insights_path, index=False)
                files['insights_csv'] = str(insights_path)
        
        # Export product analysis as CSV
        if 'product_analysis' in analysis:
            prod_analysis = analysis['product_analysis']
            if 'product_summary' in prod_analysis:
                prod_df = prod_analysis['product_summary']
                if isinstance(prod_df, pd.DataFrame) and len(prod_df) > 0:
                    prod_path = self.output_dir / "csv" / "product_analysis.csv"
                    prod_df.to_csv(prod_path, index=False)
                    files['product_analysis_csv'] = str(prod_path)
        
        return files
    
    def _export_cross_sell(self, cross_sell: pd.DataFrame) -> Dict[str, str]:
        """Export cross-sell recommendations."""
        files = {}
        
        if "csv" in self.config.export_formats:
            csv_path = self.output_dir / "csv" / "cross_sell_recommendations.csv"
            cross_sell.to_csv(csv_path, index=False)
            files['cross_sell_csv'] = str(csv_path)
            self._log_export('cross_sell_recommendations.csv', 'csv', len(cross_sell))
        
        return files
    
    def _export_network(self, network_data: Dict[str, Any]) -> Dict[str, str]:
        """Export network visualization data."""
        files = {}
        
        if "json" in self.config.export_formats:
            json_path = self.output_dir / "json" / "product_network.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(network_data, f, indent=2)
            files['network_json'] = str(json_path)
        
        return files
    
    def _export_streamlit_package(
        self,
        rules: pd.DataFrame,
        itemsets: pd.DataFrame,
        analysis: Dict[str, Any],
        cross_sell: Optional[pd.DataFrame]
    ) -> Dict[str, str]:
        """Create combined data package for Streamlit."""
        files = {}
        
        if "pkl" not in self.config.export_formats:
            return files
        
        # Prepare package
        package = {
            'data': {
                'association_rules': rules,
                'frequent_itemsets': itemsets,
                'cross_sell_report': cross_sell if cross_sell is not None else pd.DataFrame()
            },
            'analysis': analysis,
            'metadata': {
                'created_at': datetime.now().isoformat(),
                'config': self.config.to_dict(),
                'rules_count': len(rules),
                'itemsets_count': len(itemsets)
            }
        }
        
        # Save package
        pkl_path = self.output_dir / "pkl" / "mba_streamlit_data.pkl"
        joblib.dump(package, pkl_path)
        files['streamlit_package'] = str(pkl_path)
        
        self._log_export('mba_streamlit_data.pkl', 'pkl', 0)
        
        return files
    
    def _export_metadata(self) -> Dict[str, str]:
        """Export pipeline metadata."""
        files = {}
        
        metadata = {
            'pipeline': 'Market Basket Analysis',
            'version': '1.0.0',
            'created_at': datetime.now().isoformat(),
            'config': self.config.to_dict(),
            'export_log': self.export_log,
            'output_directory': str(self.output_dir)
        }
        
        json_path = self.output_dir / "json" / "mba_metadata.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        files['metadata'] = str(json_path)
        
        return files
    
    def _make_json_serializable(self, obj: Any) -> Any:
        """Convert object to JSON-serializable format."""
        if isinstance(obj, dict):
            return {k: self._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, pd.DataFrame):
            return obj.to_dict(orient='records')
        elif isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, frozenset):
            return list(obj)
        elif isinstance(obj, (datetime,)):
            return obj.isoformat()
        elif pd.isna(obj):
            return None
        else:
            return obj
    
    def _log_export(self, filename: str, format_type: str, rows: int) -> None:
        """Log export operation."""
        self.export_log.append({
            'filename': filename,
            'format': format_type,
            'rows': rows,
            'timestamp': datetime.now().isoformat()
        })
    
    def _print_export_summary(self, files: Dict[str, str]) -> None:
        """Print export summary."""
        print("\n" + "=" * 60)
        print("MBA EXPORT SUMMARY")
        print("=" * 60)
        
        print(f"\nOutput Directory: {self.output_dir}")
        print(f"Files Exported: {len(files)}")
        
        print("\n--- Exported Files ---")
        for name, path in files.items():
            file_path = Path(path)
            if file_path.exists():
                size_kb = file_path.stat().st_size / 1024
                print(f"  [{name}] {file_path.name} ({size_kb:.1f} KB)")
            else:
                print(f"  [{name}] {file_path.name}")
        
        print("\n--- Usage ---")
        print("  Streamlit:")
        print("    import joblib")
        print(f"    data = joblib.load('{self.output_dir}/pkl/mba_streamlit_data.pkl')")
        print("    rules = data['data']['association_rules']")
