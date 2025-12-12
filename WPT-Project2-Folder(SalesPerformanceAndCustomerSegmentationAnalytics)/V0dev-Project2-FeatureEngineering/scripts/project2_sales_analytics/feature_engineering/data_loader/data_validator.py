"""
Data Validator

Validasi data sebelum feature engineering.
Memastikan data memenuhi syarat minimum untuk analisis.

Author: v0
Version: 1.2 - Added comprehensive None handling
"""

import sys
from pathlib import Path

_PARENT_DIR = Path(__file__).resolve().parent.parent
if str(_PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(_PARENT_DIR))

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

from data_loader.data_schema import REQUIRED_COLUMNS, DataSchema, find_column, COLUMN_ALIASES


@dataclass
class ValidationResult:
    """Result of data validation."""
    
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    info: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        status = "VALID" if self.is_valid else "INVALID"
        lines = [f"Validation Result: {status}"]
        
        if self.errors:
            lines.append(f"  Errors ({len(self.errors)}):")
            for e in self.errors:
                lines.append(f"    - {e}")
        
        if self.warnings:
            lines.append(f"  Warnings ({len(self.warnings)}):")
            for w in self.warnings:
                lines.append(f"    - {w}")
        
        return "\n".join(lines)


class DataValidator:
    """
    Validate data sebelum feature engineering.
    
    Usage:
        validator = DataValidator()
        result = validator.validate_all(data)
        
        if not result.is_valid:
            print(result)
            raise ValueError("Data validation failed")
    """
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.schema = DataSchema()
    
    def _find_col(self, df: Optional[pd.DataFrame], expected: str) -> Optional[str]:
        """Find actual column name using aliases. Returns None if df is None."""
        if df is None:
            return None
        return find_column(df, expected, COLUMN_ALIASES)
    
    def validate_sales_details(self, df: pd.DataFrame) -> ValidationResult:
        """
        Validate sales_details DataFrame.
        
        Required for:
        - RFM Analysis (customer_id, transaction dates, amounts)
        - Market Basket Analysis (invoice_id, product_id)
        - Customer Features (all customer-level metrics)
        """
        errors = []
        warnings = []
        info = {}
        
        if df is None:
            return ValidationResult(
                is_valid=False,
                errors=["sales_details DataFrame is None"],
                warnings=[],
                info={}
            )
        
        required_base = ["customer_id", "product_id", "quantity"]
        missing = []
        found_cols = {}
        
        for col in required_base:
            actual = self._find_col(df, col)
            if actual:
                found_cols[col] = actual
            else:
                missing.append(col)
        
        # invoice_id is optional but recommended
        invoice_col = self._find_col(df, "invoice_id")
        if invoice_col:
            found_cols["invoice_id"] = invoice_col
        else:
            warnings.append("No invoice_id column found (needed for basket analysis)")
        
        if missing:
            errors.append(f"Missing required columns: {missing}")
        
        info["found_columns"] = found_cols
        
        # Check data volume
        info["row_count"] = len(df)
        if len(df) < 100:
            warnings.append(f"Low data volume: {len(df)} rows (recommend > 100)")
        
        # Check for null values in key columns
        customer_col = found_cols.get("customer_id", "customer_id")
        if customer_col in df.columns:
            null_pct = df[customer_col].isnull().mean() * 100
            info["customer_id_null_pct"] = null_pct
            if null_pct > 5:
                errors.append(f"High null rate in {customer_col}: {null_pct:.1f}%")
        
        if invoice_col and invoice_col in df.columns:
            null_pct = df[invoice_col].isnull().mean() * 100
            info["invoice_id_null_pct"] = null_pct
            if null_pct > 0:
                warnings.append(f"Null {invoice_col} found: {null_pct:.1f}%")
        
        amount_col = self._find_col(df, "total_amount")
        if amount_col and amount_col in df.columns:
            negative_pct = (df[amount_col] < 0).mean() * 100
            info["negative_amount_pct"] = negative_pct
            info["amount_column"] = amount_col
            if negative_pct > 10:
                warnings.append(f"High negative amounts in {amount_col}: {negative_pct:.1f}% (check for returns)")
        
        # Check unique counts
        if customer_col in df.columns:
            info["unique_customers"] = df[customer_col].nunique()
        
        product_col = found_cols.get("product_id", "product_id")
        if product_col in df.columns:
            info["unique_products"] = df[product_col].nunique()
        
        if invoice_col and invoice_col in df.columns:
            info["unique_invoices"] = df[invoice_col].nunique()
        
        date_col = self._find_col(df, "transaction_date") or self._find_col(df, "trans_date")
        if date_col:
            info["date_column"] = date_col
            if df[date_col].dtype == 'object':
                warnings.append(f"Date column '{date_col}' is not datetime type (will be converted)")
        else:
            # Try to find any date-like column
            date_cols = [c for c in df.columns if "date" in c.lower()]
            if date_cols:
                info["date_columns_found"] = date_cols
                info["date_column"] = date_cols[0]  # Use first one found
                warnings.append(f"Using '{date_cols[0]}' as date column")
            else:
                warnings.append("No date column found (needed for RFM recency)")
        
        is_valid = len(errors) == 0
        return ValidationResult(is_valid, errors, warnings, info)
    
    def validate_sales_by_customer(self, df: Optional[pd.DataFrame]) -> ValidationResult:
        """Validate sales_by_customer DataFrame."""
        errors = []
        warnings = []
        info = {}
        
        # Handle None DataFrame
        if df is None:
            return ValidationResult(
                is_valid=True,  # Not an error - can be derived from sales_details
                errors=[],
                warnings=["sales_by_customer is None - will be derived from sales_details"],
                info={"is_none": True}
            )
        
        customer_col = self._find_col(df, "customer_id")
        if not customer_col:
            errors.append("Missing required column: customer_id")
        else:
            info["customer_id_column"] = customer_col
        
        info["row_count"] = len(df)
        
        if customer_col and customer_col in df.columns:
            info["unique_customers"] = df[customer_col].nunique()
            
            # Check for duplicates
            dup_count = df[customer_col].duplicated().sum()
            if dup_count > 0:
                warnings.append(f"Duplicate {customer_col} found: {dup_count} rows")
        
        revenue_col = self._find_col(df, "total_revenue")
        if revenue_col and revenue_col in df.columns:
            info["revenue_column"] = revenue_col
            zero_revenue = (df[revenue_col] <= 0).sum()
            info["zero_revenue_customers"] = zero_revenue
            if zero_revenue > 0:
                warnings.append(f"{zero_revenue} customers with zero/negative revenue")
        else:
            warnings.append("No revenue column found (will be calculated from sales_details)")
        
        trans_col = self._find_col(df, "total_transactions")
        if trans_col:
            info["transaction_count_column"] = trans_col
        else:
            warnings.append("No transaction count column found (will be calculated from sales_details)")
        
        is_valid = len(errors) == 0
        return ValidationResult(is_valid, errors, warnings, info)
    
    def validate_sales_by_product(self, df: Optional[pd.DataFrame]) -> ValidationResult:
        """Validate sales_by_product DataFrame."""
        errors = []
        warnings = []
        info = {}
        
        # Handle None DataFrame
        if df is None:
            return ValidationResult(
                is_valid=True,  # Not an error - can be derived from sales_details
                errors=[],
                warnings=["sales_by_product is None - will be derived from sales_details"],
                info={"is_none": True}
            )
        
        product_col = self._find_col(df, "product_id")
        if not product_col:
            errors.append("Missing required column: product_id")
        else:
            info["product_id_column"] = product_col
        
        info["row_count"] = len(df)
        
        if product_col and product_col in df.columns:
            info["unique_products"] = df[product_col].nunique()
            
            # Check for duplicates
            dup_count = df[product_col].duplicated().sum()
            if dup_count > 0:
                warnings.append(f"Duplicate {product_col} found: {dup_count} rows")
        
        qty_col = self._find_col(df, "total_quantity")
        if qty_col:
            info["quantity_column"] = qty_col
        else:
            warnings.append("No quantity column found (will be calculated from sales_details)")
        
        is_valid = len(errors) == 0
        return ValidationResult(is_valid, errors, warnings, info)
    
    def validate_all(self, data: Dict[str, Optional[pd.DataFrame]]) -> ValidationResult:
        """
        Validate all required DataFrames.
        
        Args:
            data: Dictionary with keys 'sales_details', 'sales_by_customer', 'sales_by_product'
            
        Returns:
            Combined ValidationResult
        """
        all_errors = []
        all_warnings = []
        all_info = {}
        
        if self.verbose:
            print("\n" + "="*60)
            print("DATA VALIDATION")
            print("="*60)
        
        # Validate sales_details (REQUIRED)
        sales_details = data.get("sales_details")
        if sales_details is not None:
            result = self.validate_sales_details(sales_details)
            all_errors.extend([f"[sales_details] {e}" for e in result.errors])
            all_warnings.extend([f"[sales_details] {w}" for w in result.warnings])
            all_info["sales_details"] = result.info
            
            if self.verbose:
                status = "OK" if result.is_valid else "FAIL"
                print(f"\n[{status}] sales_details: {result.info.get('row_count', 0):,} rows")
                if result.info.get("date_column"):
                    print(f"      Date column: {result.info['date_column']}")
                if result.info.get("amount_column"):
                    print(f"      Amount column: {result.info['amount_column']}")
                if result.warnings:
                    for w in result.warnings:
                        print(f"      WARN: {w}")
        else:
            all_errors.append("[sales_details] DataFrame not found - THIS IS REQUIRED")
        
        # Validate sales_by_customer (optional - can be derived)
        sales_by_customer = data.get("sales_by_customer")
        result = self.validate_sales_by_customer(sales_by_customer)
        all_warnings.extend([f"[sales_by_customer] {e}" for e in result.errors])
        all_warnings.extend([f"[sales_by_customer] {w}" for w in result.warnings])
        all_info["sales_by_customer"] = result.info
        
        if self.verbose:
            if sales_by_customer is not None:
                status = "OK" if result.is_valid else "WARN"
                print(f"[{status}] sales_by_customer: {result.info.get('row_count', 0):,} rows")
            else:
                print(f"[INFO] sales_by_customer: None (will derive from sales_details)")
        
        # Validate sales_by_product (optional - can be derived)
        sales_by_product = data.get("sales_by_product")
        result = self.validate_sales_by_product(sales_by_product)
        all_warnings.extend([f"[sales_by_product] {e}" for e in result.errors])
        all_warnings.extend([f"[sales_by_product] {w}" for w in result.warnings])
        all_info["sales_by_product"] = result.info
        
        if self.verbose:
            if sales_by_product is not None:
                status = "OK" if result.is_valid else "WARN"
                print(f"[{status}] sales_by_product: {result.info.get('row_count', 0):,} rows")
            else:
                print(f"[INFO] sales_by_product: None (will derive from sales_details)")
        
        is_valid = not any("[sales_details]" in e for e in all_errors)
        
        if self.verbose:
            print("\n" + "-"*60)
            status = "PASSED" if is_valid else "FAILED"
            print(f"Validation {status}: {len(all_errors)} errors, {len(all_warnings)} warnings")
        
        return ValidationResult(is_valid, all_errors, all_warnings, all_info)
    
    def get_data_quality_report(self, data: Dict[str, Optional[pd.DataFrame]]) -> pd.DataFrame:
        """Generate detailed data quality report."""
        reports = []
        
        for name, df in data.items():
            if df is None:
                reports.append({
                    "dataset": name,
                    "column": "(None)",
                    "dtype": "N/A",
                    "non_null": 0,
                    "null_count": 0,
                    "null_pct": 0,
                    "unique": 0,
                    "unique_pct": 0,
                })
                continue
                
            for col in df.columns:
                reports.append({
                    "dataset": name,
                    "column": col,
                    "dtype": str(df[col].dtype),
                    "non_null": df[col].notna().sum(),
                    "null_count": df[col].isna().sum(),
                    "null_pct": df[col].isna().mean() * 100,
                    "unique": df[col].nunique(),
                    "unique_pct": df[col].nunique() / len(df) * 100 if len(df) > 0 else 0,
                })
        
        return pd.DataFrame(reports)


def detect_columns(df: Optional[pd.DataFrame]) -> Dict[str, str]:
    """
    Auto-detect column names for common fields.
    
    Returns:
        Dict mapping standard names to actual column names found
    """
    if df is None:
        return {}
    
    detected = {}
    
    standard_cols = [
        "customer_id", "product_id", "invoice_id",
        "transaction_date", "total_amount", "quantity",
        "total_revenue", "total_transactions", "total_quantity"
    ]
    
    for std_col in standard_cols:
        actual = find_column(df, std_col, COLUMN_ALIASES)
        if actual:
            detected[std_col] = actual
    
    return detected
