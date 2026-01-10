"""
FetchManager - Handles fetching data from Polymarket's Gamma API
Wraps utility functions for use in PMTerminal
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# Import the utility functions from gamma-api folder
utils_path = Path(__file__).parent.parent / "utils" / "gamma-api"
if str(utils_path) not in sys.path:
    sys.path.insert(0, str(utils_path))

from get_events_by_slug import get_events_by_slug
from get_markets_by_slug import get_markets_by_slug


class FetchManager:
    """
    Manager for interacting with Polymarket's Gamma API
    Provides methods to fetch events and markets by slug
    
    This is a wrapper around utility functions with added logging and formatting
    """
    
    def __init__(self, logger=None):
        """
        Initialize the Fetch Manager
        
        Args:
            logger: Optional logger instance for debugging
        """
        self.logger = logger
    
    def get_event_by_slug(self, slug: str, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Fetch event data from Gamma API /events/slug/ endpoint
        
        Args:
            slug: The event slug to fetch
            fields: Optional list of fields to extract. If None, returns everything.
        
        Returns:
            Dict with event data
            
        Raises:
            ValueError: If event not found (404)
            Exception: For other errors
        """
        # Simply call the utility function - it handles everything
        return get_events_by_slug(slug, fields)
    
    def get_market_by_slug(self, slug: str, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Fetch market data from Gamma API /markets/slug/ endpoint
        
        Args:
            slug: The market slug to fetch
            fields: Optional list of fields to extract. If None, returns everything.
        
        Returns:
            Dict with market data
            
        Raises:
            ValueError: If market not found (404)
            Exception: For other errors
        """
        # Simply call the utility function - it handles everything
        return get_markets_by_slug(slug, fields)
    
    def format_event_info(self, event_data: Dict[str, Any]) -> str:
        """
        Format event data into a human-readable string
        
        Args:
            event_data: Raw event data from API
            
        Returns:
            Formatted string representation
        """
        lines = []
        lines.append("=" * 60)
        lines.append("EVENT INFORMATION")
        lines.append("=" * 60)
        
        # Basic info
        if 'id' in event_data:
            lines.append(f"ID: {event_data['id']}")
        if 'slug' in event_data:
            lines.append(f"Slug: {event_data['slug']}")
        if 'title' in event_data:
            lines.append(f"Title: {event_data['title']}")
        if 'description' in event_data:
            desc = event_data['description']
            if len(desc) > 200:
                desc = desc[:197] + "..."
            lines.append(f"Description: {desc}")
        
        # Status
        if 'active' in event_data:
            status = "Active" if event_data['active'] else "Inactive"
            lines.append(f"Status: {status}")
        if 'closed' in event_data:
            lines.append(f"Closed: {event_data['closed']}")
        if 'archived' in event_data:
            lines.append(f"Archived: {event_data['archived']}")
        
        # Markets
        if 'markets' in event_data and event_data['markets']:
            markets = event_data['markets']
            lines.append(f"\nMarkets ({len(markets)}):")
            for i, market in enumerate(markets[:5], 1):  # Show first 5
                market_title = market.get('question', market.get('title', 'Unknown'))
                market_slug = market.get('slug', 'N/A')
                lines.append(f"  {i}. {market_title}")
                lines.append(f"     Slug: {market_slug}")
            if len(markets) > 5:
                lines.append(f"  ... and {len(markets) - 5} more markets")
        
        lines.append("=" * 60)
        return "\n".join(lines)
    
    def format_market_info(self, market_data: Dict[str, Any]) -> str:
        """
        Format market data into a human-readable string
        
        Args:
            market_data: Raw market data from API
            
        Returns:
            Formatted string representation
        """
        lines = []
        lines.append("=" * 60)
        lines.append("MARKET INFORMATION")
        lines.append("=" * 60)
        
        # Basic info
        if 'id' in market_data:
            lines.append(f"ID: {market_data['id']}")
        if 'condition_id' in market_data:
            lines.append(f"Condition ID: {market_data['condition_id']}")
        if 'slug' in market_data:
            lines.append(f"Slug: {market_data['slug']}")
        if 'question' in market_data:
            lines.append(f"Question: {market_data['question']}")
        if 'description' in market_data:
            desc = market_data['description']
            if len(desc) > 200:
                desc = desc[:197] + "..."
            lines.append(f"Description: {desc}")
        
        # Status
        if 'active' in market_data:
            status = "Active" if market_data['active'] else "Inactive"
            lines.append(f"Status: {status}")
        if 'closed' in market_data:
            lines.append(f"Closed: {market_data['closed']}")
        if 'archived' in market_data:
            lines.append(f"Archived: {market_data['archived']}")
        
        # Tokens
        if 'tokens' in market_data and market_data['tokens']:
            tokens = market_data['tokens']
            lines.append(f"\nTokens ({len(tokens)}):")
            for token in tokens:
                outcome = token.get('outcome', 'Unknown')
                token_id = token.get('token_id', 'N/A')
                lines.append(f"  {outcome}: {token_id}")
        
        # Prices
        if 'clobTokenIds' in market_data:
            lines.append(f"\nCLOB Token IDs: {market_data['clobTokenIds']}")
        
        # Volume and liquidity
        if 'volume' in market_data:
            lines.append(f"Volume: ${market_data['volume']:,.2f}")
        if 'liquidity' in market_data:
            lines.append(f"Liquidity: ${market_data['liquidity']:,.2f}")
        
        lines.append("=" * 60)
        return "\n".join(lines)
    
    def extract_market_table_data(self, slug: str) -> Dict[str, Any]:
        """
        Extract key market data for table display: event-slug, market-slugs, tokenIds, lastTradePrice
        
        This method tries to fetch as event first (to get all markets), then as market if not found.
        
        Args:
            slug: Event or market slug to fetch
            
        Returns:
            Dict with:
                - type: "event" or "market"
                - event_slug: Event slug
                - markets: List of dicts with {market_slug, token_ids, last_price}
                - token_to_market: Dict mapping token_id to market_slug
        """
        import json
        
        # Try as event first
        try:
            event_data = self.get_event_by_slug(slug)
            
            markets_info = []
            token_to_market = {}  # NEW: map token_id -> market_slug
            event_slug = event_data.get('slug', slug)
            
            # Extract data from each market in the event
            for market in event_data.get('markets', []):
                market_slug = market.get('slug', 'N/A')
                market_info = {
                    'market_slug': market_slug,
                    'question': market.get('question', 'N/A'),
                    'token_ids': [],
                    'outcomes': [],
                    'last_prices': []
                }
                
                # Get outcomes - they're in JSON string format
                outcomes_str = market.get('outcomes', '[]')
                if isinstance(outcomes_str, str):
                    market_info['outcomes'] = json.loads(outcomes_str)
                else:
                    market_info['outcomes'] = outcomes_str
                
                # Get token IDs from clobTokenIds - also JSON string
                token_ids_str = market.get('clobTokenIds', '[]')
                if isinstance(token_ids_str, str):
                    market_info['token_ids'] = json.loads(token_ids_str)
                else:
                    market_info['token_ids'] = token_ids_str
                
                # NEW: Build token_id -> market_slug mapping
                for token_id in market_info['token_ids']:
                    token_to_market[token_id] = market_slug
                
                # Get outcome prices - also JSON string
                prices_str = market.get('outcomePrices', '[]')
                if isinstance(prices_str, str):
                    prices = json.loads(prices_str)
                    market_info['last_prices'] = [float(p) if p else 0.0 for p in prices]
                else:
                    market_info['last_prices'] = [float(p) if p else 0.0 for p in prices_str]
                
                markets_info.append(market_info)
            
            return {
                'type': 'event',
                'event_slug': event_slug,
                'event_title': event_data.get('title', 'N/A'),
                'markets': markets_info,
                'token_to_market': token_to_market  # NEW
            }
            
        except ValueError:
            # Not an event, try as market
            try:
                market_data = self.get_market_by_slug(slug)
                
                market_slug = market_data.get('slug', slug)
                market_info = {
                    'market_slug': market_slug,
                    'question': market_data.get('question', 'N/A'),
                    'token_ids': [],
                    'outcomes': [],
                    'last_prices': []
                }
                
                token_to_market = {}  # NEW: map token_id -> market_slug
                
                # For individual markets, check if they have tokens array
                if 'tokens' in market_data:
                    for token in market_data.get('tokens', []):
                        token_id = token.get('token_id', 'N/A')
                        market_info['token_ids'].append(token_id)
                        market_info['outcomes'].append(token.get('outcome', 'Unknown'))
                        token_to_market[token_id] = market_slug  # NEW
                else:
                    # Use JSON string fields like in events
                    outcomes_str = market_data.get('outcomes', '[]')
                    if isinstance(outcomes_str, str):
                        market_info['outcomes'] = json.loads(outcomes_str)
                    
                    token_ids_str = market_data.get('clobTokenIds', '[]')
                    if isinstance(token_ids_str, str):
                        market_info['token_ids'] = json.loads(token_ids_str)
                    
                    # NEW: Build token_id -> market_slug mapping
                    for token_id in market_info['token_ids']:
                        token_to_market[token_id] = market_slug
                
                # Extract last trade prices if available
                if 'outcomePrices' in market_data:
                    prices_str = market_data.get('outcomePrices', '[]')
                    if isinstance(prices_str, str):
                        prices = json.loads(prices_str)
                        market_info['last_prices'] = [float(p) if p else 0.0 for p in prices]
                    else:
                        prices = market_data.get('outcomePrices', [])
                        market_info['last_prices'] = [float(p) if p else 0.0 for p in prices]
                
                return {
                    'type': 'market',
                    'event_slug': market_data.get('slug', slug),
                    'event_title': market_data.get('question', 'N/A'),
                    'markets': [market_info],
                    'token_to_market': token_to_market  # NEW
                }
                
            except ValueError:
                raise ValueError(f"Slug '{slug}' not found as event or market")
    
    def format_market_table(self, table_data: Dict[str, Any]) -> str:
        """
        Format extracted market data as a text table
        
        Args:
            table_data: Data from extract_market_table_data()
            
        Returns:
            Formatted table string
        """
        lines = []
        lines.append("=" * 120)
        
        if table_data['type'] == 'event':
            lines.append(f"EVENT: {table_data['event_title']}")
            lines.append(f"Slug: {table_data['event_slug']}")
        else:
            lines.append(f"MARKET: {table_data['event_title']}")
            lines.append(f"Slug: {table_data['event_slug']}")
        
        lines.append("=" * 120)
        
        # Table header
        lines.append(f"{'Market Slug':<40} | {'Outcome':<8} | {'Token ID':<66} | {'Last Price':<10}")
        lines.append("-" * 120)
        
        # Table rows
        for market in table_data['markets']:
            market_slug = market['market_slug']
            
            # For each outcome/token pair
            for i, (outcome, token_id) in enumerate(zip(market['outcomes'], market['token_ids'])):
                # Truncate token ID for display
                token_short = f"{token_id[:8]}...{token_id[-8:]}" if len(token_id) > 20 else token_id
                
                # Get price if available
                price_str = f"${market['last_prices'][i]:.3f}" if i < len(market['last_prices']) else "N/A"
                
                # Only show market slug on first row for this market
                slug_display = market_slug if i == 0 else ""
                
                lines.append(f"{slug_display:<40} | {outcome:<8} | {token_short:<66} | {price_str:<10}")
            
            # Add separator between markets
            if len(table_data['markets']) > 1:
                lines.append("-" * 120)
        
        lines.append("=" * 120)
        
        return "\n".join(lines)



    
    # =========================================================================
    # BALANCE FETCHING METHODS
    # =========================================================================
    
    def get_funder_balance(self, cache_file: Optional[Path] = None) -> Dict[str, Any]:
        """
        Get funder wallet USDC balance from blockchain and cache the result
        
        Args:
            cache_file: Optional path to cache file. If None, uses data/balance.json
            
        Returns:
            Dict with:
                - usdc_balance: float (USDC balance)
                - pol_balance: float (POL/MATIC balance)
                - timestamp: str (ISO format timestamp)
                - address: str (wallet address)
                
        Raises:
            Exception: If balance fetch fails
        """
        import json
        import time
        from datetime import datetime
        
        # Set default cache location
        if cache_file is None:
            data_dir = Path(__file__).parent.parent / "data"
            data_dir.mkdir(exist_ok=True)
            cache_file = data_dir / "balance.json"
        
        try:
            # Import the balance utility function
            utils_balance_path = Path(__file__).parent.parent / "utils" / "account" / "derived-wallet"
            if str(utils_balance_path) not in sys.path:
                sys.path.insert(0, str(utils_balance_path))
            
            from get_balance_derived_address_blockchain import get_balance_derived_address
            
            if self.logger:
                self.logger.info("Fetching funder USDC balance from blockchain...")
            
            # Fetch USDC balance (includes native + bridged)
            usdc_balance = get_balance_derived_address("USDC")
            
            # Fetch POL/MATIC balance
            pol_balance = get_balance_derived_address("POL")
            
            # Get wallet address from environment
            import os
            from dotenv import load_dotenv
            pmterminal_root = Path(__file__).parent.parent
            env_path = pmterminal_root / "config" / ".env"
            
            # Check if .env exists
            if not env_path.exists():
                raise ValueError(
                    f"Configuration file not found: {env_path}\n"
                    "Please create PMTerminal/config/.env with PRIVATE_KEY"
                )
            
            load_dotenv(env_path)
            
            private_key = os.getenv("PRIVATE_KEY")
            if not private_key:
                raise ValueError(
                    f"PRIVATE_KEY not found in {env_path}\n"
                    "Please add PRIVATE_KEY=your_private_key to the .env file"
                )
            
            from web3 import Web3
            web3 = Web3(Web3.HTTPProvider("https://polygon-rpc.com"))
            account = web3.eth.account.from_key(private_key)
            address = account.address
            
            # Prepare result
            result = {
                "usdc_balance": usdc_balance,
                "pol_balance": pol_balance,
                "timestamp": datetime.now().isoformat(),
                "address": address
            }
            
            # Cache the result
            try:
                with open(cache_file, 'w') as f:
                    json.dump(result, f, indent=2)
                if self.logger:
                    self.logger.debug(f"Balance cached to {cache_file}")
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Failed to cache balance: {e}")
            
            if self.logger:
                self.logger.info(f"Funder balance: ${usdc_balance:.2f} USDC, {pol_balance:.4f} POL")
            
            return result
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to fetch funder balance: {e}", exc_info=True)
            raise
    
    def get_cached_balance(self, cache_file: Optional[Path] = None) -> Optional[Dict[str, Any]]:
        """
        Get balance from cache file (fast, no blockchain call)
        
        Args:
            cache_file: Optional path to cache file. If None, uses data/balance.json
            
        Returns:
            Dict with balance data, or None if cache doesn't exist or is invalid
        """
        import json
        
        # Set default cache location
        if cache_file is None:
            data_dir = Path(__file__).parent.parent / "data"
            cache_file = data_dir / "balance.json"
        
        try:
            if not cache_file.exists():
                return None
            
            with open(cache_file, 'r') as f:
                data = json.load(f)
            
            # Validate required fields
            if 'usdc_balance' not in data or 'timestamp' not in data:
                return None
            
            if self.logger:
                self.logger.debug(f"Loaded cached balance: ${data['usdc_balance']:.2f} USDC")
            
            return data
            
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Failed to load cached balance: {e}")
            return None
    
    def get_proxy_balance(self, cache_file: Optional[Path] = None) -> Dict[str, Any]:
        """
        Get proxy wallet USDC balance from blockchain and cache the result
        
        Args:
            cache_file: Optional path to cache file. If None, uses data/proxy_balance.json
            
        Returns:
            Dict with:
                - usdc_balance: float (USDC balance)
                - allowance: float (allowance to exchange contract)
                - timestamp: str (ISO format timestamp)
                - address: str (wallet address)
                
        Raises:
            Exception: If balance fetch fails
        """
        import json
        from datetime import datetime
        
        # Set default cache location
        if cache_file is None:
            data_dir = Path(__file__).parent.parent / "data"
            data_dir.mkdir(exist_ok=True)
            cache_file = data_dir / "proxy_balance.json"
        
        try:
            # Import the proxy balance utility function
            utils_balance_path = Path(__file__).parent.parent / "utils" / "account" / "proxy-wallet"
            if str(utils_balance_path) not in sys.path:
                sys.path.insert(0, str(utils_balance_path))
            
            from get_balance_proxy_address_blockchain import check_blockchain_balance
            
            if self.logger:
                self.logger.info("Fetching proxy USDC balance from blockchain...")
            
            # Get proxy address from environment
            import os
            from dotenv import load_dotenv
            pmterminal_root = Path(__file__).parent.parent
            env_path = pmterminal_root / "config" / ".env"
            
            # Check if .env exists
            if not env_path.exists():
                raise ValueError(
                    f"Configuration file not found: {env_path}\n"
                    "Please create PMTerminal/config/.env with PROXY_ADDRESS or FUNDER"
                )
            
            load_dotenv(env_path)
            
            # Try PROXY_ADDRESS first, then FUNDER
            proxy_address = os.getenv("PROXY_ADDRESS") or os.getenv("FUNDER")
            if not proxy_address:
                raise ValueError(
                    f"PROXY_ADDRESS or FUNDER not found in {env_path}\n"
                    "Please add PROXY_ADDRESS=0x... or FUNDER=0x... to the .env file"
                )
            
            # Fetch USDC balance and allowance
            usdc_balance, allowance = check_blockchain_balance(
                address=proxy_address,
                verbose=False
            )
            
            # Prepare result
            result = {
                "usdc_balance": usdc_balance,
                "allowance": allowance if allowance < 1000000 else -1,  # -1 indicates unlimited
                "timestamp": datetime.now().isoformat(),
                "address": proxy_address
            }
            
            # Cache the result
            try:
                with open(cache_file, 'w') as f:
                    json.dump(result, f, indent=2)
                if self.logger:
                    self.logger.debug(f"Proxy balance cached to {cache_file}")
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Failed to cache proxy balance: {e}")
            
            if self.logger:
                allowance_str = "UNLIMITED" if allowance > 1000000 else f"${allowance:.2f}"
                self.logger.info(f"Proxy balance: ${usdc_balance:.2f} USDC, Allowance: {allowance_str}")
            
            return result
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to fetch proxy balance: {e}", exc_info=True)
            raise
    
    def get_cached_proxy_balance(self, cache_file: Optional[Path] = None) -> Optional[Dict[str, Any]]:
        """
        Get proxy balance from cache file (fast, no blockchain call)
        
        Args:
            cache_file: Optional path to cache file. If None, uses data/proxy_balance.json
            
        Returns:
            Dict with balance data, or None if cache doesn't exist or is invalid
        """
        import json
        
        # Set default cache location
        if cache_file is None:
            data_dir = Path(__file__).parent.parent / "data"
            cache_file = data_dir / "proxy_balance.json"
        
        try:
            if not cache_file.exists():
                return None
            
            with open(cache_file, 'r') as f:
                data = json.load(f)
            
            # Validate required fields
            if 'usdc_balance' not in data or 'timestamp' not in data:
                return None
            
            if self.logger:
                self.logger.debug(f"Loaded cached proxy balance: ${data['usdc_balance']:.2f} USDC")
            
            return data
            
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Failed to load cached proxy balance: {e}")
            return None



# ═══════════════════════════════════════════════════════════════
#                    TESTING / MAIN
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import time
    import logging
    
    # Setup basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    print("\n" + "=" * 80)
    print("TESTING FUNDER BALANCE FETCHING")
    print("=" * 80 + "\n")
    
    # Initialize manager with logger
    manager = FetchManager(logger=logger)
    
    # Test 1: Check if cached balance exists
    print("Test 1: Checking for cached balance...")
    cached = manager.get_cached_balance()
    if cached:
        print("✓ Found cached balance:")
        print(f"  - USDC: ${cached['usdc_balance']:.2f}")
        print(f"  - POL: {cached['pol_balance']:.4f}")
        print(f"  - Address: {cached['address']}")
        print(f"  - Timestamp: {cached['timestamp']}")
    else:
        print("✗ No cached balance found")
    print()
    
    # Test 2: Fetch fresh balance from blockchain
    print("Test 2: Fetching fresh balance from blockchain...")
    print("(This will take a few seconds...)")
    try:
        start_time = time.time()
        result = manager.get_funder_balance()
        elapsed = time.time() - start_time
        
        print(f"✓ Successfully fetched balance in {elapsed:.2f} seconds:")
        print(f"  - USDC Balance: ${result['usdc_balance']:.2f}")
        print(f"  - POL Balance: {result['pol_balance']:.4f}")
        print(f"  - Wallet Address: {result['address']}")
        print(f"  - Timestamp: {result['timestamp']}")
        print()
        
        # Test 3: Verify cache was updated
        print("Test 3: Verifying cache was updated...")
        cached_after = manager.get_cached_balance()
        if cached_after and cached_after['timestamp'] == result['timestamp']:
            print("✓ Cache successfully updated")
        else:
            print("✗ Cache update failed")
        
    except Exception as e:
        print(f"✗ Failed to fetch balance: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("TESTING COMPLETE")
    print("=" * 80 + "\n")