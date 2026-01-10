"""
Wallet Manager - Manage wallet addresses and balances
"""
from typing import Optional, Dict, Any
import asyncio
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import Web3 client
try:
    from fqs.client.web3_client import PolymarketWeb3Client
    from fqs.client.SimpleAuth import SimplePolymarketAuth
    WEB3_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Web3 client not available: {e}")
    WEB3_AVAILABLE = False


class WalletCore:
    """
    Manage wallet addresses and balances
    
    Features:
    - Track funder and derived addresses
    - Get wallet USDC balances via Web3
    - Manage wallet credentials
    """
    
    def __init__(self):
        """Initialize wallet manager"""
        self.web3_client: Optional[Any] = None
        self.auth: Optional[Any] = None
        
        # Wallet addresses
        self.funder_address: Optional[str] = None
        self.derived_address: Optional[str] = None
        
        # Balances cache
        self._funder_balance: float = 0.0
        self._derived_balance: float = 0.0
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize wallet with auth and Web3 client"""
        if not WEB3_AVAILABLE:
            print("Warning: Web3 client not available, running in demo mode")
            self._initialized = True
            return
        
        try:
            # Initialize auth
            self.auth = SimplePolymarketAuth()
            
            # Get addresses from auth
            self.funder_address = self.auth.funder_address
            self.derived_address = self.auth.derived_address
            
            # Initialize Web3 client
            self.web3_client = PolymarketWeb3Client()
            
            self._initialized = True
            print(f"✅ WalletCore initialized")
            print(f"   Funder: {self.funder_address}")
            print(f"   Derived: {self.derived_address}")
            
        except Exception as e:
            print(f"❌ Failed to initialize WalletCore: {e}")
            self._initialized = False
    
    async def load_addresses(self) -> Dict[str, Optional[str]]:
        """
        Load wallet addresses from configuration
        
        Returns:
            Dictionary with funder_address and derived_address
        """
        if not self._initialized:
            await self.initialize()
        
        return {
            "funder_address": self.funder_address,
            "derived_address": self.derived_address
        }
    
    async def get_funder_balance(self) -> float:
        """
        Get funder wallet USDC balance
        
        Returns:
            Balance in USDC
        """
        if not self._initialized:
            await self.initialize()
        
        if not WEB3_AVAILABLE or not self.web3_client or not self.funder_address:
            # Return cached demo value
            return self._funder_balance
        
        try:
            # Get balance from Web3 client (run in executor to avoid blocking)
            balance = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.web3_client.get_usdc_balance(self.funder_address)
            )
            
            self._funder_balance = float(balance) if balance is not None else 0.0
            return self._funder_balance
            
        except Exception as e:
            print(f"Error getting funder balance: {e}")
            return self._funder_balance
    
    async def get_derived_balance(self) -> float:
        """
        Get derived wallet USDC balance
        
        Returns:
            Balance in USDC
        """
        if not self._initialized:
            await self.initialize()
        
        if not WEB3_AVAILABLE or not self.web3_client or not self.derived_address:
            # Return cached demo value
            return self._derived_balance
        
        try:
            # Get balance from Web3 client
            balance = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.web3_client.get_usdc_balance(self.derived_address)
            )
            
            self._derived_balance = float(balance) if balance is not None else 0.0
            return self._derived_balance
            
        except Exception as e:
            print(f"Error getting derived balance: {e}")
            return self._derived_balance
    
    async def get_proxy_balance(self) -> float:
        """
        Get proxy wallet USDC balance (alias for derived balance)
        
        Returns:
            Balance in USDC
        """
        return await self.get_derived_balance()
    
    async def refresh_balances(self) -> Dict[str, float]:
        """
        Refresh both wallet balances
        
        Returns:
            Dictionary with funder_balance and derived_balance
        """
        funder = await self.get_funder_balance()
        derived = await self.get_derived_balance()
        
        return {
            "funder_balance": funder,
            "derived_balance": derived,
            "proxy_balance": derived,  # Alias
            "total_balance": funder + derived
        }
    
    async def get_balance(self, address: Optional[str] = None) -> float:
        """
        Get USDC balance for a specific address or combined balance
        
        Args:
            address: Wallet address (if None, returns combined balance)
            
        Returns:
            Balance in USDC
        """
        if address:
            if not WEB3_AVAILABLE or not self.web3_client:
                return 0.0
            
            try:
                balance = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.web3_client.get_usdc_balance(address)
                )
                return float(balance) if balance is not None else 0.0
            except Exception as e:
                print(f"Error getting balance for {address}: {e}")
                return 0.0
        else:
            # Return combined balance
            balances = await self.refresh_balances()
            return balances.get("total_balance", 0.0)
    
    def set_demo_balances(self, funder: float = 1000.0, proxy: float = 0.0) -> None:
        """
        Set demo balances for testing
        
        Args:
            funder: Funder balance
            proxy: Proxy balance
        """
        self._funder_balance = funder
        self._proxy_balance = proxy
