"""
Market Cache - Cache market data for fast lookups
"""
import json
from pathlib import Path
from typing import Optional, Dict, Any, List


class MarketCache:
    """
    Cache for market data (events, slugs, tokens)
    
    Features:
    - Cache event.json (market metadata)
    - Cache slug-to-condition mappings
    - Fast market lookups
    """
    
    def __init__(self, event_path: Path, slug_cache_path: Path):
        """
        Initialize market cache
        
        Args:
            event_path: Path to event.json
            slug_cache_path: Path to slug_cache.json
        """
        self.event_path = event_path
        self.slug_cache_path = slug_cache_path
        
        # Ensure parent directories exist
        self.event_path.parent.mkdir(parents=True, exist_ok=True)
        self.slug_cache_path.parent.mkdir(parents=True, exist_ok=True)
        
        # In-memory caches
        self._event_cache: Optional[Dict[str, Any]] = None
        self._slug_cache: Dict[str, str] = {}
    
    def load_event(self) -> Optional[Dict[str, Any]]:
        """
        Load event.json from cache
        
        Returns:
            Event data dictionary or None
        """
        if self._event_cache is not None:
            return self._event_cache
        
        if not self.event_path.exists():
            return None
        
        try:
            with open(self.event_path, 'r') as f:
                self._event_cache = json.load(f)
            return self._event_cache
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load event cache: {e}")
            return None
    
    def save_event(self, event_data: Dict[str, Any]) -> None:
        """
        Save event data to cache
        
        Args:
            event_data: Event dictionary to save
        """
        try:
            with open(self.event_path, 'w') as f:
                json.dump(event_data, f, indent=2)
            self._event_cache = event_data
        except IOError as e:
            print(f"Warning: Failed to save event cache: {e}")
    
    def load_slug_cache(self) -> Dict[str, str]:
        """
        Load slug-to-condition mappings
        
        Returns:
            Dictionary of slug -> condition_id
        """
        if self._slug_cache:
            return self._slug_cache
        
        if not self.slug_cache_path.exists():
            return {}
        
        try:
            with open(self.slug_cache_path, 'r') as f:
                self._slug_cache = json.load(f)
            return self._slug_cache
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load slug cache: {e}")
            return {}
    
    def save_slug_mapping(self, slug: str, condition_id: str) -> None:
        """
        Save a slug-to-condition mapping
        
        Args:
            slug: Market slug
            condition_id: Condition ID
        """
        self._slug_cache[slug] = condition_id
        
        try:
            with open(self.slug_cache_path, 'w') as f:
                json.dump(self._slug_cache, f, indent=2)
        except IOError as e:
            print(f"Warning: Failed to save slug cache: {e}")
    
    def get_condition_by_slug(self, slug: str) -> Optional[str]:
        """
        Get condition ID by slug
        
        Args:
            slug: Market slug
            
        Returns:
            Condition ID or None
        """
        cache = self.load_slug_cache()
        return cache.get(slug)
    
    def clear(self) -> None:
        """Clear all caches"""
        self._event_cache = None
        self._slug_cache = {}
        
        if self.event_path.exists():
            self.event_path.unlink()
        if self.slug_cache_path.exists():
            self.slug_cache_path.unlink()
