"""
FQS Flask Server - Entry Point
Provides REST API for football trading terminal
"""
import sys
import os

# Add parent directory to path so we can import fqs modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fqs.server import create_app

app = create_app()

if __name__ == "__main__":
    print("=" * 80)
    print("🚀 FQS FLASK SERVER - Football Trading API")
    print("=" * 80)
    print("📊 Endpoints:")
    print("   POST /api/order/buy         - Place buy order")
    print("   POST /api/order/sell        - Place sell order")
    print("   GET  /api/balance           - Get wallet balance")
    print("   GET  /api/markets/football  - Get active football markets")
    print("   GET  /api/market/<slug>     - Get market details and token IDs")
    print("")
    print("🔧 Server starting on http://127.0.0.1:5000")
    print("=" * 80)
    print("")
    
    # Run Flask development server
    app.run(host="127.0.0.1", port=5000, debug=True)
