"""
ProfileConfigManager - Base class for managing profile-based JSON configuration.

Purpose:
- Provide a reusable foundation for any manager that needs profile-based config
- Handle CRUD operations for profiles (Create, Read, Update, Delete)
- Load and save profiles from/to JSON files
- Switch between profiles dynamically
- Abstract configuration details - subclasses define their own config structure

Architecture:
- This is a base class - it should be subclassed, not used directly
- Subclasses must implement abstract methods to define config structure
- Subclasses can add domain-specific logic (e.g., trading, bot control, etc.)

Usage Example:
    class QuickBuyManager(ProfileConfigManager):
        def _create_default_config(self):
            return QuickBuyConfig()
        
        def _load_profile_config(self, profile_data):
            return QuickBuyConfig.from_dict(profile_data)
        
        # Add trading-specific methods
        async def execute_quick_buy(self, ...):
            ...
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from PMTerminal.utils.logger import setup_logger
except Exception:
    import logging
    def setup_logger(name):
        return logging.getLogger(name)


class ProfileConfigManager(ABC):
    """
    Abstract base class for managing profile-based JSON configuration.
    
    This class provides common functionality for:
    - Loading/saving profiles from/to JSON files
    - Switching between profiles
    - Creating and deleting profiles
    - Listing available profiles
    
    Subclasses must implement:
    - _create_default_config(): Create a default configuration instance
    - _load_profile_config(profile_data): Load config from dict
    - _config_to_dict(): Convert config to dict for JSON serialization
    - _on_profile_switched(): Optional hook called after profile switch
    """
    
    def __init__(
        self,
        config_file: Path,
        *,
        logger: Optional[Any] = None,
        default_profile: str = "default"
    ):
        """
        Initialize the profile config manager.
        
        Args:
            config_file: Path to JSON file storing profiles
            logger: Logger instance (optional)
            default_profile: Name of the default profile to use
        """
        self.config_file = config_file
        self.logger = logger or setup_logger(self.__class__.__name__)
        self.default_profile_name = default_profile
        
        # Profile storage
        self.profiles: Dict[str, Dict[str, Any]] = {}
        self.active_profile: str = default_profile
        self.config: Any = None  # Will be set by subclass
        
        # Load configuration at init
        self.load_profiles()
    
    # ============================================================
    # Abstract methods - must be implemented by subclasses
    # ============================================================
    
    @abstractmethod
    def _create_default_config(self) -> Any:
        """
        Create a default configuration instance.
        
        Returns:
            Default configuration object (dataclass, dict, etc.)
        """
        pass
    
    @abstractmethod
    def _load_profile_config(self, profile_data: Dict[str, Any]) -> Any:
        """
        Load configuration from profile data dictionary.
        
        Args:
            profile_data: Dictionary containing profile configuration
        
        Returns:
            Configuration object loaded from data
        """
        pass
    
    @abstractmethod
    def _config_to_dict(self) -> Dict[str, Any]:
        """
        Convert current configuration to dictionary for JSON serialization.
        
        Returns:
            Dictionary representation of configuration
        """
        pass
    
    def _on_profile_switched(self, old_profile: str, new_profile: str) -> None:
        """
        Hook called after a profile switch completes.
        
        Override this in subclasses to perform additional actions when
        switching profiles (e.g., loading strategies, updating UI, etc.)
        
        Args:
            old_profile: Name of the previous profile
            new_profile: Name of the newly activated profile
        """
        pass
    
    def _get_default_profile_data(self) -> Dict[str, Any]:
        """
        Get default profile data as dictionary.
        
        Override this if you need custom default profile data.
        
        Returns:
            Dictionary of default profile data
        """
        config = self._create_default_config()
        if hasattr(config, 'to_dict'):
            return config.to_dict()
        elif hasattr(config, '__dict__'):
            return vars(config)
        else:
            return {}
    
    # ============================================================
    # Public API - used by subclasses and external code
    # ============================================================
    
    def load_profiles(self) -> bool:
        """
        Load all profiles from JSON file.
        
        Returns:
            bool: True if loaded successfully, False otherwise
        """
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                
                # Load all profiles
                self.profiles = data.get('profiles', {})
                self.active_profile = data.get('active_profile', self.default_profile_name)
                
                # Ensure active profile exists
                if self.active_profile not in self.profiles:
                    self.logger.warning(
                        f"Active profile '{self.active_profile}' not found, "
                        f"using '{self.default_profile_name}'"
                    )
                    self.active_profile = self.default_profile_name
                    
                    # Create default if it doesn't exist
                    if self.active_profile not in self.profiles:
                        self.profiles[self.active_profile] = self._get_default_profile_data()
                
                # Load the active profile config
                profile_data = self.profiles.get(self.active_profile, {})
                self.config = self._load_profile_config(profile_data)
                
                self.logger.info(
                    f"Loaded profile '{self.active_profile}' from {self.config_file}"
                )
            else:
                # Create default config file with default profile
                self.logger.info(
                    f"Config file not found, creating default at {self.config_file}"
                )
                self._create_default_profile()
                self.save_profiles()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load profiles: {e}", exc_info=True)
            # Fallback to default config
            self._create_default_profile()
            return False
    
    def save_profiles(self) -> bool:
        """
        Save all profiles to JSON file.
        
        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            # Update timestamp in active profile
            config_dict = self._config_to_dict()
            config_dict['last_updated'] = datetime.now().isoformat()
            
            # Update the active profile in profiles dict
            self.profiles[self.active_profile] = config_dict
            
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
            
            self.logger.info(
                f"Saved profile '{self.active_profile}' to {self.config_file}"
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save profiles: {e}", exc_info=True)
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
                return (
                    f"Profile '{profile_name}' not found. Available: {available}",
                    False
                )
            
            # Save current profile before switching
            self.save_profiles()
            
            # Store old profile name for hook
            old_profile = self.active_profile
            
            # Switch to new profile
            self.active_profile = profile_name
            profile_data = self.profiles[profile_name]
            self.config = self._load_profile_config(profile_data)
            
            # Save to update active_profile in file
            self.save_profiles()
            
            # Call hook for subclass-specific actions
            self._on_profile_switched(old_profile, profile_name)
            
            return (f"Switched to profile: {profile_name}", True)
            
        except Exception as e:
            self.logger.error(f"Failed to switch profile: {e}", exc_info=True)
            return (f"Failed to switch profile: {str(e)}", False)
    
    def list_profiles(self) -> str:
        """
        Get formatted list of all profiles.
        
        Returns:
            str: Formatted string listing all profiles
        """
        if not self.profiles:
            return "No profiles configured"
        
        lines = ["Available Profiles:", "=" * 60]
        for name, data in self.profiles.items():
            active_marker = " (ACTIVE)" if name == self.active_profile else ""
            display_name = data.get('name', name)
            lines.append(f"  {name}{active_marker}")
            lines.append(f"    Name: {display_name}")
            
            # Show last updated if available
            if 'last_updated' in data:
                lines.append(f"    Last Updated: {data['last_updated']}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def create_profile(
        self,
        profile_name: str,
        base_profile: Optional[str] = None
    ) -> tuple[str, bool]:
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
            
            # Use base profile or default
            if base_profile and base_profile in self.profiles:
                new_profile = self.profiles[base_profile].copy()
                new_profile['name'] = profile_name
                self.logger.info(
                    f"Creating profile '{profile_name}' based on '{base_profile}'"
                )
            else:
                # Create default profile
                new_profile = self._get_default_profile_data()
                new_profile['name'] = profile_name
                self.logger.info(f"Creating profile '{profile_name}' with defaults")
            
            # Add to profiles
            self.profiles[profile_name] = new_profile
            self.save_profiles()
            
            return (f"Created profile: {profile_name}", True)
            
        except Exception as e:
            self.logger.error(f"Failed to create profile: {e}", exc_info=True)
            return (f"Failed to create profile: {str(e)}", False)
    
    def delete_profile(self, profile_name: str) -> tuple[str, bool]:
        """
        Delete a profile.
        
        Args:
            profile_name: Name of the profile to delete
        
        Returns:
            tuple: (message, success)
        """
        try:
            if profile_name not in self.profiles:
                return (f"Profile '{profile_name}' not found", False)
            
            if profile_name == self.active_profile:
                return (
                    "Cannot delete active profile. Switch to another profile first.",
                    False
                )
            
            del self.profiles[profile_name]
            self.save_profiles()
            
            self.logger.info(f"Deleted profile: {profile_name}")
            return (f"Deleted profile: {profile_name}", True)
            
        except Exception as e:
            self.logger.error(f"Failed to delete profile: {e}", exc_info=True)
            return (f"Failed to delete profile: {str(e)}", False)
    
    def get_active_profile_name(self) -> str:
        """
        Get the name of the currently active profile.
        
        Returns:
            str: Active profile name
        """
        return self.active_profile
    
    def update_config_property(
        self,
        property_name: str,
        value: Any
    ) -> tuple[str, bool]:
        """
        Update a configuration property in the active profile.
        
        This is a generic method - subclasses should override with
        validation logic specific to their configuration structure.
        
        Args:
            property_name: Name of the property to update
            value: New value for the property
        
        Returns:
            tuple: (message, success)
        """
        try:
            if not hasattr(self.config, property_name):
                return (f"Invalid property '{property_name}'", False)
            
            # Set the property
            setattr(self.config, property_name, value)
            
            # Save to file
            self.save_profiles()
            
            return (f"Updated {property_name} = {value}", True)
            
        except Exception as e:
            self.logger.error(
                f"Failed to update property {property_name}: {e}",
                exc_info=True
            )
            return (f"Failed to update {property_name}: {str(e)}", False)
    
    # ============================================================
    # Internal helper methods
    # ============================================================
    
    def _create_default_profile(self) -> None:
        """Create a default profile and set it as active."""
        self.config = self._create_default_config()
        self.profiles = {
            self.active_profile: self._config_to_dict()
        }
        self.logger.info(f"Created default profile: {self.active_profile}")


__all__ = ["ProfileConfigManager"]
