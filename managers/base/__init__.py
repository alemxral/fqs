"""
Base manager classes for PMTerminal.

This module provides foundational manager classes that can be inherited
to create specialized managers with profile-based configuration.
"""
from .profile_config_manager import ProfileConfigManager

__all__ = ["ProfileConfigManager"]
