"""
Data Schema Definition

Mendefinisikan schema dan kolom yang diperlukan untuk feature engineering.
Sesuai dengan output dari data preparation pipeline.

Author: v0
Version: 1.2 - Added None handling in find_column
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import pandas as pd


@dataclass
class SheetSchema:
    """Schema untuk satu sheet Excel."""
    
    name: str
    required_columns: List[str]
    optional_columns: List[str] = field(default_factory=list)
    date_columns: List[str] = field(default_factory=list)
    numeric_columns: List[str] = field(default_factory=list)
    description: str = ""
    column_aliases: Dict[str, List[str]] = field(default_factory=dict)


COLUMN_ALIASES = {
    # Date columns
    "trans_date": ["transaction_date", "trans_date", "date", "invoice_date", "order_date"],
    "transaction_date": ["trans_date", "transaction_date", "date", "invoice_date"],
    
    # Revenue/Amount columns  
    "total_revenue": ["total_revenue", "total_amount", "revenue", "amount", "total_sales", "sales_amount"],
    "total_amount": ["total_amount", "total_revenue", "amount", "revenue", "line_total"],
    
    # Transaction columns
    "total_transactions": ["total_transactions", "transaction_count", "order_count", "num_transactions", "invoice_count"],
    "transaction_count": ["transaction_count", "total_transactions", "num_transactions", "order_count"],
    
    # Quantity columns
    "total_quantity": ["total_quantity", "quantity", "qty", "total_qty", "sum_quantity"],
    "quantity": ["quantity", "qty", "total_quantity", "total_qty"],
    
    # Customer columns
    "customer_id": ["customer_id", "customerId", "cust_id", "id"],
    "customer_name": ["customer_name", "customerName", "name", "cust_name"],
    
    # Product columns
    "product_id": ["product_id", "productId", "item_id", "itemId", "id"],
    "product_name": ["product_name", "productName", "item_name", "itemName", "name"],
    "product_code": ["product_code", "productCode", "item_code", "itemCode", "itemNo"],
}


def find_column(df: Optional[pd.DataFrame], expected_col: str, aliases: Dict[str, List[str]] = None) -> Optional[str]:
    """
    Find the actual column name in dataframe, checking aliases.
    
    Parameters
    ----------
    df : pd.DataFrame or None
        DataFrame to search (can be None)
    expected_col : str
        Expected column name
    aliases : Dict[str, List[str]], optional
        Column aliases dictionary
    
    Returns
    -------
    str or None
        Actual column name found, or None if not found or df is None
    """
    # Handle None DataFrame
    if df is None:
        return None
    
    # Handle empty DataFrame
    if not hasattr(df, 'columns') or len(df.columns) == 0:
        return None
    
    aliases = aliases or COLUMN_ALIASES
    
    # Direct match
    if expected_col in df.columns:
        return expected_col
    
    # Check aliases
    possible_names = aliases.get(expected_col, [])
    for alias in possible_names:
        if alias in df.columns:
            return alias
    
    # Case-insensitive search
    expected_lower = expected_col.lower()
    for col in df.columns:
        if col.lower() == expected_lower:
            return col
        # Also check aliases case-insensitive
        for alias in possible_names:
            if col.lower() == alias.lower():
                return col
    
    return None


def get_column_mapping(df: Optional[pd.DataFrame], required_columns: List[str]) -> Dict[str, str]:
    """
    Get mapping from expected column names to actual column names.
    
    Returns
    -------
    Dict[str, str]
        {expected_name: actual_name}
    """
    if df is None:
        return {}
    
    mapping = {}
    for expected in required_columns:
        actual = find_column(df, expected)
        if actual:
            mapping[expected] = actual
    return mapping


SHEET_SCHEMAS = {
    # Sheet 1: RFM Analysis (hasil RFM dari data prep)
    "1_RFM_Analysis": SheetSchema(
        name="1_RFM_Analysis",
        required_columns=[
            "customer_id",  # customer_id harus ada
            "recency", "frequency", "monetary",
        ],
        optional_columns=[
            "customer_name", 
            "r_score", "f_score", "m_score", "rfm_score",
            "segment", "rfm_segment", "customer_category",
            "last_purchase_date"
        ],
        date_columns=["last_purchase_date"],
        numeric_columns=["recency", "frequency", "monetary", "r_score", "f_score", "m_score"],
        description="RFM scores dan segmentasi customer"
    ),
    
    # Sheet 2: Customer Segments Summary
    "2_Customer_Segments": SheetSchema(
        name="2_Customer_Segments",
        required_columns=["segment"],  # Only segment is required
        optional_columns=["customer_count", "avg_monetary", "avg_frequency", "avg_recency", "total_revenue", "pct_customers"],
        numeric_columns=["customer_count", "avg_monetary", "avg_frequency", "avg_recency"],
        description="Ringkasan metrik per segment"
    ),
    
    # Sheet 3: Market Basket (Association Rules)
    "3_Market_Basket": SheetSchema(
        name="3_Market_Basket",
        required_columns=["antecedents", "consequents", "support", "confidence", "lift"],
        optional_columns=["conviction", "leverage", "antecedent_support", "consequent_support"],
        numeric_columns=["support", "confidence", "lift"],
        description="Association rules dari market basket analysis"
    ),
    
    # Sheet 4: Product Associations (Frequent Itemsets)
    "4_Product_Associations": SheetSchema(
        name="4_Product_Associations",
        required_columns=["itemsets", "support"],
        optional_columns=["count", "length"],
        numeric_columns=["support", "count"],
        description="Frequent itemsets (product combinations)"
    ),
    
    # Sheet 5: Sales Details (Transaction Level) - MOST IMPORTANT
    "5_Sales_Details": SheetSchema(
        name="5_Sales_Details",
        required_columns=[
            "invoice_id", "customer_id", "product_id",
            "quantity", "unit_price"
        ],
        optional_columns=[
            "total_amount", "transaction_date", "trans_date", "invoice_date",
            "invoice_number", "customer_name", "product_code", "product_name",
            "category_id", "category_name", "discount", "tax"
        ],
        date_columns=["transaction_date", "trans_date", "invoice_date"],
        numeric_columns=["quantity", "unit_price", "total_amount", "discount", "tax"],
        description="Detail transaksi per line item"
    ),
    
    # Sheet 6: Sales By Customer (Aggregated)
    "6_Sales_By_Customer": SheetSchema(
        name="6_Sales_By_Customer",
        required_columns=["customer_id"],  # Relaxed - only ID required
        optional_columns=[
            "customer_name",
            "total_transactions", "transaction_count", "order_count",  # Aliases
            "total_quantity", "quantity",
            "total_revenue", "total_amount", "revenue",  # Aliases
            "first_purchase_date", "last_purchase_date", 
            "avg_transaction_value", "unique_products", "customer_category"
        ],
        date_columns=["first_purchase_date", "last_purchase_date"],
        numeric_columns=["total_transactions", "total_quantity", "total_revenue", "avg_transaction_value"],
        description="Agregasi penjualan per customer"
    ),
    
    # Sheet 7: Sales By Product (Aggregated)
    "7_Sales_By_Product": SheetSchema(
        name="7_Sales_By_Product",
        required_columns=["product_id"],  # Relaxed - only ID required
        optional_columns=[
            "product_code", "product_name", "item_code", "item_name",
            "total_quantity", "quantity",
            "total_revenue", "total_amount", "revenue",
            "category_id", "category_name", "unique_customers",
            "avg_unit_price", "transaction_count"
        ],
        numeric_columns=["total_quantity", "total_revenue", "unique_customers", "avg_unit_price"],
        description="Agregasi penjualan per produk"
    ),
    
    # Sheet 8: Customer Master
    "8_Customer_Master": SheetSchema(
        name="8_Customer_Master",
        required_columns=["id"],  # Only ID required
        optional_columns=[
            "name", "customerNo", "categoryId", "categoryName",
            "address", "city", "phone", "email"
        ],
        description="Master data customer"
    ),
    
    # Sheet 9: Item Master
    "9_Item_Master": SheetSchema(
        name="9_Item_Master",
        required_columns=["id"],  # Only ID required
        optional_columns=[
            "itemNo", "name", "itemCategoryId", "itemCategoryName",
            "unitPrice", "unit", "description"
        ],
        numeric_columns=["unitPrice"],
        description="Master data item/produk"
    ),
    
    # Sheet 10: Summary Stats
    "10_Summary_Stats": SheetSchema(
        name="10_Summary_Stats",
        required_columns=["metric", "value"],
        optional_columns=["category", "description"],
        description="Statistik ringkasan pipeline"
    ),
}


REQUIRED_COLUMNS = {
    "rfm_analysis": ["customer_id", "recency", "frequency", "monetary"],
    "customer_features": ["customer_id"],  # Relaxed
    "product_features": ["product_id"],  # Relaxed
    "basket_analysis": ["invoice_id", "customer_id", "product_id", "quantity"],
}


@dataclass
class DataSchema:
    """
    Master data schema untuk feature engineering.
    
    Attributes:
        sheets: Dictionary of sheet schemas
        required_sheets: List of sheets that must exist
        optional_sheets: List of sheets that are nice to have
    """
    
    sheets: Dict[str, SheetSchema] = field(default_factory=lambda: SHEET_SCHEMAS)
    column_aliases: Dict[str, List[str]] = field(default_factory=lambda: COLUMN_ALIASES)
    
    required_sheets: List[str] = field(default_factory=lambda: [
        "5_Sales_Details",      # Transaction data - PALING PENTING
    ])
    
    optional_sheets: List[str] = field(default_factory=lambda: [
        "1_RFM_Analysis",       # Bisa di-recalculate
        "2_Customer_Segments",  # Summary saja
        "3_Market_Basket",      # Bisa di-recalculate
        "4_Product_Associations",
        "6_Sales_By_Customer",  # Can be aggregated from sales_details
        "7_Sales_By_Product",   # Can be aggregated from sales_details
        "8_Customer_Master",
        "9_Item_Master",
        "10_Summary_Stats",
    ])
    
    def get_sheet_schema(self, sheet_name: str) -> Optional[SheetSchema]:
        """Get schema for a specific sheet."""
        return self.sheets.get(sheet_name)
    
    def find_column(self, df: Optional[pd.DataFrame], expected_col: str) -> Optional[str]:
        """Find actual column name using aliases."""
        return find_column(df, expected_col, self.column_aliases)
    
    def get_column_mapping(self, df: Optional[pd.DataFrame], required_columns: List[str]) -> Dict[str, str]:
        """Get mapping from expected to actual column names."""
        return get_column_mapping(df, required_columns)
    
    def validate_columns(self, sheet_name: str, columns: List[str], df: Optional[pd.DataFrame] = None) -> Dict:
        """
        Validate columns against schema.
        
        Returns:
            Dict with 'valid', 'missing_required', 'extra_columns'
        """
        schema = self.get_sheet_schema(sheet_name)
        if schema is None:
            return {"valid": True, "warning": f"No schema defined for: {sheet_name}"}
        
        columns_set = set(columns)
        required_set = set(schema.required_columns)
        optional_set = set(schema.optional_columns)
        
        missing_required = []
        for req_col in required_set:
            if req_col not in columns_set:
                # Check if any alias exists
                if df is not None:
                    actual = find_column(df, req_col, self.column_aliases)
                    if actual is None:
                        missing_required.append(req_col)
                else:
                    # Check aliases in column list
                    aliases = self.column_aliases.get(req_col, [])
                    if not any(alias in columns_set for alias in aliases):
                        missing_required.append(req_col)
        
        extra_columns = columns_set - required_set - optional_set
        
        return {
            "valid": len(missing_required) == 0,
            "missing_required": missing_required,
            "extra_columns": list(extra_columns),
            "found_optional": list(optional_set & columns_set),
        }
