# Data Cache Directory

This directory stores cached JSON data from Polymarket APIs to reduce API calls and improve performance.

## Cache Files

### `live_football_matches.json`
- **Source**: Gamma API via `get_live_football_matches()` utility
- **Updated**: On app startup and when `/api/markets/football/live` endpoint is called
- **TTL**: 5 minutes
- **Structure**:
  ```json
  {
    "metadata": {
      "total_matches": 42,
      "extraction_timestamp": "2026-01-11T14:30:00.123456",
      "source": "Gamma API /sports endpoint",
      "ttl_seconds": 300
    },
    "matches": [
      {
        "slug": "epl-tot-ast-2026-01-11",
        "id": "12345",
        "title": "Tottenham vs Aston Villa",
        "startDate": "2026-01-11T15:00:00Z",
        "endDate": "2026-01-11T17:00:00Z",
        ...
      }
    ]
  }
  ```

### `all_active_markets.json`
- **Source**: Home screen market fetching
- **Updated**: When home screen loads markets
- **TTL**: 10 minutes
- **Structure**: Same as `live_football_matches.json` but includes all sports

## Cache Management

The `utils/core/cache_manager.py` module provides:
- **`read_cache(filename, ttl_seconds)`**: Read cache if not expired
- **`write_cache(filename, data, metadata)`**: Write data with timestamp
- **`is_cache_valid(filename, ttl_seconds)`**: Check if cache is still fresh
- **`clear_cache(filename)`**: Remove specific cache file

## Notes

- All cache files are gitignored
- Cache is stored as pretty-printed JSON for debugging
- Expired cache can still be used as fallback during API failures
- Cache directory is automatically created if missing
