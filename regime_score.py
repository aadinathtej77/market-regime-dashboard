import yfinance as yf
import pandas as pd
import ta
import json
import os
from datetime import datetime

SECTORS = {
    'XLB': 'Materials',
    'XLC': 'Communication',
    'XLE': 'Energy',
    'XLF': 'Financials',
    'XLI': 'Industrials',
    'XLK': 'Technology',
    'XLP': 'Consumer Staples',
    'XLRE': 'Real Estate',
    'XLU': 'Utilities',
    'XLV': 'Health Care',
    'XLY': 'Consumer Disc'
}

def get_rsi(series, period=14):
    return ta.momentum.RSIIndicator(series, window=period).rsi().iloc[-1]

def get_sma(series, period):
    return series.rolling(period).mean().iloc[-1]

def compute_breadth():
    print("Computing breadth from sector ETFs...")
    etfs = list(SECTORS.keys())
    above50 = 0
    above200 = 0
    total = 0
    for etf in etfs:
        try:
            data = yf.download(etf, period='1y', auto_adjust=True, progress=False)
            closes = data['Close'].squeeze()
            price = float(closes.iloc[-1])
            sma50 = float(closes.rolling(50).mean().iloc[-1])
            sma200 = float(closes.rolling(200).mean().iloc[-1])
            if price > sma50:
                above50 += 1
            if price > sma200:
                above200 += 1
            total += 1
        except:
            pass
    if total == 0:
        return None, None
    return round((above50 / total) * 100, 1), round((above200 / total) * 100, 1)

def fetch_regime():
    print("Fetching SPY data...")
    spy_data = yf.download('SPY', period='1y', auto_adjust=True, progress=False)
    spy = spy_data['Close'].squeeze()
    spy_price = round(float(spy.iloc[-1]), 2)
    sma50 = round(float(get_sma(spy, 50)), 2)
    sma200 = round(float(get_sma(spy, 200)), 2)
    spy_rsi = round(float(get_rsi(spy)), 1)

    print("Fetching VIX data...")
    vix_data = yf.download('^VIX', period='30d', auto_adjust=True, progress=False)
    vix = vix_data['Close'].squeeze()
    vix_spot = round(float(vix.iloc[-1]), 2)
    vix_5d_change = round(float(vix.iloc[-1] - vix.iloc[-6]), 2)

    vix3m_data = yf.download('^VIX3M', period='5d', auto_adjust=True, progress=False)
    vix3m = round(float(vix3m_data['Close'].squeeze().iloc[-1]), 2)
    vix_ratio = round(vix_spot / vix3m, 3)

    breadth50, breadth200 = compute_breadth()

    print("Fetching HYG data...")
    hyg_data = yf.download('HYG', period='100d', auto_adjust=True, progress=False)
    hyg = hyg_data['Close'].squeeze()
    hyg_price = round(float(hyg.iloc[-1]), 2)
    hyg_sma50 = round(float(get_sma(hyg, 50)), 2)

    print("Fetching sector data...")
    sector_results = {}
    for etf, name in SECTORS.items():
        try:
            data = yf.download(etf, period='100d', auto_adjust=True, progress=False)
            closes = data['Close'].squeeze()
            rsi = round(float(get_rsi(closes)), 1)
            if rsi > 55:
                status = 'Bullish'
            elif rsi < 45:
                status = 'Bearish'
            else:
                status = 'Neutral'
            sector_results[etf] = {'name': name, 'rsi': rsi, 'status': status}
        except:
            sector_results[etf] = {'name': name, 'rsi': None, 'status': 'Unknown'}

    bullish_sectors = sum(1 for v in sector_results.values() if v['status'] == 'Bullish')

    score = 0
    components = {}

    components['spy_above_sma50'] = spy_price > sma50
    score += 1 if components['spy_above_sma50'] else 0

    components['sma50_above_sma200'] = sma50 > sma200
    score += 1 if components['sma50_above_sma200'] else 0

    components['breadth_sma50'] = breadth50 is not None and breadth50 > 60
    score += 1 if components['breadth_sma50'] else 0

    components['breadth_sma200'] = breadth200 is not None and breadth200 > 60
    score += 1 if components['breadth_sma200'] else 0

    components['sectors_bullish'] = bullish_sectors >= 7
    score += 1 if components['sectors_bullish'] else 0

    components['vix_contango'] = vix_ratio < 1
    score += 2 if components['vix_contango'] else 0

    components['hyg_above_sma50'] = hyg_price > hyg_sma50
    score += 1 if components['hyg_above_sma50'] else 0

    components['vix_falling'] = vix_5d_change < 0
    score += 1 if components['vix_falling'] else 0

    if score >= 6:
        regime = 'BULLISH'
    elif score <= 3:
        regime = 'BEARISH'
    else:
        regime = 'NEUTRAL'

    result = {
        'date': datetime.today().strftime('%Y-%m-%d'),
        'score': score,
        'regime': regime,
        'spy': {
            'price': spy_price,
            'sma50': sma50,
            'sma200': sma200,
            'rsi': spy_rsi
        },
        'vix': {
            'spot': vix_spot,
            'vix3m': vix3m,
            'ratio': vix_ratio,
            'change_5d': vix_5d_change
        },
        'breadth': {
            'above_sma50': breadth50,
            'above_sma200': breadth200
        },
        'hyg': {
            'price': hyg_price,
            'sma50': hyg_sma50
        },
        'components': components,
        'sectors': sector_results,
        'bullish_sectors': bullish_sectors
    }

    return result

def update_history(data):
    history_path = 'data/regime_history.json'
    if os.path.exists(history_path):
        with open(history_path, 'r') as f:
            history = json.load(f)
    else:
        history = []

    entry = {
        'date': data['date'],
        'score': data['score'],
        'regime': data['regime'],
        'spy_price': data['spy']['price'],
        'vix_spot': data['vix']['spot'],
        'vix_ratio': data['vix']['ratio'],
        'breadth50': data['breadth']['above_sma50'],
        'breadth200': data['breadth']['above_sma200'],
        'bullish_sectors': data['bullish_sectors']
    }

    dates = [h['date'] for h in history]
    if data['date'] not in dates:
        history.append(entry)

    history = sorted(history, key=lambda x: x['date'])

    with open(history_path, 'w') as f:
        json.dump(history, f, indent=2)

    print(f"History updated — {len(history)} weekly entries")

if __name__ == '__main__':
    print("Starting market regime scoring...")
    data = fetch_regime()
    with open('data/regime_latest.json', 'w') as f:
        json.dump(data, f, indent=2)
    update_history(data)
    print(f"\nDone! Score: {data['score']}/9 — {data['regime']}")
    print(f"Saved to data/regime_latest.json and data/regime_history.json")