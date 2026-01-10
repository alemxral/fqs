"""
Polymarket CLOB Client Authentication Wrapper
Provides easy authentication setup for both API and WebSocket connections
Uses SimpleAuth for secure credential management
"""

import os
from typing import Optional, Dict, Any
from pathlib import Path

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds
from py_clob_client.constants import AMOY, POLYGON

# Import SimpleAuth for credential management
try:
    from .SimpleAuth import SimplePolymarketAuth
except ImportError:
    # If relative import fails (running directly), use absolute import
    from SimpleAuth import SimplePolymarketAuth


class PolymarketAuth:
    """
    Authentication wrapper for Polymarket CLOB API and WebSocket connections
    Uses SimpleAuth for secure credential management
    """
    
    def __init__(self, 
                 env_file: Optional[str] = None, 
                 chain_id: int = POLYGON):
        """
        Initialize authentication wrapper
        
        Args:
            env_file: Path to .env file (optional, defaults to config/.env)
            chain_id: Blockchain network (POLYGON for mainnet, AMOY for testnet)
        """
        self.chain_id = chain_id
        
        # Use SimplePolymarketAuth for credential management
        self.auth = SimplePolymarketAuth(chain_id=chain_id)
        self._load_credentials()
    
    def _load_credentials(self):
        """Load credentials using SimplePolymarketAuth"""
        # The auth object already has all the credentials loaded
        self.host = self.auth.host
        self.private_key = self.auth.private_key
        self.funder_address = self.auth.funder_address
        self.api_creds = self.auth.api_creds
        
        # Validate credentials
        self._validate_credentials()
    
    def _extract_credentials(self, credentials: dict):
        """This method is no longer needed - kept for compatibility"""
        pass
    
    def _validate_credentials(self):
        """Validate that all required credentials are present"""
        missing_vars = []
        
        # Check API credentials
        if not self.api_creds.api_key:
            missing_vars.append("api_key/CLOB_API_KEY")
        if not self.api_creds.api_secret:
            missing_vars.append("api_secret/CLOB_SECRET")
        if not self.api_creds.api_passphrase:
            missing_vars.append("api_passphrase/CLOB_PASS_PHRASE")
        
        # Check private key
        if not self.private_key:
            missing_vars.append("PRIVATE_KEY/PK")
        
        if missing_vars:
            raise ValueError(f"Missing required credentials: {', '.join(missing_vars)}")
        
        print("✅ All required credentials validated")
    
    def refresh_credentials(self):
        """Refresh credentials from SimplePolymarketAuth"""
        print("🔄 Refreshing credentials...")
        # Create a new auth instance to reload credentials
        self.auth = SimplePolymarketAuth(chain_id=self.chain_id)
        self._load_credentials()
    
    def get_client(self) -> ClobClient:
        """
        Get authenticated CLOB client
        
        Returns:
            ClobClient: Authenticated client ready to use
        """
        return ClobClient(
            host=self.host,
            key=self.private_key,
            chain_id=self.chain_id,
            creds=self.api_creds
        )
    
    def get_websocket_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for WebSocket connections
        
        Returns:
            Dict with authentication headers for WebSocket
        """
        return {
            "Authorization": f"Bearer {self.api_creds.api_key}",
            "X-API-SECRET": self.api_creds.api_secret,
            "X-API-PASSPHRASE": self.api_creds.api_passphrase,
            "X-PRIVATE-KEY": self.private_key,
        }
    
    def get_connection_info(self) -> Dict[str, Any]:
        """
        Get connection information for debugging
        
        Returns:
            Dict with connection details (without sensitive data)
        """
        return {
            "host": self.host,
            "chain_id": self.chain_id,
            "funder_address": self.funder_address,
            "has_api_key": bool(self.api_creds.api_key),
            "has_private_key": bool(self.private_key),
        }
    
    def test_connection(self) -> bool:
        """
        Test API connection
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            client = self.get_client()
            # Test with a simple API call
            result = client.get_ok()
            return result is not None
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False


# Convenience functions for quick setup
def get_authenticated_client(chain_id: int = POLYGON) -> ClobClient:
    """
    Quick function to get an authenticated CLOB client
    
    Args:
        chain_id: Blockchain network (POLYGON for mainnet, AMOY for testnet)
    
    Returns:
        ClobClient: Authenticated client
    """
    auth = PolymarketAuth(chain_id=chain_id)
    return auth.get_client()


def get_testnet_client() -> ClobClient:
    """
    Quick function to get an authenticated testnet client
    
    Returns:
        ClobClient: Authenticated testnet client
    """
    return get_authenticated_client(chain_id=AMOY)


def get_mainnet_client() -> ClobClient:
    """
    Quick function to get an authenticated mainnet client
    
    Returns:
        ClobClient: Authenticated mainnet client
    """
    return get_authenticated_client(chain_id=POLYGON)


# Example usage
if __name__ == "__main__":
    # Test the authentication
    auth = PolymarketAuth()
    
    print("Connection Info:")
    print(auth.get_connection_info())
    
    print("\nTesting connection...")
    if auth.test_connection():
        print("✅ Authentication successful!")
        
        # Get client and test some basic calls
        client = auth.get_client()
        print(f"✅ Markets available: {len(client.get_markets())}")
    else:
        print("❌ Authentication failed!")