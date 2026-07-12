import json
import sys
from datetime import datetime

with open('data/regime_latest.json', 'r') as f:
    data = json.load(f)

errors = []

# Check the date is today (or at least not stale)
today = datetime.today().strftime('%Y-%m-%d')
if data.get('date') != today:
    errors.append(f"Date mismatch: expected {today}, got {data.get('date')}")

# Check critical numeric fields aren't None
checks = {
    'spy.price': data.get('spy', {}).get('price'),
    'spy.sma50': data.get('spy', {}).get('sma50'),
    'spy.sma200': data.get('spy', {}).get('sma200'),
    'spy.rsi': data.get('spy', {}).get('rsi'),
    'vix.spot': data.get('vix', {}).get('spot'),
    'vix.vix3m': data.get('vix', {}).get('vix3m'),
    'vix.ratio': data.get('vix', {}).get('ratio'),
    'breadth.above_sma50': data.get('breadth', {}).get('above_sma50'),
    'breadth.above_sma200': data.get('breadth', {}).get('above_sma200'),
    'hyg.price': data.get('hyg', {}).get('price'),
    'hyg.sma50': data.get('hyg', {}).get('sma50'),
}

for field, value in checks.items():
    if value is None:
        errors.append(f"Missing/null field: {field}")

# Check sector data — at least most sectors should have resolved
sectors = data.get('sectors', {})
unknown_sectors = [etf for etf, v in sectors.items() if v.get('status') == 'Unknown']
if len(unknown_sectors) > 3:
    errors.append(f"Too many sectors failed to fetch: {unknown_sectors}")

if errors:
    print("VALIDATION FAILED:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print(f"Validation passed — date: {data['date']}, score: {data['score']}/9, regime: {data['regime']}")