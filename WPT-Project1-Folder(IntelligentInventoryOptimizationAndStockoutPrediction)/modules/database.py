"""
Database Module for User Authentication
========================================
Handles PostgreSQL database connection and user management operations.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import sql
import hashlib
import logging
from typing import Optional, Dict, Tuple, List

logger = logging.getLogger(__name__)

# Database Configuration
DATABASE_CONFIG = {
    'engine': 'postgresql',
    'host': 'localhost',
    'port': 5432,
    'username': 'postgres',
    'password': '12345678',
    'database': 'wahana',
}
DATABASE_URI = f"postgresql://postgres:12345678@localhost:5432/wahana"


def get_db_connection():
    """Create and return a database connection."""
    try:
        conn = psycopg2.connect(
            host=DATABASE_CONFIG['host'],
            port=DATABASE_CONFIG['port'],
            user=DATABASE_CONFIG['username'],
            password=DATABASE_CONFIG['password'],
            database=DATABASE_CONFIG['database']
        )
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        return None


def hash_password(password: str) -> str:
    """Hash password using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()


def init_database():
    """Initialize database tables if they don't exist."""
    conn = get_db_connection()
    if conn is None:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'user')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index on username for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)
        """)
        
        # Create data_puller_config table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS data_puller_config (
                id SERIAL PRIMARY KEY,
                project_name VARCHAR(50) NOT NULL CHECK (project_name IN ('project1', 'project2', 'both')),
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                schedule_type VARCHAR(20) DEFAULT 'weekly' CHECK (schedule_type IN ('weekly', 'manual')),
                last_run_at TIMESTAMP,
                next_run_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(50),
                CONSTRAINT valid_date_range CHECK (end_date >= start_date)
            )
        """)
        
        # Create data_puller_executions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS data_puller_executions (
                id SERIAL PRIMARY KEY,
                config_id INTEGER REFERENCES data_puller_config(id) ON DELETE CASCADE,
                project_name VARCHAR(50) NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                status VARCHAR(20) NOT NULL CHECK (status IN ('running', 'completed', 'failed', 'cancelled')),
                records_pulled INTEGER DEFAULT 0,
                execution_time_seconds INTEGER,
                error_message TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                executed_by VARCHAR(50)
            )
        """)
        
        # Create data_ranges table to track pulled date ranges
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS data_ranges (
                id SERIAL PRIMARY KEY,
                project_name VARCHAR(50) NOT NULL,
                table_name VARCHAR(100) NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                records_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                execution_id INTEGER REFERENCES data_puller_executions(id) ON DELETE SET NULL,
                UNIQUE(project_name, table_name, start_date, end_date)
            )
        """)
        
        # Create index for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_data_ranges_project_table ON data_ranges(project_name, table_name)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_data_ranges_dates ON data_ranges(start_date, end_date)
        """)
        
        # Create indexes for better query performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_puller_config_active ON data_puller_config(is_active)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_puller_executions_config ON data_puller_executions(config_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_puller_executions_status ON data_puller_executions(status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_puller_executions_started ON data_puller_executions(started_at DESC)
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info("Database tables initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        if conn:
            conn.rollback()
            conn.close()
        return False


def create_user(username: str, password: str, role: str) -> Tuple[bool, str]:
    """
    Create a new user in the database.
    
    Args:
        username: Username for the new user
        password: Plain text password
        role: User role ('admin' or 'user')
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    if role not in ['admin', 'user']:
        return False, "Invalid role. Must be 'admin' or 'user'"
    
    conn = get_db_connection()
    if conn is None:
        return False, "Database connection failed"
    
    try:
        cursor = conn.cursor()
        
        # Check if username already exists
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return False, "Username already exists"
        
        # Hash password and insert user
        password_hash = hash_password(password)
        cursor.execute("""
            INSERT INTO users (username, password_hash, role)
            VALUES (%s, %s, %s)
        """, (username, password_hash, role))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"User created: {username} with role {role}")
        return True, "User created successfully"
        
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        if conn:
            conn.rollback()
            conn.close()
        return False, f"Error creating user: {str(e)}"


def authenticate_user(username: str, password: str) -> Optional[Dict]:
    """
    Authenticate a user with username and password.
    
    Args:
        username: Username
        password: Plain text password
    
    Returns:
        User dictionary with id, username, and role if authenticated, None otherwise
    """
    conn = get_db_connection()
    if conn is None:
        return None
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        password_hash = hash_password(password)
        cursor.execute("""
            SELECT id, username, role FROM users
            WHERE username = %s AND password_hash = %s
        """, (username, password_hash))
        
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user:
            logger.info(f"User authenticated: {username}")
            return dict(user)
        else:
            logger.warning(f"Authentication failed for: {username}")
            return None
            
    except Exception as e:
        logger.error(f"Error authenticating user: {str(e)}")
        if conn:
            conn.close()
        return None


def get_user_by_username(username: str) -> Optional[Dict]:
    """Get user information by username."""
    conn = get_db_connection()
    if conn is None:
        return None
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT id, username, role, created_at FROM users
            WHERE username = %s
        """, (username,))
        
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user:
            return dict(user)
        return None
        
    except Exception as e:
        logger.error(f"Error getting user: {str(e)}")
        if conn:
            conn.close()
        return None


def init_default_users():
    """Initialize default admin and user accounts."""
    # Create default admin account
    success, msg = create_user('admin1', 'admin1!wahana25', 'admin')
    if success:
        logger.info("Default admin account created: admin1")
    elif "already exists" in msg:
        logger.info("Default admin account already exists")
    else:
        logger.warning(f"Failed to create default admin: {msg}")
    
    # Create default user account
    success, msg = create_user('user1', 'user1!wahana25', 'user')
    if success:
        logger.info("Default user account created: user1")
    elif "already exists" in msg:
        logger.info("Default user account already exists")
    else:
        logger.warning(f"Failed to create default user: {msg}")


def get_puller_config(project_name: str = None) -> Optional[Dict]:
    """Get active puller configuration."""
    conn = get_db_connection()
    if conn is None:
        return None
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        if project_name:
            cursor.execute("""
                SELECT * FROM data_puller_config 
                WHERE is_active = TRUE AND project_name IN (%s, 'both')
                ORDER BY updated_at DESC
                LIMIT 1
            """, (project_name,))
        else:
            cursor.execute("""
                SELECT * FROM data_puller_config 
                WHERE is_active = TRUE
                ORDER BY updated_at DESC
                LIMIT 1
            """)
        
        config = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if config:
            return dict(config)
        return None
        
    except Exception as e:
        logger.error(f"Error getting puller config: {str(e)}")
        if conn:
            conn.close()
        return None


def save_puller_config(
    project_name: str,
    start_date: str,
    end_date: str,
    schedule_type: str = 'weekly',
    created_by: str = None
) -> Tuple[bool, str]:
    """Save or update puller configuration."""
    conn = get_db_connection()
    if conn is None:
        return False, "Database connection failed"
    
    try:
        cursor = conn.cursor()
        
        # Deactivate existing configs for the same project
        cursor.execute("""
            UPDATE data_puller_config 
            SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
            WHERE project_name = %s AND is_active = TRUE
        """, (project_name,))
        
        # Insert new config
        cursor.execute("""
            INSERT INTO data_puller_config 
            (project_name, start_date, end_date, schedule_type, created_by)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (project_name, start_date, end_date, schedule_type, created_by))
        
        config_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Puller config saved: {project_name} ({start_date} to {end_date})")
        return True, f"Configuration saved successfully (ID: {config_id})"
        
    except Exception as e:
        logger.error(f"Error saving puller config: {str(e)}")
        if conn:
            conn.rollback()
            conn.close()
        return False, f"Error saving configuration: {str(e)}"


def create_puller_execution(
    config_id: int,
    project_name: str,
    start_date: str,
    end_date: str,
    executed_by: str = None
) -> Optional[int]:
    """Create a new puller execution record."""
    conn = get_db_connection()
    if conn is None:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO data_puller_executions 
            (config_id, project_name, start_date, end_date, status, executed_by)
            VALUES (%s, %s, %s, %s, 'running', %s)
            RETURNING id
        """, (config_id, project_name, start_date, end_date, executed_by))
        
        execution_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        
        return execution_id
        
    except Exception as e:
        logger.error(f"Error creating execution record: {str(e)}")
        if conn:
            conn.rollback()
            conn.close()
        return None


def update_puller_execution(
    execution_id: int,
    status: str,
    records_pulled: int = 0,
    execution_time: float = None,
    error_message: str = None
) -> bool:
    """Update puller execution status."""
    conn = get_db_connection()
    if conn is None:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE data_puller_executions 
            SET status = %s,
                records_pulled = %s,
                execution_time_seconds = %s,
                error_message = %s,
                completed_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (status, records_pulled, int(execution_time) if execution_time else None, error_message, execution_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"Error updating execution: {str(e)}")
        if conn:
            conn.rollback()
            conn.close()
        return False


def get_puller_execution_history(limit: int = 20) -> List[Dict]:
    """Get puller execution history."""
    conn = get_db_connection()
    if conn is None:
        return []
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT e.*, c.project_name as config_project
            FROM data_puller_executions e
            LEFT JOIN data_puller_config c ON e.config_id = c.id
            ORDER BY e.started_at DESC
            LIMIT %s
        """, (limit,))
        
        executions = [dict(row) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        
        return executions
        
    except Exception as e:
        logger.error(f"Error getting execution history: {str(e)}")
        if conn:
            conn.close()
        return []


# Initialize database on module import
try:
    init_database()
    init_default_users()
except Exception as e:
    logger.warning(f"Database initialization warning: {str(e)}")
