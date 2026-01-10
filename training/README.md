# Football Model Training Pipeline

Scripts to collect time series match data and train probability prediction models.

## Quick Start

### 1. Install Dependencies
```bash
pip install pandas numpy scikit-learn requests
```

### 2. Get Data

#### Option A: StatsBomb (Free, Event-Level)
```bash
python training/fetch_statsbomb.py
```

Downloads:
- FIFA World Cup 2018 (64 matches)
- Event-level timestamps
- Saves to: `data/statsbomb/timeseries_comp43_season3.csv`

#### Option B: API-Football (Live + Historical)
```bash
# 1. Get API key from https://www.api-football.com/
# 2. Edit fetch_api_football.py and set your API_KEY
# 3. Run:
python training/fetch_api_football.py
```

Features:
- Live match monitoring
- Historical fixtures
- Free tier: 100 requests/day

### 3. Train Model
```bash
python training/train_model.py
```

Outputs:
- Model performance metrics
- Feature importance
- Coefficients → `training/model_coefficients.json`

### 4. Use in Strategy

Copy coefficients to your config:
```json
{
  "profiles": {
    "football_ml": {
      "model_coefficients": {
        "intercept": 0.15,
        "time_factor": 0.002,
        "goal_diff": -0.03,
        "shots_diff": 0.005,
        ...
      }
    }
  }
}
```

---

## Data Format

### Time Series Structure
```csv
match_id,minute,score_home,score_away,goal_diff,shots_home,shots_away,...
12345,0,0,0,0,0,0,...
12345,1,0,0,0,0,0,...
12345,23,1,0,1,4,2,...  <- Goal scored at minute 23
12345,24,1,0,1,4,2,...
...
```

### What You Need Per Minute:
- **Basic**: score, minute
- **Important**: shots, corners, cards
- **Advanced**: possession, attacks, momentum

---

## Available Competitions (StatsBomb)

| ID | Competition | Season | Matches |
|----|-------------|--------|---------|
| 43 | FIFA World Cup | 2018 | 64 |
| 11 | La Liga | 2018/2019 | 380 |
| 2 | Champions League | 2018/2019 | 125 |
| 37 | FA Women's Super League | 2019/2020 | 132 |

See full list: `fetch_statsbomb.py` → `get_competitions()`

---

## API-Football Leagues

Popular league IDs:
- **39**: Premier League (England)
- **140**: La Liga (Spain)
- **61**: Ligue 1 (France)
- **78**: Bundesliga (Germany)
- **135**: Serie A (Italy)

---

## Model Training Tips

### 1. More Data = Better Model
- Minimum: 50 matches
- Recommended: 200+ matches
- Optimal: 1000+ matches (multiple seasons)

### 2. Feature Engineering
Current features:
- Time (minute)
- Goal difference
- Shot difference
- Possession difference
- Cards (yellow/red)
- Game state (losing/drawing)
- Late game indicator

Add your own:
- xG (expected goals)
- Team strength ratings
- Head-to-head history
- Home/away advantage

### 3. Model Selection
- **Linear Regression**: Fast, interpretable (current)
- **Ridge Regression**: Better for correlated features
- **Lasso Regression**: Auto feature selection
- **XGBoost**: Best accuracy, slower

### 4. Validation
- Split: 80% train, 20% test
- Use cross-validation (k=5)
- Test on recent matches (time-based split)

---

## Example Workflow

```bash
# 1. Download World Cup data
python training/fetch_statsbomb.py

# 2. Train initial model
python training/train_model.py

# 3. Check coefficients
cat training/model_coefficients.json

# 4. Test on live match
python training/fetch_api_football.py
# (Monitor a live match, see how predictions perform)

# 5. Iterate: collect more data, retrain, improve
```

---

## Next Steps

1. **Collect More Data**
   - Download multiple competitions
   - Use API-Football for recent matches
   - Consider web scraping (carefully)

2. **Add Features**
   - Red cards (you asked for this!)
   - Team form (last 5 matches)
   - Player injuries
   - Weather conditions

3. **Improve Model**
   - Try Ridge/Lasso regression
   - Test ensemble models
   - Implement online learning (update during match)

4. **Backtest**
   - Simulate trades on historical data
   - Calculate ROI
   - Optimize coefficients for profit, not just R²

---

## Resources

- **StatsBomb**: https://github.com/statsbomb/open-data
- **API-Football**: https://www.api-football.com/
- **Football-Data.co.uk**: http://www.football-data.co.uk/
- **FBref**: https://fbref.com/
- **Scikit-learn docs**: https://scikit-learn.org/

---

## Troubleshooting

**Q: "No data collected" from StatsBomb**
- Check internet connection
- Try different competition ID
- StatsBomb may be down (rare)

**Q: API-Football returns 403**
- Invalid API key
- Rate limit exceeded (100/day on free tier)
- Check account status

**Q: Model R² is very low**
- Need more data (try 200+ matches)
- Add more features
- Probability estimates might be inaccurate (need real betting odds)

**Q: Coefficients don't make sense**
- Feature scaling issues (normalize features)
- Multicollinearity (use Ridge regression)
- Not enough variation in data
