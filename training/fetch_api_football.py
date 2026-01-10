"""
Fetch live and historical match data from API-Football.

Requires API key from: https://www.api-football.com/
Free tier: 100 requests/day
"""

import requests
import pandas as pd
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional


class APIFootballFetcher:
    """Fetch match data from API-Football."""
    
    BASE_URL = "https://v3.football.api-sports.io"
    
    def __init__(self, api_key: str, output_dir: str = "data/api_football"):
        self.api_key = api_key
        self.headers = {
            'x-rapidapi-host': 'v3.football.api-sports.io',
            'x-rapidapi-key': api_key
        }
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def get_live_fixtures(self) -> List[Dict[str, Any]]:
        """Get all live matches."""
        url = f"{self.BASE_URL}/fixtures?live=all"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            return response.json().get('response', [])
        else:
            print(f"Error: {response.status_code}")
            return []
    
    def get_fixture_by_id(self, fixture_id: int) -> Optional[Dict[str, Any]]:
        """Get fixture details by ID."""
        url = f"{self.BASE_URL}/fixtures?id={fixture_id}"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            results = response.json().get('response', [])
            return results[0] if results else None
        return None
    
    def get_fixture_statistics(self, fixture_id: int) -> List[Dict[str, Any]]:
        """Get match statistics (possession, shots, etc.)."""
        url = f"{self.BASE_URL}/fixtures/statistics?fixture={fixture_id}"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            return response.json().get('response', [])
        return []
    
    def get_fixture_events(self, fixture_id: int) -> List[Dict[str, Any]]:
        """Get match events (goals, cards, substitutions)."""
        url = f"{self.BASE_URL}/fixtures/events?fixture={fixture_id}"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            return response.json().get('response', [])
        return []
    
    def get_league_fixtures(self, league_id: int, season: int, 
                           from_date: str = None, to_date: str = None) -> List[Dict[str, Any]]:
        """Get fixtures for a league/season."""
        url = f"{self.BASE_URL}/fixtures?league={league_id}&season={season}"
        
        if from_date:
            url += f"&from={from_date}"
        if to_date:
            url += f"&to={to_date}"
        
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            return response.json().get('response', [])
        return []
    
    def fixture_to_snapshot(self, fixture_id: int) -> Dict[str, Any]:
        """
        Create a snapshot of match state at current time.
        
        Returns dict with current stats.
        """
        fixture = self.get_fixture_by_id(fixture_id)
        if not fixture:
            return {}
        
        stats = self.get_fixture_statistics(fixture_id)
        events = self.get_fixture_events(fixture_id)
        
        # Extract basic info
        snapshot = {
            'fixture_id': fixture_id,
            'timestamp': datetime.now().isoformat(),
            'minute': fixture['fixture']['status']['elapsed'] or 0,
            'score_home': fixture['goals']['home'] or 0,
            'score_away': fixture['goals']['away'] or 0,
            'home_team': fixture['teams']['home']['name'],
            'away_team': fixture['teams']['away']['name'],
        }
        
        # Parse statistics
        if stats and len(stats) >= 2:
            home_stats = {s['type']: s['value'] for s in stats[0].get('statistics', [])}
            away_stats = {s['type']: s['value'] for s in stats[1].get('statistics', [])}
            
            # Extract key metrics
            snapshot.update({
                'shots_home': self._parse_stat(home_stats.get('Shots on Goal', 0)),
                'shots_away': self._parse_stat(away_stats.get('Shots on Goal', 0)),
                'possession_home': self._parse_stat(home_stats.get('Ball Possession', '50%')),
                'possession_away': self._parse_stat(away_stats.get('Ball Possession', '50%')),
                'corners_home': self._parse_stat(home_stats.get('Corner Kicks', 0)),
                'corners_away': self._parse_stat(away_stats.get('Corner Kicks', 0)),
                'yellow_cards_home': self._parse_stat(home_stats.get('Yellow Cards', 0)),
                'yellow_cards_away': self._parse_stat(away_stats.get('Yellow Cards', 0)),
                'red_cards_home': self._parse_stat(home_stats.get('Red Cards', 0)),
                'red_cards_away': self._parse_stat(away_stats.get('Red Cards', 0)),
            })
        
        # Count events by type
        goals_home = sum(1 for e in events if e['team']['id'] == fixture['teams']['home']['id'] 
                        and e['type'] == 'Goal')
        goals_away = sum(1 for e in events if e['team']['id'] == fixture['teams']['away']['id'] 
                        and e['type'] == 'Goal')
        
        snapshot['goals_from_events_home'] = goals_home
        snapshot['goals_from_events_away'] = goals_away
        
        return snapshot
    
    def _parse_stat(self, value: Any) -> float:
        """Parse stat value (handles percentages and None)."""
        if value is None:
            return 0.0
        if isinstance(value, str):
            # Remove % sign
            return float(value.replace('%', ''))
        return float(value)
    
    def monitor_match(self, fixture_id: int, interval: int = 30, 
                     duration: int = 120) -> pd.DataFrame:
        """
        Monitor a live match and collect time series data.
        
        Args:
            fixture_id: Match ID to monitor
            interval: Seconds between polls
            duration: Minutes to monitor (default: 120 for full match)
        
        Returns:
            DataFrame with snapshots over time
        """
        snapshots = []
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration)
        
        print(f"Monitoring fixture {fixture_id} for {duration} minutes...")
        print(f"Polling every {interval} seconds")
        
        while datetime.now() < end_time:
            try:
                snapshot = self.fixture_to_snapshot(fixture_id)
                if snapshot:
                    snapshots.append(snapshot)
                    minute = snapshot.get('minute', 0)
                    score = f"{snapshot['score_home']}-{snapshot['score_away']}"
                    print(f"  {minute}' - {score} - {len(snapshots)} snapshots")
                
                time.sleep(interval)
            
            except KeyboardInterrupt:
                print("\nStopped by user")
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(interval)
        
        # Convert to DataFrame
        if snapshots:
            df = pd.DataFrame(snapshots)
            
            # Save to CSV
            filename = f"live_monitor_{fixture_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            output_path = self.output_dir / filename
            df.to_csv(output_path, index=False)
            print(f"\nSaved {len(df)} snapshots to {output_path}")
            
            return df
        
        return pd.DataFrame()


def main():
    """Example usage."""
    
    # Replace with your API key
    API_KEY = "YOUR_API_KEY_HERE"
    
    if API_KEY == "YOUR_API_KEY_HERE":
        print("ERROR: Please set your API key!")
        print("Get one at: https://www.api-football.com/")
        return
    
    fetcher = APIFootballFetcher(API_KEY)
    
    # Example 1: Get live matches
    print("Fetching live matches...")
    live = fetcher.get_live_fixtures()
    
    if live:
        print(f"\n{len(live)} live matches:")
        for match in live[:5]:
            home = match['teams']['home']['name']
            away = match['teams']['away']['name']
            score = f"{match['goals']['home']}-{match['goals']['away']}"
            minute = match['fixture']['status']['elapsed']
            print(f"  {match['fixture']['id']}: {home} vs {away} ({score}) - {minute}'")
    else:
        print("No live matches found.")
    
    # Example 2: Monitor a specific match (uncomment to use)
    # fixture_id = 12345  # Replace with actual fixture ID
    # df = fetcher.monitor_match(fixture_id, interval=30, duration=90)


if __name__ == "__main__":
    main()
