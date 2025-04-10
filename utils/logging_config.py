import logging

def setup_logging():
    """
    Configure logging for the application.
    Sets up basic logging format and suppresses low-level HTTP logs.
    """
    # Configure logging
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    # Suppress low-level HTTP logs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)