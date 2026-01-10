"""
Example: Visualize what the data looks like from different sources.
Run this to see actual data structure and format.
"""

import json
import pandas as pd
from pathlib import Path


# ============================================================================
# EXAMPLE 1: StatsBomb Event Data (Raw JSON)
# ============================================================================

statsbomb_events_example = [
    {
        "id": "abc123",
        "index": 1,
        "period": 1,
        "timestamp": "00:00:23.456",
        "minute": 0,
        "second": 23,
        "type": {"id": 30, "name": "Pass"},
        "possession": 1,
        "possession_team": {"id": 123, "name": "Arsenal"},
        "play_pattern": {"id": 1, "name": "Regular Play"},
        "team": {"id": 123, "name": "Arsenal"},
        "player": {"id": 5678, "name": "Martin Ødegaard"},
        "position": {"id": 10, "name": "Central Attacking Midfield"},
        "location": [61.0, 40.5],
        "duration": 1.2,
        "pass": {
            "recipient": {"id": 5679, "name": "Bukayo Saka"},
            "length": 15.3,
            "angle": 0.45,
            "height": {"id": 1, "name": "Ground Pass"},
            "end_location": [75.0, 42.0],
            "outcome": {"id": 9, "name": "Complete"}
        }
    },
    {
        "id": "def456",
        "index": 234,
        "period": 1,
        "timestamp": "00:23:12.789",
        "minute": 23,
        "second": 12,
        "type": {"id": 16, "name": "Shot"},
        "possession": 45,
        "possession_team": {"id": 123, "name": "Arsenal"},
        "team": {"id": 123, "name": "Arsenal"},
        "player": {"id": 5680, "name": "Gabriel Jesus"},
        "location": [102.0, 38.0],
        "shot": {
            "statsbomb_xg": 0.32,
            "end_location": [120.0, 38.0, 2.1],
            "outcome": {"id": 97, "name": "Goal"},
            "type": {"id": 87, "name": "Open Play"},
            "body_part": {"id": 40, "name": "Right Foot"},
            "technique": {"id": 93, "name": "Normal"}
        }
    },
    {
        "id": "ghi789",
        "index": 235,
        "period": 1,
        "timestamp": "00:23:13.000",
        "minute": 23,
        "second": 13,
        "type": {"id": 41, "name": "Foul Committed"},
        "possession": 45,
        "possession_team": {"id": 123, "name": "Arsenal"},
        "team": {"id": 456, "name": "Chelsea"},
        "player": {"id": 7890, "name": "Enzo Fernández"},
        "foul_committed": {
            "counterpress": False,
            "type": {"id": 24, "name": "Foul"},
            "card": {"id": 65, "name": "Yellow Card"}
        }
    }
]


# ============================================================================
# EXAMPLE 2: Time Series Data (After Processing)
# ============================================================================

timeseries_example = pd.DataFrame([
    # Minute 0 - Match starts
    {
        'match_id': 12345,
        'minute': 0,
        'score_home': 0,
        'score_away': 0,
        'goal_diff': 0,
        'shots_home': 0,
        'shots_away': 0,
        'corners_home': 0,
        'corners_away': 0,
        'possession_home': 50.0,
        'yellow_cards_home': 0,
        'yellow_cards_away': 0,
        'red_cards_home': 0,
        'red_cards_away': 0,
        'home_team': 'Arsenal',
        'away_team': 'Chelsea'
    },
    # Minute 23 - HOME GOAL!
    {
        'match_id': 12345,
        'minute': 23,
        'score_home': 1,  # ⚽ GOAL!
        'score_away': 0,
        'goal_diff': 1,
        'shots_home': 4,
        'shots_away': 2,
        'corners_home': 3,
        'corners_away': 1,
        'possession_home': 58.3,
        'yellow_cards_home': 0,
        'yellow_cards_away': 1,  # Yellow card given
        'red_cards_home': 0,
        'red_cards_away': 0,
        'home_team': 'Arsenal',
        'away_team': 'Chelsea'
    },
    # Minute 45 - Halftime
    {
        'match_id': 12345,
        'minute': 45,
        'score_home': 1,
        'score_away': 0,
        'goal_diff': 1,
        'shots_home': 6,
        'shots_away': 3,
        'corners_home': 5,
        'corners_away': 2,
        'possession_home': 56.2,
        'yellow_cards_home': 1,
        'yellow_cards_away': 2,
        'red_cards_home': 0,
        'red_cards_away': 0,
        'home_team': 'Arsenal',
        'away_team': 'Chelsea'
    },
    # Minute 67 - AWAY GOAL!
    {
        'match_id': 12345,
        'minute': 67,
        'score_home': 1,
        'score_away': 1,  # ⚽ GOAL!
        'goal_diff': 0,
        'shots_home': 9,
        'shots_away': 7,
        'corners_home': 6,
        'corners_away': 4,
        'possession_home': 52.1,
        'yellow_cards_home': 2,
        'yellow_cards_away': 3,
        'red_cards_home': 0,
        'red_cards_away': 0,
        'home_team': 'Arsenal',
        'away_team': 'Chelsea'
    },
    # Minute 83 - RED CARD!
    {
        'match_id': 12345,
        'minute': 83,
        'score_home': 1,
        'score_away': 1,
        'goal_diff': 0,
        'shots_home': 11,
        'shots_away': 8,
        'corners_home': 7,
        'corners_away': 5,
        'possession_home': 61.3,  # More possession after red card
        'yellow_cards_home': 2,
        'yellow_cards_away': 3,
        'red_cards_home': 0,
        'red_cards_away': 1,  # 🟥 RED CARD!
        'home_team': 'Arsenal',
        'away_team': 'Chelsea'
    },
    # Minute 90 - Full time
    {
        'match_id': 12345,
        'minute': 90,
        'score_home': 2,  # ⚽ Late winner!
        'score_away': 1,
        'goal_diff': 1,
        'shots_home': 14,
        'shots_away': 8,
        'corners_home': 9,
        'corners_away': 5,
        'possession_home': 64.5,
        'yellow_cards_home': 2,
        'yellow_cards_away': 3,
        'red_cards_home': 0,
        'red_cards_away': 1,
        'home_team': 'Arsenal',
        'away_team': 'Chelsea'
    }
])


# ============================================================================
# EXAMPLE 3: API-Football Response (Live Match)
# ============================================================================

api_football_fixture = {
    "fixture": {
        "id": 12345,
        "referee": "Michael Oliver",
        "timezone": "UTC",
        "date": "2026-01-07T20:00:00+00:00",
        "timestamp": 1704657600,
        "venue": {
            "id": 494,
            "name": "Emirates Stadium",
            "city": "London"
        },
        "status": {
            "long": "Match Finished",
            "short": "FT",
            "elapsed": 90  # Current minute
        }
    },
    "league": {
        "id": 39,
        "name": "Premier League",
        "country": "England",
        "logo": "https://...",
        "season": 2025
    },
    "teams": {
        "home": {
            "id": 42,
            "name": "Arsenal",
            "logo": "https://...",
            "winner": True
        },
        "away": {
            "id": 49,
            "name": "Chelsea",
            "logo": "https://...",
            "winner": False
        }
    },
    "goals": {
        "home": 2,  # Final score
        "away": 1
    },
    "score": {
        "halftime": {"home": 1, "away": 0},
        "fulltime": {"home": 2, "away": 1},
        "extratime": {"home": None, "away": None},
        "penalty": {"home": None, "away": None}
    }
}

api_football_events = [
    {
        "time": {"elapsed": 23, "extra": None},
        "team": {"id": 42, "name": "Arsenal", "logo": "https://..."},
        "player": {"id": 5680, "name": "Gabriel Jesus"},
        "assist": {"id": 5678, "name": "M. Ødegaard"},
        "type": "Goal",
        "detail": "Normal Goal",
        "comments": None
    },
    {
        "time": {"elapsed": 23, "extra": None},
        "team": {"id": 49, "name": "Chelsea", "logo": "https://..."},
        "player": {"id": 7890, "name": "E. Fernández"},
        "assist": {"id": None, "name": None},
        "type": "Card",
        "detail": "Yellow Card",
        "comments": "Foul"
    },
    {
        "time": {"elapsed": 67, "extra": None},
        "team": {"id": 49, "name": "Chelsea", "logo": "https://..."},
        "player": {"id": 7891, "name": "N. Jackson"},
        "assist": {"id": 7892, "name": "C. Palmer"},
        "type": "Goal",
        "detail": "Normal Goal",
        "comments": None
    },
    {
        "time": {"elapsed": 83, "extra": None},
        "team": {"id": 49, "name": "Chelsea", "logo": "https://..."},
        "player": {"id": 7890, "name": "E. Fernández"},
        "assist": {"id": None, "name": None},
        "type": "Card",
        "detail": "Red Card",
        "comments": "Second yellow card"
    },
    {
        "time": {"elapsed": 90, "extra": 2},
        "team": {"id": 42, "name": "Arsenal", "logo": "https://..."},
        "player": {"id": 5679, "name": "B. Saka"},
        "assist": {"id": 5680, "name": "G. Jesus"},
        "type": "Goal",
        "detail": "Normal Goal",
        "comments": "Counter-attack"
    }
]

api_football_statistics = [
    {
        "team": {"id": 42, "name": "Arsenal"},
        "statistics": [
            {"type": "Shots on Goal", "value": 14},
            {"type": "Shots off Goal", "value": 8},
            {"type": "Total Shots", "value": 22},
            {"type": "Blocked Shots", "value": 3},
            {"type": "Shots insidebox", "value": 16},
            {"type": "Shots outsidebox", "value": 6},
            {"type": "Fouls", "value": 12},
            {"type": "Corner Kicks", "value": 9},
            {"type": "Offsides", "value": 2},
            {"type": "Ball Possession", "value": "64%"},
            {"type": "Yellow Cards", "value": 2},
            {"type": "Red Cards", "value": 0},
            {"type": "Goalkeeper Saves", "value": 4},
            {"type": "Total passes", "value": 587},
            {"type": "Passes accurate", "value": 512},
            {"type": "Passes %", "value": "87%"}
        ]
    },
    {
        "team": {"id": 49, "name": "Chelsea"},
        "statistics": [
            {"type": "Shots on Goal", "value": 8},
            {"type": "Shots off Goal", "value": 5},
            {"type": "Total Shots", "value": 13},
            {"type": "Blocked Shots", "value": 2},
            {"type": "Shots insidebox", "value": 9},
            {"type": "Shots outsidebox", "value": 4},
            {"type": "Fouls", "value": 15},
            {"type": "Corner Kicks", "value": 5},
            {"type": "Offsides", "value": 3},
            {"type": "Ball Possession", "value": "36%"},
            {"type": "Yellow Cards", "value": 3},
            {"type": "Red Cards", "value": 1},
            {"type": "Goalkeeper Saves", "value": 7},
            {"type": "Total passes", "value": 342},
            {"type": "Passes accurate", "value": 278},
            {"type": "Passes %", "value": "81%"}
        ]
    }
]


# ============================================================================
# EXAMPLE 4: Training Dataset (Goals with Context)
# ============================================================================

training_data_example = pd.DataFrame([
    {
        # Arsenal scores at 23' while drawing 0-0
        'match_id': 12345,
        'minute': 23,
        'prev_score_home': 0,
        'prev_score_away': 0,
        'new_score_home': 1,
        'new_score_away': 0,
        'goal_by_home': 1,
        'goal_diff_before': 0,
        'goal_diff_after': 1,
        'shots_home': 4,
        'shots_away': 2,
        'shots_diff': 2,
        'possession_home': 58.3,
        'possession_diff': 8.3,
        'yellow_cards_home': 0,
        'yellow_cards_away': 1,
        'red_cards_home': 0,
        'red_cards_away': 0,
        'is_losing': 0,
        'is_drawing': 1,
        'is_winning': 0,
        'late_game': 0,
        'prob_before': 0.33,  # 33% win probability
        'prob_after': 0.55,   # Jumps to 55%
        'prob_change': 0.22   # +22% jump! (TARGET VARIABLE)
    },
    {
        # Chelsea equalizes at 67' while losing 0-1
        'match_id': 12345,
        'minute': 67,
        'prev_score_home': 1,
        'prev_score_away': 0,
        'new_score_home': 1,
        'new_score_away': 1,
        'goal_by_home': 0,
        'goal_diff_before': 1,
        'goal_diff_after': 0,
        'shots_home': 9,
        'shots_away': 7,
        'shots_diff': 2,
        'possession_home': 52.1,
        'possession_diff': 2.1,
        'yellow_cards_home': 2,
        'yellow_cards_away': 3,
        'red_cards_home': 0,
        'red_cards_away': 0,
        'is_losing': 0,  # For away team perspective
        'is_drawing': 0,
        'is_winning': 0,
        'late_game': 0,
        'prob_before': 0.20,  # Chelsea 20% to win
        'prob_after': 0.33,   # Jumps to 33%
        'prob_change': 0.13   # +13% jump
    },
    {
        # Arsenal scores winner at 90' with man advantage (Chelsea red card 83')
        'match_id': 12345,
        'minute': 90,
        'prev_score_home': 1,
        'prev_score_away': 1,
        'new_score_home': 2,
        'new_score_away': 1,
        'goal_by_home': 1,
        'goal_diff_before': 0,
        'goal_diff_after': 1,
        'shots_home': 14,
        'shots_away': 8,
        'shots_diff': 6,
        'possession_home': 64.5,
        'possession_diff': 14.5,
        'yellow_cards_home': 2,
        'yellow_cards_away': 3,
        'red_cards_home': 0,
        'red_cards_away': 1,  # Chelsea down to 10 men!
        'is_losing': 0,
        'is_drawing': 1,
        'is_winning': 0,
        'late_game': 1,  # After 75'
        'prob_before': 0.40,  # Higher due to man advantage
        'prob_after': 0.95,   # Almost certain now
        'prob_change': 0.55   # +55% HUGE jump! (late + man advantage)
    }
])


# ============================================================================
# DISPLAY FUNCTIONS
# ============================================================================

def print_section(title: str):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def show_examples():
    """Display all data format examples."""
    
    print_section("EXAMPLE 1: StatsBomb Raw Event Data (JSON)")
    print("\nWhat you download from StatsBomb:")
    print(json.dumps(statsbomb_events_example[1], indent=2))  # Show the goal
    
    print("\nKey info:")
    print("  ✓ Exact timestamp: 00:23:12.789")
    print("  ✓ Event type: Shot → Goal")
    print("  ✓ Player: Gabriel Jesus")
    print("  ✓ xG: 0.32 (expected goals)")
    
    
    print_section("EXAMPLE 2: Processed Time Series (CSV)")
    print("\nAfter processing events into minute-by-minute snapshots:")
    print(timeseries_example.to_string(index=False))
    
    print("\n\nHow to use:")
    print("  → Each row = match state at that minute")
    print("  → Score changes = goals scored")
    print("  → All stats are cumulative")
    print("  → Feed this into your ML model")
    
    
    print_section("EXAMPLE 3: API-Football Live Data")
    print("\nMatch Summary:")
    print(json.dumps(api_football_fixture['goals'], indent=2))
    print(json.dumps(api_football_fixture['status'], indent=2))
    
    print("\n\nEvents (goals, cards):")
    for event in api_football_events:
        minute = event['time']['elapsed']
        extra = f"+{event['time']['extra']}" if event['time']['extra'] else ""
        player = event['player']['name']
        event_type = event['type']
        detail = event['detail']
        print(f"  {minute}'{extra} - {player}: {event_type} ({detail})")
    
    print("\n\nLive Statistics:")
    for team_stats in api_football_statistics:
        print(f"\n  {team_stats['team']['name']}:")
        for stat in team_stats['statistics'][:8]:  # Show first 8
            print(f"    {stat['type']:20s}: {stat['value']}")
    
    
    print_section("EXAMPLE 4: Training Dataset (Features + Target)")
    print("\nData ready for ML training:")
    print(training_data_example[['minute', 'goal_diff_before', 'shots_diff', 
                                  'possession_diff', 'red_cards_away', 
                                  'late_game', 'prob_change']].to_string(index=False))
    
    print("\n\nWhat this shows:")
    print("  → Minute 23: Home scores while drawing → +22% probability jump")
    print("  → Minute 67: Away scores while losing → +13% probability jump")
    print("  → Minute 90: Home scores (late + man advantage) → +55% MASSIVE jump!")
    
    print("\n\nThese 'prob_change' values are what you train your model to predict!")
    
    
    print_section("SUMMARY: Timeline View")
    print("""
    0'  ⚪ 0-0 | Arsenal 50% poss, 0 shots | Chelsea 0 shots
    
    23' ⚽ 1-0 | Arsenal GOAL! (G. Jesus)
             | Arsenal 58% poss, 4 shots | Chelsea 2 shots, 1 yellow
             | WIN PROBABILITY: 33% → 55% (+22%)
    
    45' 🕐 HT  | Arsenal 56% poss, 6 shots | Chelsea 3 shots, 2 yellows
    
    67' ⚽ 1-1 | Chelsea GOAL! (N. Jackson)
             | Arsenal 52% poss, 9 shots | Chelsea 7 shots
             | WIN PROBABILITY: 55% → 40% (-15%)
    
    83' 🟥 1-1 | Chelsea RED CARD! (E. Fernández)
             | Arsenal now 11v10
             | WIN PROBABILITY: 40% → 65% (+25%)
    
    90' ⚽ 2-1 | Arsenal GOAL! (B. Saka) - WINNER!
             | Arsenal 64% poss, 14 shots | Chelsea 8 shots (10 men)
             | WIN PROBABILITY: 65% → 95% (+30%)
    
    FT  🏁 2-1 | Arsenal wins
    """)
    
    
    print_section("HOW TO GET THIS DATA")
    print("""
    1. TRAINING DATA (Historical):
       python training/fetch_statsbomb.py
       → Downloads World Cup 2018 (64 matches)
       → Minute-by-minute time series
       → FREE
    
    2. LIVE DATA (Real-time trading):
       python training/fetch_api_football.py
       → Set your API key
       → Monitor live matches
       → Get stats every 30 seconds
       → Free tier: 100 requests/day
    
    3. TRAIN YOUR MODEL:
       python training/train_model.py
       → Learns probability jumps from historical goals
       → Exports coefficients to use in strategy
       → R² score shows accuracy
    """)


if __name__ == "__main__":
    show_examples()
    
    # Save examples to files for reference
    print_section("SAVING EXAMPLES")
    
    output_dir = Path("training/examples")
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # Save time series example
    timeseries_example.to_csv(output_dir / "timeseries_example.csv", index=False)
    print(f"✓ Saved: {output_dir / 'timeseries_example.csv'}")
    
    # Save training data example
    training_data_example.to_csv(output_dir / "training_data_example.csv", index=False)
    print(f"✓ Saved: {output_dir / 'training_data_example.csv'}")
    
    # Save JSON examples
    with open(output_dir / "statsbomb_events_example.json", 'w') as f:
        json.dump(statsbomb_events_example, f, indent=2)
    print(f"✓ Saved: {output_dir / 'statsbomb_events_example.json'}")
    
    with open(output_dir / "api_football_example.json", 'w') as f:
        json.dump({
            'fixture': api_football_fixture,
            'events': api_football_events,
            'statistics': api_football_statistics
        }, f, indent=2)
    print(f"✓ Saved: {output_dir / 'api_football_example.json'}")
    
    print("\n✅ All examples saved to training/examples/")
