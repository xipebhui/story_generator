#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_manager
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_query():
    config_id = "config_20250903162833_fd02a053"
    
    logger.info("Testing database query...")
    
    db = get_db_manager()
    logger.info(f"Database manager: {db}")
    logger.info(f"Database URL: {db.db_url}")
    
    with db.get_session() as session:
        logger.info(f"Session: {session}")
        
        # Test 1: Direct query
        result1 = session.execute(text("""
            SELECT config_id FROM publish_configs WHERE config_id = :config_id
        """), {"config_id": config_id}).fetchone()
        
        logger.info(f"Query result: {result1}")
        logger.info(f"Found: {result1 is not None}")
        
        # Test 2: List all configs
        all_configs = session.execute(text("SELECT config_id FROM publish_configs")).fetchall()
        logger.info(f"All configs: {all_configs}")

if __name__ == "__main__":
    test_query()