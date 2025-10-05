"""
Filename: waitress_app.py
Description: This script sets up and runs a Waitress WSGI server
to serve a Flask web application.
"""

from main_app import app
import os
from sys import stdout, path
import logging
from datetime import datetime

# Add current directory to path to ensure imports work
path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Get the absolute path to this script's directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(SCRIPT_DIR, "logs")
# Use waitress_app.log as the base so rotated files are waitress_app.log, waitress_app.log.2025-08-19, etc.
LOG_FILE = os.path.join(LOG_DIR, "waitress_app.log")

# Create logs directory
os.makedirs(LOG_DIR, exist_ok=True)

THREADS = 64

# NOW set up logging AFTER main_app import to override its configuration
try:
    # Get or create the waitress logger
    logger = logging.getLogger('waitress_app')
    logger.setLevel(logging.INFO)
    
    # Clear any existing handlers from this logger
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo

    MOUNTAIN_TZ = ZoneInfo("America/Denver")

    class MountainFormatter(logging.Formatter):
        def formatTime(self, record, datefmt=None):
            dt = datetime.fromtimestamp(record.created, MOUNTAIN_TZ)
            if datefmt:
                return dt.strftime(datefmt)
            return dt.strftime("%Y-%m-%d %H:%M:%S %Z")

    # Use TimedRotatingFileHandler so rotated files are waitress_app.log, waitress_app.log.2025-08-19, etc.
    handler = logging.handlers.TimedRotatingFileHandler(
        LOG_FILE,
        when="midnight",
        interval=1,
        backupCount=14,
        encoding="utf-8"
    )
    handler.suffix = "%Y-%m-%d.log"
    # use MountainFormatter so logs are in Mountain time
    handler.setFormatter(MountainFormatter("%(asctime)s %(levelname)s %(message)s"))
    
    logger.addHandler(handler)
    
    # Prevent this logger from propagating to root logger (which main_app might control)
    logger.propagate = False
    
    # Test logging immediately
    logger.info("=== Waitress app logging reconfigured with rotation ===")
    logger.info(f"Script directory: {SCRIPT_DIR}")
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Log base file (current): {LOG_FILE}")
    logger.info("Flask app imported successfully")
    
    # Force flush
    handler.flush()
    
except Exception as e:
    print(f"Logging setup failed: {e}")


def main():
    port = int(os.environ.get("HTTP_PLATFORM_PORT", 8080))
    host = "127.0.0.1"

    try:
        logger.info(f"Starting Waitress server on {host}:{port}")
    except:
        pass

    try:
        from waitress import serve
        serve(
            app,
            host=host,
            port=port,
            threads=THREADS,
            connection_limit=1000,
        )
    except Exception as e:
        try:
            logger.error(f"Failed to start Waitress: {e}")
        except:
            print(f"Failed to start Waitress: {e}")
        exit(1)


if __name__ == "__main__":
    try:
        logger.info("Running as main script")
    except:
        pass
    main()
else:
    try:
        logger.info("Module imported by IIS")
    except:
        pass
