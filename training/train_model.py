"""
Train linear regression model on historical time series data.

This script:
1. Loads time series match data
2. Calculates probability changes after goals
3. Trains a regression model
4. Exports coefficients for use in trading strategy
"""

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from typing import Dict, Tuple
import json


class FootballModelTrainer:
    """Train probability prediction model from time series data."""
    
    def __init__(self, data_path: str):
        self.data_path = Path(data_path)
        self.df = None
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = []
    
    def load_data(self) -> pd.DataFrame:
        """Load time series CSV data."""
        print(f"Loading data from {self.data_path}...")
        self.df = pd.read_csv(self.data_path)
        print(f"Loaded {len(self.df)} rows, {self.df['match_id'].nunique()} matches")
        return self.df
    
    def calculate_probability_changes(self) -> pd.DataFrame:
        """
        Calculate probability change after each goal.
        
        This simulates what would happen in betting markets:
        - When home team scores, home win probability jumps
        - Use historical betting odds or simple heuristics
        """
        results = []
        
        for match_id in self.df['match_id'].unique():
            match_df = self.df[self.df['match_id'] == match_id].sort_values('minute')
            
            # Get final score to determine winner
            final_score_home = match_df.iloc[-1]['score_home']
            final_score_away = match_df.iloc[-1]['score_away']
            
            if final_score_home > final_score_away:
                final_result = 'home'
            elif final_score_away > final_score_home:
                final_result = 'away'
            else:
                final_result = 'draw'
            
            # Process minute by minute
            prev_score_home = 0
            prev_score_away = 0
            prev_prob_home = 0.33  # Start with equal probabilities
            
            for idx, row in match_df.iterrows():
                current_score_home = row['score_home']
                current_score_away = row['score_away']
                
                # Calculate current win probability (simple heuristic)
                # In reality, you'd use betting odds
                current_prob_home = self._estimate_win_probability(
                    row['minute'],
                    current_score_home,
                    current_score_away,
                    final_result
                )
                
                # Check if goal scored this minute
                goal_scored = (current_score_home != prev_score_home or 
                             current_score_away != prev_score_away)
                
                if goal_scored and row['minute'] > 0:
                    # Calculate probability jump
                    prob_change = current_prob_home - prev_prob_home
                    
                    # Extract features at time of goal
                    features = {
                        'match_id': match_id,
                        'minute': row['minute'],
                        'prev_score_home': prev_score_home,
                        'prev_score_away': prev_score_away,
                        'goal_diff_before': prev_score_home - prev_score_away,
                        'goal_by_home': 1 if current_score_home > prev_score_home else 0,
                        'shots_home': row.get('shots_home', 0),
                        'shots_away': row.get('shots_away', 0),
                        'shots_diff': row.get('shots_diff', 0),
                        'possession_home': row.get('possession_home', 50),
                        'possession_diff': row.get('possession_diff', 0),
                        'yellow_cards_home': row.get('yellow_cards_home', 0),
                        'yellow_cards_away': row.get('yellow_cards_away', 0),
                        'red_cards_home': row.get('red_cards_home', 0),
                        'red_cards_away': row.get('red_cards_away', 0),
                        'is_losing': 1 if prev_score_home < prev_score_away else 0,
                        'is_drawing': 1 if prev_score_home == prev_score_away else 0,
                        'late_game': 1 if row['minute'] >= 75 else 0,
                        'prob_change': prob_change,
                        'prob_before': prev_prob_home,
                        'prob_after': current_prob_home,
                    }
                    
                    results.append(features)
                
                prev_score_home = current_score_home
                prev_score_away = current_score_away
                prev_prob_home = current_prob_home
        
        return pd.DataFrame(results)
    
    def _estimate_win_probability(self, minute: int, score_home: int, 
                                  score_away: int, final_result: str) -> float:
        """
        Estimate win probability at given game state.
        
        Simple heuristic - in production, use actual betting odds.
        """
        goal_diff = score_home - score_away
        time_remaining = 90 - minute
        
        # Base probability on score
        if goal_diff >= 2:
            base_prob = 0.75
        elif goal_diff == 1:
            base_prob = 0.55
        elif goal_diff == 0:
            base_prob = 0.33
        elif goal_diff == -1:
            base_prob = 0.20
        else:
            base_prob = 0.10
        
        # Adjust for time (less certain early in match)
        time_factor = 1 - (time_remaining / 90) * 0.3
        
        # Adjust based on final result (hindsight knowledge for training)
        if final_result == 'home':
            result_adjustment = 0.1
        elif final_result == 'away':
            result_adjustment = -0.1
        else:
            result_adjustment = 0.0
        
        prob = base_prob * time_factor + result_adjustment
        return max(0.01, min(0.99, prob))
    
    def prepare_features(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, list]:
        """Prepare feature matrix and target vector."""
        
        feature_cols = [
            'minute',
            'goal_diff_before',
            'shots_diff',
            'possession_diff',
            'yellow_cards_home',
            'yellow_cards_away',
            'red_cards_home',
            'red_cards_away',
            'is_losing',
            'is_drawing',
            'late_game',
        ]
        
        X = df[feature_cols].values
        y = df['prob_change'].values
        
        self.feature_names = feature_cols
        
        return X, y, feature_cols
    
    def train(self, X: np.ndarray, y: np.ndarray, model_type: str = 'linear') -> Dict:
        """
        Train regression model.
        
        Args:
            X: Feature matrix
            y: Target (probability change)
            model_type: 'linear', 'ridge', or 'lasso'
        """
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Choose model
        if model_type == 'ridge':
            self.model = Ridge(alpha=1.0)
        elif model_type == 'lasso':
            self.model = Lasso(alpha=0.01)
        else:
            self.model = LinearRegression()
        
        # Train
        print(f"\nTraining {model_type} regression model...")
        self.model.fit(X_train, y_train)
        
        # Evaluate
        train_score = self.model.score(X_train, y_train)
        test_score = self.model.score(X_test, y_test)
        
        # Cross-validation
        cv_scores = cross_val_score(self.model, X, y, cv=5)
        
        print(f"Train R²: {train_score:.4f}")
        print(f"Test R²: {test_score:.4f}")
        print(f"CV R² (mean): {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")
        
        return {
            'train_score': train_score,
            'test_score': test_score,
            'cv_scores': cv_scores.tolist(),
            'cv_mean': cv_scores.mean(),
            'cv_std': cv_scores.std(),
        }
    
    def export_coefficients(self, output_path: str = "coefficients.json"):
        """Export model coefficients for use in trading strategy."""
        
        if self.model is None:
            raise ValueError("Model not trained yet!")
        
        coefficients = {
            'intercept': float(self.model.intercept_),
            'features': {}
        }
        
        for name, coef in zip(self.feature_names, self.model.coef_):
            coefficients['features'][name] = float(coef)
        
        # Map to strategy format
        strategy_coefficients = {
            'intercept': coefficients['intercept'],
            'time_factor': coefficients['features'].get('minute', 0.0) / 90,  # Normalize
            'goal_diff': coefficients['features'].get('goal_diff_before', 0.0),
            'shots_diff': coefficients['features'].get('shots_diff', 0.0),
            'possession_diff': coefficients['features'].get('possession_diff', 0.0),
            'is_losing': coefficients['features'].get('is_losing', 0.0),
            'late_game': coefficients['features'].get('late_game', 0.0),
        }
        
        # Save both formats
        output = {
            'raw_coefficients': coefficients,
            'strategy_coefficients': strategy_coefficients,
            'feature_names': self.feature_names,
            'model_type': type(self.model).__name__,
        }
        
        output_path = Path(output_path)
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\nCoefficients exported to {output_path}")
        print("\nStrategy coefficients:")
        for key, value in strategy_coefficients.items():
            print(f"  {key}: {value:.6f}")
        
        return strategy_coefficients
    
    def print_feature_importance(self):
        """Print feature importance (coefficient magnitudes)."""
        
        if self.model is None:
            raise ValueError("Model not trained yet!")
        
        importance = list(zip(self.feature_names, self.model.coef_))
        importance.sort(key=lambda x: abs(x[1]), reverse=True)
        
        print("\nFeature Importance (by |coefficient|):")
        for name, coef in importance:
            print(f"  {name:20s}: {coef:+.6f}")


def main():
    """Train model on StatsBomb data."""
    
    # Path to your time series data
    data_path = "data/statsbomb/timeseries_comp43_season3.csv"
    
    if not Path(data_path).exists():
        print(f"Error: Data file not found: {data_path}")
        print("Run fetch_statsbomb.py first to download data.")
        return
    
    # Initialize trainer
    trainer = FootballModelTrainer(data_path)
    
    # Load and process data
    trainer.load_data()
    goal_events = trainer.calculate_probability_changes()
    
    print(f"\nExtracted {len(goal_events)} goal events")
    print(f"Average probability change: {goal_events['prob_change'].mean():.4f}")
    print(f"Std probability change: {goal_events['prob_change'].std():.4f}")
    
    # Prepare features
    X, y, feature_names = trainer.prepare_features(goal_events)
    
    # Train model
    metrics = trainer.train(X, y, model_type='linear')
    
    # Show feature importance
    trainer.print_feature_importance()
    
    # Export coefficients
    trainer.export_coefficients('training/model_coefficients.json')


if __name__ == "__main__":
    main()
