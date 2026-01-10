"""
FQS Application Settings
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    """Application configuration settings"""
    
    # API Configuration
    CLOB_API_URL = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")
    CLOB_API_KEY = os.getenv("CLOB_API_KEY", "")
    CLOB_SECRET = os.getenv("CLOB_SECRET", "")
    CLOB_PASS_PHRASE = os.getenv("CLOB_PASS_PHRASE", "")
    CHAIN_ID = int(os.getenv("CHAIN_ID", "137"))
    PRIVATE_KEY = os.getenv("PRIVATE_KEY", "")
    
    # Flask Configuration
    FLASK_HOST = os.getenv("FLASK_HOST", "127.0.0.1")
    FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"
    
    # WebSocket Configuration
    WS_MARKET_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
    WS_USER_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/user"
    
    # Trading Defaults
    DEFAULT_SIZE = 10
    MAX_POSITION = 1000
    SLIPPAGE = 0.01
    AUTO_SELL = False
    
    # Display Settings
    REFRESH_INTERVAL = 5
    THEME = "dark"
    SHOW_DEBUG = True
    
    # Paths
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / "data"
    LOGS_DIR = BASE_DIR / "logs"
    CONFIG_DIR = BASE_DIR / "config"
    
    @classmethod
    def validate(cls):
        """Validate required settings"""
        required = ["CLOB_API_KEY", "CLOB_SECRET", "CLOB_PASS_PHRASE", "PRIVATE_KEY"]
        missing = [key for key in required if not getattr(cls, key)]
        if missing:
            raise ValueError(f"Missing required settings: {', '.join(missing)}")
        return True
