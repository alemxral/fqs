"""
QuickBuyManager - handles quick buy/sell configuration and execution with profile support.

Purpose:
- Load and save quick buy configuration from JSON with multiple profiles
- Update configuration properties dynamically
- Execute quick buy orders based on active profile and strategy
- Handle auto-sell logic with timers
- Support strategy-based dynamic parameter calculation
"""
from __future__ import annotations

import json
import asyncio
import importlib
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, Literal
from pathlib import Path
from datetime import datetime
from decimal import Decimal
import time

try:
    from PMTerminal.utils.logger import setup_logger
except Exception:
    import logging
    def setup_logger(name):
        return logging.getLogger(name)


@dataclass
class QuickBuyConfig:
    """Configuration for quick buy/sell operations (profile-based)."""
    name: str = "Generic Trading"  # Display name for profile
    strategy: str = "generic"  # Strategy module to use
    amount_percent: float = 10.0  # % of funder wallet to use
    auto_sell: bool = False  # Whether to auto-sell after buy
    auto_sell_time: int = 30  # Seconds to wait before auto-selling
    shortcut_yes: str = "ctrl+y"  # Keyboard shortcut for YES token
    shortcut_no: str = "ctrl+n"  # Keyboard shortcut for NO token
    max_probability: Optional[float] = None  # Max probability to buy (0-1)
    max_shares: Optional[int] = None  # Max shares to buy
    last_updated: Optional[str] = None  # Timestamp of last update
    
    # Extra strategy-specific parameters stored as dict
    extra_params: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        # Flatten extra_params into main dict
        extra = data.pop('extra_params', {})
        data.update(extra)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QuickBuyConfig":
        """Create instance from dictionary."""
        # Separate known fields from extra params
        known_fields = set(cls.__dataclass_fields__.keys()) - {'extra_params'}
        known_data = {k: v for k, v in data.items() if k in known_fields}
        extra_data = {k: v for k, v in data.items() if k not in known_fields}
        
        config = cls(**known_data)
        config.extra_params = extra_data
        return config


class QuickBuyManager:
    """
    Manages quick buy/sell configuration and operations with profile support.
    
    Key responsibilities:
    - Load/save configuration from/to JSON file with multiple profiles
    - Switch between profiles dynamically
    - Load strategy modules based on active profile
    - Execute quick buy orders using strategy logic
    - Track pending auto-sells and execute them
    """
    
    def __init__(self, core: Optional[Any] = None, *, logger: Optional[Any] = None):
        self.core = core
        self.logger = logger or setup_logger("quickbuy_manager")
        
        # Configuration
        self.config: QuickBuyConfig = QuickBuyConfig()
        self.config_file = Path(__file__).parent.parent.parent / "data" / "quickbuy_config.json"
        
        # Profile management
        self.profiles: Dict[str, Dict[str, Any]] = {}
        self.active_profile: str = "generic"
        
        # Strategy instance
        self.strategy: Optional[Any] = None  # BaseStrategy subclass instance
        
        # Track pending auto-sells: {order_id: (token_id, sell_time, task)}
        self._pending_auto_sells: Dict[str, tuple] = {}
        
        # Store YES/NO token IDs from WebSocket for quick switching
        self._yes_token_id: Optional[str] = None
        self._no_token_id: Optional[str] = None
        
        # Load configuration at init
        self.load_config()
    
    def load_config(self) -> bool:
        """
        Load configuration from JSON file with profile support.
        
        Returns:
            bool: True if loaded successfully, False otherwise
        """
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                
                # Load all profiles
                self.profiles = data.get('profiles', {})
                self.active_profile = data.get('active_profile', 'generic')
                
                # Ensure active profile exists
                if self.active_profile not in self.profiles:
                    self.logger.warning(f"Active profile '{self.active_profile}' not found, using 'generic'")
                    self.active_profile = 'generic'
                
                # Load the active profile config
                profile_data = self.profiles.get(self.active_profile, {})
                self.config = QuickBuyConfig.from_dict(profile_data)
                
                # Load strategy for this profile
                self._load_strategy()
                
                self.logger.info(
                    f"Loaded QuickBuy profile '{self.active_profile}': "
                    f"{self.config.name} ({self.config.strategy} strategy), "
                    f"{self.config.amount_percent}% amount"
                )
            else:
                # Create default config file with profiles
                self.save_config()
                self.logger.info("Created default QuickBuy config file with profiles")
            
            # Try to load YES/NO token IDs from ws_active_tokens.json
            ws_tokens_file = self.config_file.parent / "ws_active_tokens.json"
            if ws_tokens_file.exists():
                try:
                    with open(ws_tokens_file, 'r') as f:
                        ws_data = json.load(f)
                    
                    # Extract YES and NO token IDs
                    tokens = ws_data.get('tokens', {})
                    yes_tokens = tokens.get('YES', [])
                    no_tokens = tokens.get('NO', [])
                    
                    if yes_tokens:
                        self._yes_token_id = yes_tokens[0]
                        self.logger.info(f"Loaded YES token from ws_active_tokens: {self._yes_token_id[:10]}...")
                    if no_tokens:
                        self._no_token_id = no_tokens[0]
                        self.logger.info(f"Loaded NO token from ws_active_tokens: {self._no_token_id[:10]}...")
                except Exception as e:
                    self.logger.warning(f"Failed to load ws_active_tokens.json: {e}")
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to load QuickBuy config: {e}", exc_info=True)
            return False
    
    def _load_strategy(self) -> None:
        """Load the strategy module for the current profile."""
        try:
            strategy_name = self.config.strategy
            module_path = f"PMTerminal.strategies.quickbuy.{strategy_name}_strategy"
            
            # Import the strategy module
            strategy_module = importlib.import_module(module_path)
            
            # Get the strategy class (capitalize first letter + Strategy)
            class_name = f"{strategy_name.capitalize()}Strategy"
            strategy_class = getattr(strategy_module, class_name)
            
            # Create strategy instance with config
            strategy_config = self.config.to_dict()
            self.strategy = strategy_class(strategy_config)
            
            self.logger.info(f"Loaded strategy: {class_name}")
        except Exception as e:
            self.logger.error(f"Failed to load strategy '{self.config.strategy}': {e}", exc_info=True)
            # Fallback to generic strategy
            try:
                from PMTerminal.strategies.quickbuy.generic_strategy import GenericStrategy
                self.strategy = GenericStrategy(self.config.to_dict())
                self.logger.info("Fallback to GenericStrategy")
            except Exception as fallback_error:
                self.logger.error(f"Failed to load fallback strategy: {fallback_error}")
                self.strategy = None
    
    def save_config(self) -> bool:
        """
        Save current configuration to JSON file with profiles.
        
        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            # Update timestamp in active profile
            self.config.last_updated = datetime.now().isoformat()
            
            # Update the active profile in profiles dict
            self.profiles[self.active_profile] = self.config.to_dict()
            
            # Prepare full config structure
            full_config = {
                "active_profile": self.active_profile,
                "profiles": self.profiles
            }
            
            # Ensure directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to file
            with open(self.config_file, 'w') as f:
                json.dump(full_config, f, indent=2)
            
            self.logger.info(f"Saved QuickBuy profile '{self.active_profile}' to {self.config_file}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save QuickBuy config: {e}", exc_info=True)
            return False
    
    def switch_profile(self, profile_name: str) -> tuple[str, bool]:
        """
        Switch to a different profile.
        
        Args:
            profile_name: Name of the profile to switch to
        
        Returns:
            tuple: (message, success)
        """
        try:
            if profile_name not in self.profiles:
                available = ", ".join(self.profiles.keys())
                return (f"Profile '{profile_name}' not found. Available: {available}", False)
            
            # Save current profile before switching
            self.save_config()
            
            # Switch to new profile
            self.active_profile = profile_name
            profile_data = self.profiles[profile_name]
            self.config = QuickBuyConfig.from_dict(profile_data)
            
            # Load strategy for new profile
            self._load_strategy()
            
            # Save to update active_profile in file
            self.save_config()
            
            return (f"Switched to profile: {self.config.name} ({self.config.strategy} strategy)", True)
        except Exception as e:
            self.logger.error(f"Failed to switch profile: {e}", exc_info=True)
            return (f"Failed to switch profile: {str(e)}", False)
    
    def list_profiles(self) -> str:
        """Get formatted list of all profiles."""
        if not self.profiles:
            return "No profiles configured"
        
        lines = ["Available Profiles:", "=" * 60]
        for name, data in self.profiles.items():
            active_marker = " (ACTIVE)" if name == self.active_profile else ""
            display_name = data.get('name', name)
            strategy = data.get('strategy', 'unknown')
            lines.append(f"  {name}{active_marker}")
            lines.append(f"    Name: {display_name}")
            lines.append(f"    Strategy: {strategy}")
            lines.append("")
        
        return "\n".join(lines)
    
    def create_profile(self, profile_name: str, base_profile: Optional[str] = None) -> tuple[str, bool]:
        """
        Create a new profile (optionally based on existing one).
        
        Args:
            profile_name: Name for the new profile
            base_profile: Optional existing profile to copy from
        
        Returns:
            tuple: (message, success)
        """
        try:
            if profile_name in self.profiles:
                return (f"Profile '{profile_name}' already exists", False)
            
            # Use base profile or generic default
            if base_profile and base_profile in self.profiles:
                new_profile = self.profiles[base_profile].copy()
                new_profile['name'] = profile_name
            else:
                # Create minimal generic profile
                new_profile = {
                    "name": profile_name,
                    "strategy": "generic",
                    "amount_percent": 10,
                    "auto_sell": False,
                    "auto_sell_time": 30,
                    "shortcut_yes": "ctrl+y",
                    "shortcut_no": "ctrl+n",
                    "max_probability": None,
                    "max_shares": None,
                }
            
            # Add to profiles
            self.profiles[profile_name] = new_profile
            self.save_config()
            
            return (f"Created profile: {profile_name}", True)
        except Exception as e:
            self.logger.error(f"Failed to create profile: {e}", exc_info=True)
            return (f"Failed to create profile: {str(e)}", False)
    
    def update_property(self, property_name: str, value: Any) -> tuple[str, bool]:
        """
        Update a configuration property.
        
        Args:
            property_name: Name of the property to update
            value: New value for the property
        
        Returns:
            tuple: (message, success)
        """
        try:
            # Validate property name
            if property_name not in QuickBuyConfig.__dataclass_fields__:
                valid_props = ", ".join(QuickBuyConfig.__dataclass_fields__.keys())
                return (f"Invalid property '{property_name}'. Valid: {valid_props}", False)
            
            # Type conversion and validation
            if property_name == "amount_percent":
                value = float(value)
                if value <= 0 or value > 100:
                    return ("amount_percent must be between 0 and 100", False)
            
            elif property_name == "auto_sell":
                if isinstance(value, str):
                    value = value.lower() in ("true", "yes", "1", "on")
                else:
                    value = bool(value)
            
            elif property_name == "auto_sell_time":
                value = int(value)
                if value < 0:
                    return ("auto_sell_time must be >= 0", False)
            
            elif property_name in ("shortcut_yes", "shortcut_no"):
                value = str(value).lower()
                # Basic validation for keyboard shortcut format
                if not value or ' ' in value:
                    return (f"{property_name} must be a valid key combination (e.g., 'ctrl+y', 'alt+b')", False)
            
            # Update the property
            setattr(self.config, property_name, value)
            
            # Save to file
            self.save_config()
            
            return (f"Updated {property_name} = {value}", True)
        
        except ValueError as e:
            return (f"Invalid value for {property_name}: {e}", False)
        except Exception as e:
            self.logger.error(f"Failed to update property {property_name}: {e}", exc_info=True)
            return (f"Failed to update {property_name}: {str(e)}", False)
    
    def get_shortcuts(self) -> tuple[str, str]:
        """
        Get the current keyboard shortcuts.
        
        Returns:
            tuple: (shortcut_yes, shortcut_no)
        """
        return (self.config.shortcut_yes, self.config.shortcut_no)
    
    def get_config_summary(self) -> str:
        """
        Get a formatted summary of the current configuration with profile and strategy info.
        
        Returns:
            str: Formatted configuration summary
        """
        lines = [
            "QuickBuy Configuration:",
            "=" * 70,
            f"Active Profile: {self.active_profile} - {self.config.name}",
            f"Strategy: {self.config.strategy}",
            "=" * 70,
            ""
        ]
        
        # Strategy-specific display info
        if self.strategy:
            strategy_info = self.strategy.get_display_info()
            lines.append(strategy_info)
            lines.append("")
            lines.append("=" * 70)
            lines.append("")
        
        # Format percentage with command reference
        amount_line = f"Amount: {self.config.amount_percent}% of funder wallet"
        amount_cmd = "quickbuy setup amount_percent <0-100>"
        
        # Format auto-sell with command reference
        autosell_line = f"Auto-Sell: {'Enabled' if self.config.auto_sell else 'Disabled'}"
        autosell_cmd = "quickbuy setup auto_sell <true|false>"
        
        # Format auto-sell time with command reference
        selltime_line = f"Auto-Sell Time: {self.config.auto_sell_time} seconds"
        selltime_cmd = "quickbuy setup auto_sell_time <seconds>"
        
        # Format shortcuts with command references
        shortcut_yes_line = f"{self.config.shortcut_yes.upper()} - Quick buy YES token"
        shortcut_yes_cmd = "quickbuy setup shortcut_yes <key>"
        
        shortcut_no_line = f"{self.config.shortcut_no.upper()} - Quick buy NO token"
        shortcut_no_cmd = "quickbuy setup shortcut_no <key>"
        
        lines.extend([
            "General Configuration:",
            f"{amount_line:<45} [{amount_cmd}]",
            "",
            "Token IDs (from WebSocket):",
            f"  YES Token: {self._yes_token_id[:10] + '...' if self._yes_token_id else 'Not available'}",
            f"  NO Token:  {self._no_token_id[:10] + '...' if self._no_token_id else 'Not available'}",
            "",
            f"{autosell_line:<45} [{autosell_cmd}]",
            f"{selltime_line:<45} [{selltime_cmd}]",
            "",
            "Keyboard Shortcuts:",
            f"  {shortcut_yes_line:<43} [{shortcut_yes_cmd}]",
            f"  {shortcut_no_line:<43} [{shortcut_no_cmd}]",
            "",
            f"Last Updated: {self.config.last_updated or 'Never'}",
            "=" * 70,
            "",
            "Profile Commands:",
            "  quickbuy profile list          - Show all profiles",
            "  quickbuy profile switch <name> - Switch to different profile",
            "  quickbuy profile create <name> - Create new profile",
        ])
        
        # Add football-specific commands if using football profile
        if self.config.strategy == "football":
            lines.extend([
                "",
                "Football Commands:",
                "  quickbuy football score <home> <away> - Set match score",
                "  quickbuy football time <minute>       - Set match time",
                "  quickbuy football timer start         - Start match timer",
                "  quickbuy football timer stop          - Stop match timer",
                "  quickbuy football side <home|away>    - Set tracked team",
            ])
        
        lines.append("")
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    async def execute_quick_buy(self, token_side: str, session: Optional[Dict] = None, current_price: Optional[Decimal] = None) -> tuple[str, bool]:
        """
        Execute a quick buy order for specified token side using strategy logic.
        
        Args:
            token_side: "YES" or "NO" to specify which token to buy
            session: Optional session data containing wallet info
            current_price: Optional current market price for strategy calculations
        
        Returns:
            tuple: (message, success)
        """
        try:
            # Determine which token ID to use
            token_side_upper = token_side.upper()
            if token_side_upper == "YES":
                token_id = self._yes_token_id
                if not token_id:
                    return ("Cannot execute quick buy: YES token not available. Connect WebSocket first with 'ws sub <market-slug>'", False)
            elif token_side_upper == "NO":
                token_id = self._no_token_id
                if not token_id:
                    return ("Cannot execute quick buy: NO token not available. Connect WebSocket first with 'ws sub <market-slug>'", False)
            else:
                return (f"Invalid token side: {token_side}. Must be 'YES' or 'NO'", False)
            
            # Default current price if not provided (placeholder)
            if current_price is None:
                current_price = Decimal("0.50")  # TODO: Get from market data
            
            # Strategy pre-execution check
            if self.strategy:
                should_proceed, check_message = await self.strategy.pre_execution_check(token_side_upper, current_price)
                if not should_proceed:
                    return (f"Strategy check failed: {check_message}", False)
            
            # Get wallet balance
            if not session or "funder_balance" not in session:
                return ("Cannot execute quick buy: funder balance not available", False)
            
            funder_balance = session.get("funder_balance", 0)
            buy_amount = funder_balance * (self.config.amount_percent / 100.0)
            
            if buy_amount <= 0:
                return ("Cannot execute quick buy: calculated amount is 0", False)
            
            # Calculate max probability from strategy
            max_prob = None
            if self.strategy:
                max_prob = await self.strategy.calculate_max_probability(token_side_upper, current_price)
                if max_prob and current_price > max_prob:
                    return (
                        f"Current price ({float(current_price):.1%}) exceeds strategy max "
                        f"({float(max_prob):.1%}). Not buying.",
                        False
                    )
            
            # Calculate max shares from strategy
            max_shares = None
            if self.strategy:
                max_shares = await self.strategy.calculate_max_shares(token_side_upper, current_price)
            
            self.logger.info(
                f"Executing quick buy: {token_side} token, "
                f"amount={buy_amount:.2f} ({self.config.amount_percent}% of {funder_balance:.2f}), "
                f"max_prob={max_prob}, max_shares={max_shares}"
            )
            
            # TODO: Execute actual buy order through CLOB client
            # For now, this is a placeholder
            # You would call: await self.core.clob_client.buy(token_id, amount, price, etc.)
            # Use max_prob and max_shares in order parameters
            
            executed_price = current_price  # Placeholder
            shares = max_shares or 1  # Placeholder
            
            message = (
                f"Quick buy executed: {token_side} token, "
                f"amount={buy_amount:.2f} USDC ({self.config.amount_percent}%)"
            )
            
            if max_prob:
                message += f" | Max: {float(max_prob):.1%}"
            
            # Strategy post-execution hook
            if self.strategy:
                await self.strategy.post_execution_hook(token_side_upper, executed_price, shares)
            
            # Schedule auto-sell if enabled
            if self.config.auto_sell and self.config.auto_sell_time > 0:
                order_id = f"qb_{token_side.lower()}_{int(time.time())}"  # Placeholder order ID
                await self._schedule_auto_sell(order_id, token_id, self.config.auto_sell_time)
                message += f" | Auto-sell in {self.config.auto_sell_time}s"
            
            return (message, True)
        
        except Exception as e:
            self.logger.error(f"Failed to execute quick buy: {e}", exc_info=True)
            return (f"Quick buy failed: {str(e)}", False)
    
    async def _schedule_auto_sell(self, order_id: str, token_id: str, delay_seconds: int) -> None:
        """
        Schedule an auto-sell after a delay.
        
        Args:
            order_id: ID of the buy order
            token_id: Token ID to sell
            delay_seconds: Seconds to wait before selling
        """
        try:
            self.logger.info(f"Scheduling auto-sell for order {order_id} in {delay_seconds}s")
            
            # Create async task for auto-sell
            task = asyncio.create_task(self._execute_auto_sell(order_id, token_id, delay_seconds))
            
            # Track the pending auto-sell
            sell_time = time.time() + delay_seconds
            self._pending_auto_sells[order_id] = (token_id, sell_time, task)
        
        except Exception as e:
            self.logger.error(f"Failed to schedule auto-sell: {e}", exc_info=True)
    
    async def _execute_auto_sell(self, order_id: str, token_id: str, delay_seconds: int) -> None:
        """
        Execute auto-sell after waiting for specified time.
        
        Args:
            order_id: ID of the buy order
            token_id: Token ID to sell
            delay_seconds: Seconds to wait before selling
        """
        try:
            # Wait for the specified delay
            await asyncio.sleep(delay_seconds)
            
            self.logger.info(f"Executing auto-sell for order {order_id}, token {token_id[:10]}...")
            
            # TODO: Execute actual sell order through CLOB client
            # For now, this is a placeholder
            # You would call: await self.core.clob_client.sell(token_id, amount, price, etc.)
            
            # Remove from pending
            if order_id in self._pending_auto_sells:
                del self._pending_auto_sells[order_id]
            
            self.logger.info(f"Auto-sell completed for order {order_id}")
        
        except asyncio.CancelledError:
            self.logger.info(f"Auto-sell cancelled for order {order_id}")
        except Exception as e:
            self.logger.error(f"Failed to execute auto-sell for order {order_id}: {e}", exc_info=True)
    
    def cancel_auto_sell(self, order_id: str) -> tuple[str, bool]:
        """
        Cancel a pending auto-sell.
        
        Args:
            order_id: ID of the order to cancel
        
        Returns:
            tuple: (message, success)
        """
        try:
            if order_id not in self._pending_auto_sells:
                return (f"No pending auto-sell for order {order_id}", False)
            
            # Cancel the task
            token_id, sell_time, task = self._pending_auto_sells[order_id]
            task.cancel()
            del self._pending_auto_sells[order_id]
            
            return (f"Cancelled auto-sell for order {order_id}", True)
        
        except Exception as e:
            self.logger.error(f"Failed to cancel auto-sell: {e}", exc_info=True)
            return (f"Failed to cancel: {str(e)}", False)
    
    def get_pending_auto_sells(self) -> str:
        """
        Get a summary of pending auto-sells.
        
        Returns:
            str: Formatted list of pending auto-sells
        """
        if not self._pending_auto_sells:
            return "No pending auto-sells"
        
        lines = ["Pending Auto-Sells:", "=" * 50]
        current_time = time.time()
        
        for order_id, (token_id, sell_time, _) in self._pending_auto_sells.items():
            remaining = max(0, int(sell_time - current_time))
            lines.append(f"Order {order_id}: {token_id[:10]}... in {remaining}s")
        
        return "\n".join(lines)
    
    # Football-specific methods
    def football_set_score(self, home: int, away: int) -> tuple[str, bool]:
        """Set match score (football strategy only)."""
        try:
            print(f"[FOOTBALL_CMD] set_score({home}, {away}) called")
            if self.config.strategy not in ("football", "football_ml"):
                return ("Football commands only available when using football profile", False)
            
            if not self.strategy:
                print(f"[FOOTBALL_CMD] ERROR: No strategy loaded!")
                return ("Football strategy not loaded", False)
            
            self.strategy.match_state.set_score(home, away)
            print(f"[FOOTBALL_CMD] Score updated in match_state: {self.strategy.match_state.home_score}-{self.strategy.match_state.away_score}")
            self.logger.info(f"Score updated to {home}-{away} in match_state")
            return (f"Match score set to {home}-{away}", True)
        except Exception as e:
            return (f"Failed to set score: {str(e)}", False)
    
    def football_set_time(self, minute: int, injury_time: int = 0) -> tuple[str, bool]:
        """Set match time (football strategy only)."""
        try:
            if self.config.strategy not in ("football", "football_ml"):
                return ("Football commands only available when using football profile", False)
            
            if not self.strategy:
                return ("Football strategy not loaded", False)
            
            self.strategy.match_state.set_time(minute, injury_time)
            return (f"Match time set to {minute}'{'+' + str(injury_time) if injury_time else ''}", True)
        except Exception as e:
            return (f"Failed to set time: {str(e)}", False)
    
    def football_timer_start(self) -> tuple[str, bool]:
        """Start match timer (football strategy only)."""
        try:
            if self.config.strategy not in ("football", "football_ml"):
                return ("Football commands only available when using football profile", False)
            
            if not self.strategy:
                return ("Football strategy not loaded", False)
            
            self.strategy.match_state.start_timer()
            self.logger.info(f"Timer started in match_state, is_running={self.strategy.match_state.is_running}")
            return ("Match timer started", True)
        except Exception as e:
            return (f"Failed to start timer: {str(e)}", False)
    
    def football_timer_stop(self) -> tuple[str, bool]:
        """Stop match timer (football strategy only)."""
        try:
            if self.config.strategy not in ("football", "football_ml"):
                return ("Football commands only available when using football profile", False)
            
            if not self.strategy:
                return ("Football strategy not loaded", False)
            
            self.strategy.match_state.stop_timer()
            return ("Match timer stopped", True)
        except Exception as e:
            return (f"Failed to stop timer: {str(e)}", False)
    
    def football_set_side(self, side: str) -> tuple[str, bool]:
        """Set tracked team side (football strategy only)."""
        try:
            if self.config.strategy not in ("football", "football_ml"):
                return ("Football commands only available when using football profile", False)
            
            if not self.strategy:
                return ("Football strategy not loaded", False)
            
            side = side.lower()
            if side not in ("home", "away"):
                return ("Side must be 'home' or 'away'", False)
            
            self.strategy.match_state.match_side = side
            return (f"Tracking {side} team", True)
        except Exception as e:
            return (f"Failed to set side: {str(e)}", False)
    
    def get_widget_data(self) -> Optional[Dict[str, Any]]:
        """Get widget data from current strategy (if applicable)."""
        print(f"[QUICKBUY_MGR] get_widget_data() called, strategy={self.strategy is not None}")
        if self.strategy:
            data = self.strategy.get_widget_data()
            print(f"[QUICKBUY_MGR] strategy.get_widget_data() returned: {data}")
            return data
        print(f"[QUICKBUY_MGR] No strategy loaded, returning None")
        return None
    
    # Football ML strategy methods for match statistics
    def football_set_possession(self, home_pct: float) -> tuple[str, bool]:
        """Set possession percentage (football ML strategy only)."""
        try:
            if self.config.strategy not in ("football", "football_ml"):
                return ("Stats commands only available for football strategies", False)
            
            if not self.strategy or not hasattr(self.strategy, 'match_state'):
                return ("Football strategy not loaded", False)
            
            if home_pct < 0 or home_pct > 100:
                return ("Possession must be between 0 and 100", False)
            
            self.strategy.match_state.set_possession(home_pct)
            return (f"Possession set to {home_pct:.0f}% - {100-home_pct:.0f}%", True)
        except Exception as e:
            return (f"Failed to set possession: {str(e)}", False)
    
    def football_set_shots(self, home: int, away: int) -> tuple[str, bool]:
        """Set shots on target (football ML strategy only)."""
        try:
            if self.config.strategy not in ("football", "football_ml"):
                return ("Stats commands only available for football strategies", False)
            
            if not self.strategy or not hasattr(self.strategy, 'match_state'):
                return ("Football strategy not loaded", False)
            
            self.strategy.match_state.set_shots(home, away)
            return (f"Shots set to {home}-{away}", True)
        except Exception as e:
            return (f"Failed to set shots: {str(e)}", False)
    
    def football_set_corners(self, home: int, away: int) -> tuple[str, bool]:
        """Set corners (football ML strategy only)."""
        try:
            if self.config.strategy not in ("football", "football_ml"):
                return ("Stats commands only available for football strategies", False)
            
            if not self.strategy or not hasattr(self.strategy, 'match_state'):
                return ("Football strategy not loaded", False)
            
            self.strategy.match_state.set_corners(home, away)
            return (f"Corners set to {home}-{away}", True)
        except Exception as e:
            return (f"Failed to set corners: {str(e)}", False)
    
    def football_set_attacks(self, home: int, away: int) -> tuple[str, bool]:
        """Set dangerous attacks (football ML strategy only)."""
        try:
            if self.config.strategy not in ("football", "football_ml"):
                return ("Stats commands only available for football strategies", False)
            
            if not self.strategy or not hasattr(self.strategy, 'match_state'):
                return ("Football strategy not loaded", False)
            
            self.strategy.match_state.set_attacks(home, away)
            return (f"Dangerous attacks set to {home}-{away}", True)
        except Exception as e:
            return (f"Failed to set attacks: {str(e)}", False)
    
    def football_set_momentum(self, momentum: float) -> tuple[str, bool]:
        """Set momentum (football ML strategy only)."""
        try:
            if self.config.strategy not in ("football", "football_ml"):
                return ("Stats commands only available for football strategies", False)
            
            if not self.strategy or not hasattr(self.strategy, 'match_state'):
                return ("Football strategy not loaded", False)
            
            if momentum < -1.0 or momentum > 1.0:
                return ("Momentum must be between -1.0 and +1.0", False)
            
            self.strategy.match_state.set_momentum(momentum)
            return (f"Momentum set to {momentum:+.2f}", True)
        except Exception as e:
            return (f"Failed to set momentum: {str(e)}", False)
