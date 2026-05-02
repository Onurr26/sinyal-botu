import ccxt
import pandas as pd
import pandas_ta as ta
import requests
import time

# --- AYARLAR ---
SYMBOL_CONFIG = {
    "BTC/USDT": {"proximity": 100, "timeframes": ['1h', '2h', '4h', '1d', '1w']},
    "ETH/USDT": {"proximity": 5, "timeframes": ['2h', '4h', '1d', '1w']}
}

TELEGRAM_TOKEN = "8205711200:AAE-76Kui2KTpPBYDeH_ktSzhSRkRTbf9Qo"
CHAT_ID = "5719402713"

# Hafıza sistemi
last_states = {symbol: {tf: 'normal' for tf in config['timeframes']} for symbol, config in SYMBOL_CONFIG.items()}

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload)
    except: print("Telegram Hatası")

def fetch_data(symbol, timeframe):
    exchange = ccxt.binance()
    limit = 200
    bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    # 1. Pivot Point SuperTrend (Pandas-TA üzerinden)
    # Genelde 2/2 veya 3/10 parametreleri kullanılır, biz standart başarılı ayarları alıyoruz
    pst = ta.supertrend(df['high'], df['low'], df['close'], length=10, multiplier=3)
    df['st_signal'] = pst['SUPERTd_10_3.0'] # 1 (Al) veya -1 (Sat)
    
    # 2. Yardımcı İndikatörler
    bb = ta.bbands(df['close'], length=20, std=2)
    df['bb_upper'] = bb['BBU_20_2.0']
    df['bb_lower'] = bb['BBL_20_2.0']
    df['rsi'] = ta.rsi(df['close'], length=14)
    df['ema200'] = ta.ema(df['close'], length=200)
    df['vol_avg'] = df['volume'].rolling(window=20).mean()
    
    return df.iloc[-1]

print("🚀 Pivot Point SuperTrend Bot Başlatıldı...")

while True:
    for symbol, config in SYMBOL_CONFIG.items():
        for tf in config['timeframes']:
            try:
                row = fetch_data(symbol, tf)
                price = row['close']
                st_signal = row['st_signal']
                rsi = row['rsi']
                ema200 = row['ema200']
                vol_status = "🔥 Yüksek" if row['volume'] > row['vol_avg'] else "⚪ Normal"
                trend_status = "📈 Boğa (EMA200 Üstü)" if price > ema200 else "📉 Ayı (EMA200 Altı)"
                
                # Sinyal Belirleme (Pivot Point SuperTrend)
                current_state = 'AL' if st_signal == 1 else 'SAT'
                
                # SADECE SİNYAL DEĞİŞTİĞİNDE MESAJ AT
                if current_state != last_states[symbol][tf]:
                    emoji = "🟢" if current_state == 'AL' else "🔴"
                    msg = (
                        f"{emoji} *{symbol} - {tf.upper()} SİNYALİ*\n"
                        f"----------------------------\n"
                        f"🔥 *STRATEJİ:* Pivot Point SuperTrend -> *{current_state}*\n"
                        f"💰 *Fiyat:* {price}\n"
                        f"----------------------------\n"
                        f"🔍 *DESTEKLEYİCİ ANALİZ:*\n"
                        f"📊 RSI: {rsi:.2f}\n"
                        f"🌊 Hacim: {vol_status}\n"
                        f"🛣️ Ana Trend: {trend_status}\n"
                        f"📍 BB Üst/Alt: {row['bb_upper']:.2f} / {row['bb_lower']:.2f}"
                    )
                    send_telegram_msg(msg)
                    last_states[symbol][tf] = current_state
                
            except Exception as e:
                print(f"Hata: {e}")
            time.sleep(1.5)
    time.sleep(60)
