"""
XLSX Data Loader

Load data dari file Excel hasil data preparation.
Supports:
- XLSX files (openpyxl)
- CSV files
- Automatic type conversion
- Column name normalization

Author: v0
Version: 1.2 - Fixed sheet loading for feature engineering
"""

import sys
from pathlib import Path

_PARENT_DIR = Path(__file__).resolve().parent.parent
if str(_PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(_PARENT_DIR))

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union, Tuple
from datetime import datetime
import warnings

from data_loader.data_schema import DataSchema, SHEET_SCHEMAS, REQUIRED_COLUMNS


class XLSXDataLoader:
    """
    Load data from XLSX file untuk feature engineering.
    
    Usage:
        loader = XLSXDataLoader("sales_performance_analytics.xlsx")
        data = loader.load_all()
        
        # Atau load sheet tertentu
        sales_details = loader.load_sheet("5_Sales_Details")
    """
    
    def __init__(
        self,
        file_path: Union[str, Path],
        verbose: bool = True,
        auto_normalize: bool = True,
    ):
        """
        Initialize data loader.
        
        Args:
            file_path: Path ke file XLSX
            verbose: Print progress messages
            auto_normalize: Auto-normalize column names (lowercase, underscore)
        """
        self.file_path = Path(file_path)
        self.verbose = verbose
        self.auto_normalize = auto_normalize
        self.schema = DataSchema()
        
        # Cached data
        self._data: Dict[str, pd.DataFrame] = {}
        self._sheet_names: List[str] = []
        
        # Validate file exists
        if not self.file_path.exists():
            raise FileNotFoundError(f"File tidak ditemukan: {self.file_path}")
        
        if self.verbose:
            print(f"[DataLoader] Initialized with: {self.file_path}")
    
    def _normalize_column_name(self, col: str) -> str:
        """Normalize column name to snake_case."""
        import re
        # camelCase to snake_case
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', col)
        s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)
        # Replace spaces and hyphens with underscore
        s3 = re.sub(r'[\s\-]+', '_', s2)
        # Remove special characters
        s4 = re.sub(r'[^\w]', '', s3)
        return s4.lower()
    
    def _convert_dates(self, df: pd.DataFrame, date_columns: List[str]) -> pd.DataFrame:
        """Convert date columns to datetime."""
        for col in date_columns:
            if col in df.columns:
                try:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                except Exception as e:
                    if self.verbose:
                        print(f"   [WARN] Cannot convert {col} to datetime: {e}")
        return df
    
    def _convert_numeric(self, df: pd.DataFrame, numeric_columns: List[str]) -> pd.DataFrame:
        """Convert numeric columns to appropriate types."""
        for col in numeric_columns:
            if col in df.columns:
                try:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                except Exception as e:
                    if self.verbose:
                        print(f"   [WARN] Cannot convert {col} to numeric: {e}")
        return df
    
    def get_sheet_names(self) -> List[str]:
        """Get list of sheet names in the Excel file."""
        if not self._sheet_names:
            xlsx = pd.ExcelFile(self.file_path)
            self._sheet_names = xlsx.sheet_names
        return self._sheet_names
    
    def load_sheet(
        self,
        sheet_name: str,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        Load single sheet from Excel file.
        
        Args:
            sheet_name: Name of sheet to load
            use_cache: Use cached data if available
            
        Returns:
            DataFrame with loaded data
        """
        # Check cache
        if use_cache and sheet_name in self._data:
            return self._data[sheet_name]
        
        if self.verbose:
            print(f"[DataLoader] Loading sheet: {sheet_name}")
        
        # Load data
        try:
            df = pd.read_excel(
                self.file_path,
                sheet_name=sheet_name,
                engine='openpyxl'
            )
        except Exception as e:
            raise ValueError(f"Error loading sheet '{sheet_name}': {e}")
        
        # Normalize column names
        if self.auto_normalize:
            original_cols = df.columns.tolist()
            df.columns = [self._normalize_column_name(c) for c in df.columns]
            
            # Log column mapping if changed
            if self.verbose:
                changed = [(o, n) for o, n in zip(original_cols, df.columns) if o != n]
                if changed:
                    print(f"   Normalized {len(changed)} column names")
        
        # Get schema for type conversion
        schema = self.schema.get_sheet_schema(sheet_name)
        if schema:
            # Convert date columns
            date_cols = [self._normalize_column_name(c) for c in schema.date_columns]
            df = self._convert_dates(df, date_cols)
            
            # Convert numeric columns
            numeric_cols = [self._normalize_column_name(c) for c in schema.numeric_columns]
            df = self._convert_numeric(df, numeric_cols)
        
        if self.verbose:
            print(f"   Loaded {len(df):,} rows, {len(df.columns)} columns")
        
        # Cache the result
        self._data[sheet_name] = df
        return df
    
    def load_all(self, sheets: Optional[List[str]] = None) -> Dict[str, pd.DataFrame]:
        """
        Load all (or specified) sheets from Excel file.
        
        Args:
            sheets: List of sheet names to load. None = load all.
            
        Returns:
            Dictionary of {sheet_name: DataFrame}
        """
        available_sheets = self.get_sheet_names()
        
        if sheets is None:
            sheets_to_load = available_sheets
        else:
            sheets_to_load = [s for s in sheets if s in available_sheets]
            missing = set(sheets) - set(available_sheets)
            if missing and self.verbose:
                print(f"[WARN] Sheets not found: {missing}")
        
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"Loading {len(sheets_to_load)} sheets from: {self.file_path.name}")
            print(f"{'='*60}")
        
        result = {}
        for sheet in sheets_to_load:
            try:
                result[sheet] = self.load_sheet(sheet)
            except Exception as e:
                if self.verbose:
                    print(f"[ERROR] Failed to load {sheet}: {e}")
        
        if self.verbose:
            print(f"\n[OK] Loaded {len(result)} sheets successfully")
        
        return result
    
    def load_for_feature_engineering(self) -> Dict[str, pd.DataFrame]:
        """
        Load sheets yang diperlukan untuk feature engineering.
        
        Returns:
            Dictionary dengan key standar untuk feature engineering
        """
        if self.verbose:
            print(f"\n{'='*60}")
            print("Loading data for Feature Engineering")
            print(f"{'='*60}")
        
        available_sheets = self.get_sheet_names()
        
        # Define sheet mapping: {output_key: (sheet_name, required)}
        sheet_mapping = {
            "sales_details": ("5_Sales_Details", True),  # Required
            "sales_by_customer": ("6_Sales_By_Customer", False),  # Optional but needed
            "sales_by_product": ("7_Sales_By_Product", False),  # Optional but needed
            "rfm_analysis": ("1_RFM_Analysis", False),
            "customer_segments": ("2_Customer_Segments", False),
            "market_basket": ("3_Market_Basket", False),
            "product_associations": ("4_Product_Associations", False),
            "customers": ("8_Customer_Master", False),
            "products": ("9_Item_Master", False),
        }
        
        result = {}
        missing_required = []
        
        for output_key, (sheet_name, is_required) in sheet_mapping.items():
            if sheet_name in available_sheets:
                try:
                    result[output_key] = self.load_sheet(sheet_name)
                except Exception as e:
                    if self.verbose:
                        print(f"[WARN] Failed to load {sheet_name}: {e}")
                    if is_required:
                        missing_required.append(sheet_name)
                    result[output_key] = None
            else:
                if is_required:
                    missing_required.append(sheet_name)
                result[output_key] = None
                if self.verbose:
                    print(f"[INFO] Sheet not found (optional): {sheet_name}")
        
        # Check required sheets
        if missing_required:
            raise ValueError(f"Missing required sheets: {missing_required}")
        
        # Remove None values from result only if they are truly optional
        # Keep keys for sales_by_customer/product even if None (will be derived)
        
        if self.verbose:
            loaded_keys = [k for k, v in result.items() if v is not None]
            print(f"\n[OK] Data ready for feature engineering")
            print(f"    Loaded: {loaded_keys}")
            none_keys = [k for k, v in result.items() if v is None]
            if none_keys:
                print(f"    Not found (will derive if needed): {none_keys}")
        
        return result
    
    def get_summary(self) -> pd.DataFrame:
        """Get summary of loaded data."""
        if not self._data:
            self.load_all()
        
        summary_data = []
        for name, df in self._data.items():
            summary_data.append({
                "sheet": name,
                "rows": len(df),
                "columns": len(df.columns),
                "memory_mb": df.memory_usage(deep=True).sum() / 1024 / 1024,
                "null_pct": (df.isnull().sum().sum() / (len(df) * len(df.columns)) * 100) if len(df) > 0 else 0,
            })
        
        return pd.DataFrame(summary_data)
    
    def clear_cache(self):
        """Clear cached data."""
        self._data = {}
        if self.verbose:
            print("[DataLoader] Cache cleared")
    
    def convert_all_to_csv(
        self,
        output_folder: Union[str, Path],
        sheets: Optional[List[str]] = None,
    ) -> Dict[str, Path]:
        """
        Convert all sheets from XLSX to CSV files.
        
        Args:
            output_folder: Folder to save CSV files
            sheets: Specific sheets to convert. None = all sheets.
            
        Returns:
            Dictionary of {sheet_name: csv_path}
        """
        output_folder = Path(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)
        
        # Load all sheets
        data = self.load_all(sheets)
        
        if self.verbose:
            print(f"\n[CSV Export] Converting {len(data)} sheets to CSV...")
        
        created_files = {}
        
        for sheet_name, df in data.items():
            # Clean filename: remove leading numbers and special chars
            clean_name = sheet_name.replace(" ", "_").replace("/", "_")
            # Remove leading number pattern like "5_"
            if clean_name[0].isdigit() and clean_name[1] == "_":
                clean_name = clean_name[2:]
            
            csv_path = output_folder / f"{clean_name.lower()}.csv"
            df.to_csv(csv_path, index=False, encoding='utf-8')
            created_files[sheet_name] = csv_path
            
            if self.verbose:
                print(f"   Saved: {csv_path.name} ({len(df):,} rows)")
        
        if self.verbose:
            print(f"\n[OK] Exported {len(created_files)} CSV files to: {output_folder}")
        
        return created_files


def load_from_csv(
    folder_path: Union[str, Path],
    file_mapping: Optional[Dict[str, str]] = None,
    verbose: bool = True,
) -> Dict[str, pd.DataFrame]:
    """
    Load data from multiple CSV files.
    
    Args:
        folder_path: Path to folder containing CSV files
        file_mapping: Mapping of {key: filename}. If None, auto-detect.
        verbose: Print progress
        
    Returns:
        Dictionary of DataFrames
        
    Usage:
        data = load_from_csv("./data/csv/", verbose=True)
    """
    folder = Path(folder_path)
    
    if file_mapping is None:
        file_mapping = {}
        for csv_file in folder.glob("*.csv"):
            key = csv_file.stem  # filename without extension
            file_mapping[key] = csv_file.name
    
    result = {}
    for key, filename in file_mapping.items():
        filepath = folder / filename
        if filepath.exists():
            if verbose:
                print(f"[CSV] Loading {filename}...")
            result[key] = pd.read_csv(filepath)
            if verbose:
                print(f"   Loaded {len(result[key]):,} rows")
        elif verbose:
            print(f"[WARN] File not found: {filepath}")
    
    return result


def convert_xlsx_to_csv(
    xlsx_path: Union[str, Path],
    output_folder: Union[str, Path],
    sheets: Optional[List[str]] = None,
    verbose: bool = True,
) -> Dict[str, Path]:
    """
    Convert XLSX sheets to CSV files.
    
    Args:
        xlsx_path: Path to XLSX file
        output_folder: Folder to save CSV files
        sheets: List of sheets to convert. None = all sheets.
        verbose: Print progress
        
    Returns:
        Dictionary of {sheet_name: csv_path}
    """
    loader = XLSXDataLoader(xlsx_path, verbose=verbose)
    return loader.convert_all_to_csv(output_folder, sheets)
