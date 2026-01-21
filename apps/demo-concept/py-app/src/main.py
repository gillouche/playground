import logging
import sys
from apps.demo_concept.py_app.src.lib import get_greeting

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
    message = get_greeting("User")
    logger.info(f"Greetings: {message}")
    logger.info("Demo Concept Application Finishing...")

if __name__ == "__main__":
    main()
