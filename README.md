# ADX + RSI Backtesting Strategy (Fyers)

This project implements a backtesting strategy using the Fyers API for data fetching and Nifty 50 stocks.

## Strategy Logic
- **Entry**: Buy when ADX(14) crosses above 25 AND RSI(14) is above 50.
- **Exit**: Stop Loss at 2%, Target Profit at 4%.
- **Timeframe**: 15 Minutes.

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Credentials**:
   - Open `backtest/config.py`.
   - Enter your Fyers `CLIENT_ID` and `ACCESS_TOKEN`.

## Running the Backtest

Run the main script as a module:

```bash
python3 -m backtest.main
```

## Output
The script will print the results for each stock and a final summary report including:
- Total Trades
- Win Rate
- Total P&L %

## Troubleshooting

### Error: `fatal error: Python.h: No such file or directory`
This occurs if you are missing Python development headers, especially on newer Python versions (like 3.14).

**Fix (Fedora/RHEL):**
```bash
sudo dnf install python3-devel gcc
```

**Fix (Ubuntu/Debian):**
```bash
sudo apt install python3-dev gcc
```
