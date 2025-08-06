#!/usr/bin/env python3
"""
Test script to verify that logging is working correctly and outputting to file.
"""

import sys
import os

# Add the parent directory to the path to import the module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from temporal_explorator.utils.logger import logger, purcl_logger_adapter

def test_logging():
    """Test that logging outputs to file instead of console."""
    print("Testing logging configuration...")
    print("Logs should be written to tests/log/test_log.log")
    
    # Test root logger
    logger.info("This is a test message from root logger")
    logger.warning("This is a warning message from root logger")
    logger.error("This is an error message from root logger")
    
    # Test purcl logger
    purcl_logger_adapter.info("This is a test message from purcl logger")
    purcl_logger_adapter.warning("This is a warning message from purcl logger")
    purcl_logger_adapter.error("This is an error message from purcl logger")
    
    print("Logging test completed. Check tests/log/test_log.log for output.")

if __name__ == "__main__":
    test_logging() 