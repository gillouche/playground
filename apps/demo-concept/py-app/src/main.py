import logging
import sys
import os
import platform
from lib import get_greeting

import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("demo-concept")

def main():
    logger.info("Demo Concept Application Started")
    
    # Log Environment Information
    logger.info(f"Architecture: {platform.machine()}")
    logger.info(f"System: {platform.system()}")
    logger.info(f"Python Version: {sys.version.split()[0]}")
    logger.info(f"Environment: {os.environ}")

    message = get_greeting("User")
    logger.info(f"Greetings: {message}")
    
    logger.info("Entering main loop...")
    while True:
        time.sleep(3600)

if __name__ == "__main__":
    main()
