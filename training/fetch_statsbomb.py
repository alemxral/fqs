"""
Fetch StatsBomb open event data and convert to time series format.

StatsBomb provides free event-level data for select competitions.
This script downloads matches and creates minute-by-minute snapshots.
"""

import requests
import json
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict


class StatsBombFetcher:
    """Fetch and process StatsBomb open data."""
    
    BASE_URL = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
    
    def __init__(self, output_dir: str = "data/statsbomb"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def get_competitions(self) -> List[Dict[str, Any]]:
        """Fetch available competitions."""
        url = f"{self.BASE_URL}/competitions.json"
        response = requests.get(url)
        return response.json()
    
    def get_matches(self, competition_id: int, season_id: int) -> List[Dict[str, Any]]:
        """Fetch matches for a competition/season."""
        url = f"{self.BASE_URL}/matches/{competition_id}/{season_id}.json"
        response = requests.get(url)
        return response.json()
    
    def get_events(self, match_id: int) -> List[Dict[str, Any]]:
        """Fetch all events for a match."""
        url = f"{self.BASE_URL}/events/{match_id}.json"
        response = requests.get(url)
        return response.json()
    
    def get_lineups(self, match_id: int) -> List[Dict[str, Any]]:
        """Fetch lineups for a match."""
        url = f"{self.BASE_URL}/lineups/{match_id}.json"
        response = requests.get(url)
        return response.json()
    
    def events_to_timeseries(self, match_id: int, match_info: Dict[str, Any]) -> pd.DataFrame:
        """
        Convert event data to minute-by-minute time series.
        
        Returns DataFrame with one row per minute, tracking cumulative stats.
        """
        events = self.get_events(match_id)
        
        home_team = match_info['home_team']['home_team_name']
        away_team = match_info['away_team']['away_team_name']
        
        # Initialize tracking
        timeline = defaultdict(lambda: {
            'match_id': match_id,
            'minute': 0,
            'score_home': 0,
            'score_away': 0,
            'shots_home': 0,
            'shots_away': 0,
            'corners_home': 0,
            'corners_away': 0,
            'yellow_cards_home': 0,
            'yellow_cards_away': 0,
            'red_cards_home': 0,
            'red_cards_away': 0,
            'passes_home': 0,
            'passes_away': 0,
            'possession_home': 50.0,
            'dangerous_attacks_home': 0,
            'dangerous_attacks_away': 0,
        })
        
        # Process events
        for event in events:
            minute = event.get('minute', 0)
            team_name = event.get('team', {}).get('name', '')
            event_type = event.get('type', {}).get('name', '')
            
            is_home = team_name == home_team
            
            # Update counters
            if event_type == 'Shot':
                if is_home:
                    timeline[minute]['shots_home'] += 1
                    # Check if goal
                    if event.get('shot', {}).get('outcome', {}).get('name') == 'Goal':
                        timeline[minute]['score_home'] += 1
                else:
                    timeline[minute]['shots_away'] += 1
                    if event.get('shot', {}).get('outcome', {}).get('name') == 'Goal':
                        timeline[minute]['score_away'] += 1
            
            elif event_type == 'Pass':
                if is_home:
                    timeline[minute]['passes_home'] += 1
                else:
                    timeline[minute]['passes_away'] += 1
            
            elif event_type == 'Foul Committed':
                card = event.get('foul_committed', {}).get('card', {}).get('name')
                if card == 'Yellow Card':
                    if is_home:
                        timeline[minute]['yellow_cards_home'] += 1
                    else:
                        timeline[minute]['yellow_cards_away'] += 1
                elif card in ['Red Card', 'Second Yellow']:
                    if is_home:
                        timeline[minute]['red_cards_home'] += 1
                    else:
                        timeline[minute]['red_cards_away'] += 1
        
        # Create cumulative timeline (0-90+ minutes)
        max_minute = max(timeline.keys()) if timeline else 90
        rows = []
        
        cumulative = {
            'score_home': 0,
            'score_away': 0,
            'shots_home': 0,
            'shots_away': 0,
            'yellow_cards_home': 0,
            'yellow_cards_away': 0,
            'red_cards_home': 0,
            'red_cards_away': 0,
            'passes_home': 0,
            'passes_away': 0,
        }
        
        for minute in range(0, int(max_minute) + 1):
            # Update cumulative from this minute's events
            minute_data = timeline[minute]
            for key in cumulative:
                cumulative[key] += minute_data[key]
            
            # Calculate possession based on passes
            total_passes = cumulative['passes_home'] + cumulative['passes_away']
            if total_passes > 0:
                possession_home = (cumulative['passes_home'] / total_passes) * 100
            else:
                possession_home = 50.0
            
            rows.append({
                'match_id': match_id,
                'minute': minute,
                'score_home': cumulative['score_home'],
                'score_away': cumulative['score_away'],
                'goal_diff': cumulative['score_home'] - cumulative['score_away'],
                'shots_home': cumulative['shots_home'],
                'shots_away': cumulative['shots_away'],
                'shots_diff': cumulative['shots_home'] - cumulative['shots_away'],
                'yellow_cards_home': cumulative['yellow_cards_home'],
                'yellow_cards_away': cumulative['yellow_cards_away'],
                'red_cards_home': cumulative['red_cards_home'],
                'red_cards_away': cumulative['red_cards_away'],
                'possession_home': possession_home,
                'possession_diff': possession_home - 50.0,
                'home_team': home_team,
                'away_team': away_team,
            })
        
        return pd.DataFrame(rows)
    
    def download_competition(self, competition_id: int, season_id: int, 
                           competition_name: str = None) -> pd.DataFrame:
        """
        Download all matches from a competition and create time series dataset.
        """
        print(f"Fetching matches for competition {competition_id}, season {season_id}...")
        matches = self.get_matches(competition_id, season_id)
        
        all_timeseries = []
        
        for i, match in enumerate(matches):
            match_id = match['match_id']
            print(f"Processing match {i+1}/{len(matches)}: {match_id}")
            
            try:
                ts = self.events_to_timeseries(match_id, match)
                all_timeseries.append(ts)
            except Exception as e:
                print(f"  Error processing match {match_id}: {e}")
                continue
        
        # Combine all matches
        if all_timeseries:
            df = pd.concat(all_timeseries, ignore_index=True)
            
            # Save to CSV
            filename = f"timeseries_comp{competition_id}_season{season_id}.csv"
            output_path = self.output_dir / filename
            df.to_csv(output_path, index=False)
            print(f"\nSaved {len(df)} rows to {output_path}")
            
            return df
        else:
            print("No data collected.")
            return pd.DataFrame()


def main():
    """Download StatsBomb data and create time series datasets."""
    
    fetcher = StatsBombFetcher()
    
    # Get available competitions
    print("Fetching available competitions...")
    competitions = fetcher.get_competitions()
    
    print("\nAvailable competitions:")
    for comp in competitions[:10]:  # Show first 10
        print(f"  {comp['competition_id']}: {comp['competition_name']} "
              f"({comp['season_name']}) - Season ID: {comp['season_id']}")
    
    # Example: Download FIFA World Cup 2018
    # Competition ID: 43, Season ID: 3
    print("\n" + "="*60)
    print("Downloading FIFA World Cup 2018...")
    print("="*60)
    
    df = fetcher.download_competition(
        competition_id=43,
        season_id=3,
        competition_name="FIFA World Cup 2018"
    )
    
    if not df.empty:
        print("\nDataset preview:")
        print(df.head(10))
        print(f"\nShape: {df.shape}")
        print(f"Matches: {df['match_id'].nunique()}")
        print(f"Total minutes: {len(df)}")


if __name__ == "__main__":
    main()
