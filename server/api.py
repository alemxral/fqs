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
    from client.clob_client import PolymarketClobClient
    from client.gamma_client import PolymarketGammaClient
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import ApiCreds
except ImportError:
    # Fallback if client modules not available
    PolymarketClobClient = None
    PolymarketGammaClient = None
    ClobClient = None

# Create Blueprint
api_bp = Blueprint('api', __name__)

# Configuration
CHAIN_ID = int(os.getenv("CHAIN_ID", "137"))
CLOB_URL = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")

# Initialize clients (will use py-clob-client wrapper)
clob_client = None
gamma_client = None

try:
    from client.ClobClientWrapper import get_authenticated_client
    print("🔧 Initializing CLOB client...")
    clob_client = get_authenticated_client()
    if clob_client:
        print("✅ CLOB client initialized successfully")
    else:
        print("❌ get_authenticated_client() returned None")
except Exception as e:
    print(f"❌ Could not initialize CLOB client: {e}")
    import traceback
    traceback.print_exc()

try:
    if PolymarketGammaClient:
        print("🔧 Initializing Gamma client...")
        gamma_client = PolymarketGammaClient()
        if gamma_client:
            print("✅ Gamma client initialized successfully")
except Exception as e:
    print(f"❌ Could not initialize Gamma client: {e}")

# Global client instances (initialized on first request)
_clob_client = None
_gamma_client = None


def get_clob_client():
    """Get or create CLOB client instance"""
    global _clob_client, clob_client
    
    # Use the already-created clob_client if available
    if clob_client is not None:
        return clob_client
    
    # Fallback: create a new instance if needed
    if _clob_client is None and ClobClient is not None:
        _clob_client = ClobClient(CLOB_URL, chain_id=CHAIN_ID)
    
    return _clob_client


def get_gamma_client():
    """Get or create Gamma API client instance"""
    global _gamma_client, gamma_client
    
    # Use the already-created gamma_client if available
    if gamma_client is not None:
        return gamma_client
    
    # Fallback: create a new instance if needed
    if _gamma_client is None and PolymarketGammaClient is not None:
        _gamma_client = PolymarketGammaClient()
    
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
    Get wallet USDC balance - serves cached data immediately, updates in background
    
    Returns JSON file cached data immediately, starts background blockchain update
    """
    import json
    from pathlib import Path
    import threading
    import sys
    
    # Setup paths
    project_root = Path(__file__).parent.parent
    data_dir = project_root / "data"
    balance_file = data_dir / "balance.json"
    
    # Add utility paths for blockchain functions
    utils_derived_path = project_root / "utils" / "account" / "derived-wallet"
    utils_proxy_path = project_root / "utils" / "account" / "proxy-wallet"
    
    if str(utils_derived_path) not in sys.path:
        sys.path.insert(0, str(utils_derived_path))
    if str(utils_proxy_path) not in sys.path:
        sys.path.insert(0, str(utils_proxy_path))
    
    # Background update function
    def update_balance_background():
        try:
            from get_balance_derived_address_blockchain import get_balance_derived_address
            from get_balance_proxy_address_blockchain import check_blockchain_balance
            
            print("🔄 Starting blockchain balance update...")
            
            # Fetch from blockchain
            derived_balance = get_balance_derived_address("USDC")
            proxy_balance, proxy_allowance = check_blockchain_balance(verbose=False)
            total_balance = derived_balance + proxy_balance
            
            # Save to JSON
            balance_data = {
                'success': True,
                'balance': total_balance,
                'derived_balance': derived_balance,
                'proxy_balance': proxy_balance,
                'proxy_allowance': proxy_allowance,
                'currency': 'USDC',
                'timestamp': datetime.utcnow().isoformat(),
                'source': 'blockchain',
                'cached': False
            }
            
            data_dir.mkdir(exist_ok=True)
            with open(balance_file, 'w') as f:
                json.dump(balance_data, f, indent=2)
            
            print(f"✅ Balance saved to JSON: ${total_balance:.2f} USDC (derived: ${derived_balance:.2f}, proxy: ${proxy_balance:.2f})")
            
        except Exception as e:
            print(f"❌ Background balance update failed: {e}")
            import traceback
            traceback.print_exc()
    
    # Start background update thread (daemon=True means it won't block app shutdown)
    update_thread = threading.Thread(target=update_balance_background, daemon=True)
    update_thread.start()
    print("⏳ Background blockchain update started")
    
    # IMMEDIATELY return cached data (don't wait for blockchain)
    try:
        if balance_file.exists():
            with open(balance_file, 'r') as f:
                cached_data = json.load(f)
                cached_data['cached'] = True
                cached_data['updating'] = True
                print(f"📦 Serving cached balance: ${cached_data.get('balance', 0):.2f} USDC")
                return jsonify(cached_data)
        else:
            print("⚠️ No cache file found, returning default")
    except Exception as e:
        print(f"❌ Could not load cached balance: {e}")
    
    # No cache exists - return default and let background update create it
    return jsonify({
        'success': True,
        'balance': 0.0,
        'derived_balance': 0.0,
        'proxy_balance': 0.0,
        'proxy_allowance': 0.0,
        'currency': 'USDC',
        'timestamp': datetime.utcnow().isoformat(),
        'cached': False,
        'updating': True,
        'message': 'Balance is being fetched from blockchain in background'
    })


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


# ============= ORDER MANAGEMENT =============

@api_bp.route('/orders/list', methods=['GET'])
def list_orders():
    """
    Get all open orders
    
    Query params:
        market: Optional market filter
    
    Response:
        {
            "success": true,
            "orders": [...],
            "count": 5
        }
    """
    try:
        # This would integrate with OrdersCore
        # For now, return empty list
        market = request.args.get('market')
        
        return jsonify({
            'success': True,
            'orders': [],
            'count': 0,
            'message': 'Order listing available when OrdersCore is integrated',
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/orders/cancel/<order_id>', methods=['POST'])
def cancel_order(order_id):
    """
    Cancel a specific order
    
    Response:
        {
            "success": true,
            "message": "Order cancelled"
        }
    """
    try:
        # This would integrate with OrdersCore
        return jsonify({
            'success': False,
            'message': 'Order cancellation available when OrdersCore is integrated',
            'order_id': order_id,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============= POSITION TRACKING =============

@api_bp.route('/positions', methods=['GET'])
def get_positions():
    """
    Get current positions
    
    Response:
        {
            "success": true,
            "positions": [...],
            "total_value": 0.0,
            "total_pnl": 0.0
        }
    """
    try:
        # This would query actual positions from CLOB
        return jsonify({
            'success': True,
            'positions': [],
            'total_value': 0.0,
            'total_pnl': 0.0,
            'message': 'Position tracking available when integrated with CLOB',
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============= TRADE HISTORY =============

@api_bp.route('/trades/history', methods=['GET'])
def get_trade_history():
    """
    Get trade history
    
    Query params:
        limit: Number of trades to return (default: 50)
        market: Optional market filter
    
    Response:
        {
            "success": true,
            "trades": [...],
            "count": 0
        }
    """
    try:
        limit = request.args.get('limit', 50, type=int)
        market = request.args.get('market')
        
        # This would query trade history from database or CLOB
        return jsonify({
            'success': True,
            'trades': [],
            'count': 0,
            'limit': limit,
            'message': 'Trade history available when integrated',
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============= LIVE FOOTBALL MARKETS =============

@api_bp.route('/markets/football/live', methods=['GET'])
def get_live_football_markets():
    """
    Get live football matches from Gamma API with caching
    
    Query params:
        force_refresh: If 'true', bypass cache and fetch fresh data
    
    Response:
        {
            "success": true,
            "matches": [...],
            "count": 42,
            "cached": false,
            "cache_age_seconds": 0,
            "timestamp": "..."
        }
    """
    try:
        # Import cache manager
        import sys
        from pathlib import Path
        utils_path = Path(__file__).parent.parent / "utils" / "core"
        if str(utils_path) not in sys.path:
            sys.path.insert(0, str(utils_path))
        
        from cache_manager import read_cache, write_cache, read_cache_stale_ok, get_cache_age
        
        # Import get_live_football_matches utility
        gamma_utils_path = Path(__file__).parent.parent / "utils" / "gamma-api"
        if str(gamma_utils_path) not in sys.path:
            sys.path.insert(0, str(gamma_utils_path))
        
        from get_live_football_matches import get_live_football_matches
        
        cache_filename = 'live_football_matches.json'
        ttl_seconds = 300  # 5 minutes
        force_refresh = request.args.get('force_refresh', '').lower() == 'true'
        
        # Try to read from cache first (unless force refresh)
        if not force_refresh:
            cached_data = read_cache(cache_filename, ttl_seconds)
            if cached_data:
                matches_data = cached_data.get('matches', cached_data.get('data', {}))
                cache_age = get_cache_age(cache_filename) or 0
                
                return jsonify({
                    'success': True,
                    'matches': matches_data,
                    'count': len(matches_data) if isinstance(matches_data, dict) else 0,
                    'cached': True,
                    'cache_age_seconds': round(cache_age, 1),
                    'timestamp': datetime.utcnow().isoformat()
                })
        
        # Fetch fresh data from API
        try:
            print(f"Fetching live football matches from Gamma API...")
            matches_dict = get_live_football_matches(fields=None)  # Get all fields
            
            if not matches_dict:
                # Try returning stale cache as fallback
                stale_cache = read_cache_stale_ok(cache_filename)
                if stale_cache:
                    matches_data = stale_cache.get('matches', stale_cache.get('data', {}))
                    cache_age = get_cache_age(cache_filename) or 0
                    
                    return jsonify({
                        'success': True,
                        'matches': matches_data,
                        'count': len(matches_data) if isinstance(matches_data, dict) else 0,
                        'cached': True,
                        'stale': True,
                        'cache_age_seconds': round(cache_age, 1),
                        'message': 'No fresh data available, using stale cache',
                        'timestamp': datetime.utcnow().isoformat()
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': 'No matches found and no cache available',
                        'matches': {},
                        'count': 0
                    }), 404
            
            # Cache the results
            metadata = {
                "total_matches": len(matches_dict),
                "source": "Gamma API /sports endpoint",
                "extraction_timestamp": datetime.utcnow().isoformat()
            }
            
            cache_data = {
                "metadata": metadata,
                "matches": matches_dict
            }
            
            write_cache(cache_filename, cache_data, ttl_seconds=ttl_seconds)
            
            return jsonify({
                'success': True,
                'matches': matches_dict,
                'count': len(matches_dict),
                'cached': False,
                'cache_age_seconds': 0,
                'timestamp': datetime.utcnow().isoformat()
            })
            
        except Exception as fetch_error:
            # Fallback to stale cache on API error
            print(f"Error fetching from API: {fetch_error}")
            stale_cache = read_cache_stale_ok(cache_filename)
            
            if stale_cache:
                matches_data = stale_cache.get('matches', stale_cache.get('data', {}))
                cache_age = get_cache_age(cache_filename) or 0
                
                return jsonify({
                    'success': True,
                    'matches': matches_data,
                    'count': len(matches_data) if isinstance(matches_data, dict) else 0,
                    'cached': True,
                    'stale': True,
                    'cache_age_seconds': round(cache_age, 1),
                    'error': str(fetch_error),
                    'message': 'API error, using stale cache as fallback',
                    'timestamp': datetime.utcnow().isoformat()
                })
            else:
                return jsonify({
                    'success': False,
                    'error': f'API error and no cache available: {str(fetch_error)}',
                    'matches': {},
                    'count': 0
                }), 500
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'matches': {},
            'count': 0
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
    
    # Register command routes blueprint
    try:
        from fqs.server.command_routes import command_bp
        app.register_blueprint(command_bp)
        print("✓ Command routes registered")
    except ImportError as e:
        print(f"⚠ Command routes not available: {e}")
    
    return app
