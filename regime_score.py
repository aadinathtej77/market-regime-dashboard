import yfinance as yf
import pandas as pd
import ta
import json
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

    print("Fetching breadth data...")
    try:
        b50_data = yf.download('^SP500-50', period='5d', auto_adjust=True, progress=False)
        breadth50 = round(float(b50_data['Close'].squeeze().iloc[-1]), 1)
    except:
        breadth50 = None

    try:
        b200_data = yf.download('^SP500-200', period='5d', auto_adjust=True, progress=False)
        breadth200 = round(float(b200_data['Close'].squeeze().iloc[-1]), 1)
    except:
        breadth200 = None

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
        except Exception as e:
            sector_results[etf] = {'name': name, 'rsi': None, 'status': 'Unknown'}

    bullish_sectors = sum(1 for v in sector_results.values() if v['status'] == 'Bullish')

    # Scoring
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
            'price': hyg