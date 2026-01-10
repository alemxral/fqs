"""
FQS API Routes
Handles trading operations and market data endpoints
"""
import os
import sys
from pathlib import Path
from flask import Blueprint, jsonify, request
from datetime import datetime
from decimal import Decimal

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

# Load environment variables
load_dotenv(PROJECT_ROOT / "config" / ".env")

# Import clients
try:
    from fqs.client.clob_client import PolymarketClobClient
    from fqs.client.gamma_client import PolymarketGammaClient
except ImportError:
    # Fallback if client modules not available
    PolymarketClobClient = None
    PolymarketGammaClient = None

# Create Blueprint
api_bp = Blueprint('api', __name__)

# Initialize clients (will use py-clob-client wrapper)
try:
    from fqs.client.ClobClientWrapper import create_clob_client
    clob_client = create_clob_client()
    gamma_client = PolymarketGammaClient()
except Exception as e:
    print(f"Warning: Could not initialize clients: {e}")
    clob_client = None
    gamma_client = None
CHAIN_ID = int(os.getenv("CHAIN_ID", "137"))

# Global client instances (initialized on first request)
_clob_client = None
_gamma_client = None


def get_clob_client():
    """Get or create CLOB client instance"""
    global _clob_client
    if _clob_client is None:
        _clob_client = ClobClient(CLOB_URL, chain_id=CHAIN_ID)
    return _clob_client


def get_gamma_client():
    """Get or create Gamma API client instance"""
    global _gamma_client
    if _gamma_client is None:
        _gamma_client = GammaAPIClient()
    return _gamma_client


# ============= TRADING ENDPOINTS =============

@api_bp.route('/order/buy', methods=['POST'])
def buy_order():
    """
    Place a buy order
    
    Request body:
        {
            "token_id": "string",
            "price": "0.65",
            "size": 100
        }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body required'
            }), 400
        
        token_id = data.get('token_id')
        price = data.get('price')
        size = data.get('size')
        
        if not all([token_id, price, size]):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: token_id, price, size'
            }), 400
        
        # Convert to appropriate types
        price = float(price)
        size = int(size)
        
        # Place order using CLOB client
        client = get_clob_client()
        result = client.create_order(
            token_id=token_id,
            price=price,
            size=size,
            side="BUY"
        )
        
        return jsonify({
            'success': True,
            'order': result,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/order/sell', methods=['POST'])
def sell_order():
    """
    Place a sell order
    
    Request body:
        {
            "token_id": "string",
            "price": "0.35",
            "size": 50
        }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body required'
            }), 400
        
        token_id = data.get('token_id')
        price = data.get('price')
        size = data.get('size')
        
        if not all([token_id, price, size]):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: token_id, price, size'
            }), 400
        
        # Convert to appropriate types
        price = float(price)
        size = int(size)
        
        # Place order using CLOB client
        client = get_clob_client()
        result = client.create_order(
            token_id=token_id,
            price=price,
            size=size,
            side="SELL"
        )
        
        return jsonify({
            'success': True,
            'order': result,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/balance', methods=['GET'])
def get_balance():
    """
    Get wallet USDC balance
    
    Returns:
        {
            "success": true,
            "balance": 1234.56,
            "currency": "USDC"
        }
    """
    try:
        client = get_clob_client()
        
        # Get balance from CLOB client
        balance_data = client.get_balance_allowance()
        
        # Extract USDC balance
        usdc_balance = float(balance_data.get('balance', 0))
        
        return jsonify({
            'success': True,
            'balance': usdc_balance,
            'currency': 'USDC',
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'balance': 0
        }), 500


# ============= MARKET DATA ENDPOINTS =============

@api_bp.route('/markets/football', methods=['GET'])
def get_football_markets():
    """
    Get active football markets
    
    Returns list of football/soccer events with market data
    """
    try:
        client = get_gamma_client()
        
        # Search for football/soccer markets
        # You can customize this query based on your needs
        football_keywords = ['football', 'soccer', 'premier league', 'la liga', 'serie a', 
                           'bundesliga', 'champions league', 'uefa', 'world cup']
        
        all_markets = []
        
        # For now, get recent active markets and filter
        # In production, you'd want more sophisticated filtering
        try:
            # This is a placeholder - adjust based on actual gamma_client API
            markets = client.get_markets(limit=100, active=True)
            
            # Filter for football-related markets
            for market in markets:
                question = market.get('question', '').lower()
                if any(keyword in question for keyword in football_keywords):
                    all_markets.append({
                        'slug': market.get('slug'),
                        'question': market.get('question'),
                        'end_date': market.get('end_date_iso'),
                        'yes_price': market.get('outcome_prices', [0.5, 0.5])[0],
                        'no_price': market.get('outcome_prices', [0.5, 0.5])[1],
                        'volume': market.get('volume', 0),
                        'liquidity': market.get('liquidity', 0)
                    })
        except:
            # Fallback: return empty list or mock data for testing
            pass
        
        return jsonify({
            'success': True,
            'markets': all_markets,
            'count': len(all_markets),
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'markets': []
        }), 500


@api_bp.route('/market/<slug>', methods=['GET'])
def get_market_details(slug):
    """
    Get market details including token IDs
    
    Args:
        slug: Market slug (e.g., "epl-tot-ast-2025-10-19")
    
    Returns:
        {
            "success": true,
            "market": {
                "slug": "...",
                "question": "...",
                "tokens": {
                    "yes": "token_id",
                    "no": "token_id"
                }
            }
        }
    """
    try:
        client = get_gamma_client()
        
        # Get market data by slug
        market_data = client.get_market(slug)
        
        if not market_data:
            return jsonify({
                'success': False,
                'error': f'Market not found: {slug}'
            }), 404
        
        # Extract token IDs
        tokens = market_data.get('tokens', [])
        yes_token = None
        no_token = None
        
        for token in tokens:
            outcome = token.get('outcome', '').upper()
            if outcome == 'YES':
                yes_token = token.get('token_id')
            elif outcome == 'NO':
                no_token = token.get('token_id')
        
        return jsonify({
            'success': True,
            'market': {
                'slug': market_data.get('slug'),
                'question': market_data.get('question'),
                'end_date': market_data.get('end_date_iso'),
                'tokens': {
                    'yes': yes_token,
                    'no': no_token
                },
                'prices': {
                    'yes': market_data.get('outcome_prices', [0.5, 0.5])[0],
                    'no': market_data.get('outcome_prices', [0.5, 0.5])[1]
                }
            },
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============= HEALTH CHECK =============

@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'fqs-api',
        'timestamp': datetime.utcnow().isoformat()
    })


def create_app():
    """Create and configure Flask application (factory pattern)"""
    from flask import Flask
    from flask_cors import CORS
    
    app = Flask(__name__)
    CORS(app)
    
    # Register blueprints
    app.register_blueprint(api_bp, url_prefix='/api')
    
    return app
