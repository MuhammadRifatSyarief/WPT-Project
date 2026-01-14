"""
Data Puller Scheduler Module
============================
Handles automatic weekly execution of data pullers based on configuration.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
from modules.database import (
    get_puller_config,
    get_db_connection
)
from modules.data_puller_service import get_puller_service
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


def should_run_puller(config: Dict) -> bool:
    """
    Check if puller should run based on schedule.
    
    Args:
        config: Puller configuration from database
    
    Returns:
        True if puller should run, False otherwise
    """
    if not config.get('is_active', False):
        return False
    
    if config.get('schedule_type') != 'weekly':
        return False
    
    last_run = config.get('last_run_at')
    next_run = config.get('next_run_at')
    
    # If never run, schedule for next week
    if not last_run:
        return False
    
    # Check if it's time to run
    if next_run:
        next_run_dt = datetime.fromisoformat(str(next_run).replace('Z', '+00:00'))
        if datetime.now() >= next_run_dt.replace(tzinfo=None):
            return True
    
    return False


def calculate_next_run(last_run: datetime) -> datetime:
    """Calculate next run time (1 week from last run)"""
    return last_run + timedelta(weeks=1)


def update_config_next_run(config_id: int, next_run: datetime):
    """Update next_run_at in configuration"""
    conn = get_db_connection()
    if conn is None:
        return
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE data_puller_config
            SET next_run_at = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (next_run, config_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"Error updating next run: {str(e)}")
        if conn:
            conn.rollback()
            conn.close()


def update_config_last_run(config_id: int):
    """Update last_run_at in configuration"""
    conn = get_db_connection()
    if conn is None:
        return
    
    try:
        cursor = conn.cursor()
        next_run = datetime.now() + timedelta(weeks=1)
        
        cursor.execute("""
            UPDATE data_puller_config
            SET last_run_at = CURRENT_TIMESTAMP,
                next_run_at = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (next_run, config_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"Error updating last run: {str(e)}")
        if conn:
            conn.rollback()
            conn.close()


def check_and_run_scheduled_pullers():
    """
    Check all active weekly puller configurations and run if needed.
    This should be called periodically (e.g., on app startup or page load).
    """
    try:
        # Get all active weekly configurations
        conn = get_db_connection()
        if conn is None:
            return
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT * FROM data_puller_config
            WHERE is_active = TRUE AND schedule_type = 'weekly'
            ORDER BY updated_at DESC
        """)
        
        configs = [dict(row) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        
        if not configs:
            return
        
        service = get_puller_service()
        
        for config in configs:
            if should_run_puller(config):
                logger.info(f"Running scheduled puller for {config['project_name']}")
                
                try:
                    # Run the puller
                    if config['project_name'] == 'project1':
                        success, message, exec_id = service.run_project1_puller(
                            config['start_date'].strftime('%Y-%m-%d'),
                            config['end_date'].strftime('%Y-%m-%d'),
                            config['id'],
                            'system'
                        )
                    elif config['project_name'] == 'project2':
                        success, message, exec_id = service.run_project2_puller(
                            config['start_date'].strftime('%Y-%m-%d'),
                            config['end_date'].strftime('%Y-%m-%d'),
                            config['id'],
                            'system'
                        )
                    else:  # both
                        success, message, exec_ids = service.run_both_pullers(
                            config['start_date'].strftime('%Y-%m-%d'),
                            config['end_date'].strftime('%Y-%m-%d'),
                            config['id'],
                            'system'
                        )
                    
                    if success:
                        # Update last run time
                        update_config_last_run(config['id'])
                        logger.info(f"Scheduled puller completed successfully: {config['project_name']}")
                    else:
                        logger.error(f"Scheduled puller failed: {config['project_name']} - {message}")
                        
                except Exception as e:
                    logger.error(f"Error running scheduled puller {config['project_name']}: {str(e)}")
                    continue
        
    except Exception as e:
        logger.error(f"Error checking scheduled pullers: {str(e)}")


def initialize_scheduler():
    """
    Initialize scheduler - set next_run_at for configurations that don't have it.
    This should be called on app startup.
    """
    try:
        conn = get_db_connection()
        if conn is None:
            return
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT * FROM data_puller_config
            WHERE is_active = TRUE 
            AND schedule_type = 'weekly'
            AND (next_run_at IS NULL OR last_run_at IS NULL)
        """)
        
        configs = [dict(row) for row in cursor.fetchall()]
        cursor.close()
        
        for config in configs:
            # Set initial next_run_at to 1 week from now if never run
            if not config.get('last_run_at'):
                next_run = datetime.now() + timedelta(weeks=1)
                update_config_next_run(config['id'], next_run)
                logger.info(f"Initialized scheduler for {config['project_name']}: next run in 1 week")
            # Or calculate from last_run if exists
            elif not config.get('next_run_at') and config.get('last_run_at'):
                last_run = config['last_run_at']
                if isinstance(last_run, str):
                    last_run = datetime.fromisoformat(last_run.replace('Z', '+00:00'))
                next_run = calculate_next_run(last_run.replace(tzinfo=None) if hasattr(last_run, 'tzinfo') else last_run)
                update_config_next_run(config['id'], next_run)
                logger.info(f"Updated scheduler for {config['project_name']}: next run calculated")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Error initializing scheduler: {str(e)}")
