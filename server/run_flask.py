"""
FQS Flask Server - Entry Point
Provides REST API for football trading terminal
"""
import sys
import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Add project root to path so we can import modules
# run_flask.py is at: fqs/server/run_flask.py
# We are already inside the fqs directory, so just import from server
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from server import create_app

# Setup logging to file
logs_dir = Path(os.path.dirname(__file__)).parent / "logs"
logs_dir.mkdir(exist_ok=True)

log_file = logs_dir / "flask.log"

# Configure file handler
file_handler = RotatingFileHandler(
    log_file,
    maxBytes=10 * 1024 * 1024,  # 10 MB
    backupCount=5
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))

# Configure console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
))

# Setup root logger
logging.basicConfig(
    level=logging.DEBUG,
    handlers=[file_handler, console_handler]
)

logger = logging.getLogger(__name__)

app = create_app()

if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("🚀 FQS FLASK SERVER - Football Trading API")
    logger.info("=" * 80)
    logger.info("📊 Endpoints:")
    logger.info("   POST /api/order/buy         - Place buy order")
    logger.info("   POST /api/order/sell        - Place sell order")
    logger.info("   GET  /api/balance           - Get wallet balance")
    logger.info("   GET  /api/markets/football  - Get active football markets")
    logger.info("   GET  /api/market/<slug>     - Get market details and token IDs")
    logger.info("   GET  /api/markets/football/live - Get cached live football matches")
    logger.info("")
    logger.info("🔧 Server starting on http://127.0.0.1:5000")
    logger.info(f"📝 Logs being written to: {log_file}")
    logger.info("=" * 80)
    logger.info("")
    
    # Run Flask development server
    app.run(host="127.0.0.1", port=5000, debug=True)
