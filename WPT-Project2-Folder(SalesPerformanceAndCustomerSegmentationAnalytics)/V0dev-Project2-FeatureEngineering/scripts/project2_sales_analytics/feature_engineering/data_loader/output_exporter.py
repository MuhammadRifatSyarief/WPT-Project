"""
Output Exporter Module

Menyimpan hasil feature engineering dalam berbagai format.

Author: v0
Version: 1.0
"""

import sys
from pathlib import Path

_PARENT_DIR = Path(__file__).resolve().parent.parent
if str(_PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(_PARENT_DIR))

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
import json

try:
    import joblib
    HAS_JOBLIB = True
except ImportError:
    HAS_JOBLIB = False
    import pickle


class FeatureExporter:
    """
    Export feature engineering results to multiple formats.
    
    Supported formats:
    - CSV: Universal, human-readable
    - PKL/Joblib: Fast loading for Python/Streamlit
    - Excel: For business users
    - Parquet: Efficient columnar storage
    
    Usage:
        exporter = FeatureExporter(output_dir="output/features")
        
        # Export single DataFrame
        exporter.to_csv(df, "customer_features")
        exporter.to_pickle(df, "customer_features")
        
        # Export multiple DataFrames
        exporter.export_all({
            "customer_features": customer_df,
            "rfm_features": rfm_df,
        })
    """
    
    def __init__(
        self,
        output_dir: Union[str, Path] = "output/features",
        add_timestamp: bool = False,
        verbose: bool = True,
    ):
        """
        Initialize exporter.
        
        Args:
            output_dir: Directory to save output files
            add_timestamp: Add timestamp suffix to filenames
            verbose: Print progress messages
        """
        self.output_dir = Path(output_dir)
        self.add_timestamp = add_timestamp
        self.verbose = verbose
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        self.csv_dir = self.output_dir / "csv"
        self.pkl_dir = self.output_dir / "pkl"
        self.csv_dir.mkdir(exist_ok=True)
        self.pkl_dir.mkdir(exist_ok=True)
        
        # Track exported files
        self.exported_files: List[Path] = []
        
        if self.verbose:
            print(f"[Exporter] Output directory: {self.output_dir}")
    
    def _get_filename(self, name: str, extension: str) -> str:
        """Generate filename with optional timestamp."""
        if self.add_timestamp:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"{name}_{timestamp}.{extension}"
        return f"{name}.{extension}"
    
    def to_csv(
        self,
        df: pd.DataFrame,
        name: str,
        index: bool = False,
        encoding: str = "utf-8",
        **kwargs
    ) -> Path:
        """
        Export DataFrame to CSV.
        
        Args:
            df: DataFrame to export
            name: Base filename (without extension)
            index: Include index in output
            encoding: File encoding
            **kwargs: Additional pandas to_csv arguments
            
        Returns:
            Path to created file
        """
        filename = self._get_filename(name, "csv")
        filepath = self.csv_dir / filename
        
        df.to_csv(filepath, index=index, encoding=encoding, **kwargs)
        self.exported_files.append(filepath)
        
        if self.verbose:
            print(f"   [CSV] Saved: {filepath.name} ({len(df):,} rows, {len(df.columns)} cols)")
        
        return filepath
    
    def to_pickle(
        self,
        data: Union[pd.DataFrame, Dict, Any],
        name: str,
        compress: int = 3,
    ) -> Path:
        """
        Export data to Pickle (joblib) for fast loading.
        
        Args:
            data: Data to export (DataFrame, dict, or any object)
            name: Base filename (without extension)
            compress: Compression level (0-9, higher = smaller file)
            
        Returns:
            Path to created file
        """
        filename = self._get_filename(name, "pkl")
        filepath = self.pkl_dir / filename
        
        if HAS_JOBLIB:
            joblib.dump(data, filepath, compress=compress)
        else:
            with open(filepath, 'wb') as f:
                pickle.dump(data, f)
        
        self.exported_files.append(filepath)
        
        # Get file size
        size_mb = filepath.stat().st_size / (1024 * 1024)
        
        if self.verbose:
            if isinstance(data, pd.DataFrame):
                print(f"   [PKL] Saved: {filepath.name} ({len(data):,} rows, {size_mb:.2f} MB)")
            else:
                print(f"   [PKL] Saved: {filepath.name} ({size_mb:.2f} MB)")
        
        return filepath
    
    def to_excel(
        self,
        df: pd.DataFrame,
        name: str,
        index: bool = False,
        sheet_name: str = "Data",
        **kwargs
    ) -> Path:
        """
        Export DataFrame to Excel.
        
        Args:
            df: DataFrame to export
            name: Base filename (without extension)
            index: Include index in output
            sheet_name: Excel sheet name
            **kwargs: Additional pandas to_excel arguments
            
        Returns:
            Path to created file
        """
        filename = self._get_filename(name, "xlsx")
        filepath = self.output_dir / filename
        
        df.to_excel(filepath, index=index, sheet_name=sheet_name, **kwargs)
        self.exported_files.append(filepath)
        
        if self.verbose:
            print(f"   [XLSX] Saved: {filepath.name} ({len(df):,} rows)")
        
        return filepath
    
    def to_parquet(
        self,
        df: pd.DataFrame,
        name: str,
        compression: str = "snappy",
        **kwargs
    ) -> Path:
        """
        Export DataFrame to Parquet (efficient columnar format).
        
        Args:
            df: DataFrame to export
            name: Base filename (without extension)
            compression: Compression algorithm
            **kwargs: Additional pandas to_parquet arguments
            
        Returns:
            Path to created file
        """
        filename = self._get_filename(name, "parquet")
        filepath = self.output_dir / filename
        
        df.to_parquet(filepath, compression=compression, **kwargs)
        self.exported_files.append(filepath)
        
        size_mb = filepath.stat().st_size / (1024 * 1024)
        
        if self.verbose:
            print(f"   [Parquet] Saved: {filepath.name} ({len(df):,} rows, {size_mb:.2f} MB)")
        
        return filepath
    
    def export_all(
        self,
        dataframes: Dict[str, pd.DataFrame],
        formats: List[str] = ["csv", "pkl"],
    ) -> Dict[str, List[Path]]:
        """
        Export multiple DataFrames to specified formats.
        
        Args:
            dataframes: Dictionary of {name: DataFrame}
            formats: List of formats to export ("csv", "pkl", "xlsx", "parquet")
            
        Returns:
            Dictionary of {format: [file_paths]}
        """
        if self.verbose:
            print(f"\n[Exporter] Exporting {len(dataframes)} DataFrames to {formats}...")
        
        result = {fmt: [] for fmt in formats}
        
        for name, df in dataframes.items():
            if "csv" in formats:
                path = self.to_csv(df, name)
                result["csv"].append(path)
            
            if "pkl" in formats:
                path = self.to_pickle(df, name)
                result["pkl"].append(path)
            
            if "xlsx" in formats:
                path = self.to_excel(df, name)
                result["xlsx"].append(path)
            
            if "parquet" in formats:
                path = self.to_parquet(df, name)
                result["parquet"].append(path)
        
        return result
    
    def export_for_streamlit(
        self,
        feature_data: Dict[str, pd.DataFrame],
        metadata: Optional[Dict] = None,
    ) -> Dict[str, Path]:
        """
        Export data optimized for Streamlit app loading.
        
        Creates:
        - Individual CSV files for each DataFrame
        - Combined PKL file with all data + metadata
        - Metadata JSON for quick reference
        
        Args:
            feature_data: Dictionary of {name: DataFrame}
            metadata: Additional metadata to include
            
        Returns:
            Dictionary of created file paths
        """
        if self.verbose:
            print(f"\n{'='*60}")
            print(" Exporting for Streamlit ")
            print(f"{'='*60}")
        
        created_files = {}
        
        valid_data = {k: v for k, v in feature_data.items() if v is not None}
        
        if self.verbose and len(valid_data) < len(feature_data):
            skipped = [k for k, v in feature_data.items() if v is None]
            print(f"\n[INFO] Skipping None DataFrames: {skipped}")
        
        # 1. Export individual CSVs
        if self.verbose:
            print("\n[1/3] Exporting CSV files...")
        
        for name, df in valid_data.items():
            path = self.to_csv(df, name)
            created_files[f"csv_{name}"] = path
        
        # 2. Create combined pickle with everything
        if self.verbose:
            print("\n[2/3] Creating combined pickle for Streamlit...")
        
        # Prepare metadata
        export_metadata = {
            "export_timestamp": datetime.now().isoformat(),
            "num_dataframes": len(valid_data),
            "dataframes": {},
        }
        
        for name, df in valid_data.items():
            export_metadata["dataframes"][name] = {
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": df.columns.tolist(),
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                "memory_mb": df.memory_usage(deep=True).sum() / (1024 * 1024),
            }
        
        if metadata:
            export_metadata.update(metadata)
        
        # Combined data package - only include valid data
        streamlit_package = {
            "data": valid_data,
            "metadata": export_metadata,
        }
        
        pkl_path = self.to_pickle(streamlit_package, "streamlit_data")
        created_files["pkl_combined"] = pkl_path
        
        # 3. Export metadata as JSON
        if self.verbose:
            print("\n[3/3] Saving metadata...")
        
        metadata_path = self.output_dir / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(export_metadata, f, indent=2, default=str)
        
        created_files["metadata"] = metadata_path
        
        if self.verbose:
            print(f"   [JSON] Saved: metadata.json")
        
        # Summary
        if self.verbose:
            print(f"\n{'='*60}")
            print(" Export Summary ")
            print(f"{'='*60}")
            print(f"  Output directory: {self.output_dir}")
            print(f"  CSV files: {self.csv_dir}")
            print(f"  PKL files: {self.pkl_dir}")
            print(f"  Total files: {len(created_files)}")
            print(f"\n  Streamlit load command:")
            print(f"    data = joblib.load('{pkl_path}')")
            print(f"    df = data['data']['customer_features']")
        
        return created_files
    
    def get_export_summary(self) -> pd.DataFrame:
        """Get summary of all exported files."""
        summary_data = []
        
        for filepath in self.exported_files:
            if filepath.exists():
                summary_data.append({
                    "filename": filepath.name,
                    "format": filepath.suffix[1:],
                    "size_mb": filepath.stat().st_size / (1024 * 1024),
                    "path": str(filepath),
                })
        
        return pd.DataFrame(summary_data)


class StreamlitDataLoader:
    """
    Helper class for loading exported data in Streamlit.
    
    Usage in Streamlit:
        from data_loader.output_exporter import StreamlitDataLoader
        
        loader = StreamlitDataLoader("output/features/pkl/streamlit_data.pkl")
        
        # Get data
        customer_features = loader.get_dataframe("customer_features")
        rfm_features = loader.get_dataframe("rfm_features")
        
        # Get metadata
        metadata = loader.get_metadata()
    """
    
    def __init__(self, pkl_path: Union[str, Path]):
        """
        Load data from pickle file.
        
        Args:
            pkl_path: Path to streamlit_data.pkl
        """
        self.pkl_path = Path(pkl_path)
        
        if not self.pkl_path.exists():
            raise FileNotFoundError(f"File not found: {self.pkl_path}")
        
        # Load data
        if HAS_JOBLIB:
            self._package = joblib.load(self.pkl_path)
        else:
            with open(self.pkl_path, 'rb') as f:
                self._package = pickle.load(f)
        
        self._data = self._package.get("data", {})
        self._metadata = self._package.get("metadata", {})
    
    def get_dataframe(self, name: str) -> pd.DataFrame:
        """Get specific DataFrame by name."""
        if name not in self._data:
            available = list(self._data.keys())
            raise KeyError(f"DataFrame '{name}' not found. Available: {available}")
        return self._data[name]
    
    def get_all_dataframes(self) -> Dict[str, pd.DataFrame]:
        """Get all DataFrames."""
        return self._data
    
    def get_metadata(self) -> Dict:
        """Get export metadata."""
        return self._metadata
    
    def list_available(self) -> List[str]:
        """List available DataFrame names."""
        return list(self._data.keys())
    
    @staticmethod
    def load_csv(csv_path: Union[str, Path]) -> pd.DataFrame:
        """Load single CSV file."""
        return pd.read_csv(csv_path)
    
    @staticmethod
    def load_all_csv(csv_dir: Union[str, Path]) -> Dict[str, pd.DataFrame]:
        """Load all CSV files from directory."""
        csv_dir = Path(csv_dir)
        data = {}
        
        for csv_file in csv_dir.glob("*.csv"):
            name = csv_file.stem
            data[name] = pd.read_csv(csv_file)
        
        return data
