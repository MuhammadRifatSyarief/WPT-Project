"""
Data Validation Module
======================
Validasi untuk mencegah duplikasi data berdasarkan rentang tanggal.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
from modules.database import get_db_connection
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


def get_existing_date_ranges(project_name: str, table_name: str) -> List[Tuple[date, date]]:
    """
    Get existing date ranges from database for a specific table.
    
    Args:
        project_name: 'project1' or 'project2'
        table_name: Name of the table to check
    
    Returns:
        List of (start_date, end_date) tuples
    """
    conn = get_db_connection()
    if conn is None:
        return []
    
    try:
        cursor = conn.cursor()
        full_table_name = f"{project_name}_{table_name}".lower().replace(' ', '_').replace('-', '_')
        
        # Check if table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = %s
            )
        """, (full_table_name,))
        
        if not cursor.fetchone()[0]:
            cursor.close()
            conn.close()
            return []
        
        # Try to find date columns (common names)
        date_columns = []
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = %s 
            AND (column_name LIKE '%date%' OR column_name LIKE '%transdate%' OR column_name LIKE '%transaction_date%')
        """, (full_table_name,))
        
        date_columns = [row[0] for row in cursor.fetchall()]
        
        if not date_columns:
            cursor.close()
            conn.close()
            return []
        
        # Get min and max dates for each date column
        date_ranges = []
        for col in date_columns:
            try:
                cursor.execute(f"""
                    SELECT MIN({col}) as min_date, MAX({col}) as max_date
                    FROM {full_table_name}
                    WHERE {col} IS NOT NULL
                """)
                result = cursor.fetchone()
                if result and len(result) >= 2 and result[0] is not None and result[1] is not None:
                    min_date = result[0]
                    max_date = result[1]
                    if isinstance(min_date, str):
                        min_date = datetime.strptime(min_date, '%Y-%m-%d').date()
                    if isinstance(max_date, str):
                        max_date = datetime.strptime(max_date, '%Y-%m-%d').date()
                    date_ranges.append((min_date, max_date))
            except Exception as e:
                logger.warning(f"Error getting date range from {col}: {str(e)}")
                continue
        
        cursor.close()
        conn.close()
        
        return date_ranges
        
    except Exception as e:
        logger.error(f"Error getting existing date ranges: {str(e)}")
        if conn:
            conn.close()
        return []


def check_date_range_overlap(
    new_start: date,
    new_end: date,
    existing_ranges: List[Tuple[date, date]]
) -> bool:
    """
    Check if new date range overlaps with any existing ranges.
    
    Args:
        new_start: Start date of new data
        new_end: End date of new data
        existing_ranges: List of (start, end) tuples
    
    Returns:
        True if overlap exists, False otherwise
    """
    for existing_start, existing_end in existing_ranges:
        # Check for overlap: new range overlaps if it starts before existing ends
        # and ends after existing starts
        if new_start <= existing_end and new_end >= existing_start:
            return True
    return False


def find_next_available_range(
    requested_start: date,
    requested_end: date,
    existing_ranges: List[Tuple[date, date]]
) -> Optional[Tuple[date, date]]:
    """
    Find next available date range that doesn't overlap with existing data.
    
    Args:
        requested_start: Requested start date
        requested_end: Requested end date
        existing_ranges: List of existing (start, end) tuples
    
    Returns:
        (start, end) tuple of next available range, or None if should skip
    """
    if not existing_ranges:
        return (requested_start, requested_end)
    
    # Sort existing ranges by start date
    sorted_ranges = sorted(existing_ranges, key=lambda x: x[0])
    
    # Find gaps between existing ranges
    for i in range(len(sorted_ranges) - 1):
        current_end = sorted_ranges[i][1]
        next_start = sorted_ranges[i + 1][0]
        
        # Check if requested range fits in this gap
        gap_start = max(requested_start, current_end + timedelta(days=1))
        gap_end = min(requested_end, next_start - timedelta(days=1))
        
        if gap_start <= gap_end:
            # Requested range can fit in this gap
            return (gap_start, min(gap_end, requested_end))
    
    # Check if requested range is after all existing ranges
    last_end = sorted_ranges[-1][1]
    if requested_start > last_end:
        return (requested_start, requested_end)
    
    # Check if requested range is before all existing ranges
    first_start = sorted_ranges[0][0]
    if requested_end < first_start:
        return (requested_start, requested_end)
    
    # No available range found
    return None


def validate_and_adjust_date_range(
    project_name: str,
    table_name: str,
    requested_start: date,
    requested_end: date,
    strategy: str = 'skip'
) -> Tuple[bool, Optional[date], Optional[date], str]:
    """
    Validate date range and adjust if needed to prevent duplicates.
    
    Args:
        project_name: 'project1' or 'project2'
        table_name: Table name to check
        requested_start: Requested start date
        requested_end: Requested end date
        strategy: 'skip' (skip if overlap) or 'delete' (delete overlapping data)
    
    Returns:
        (should_proceed, adjusted_start, adjusted_end, message)
    """
    existing_ranges = get_existing_date_ranges(project_name, table_name)
    
    if not existing_ranges:
        return (True, requested_start, requested_end, "No existing data found. Proceeding with requested range.")
    
    # Check for overlap
    has_overlap = check_date_range_overlap(requested_start, requested_end, existing_ranges)
    
    if not has_overlap:
        return (True, requested_start, requested_end, "No overlap detected. Proceeding with requested range.")
    
    # Handle overlap based on strategy
    if strategy == 'delete':
        # Delete overlapping data
        return (True, requested_start, requested_end, 
                f"Overlap detected. Will delete overlapping data in range {requested_start} to {requested_end}.")
    
    elif strategy == 'skip':
        # Find next available range
        next_range = find_next_available_range(requested_start, requested_end, existing_ranges)
        
        if next_range:
            return (True, next_range[0], next_range[1], 
                    f"Overlap detected. Adjusted range to {next_range[0]} to {next_range[1]}.")
        else:
            return (False, None, None, 
                    f"Overlap detected and no available range found. Requested range {requested_start} to {requested_end} overlaps with existing data.")
    
    return (False, None, None, f"Unknown strategy: {strategy}")


def delete_overlapping_data(
    project_name: str,
    table_name: str,
    start_date: date,
    end_date: date
) -> int:
    """
    Delete data in the specified date range from database.
    
    Args:
        project_name: 'project1' or 'project2'
        table_name: Table name
        start_date: Start date of range to delete
        end_date: End date of range to delete
    
    Returns:
        Number of rows deleted
    """
    conn = get_db_connection()
    if conn is None:
        return 0
    
    try:
        cursor = conn.cursor()
        full_table_name = f"{project_name}_{table_name}".lower().replace(' ', '_').replace('-', '_')
        
        # Find date columns
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = %s 
            AND (column_name LIKE '%date%' OR column_name LIKE '%transdate%' OR column_name LIKE '%transaction_date%')
        """, (full_table_name,))
        
        date_columns = [row[0] for row in cursor.fetchall()]
        
        if not date_columns:
            cursor.close()
            conn.close()
            return 0
        
        # Delete rows where date is in the range
        deleted_count = 0
        for col in date_columns:
            try:
                cursor.execute(f"""
                    DELETE FROM {full_table_name}
                    WHERE {col} >= %s AND {col} <= %s
                """, (start_date, end_date))
                deleted_count += cursor.rowcount
            except Exception as e:
                logger.warning(f"Error deleting from {col}: {str(e)}")
                continue
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Deleted {deleted_count} rows from {full_table_name} in range {start_date} to {end_date}")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Error deleting overlapping data: {str(e)}")
        if conn:
            conn.rollback()
            conn.close()
        return 0
