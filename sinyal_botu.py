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

# Hafıza sistemi (Yaklaşma ve Temas durumlarını ayrı ayrı tutar)
last_states = {symbol: {tf: 'normal' for tf in config['timeframes']} for symbol, config in SYMBOL_CONFIG.items()}

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload)
    except: print("Telegram Hatası")

def fetch_data(symbol, timeframe):
    exchange = ccxt.binance()
    bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=200)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    # 1. Pivot Point SuperTrend (Ana Sinyal Çizgileri)
    # Senin verdiğin özel ayarlar (Atr Period: 10, Multiplier: 3)
    pst = ta.supertrend(df['high'], df['low'], df['close'], length=10, multiplier=3)
    df['st_line'] = pst['SUPERT_10_3.0'] # Trend çizgisi
    df['st_direction'] = pst['SUPERTd_10_3.0'] # 1: Al, -1: Sat
    
    # 2. Yardımcı İndikatörler (Sinyal altında bilgi olarak verilecek)
    df['rsi'] = ta.rsi(df['close'], length=14)
    df['ema200'] = ta.ema(df['close'], length=200)
    bb = ta.bbands(df['close'], length=20, std=2)
    df['bb_upper'] = bb['BBU_20_2.0']
    df['bb_lower'] = bb['BBL_20_2.0']
    df['vol_avg'] = df['volume'].rolling(window=20).mean()
    
    return df.iloc[-1]

print("🚀 Temas Odaklı Pivot Point SuperTrend Botu Yayında...")

while True:
    for symbol, config in SYMBOL_CONFIG.items():
        for tf in config['timeframes']:
            try:
                row = fetch_data(symbol, tf)
                price = row['close']
                st_line = row['st_line'] # SuperTrend'in o anki çizgi değeri
                st_dir = row['st_direction']
                rsi = row['rsi']
                prox = config['proximity']
                
                current_state = 'normal'
                emoji, title = "", ""

                # TEMAS VE YAKINLIK MANTIĞI (SuperTrend Çizgisine Göre)
                # Sat Sinyali: Fiyat alttaki yeşil trend çizgisinden yukarıdayken üstteki kırmızıya çarpması/yaklaşması
                if st_dir == -1: # Trend SAT yönündeyse (Fiyat çizginin altında)
                    if price >= st_line:
                        current_state = 'temas_ust'
                        emoji, title = "🔴", "PST ÜST ÇİZGİ TEMASI (SAT)"
                    elif (st_line - price) <= prox:
                        current_state = 'yaklasti_ust'
                        emoji, title = "⚠️", "PST Üst Çizgiye Yaklaştı"
                
                elif st_dir == 1: # Trend AL yönündeyse (Fiyat çizginin üstünde)
                    if price <= st_line:
                        current_state = 'temas_alt'
                        emoji, title = "🟢", "PST ALT ÇİZGİ TEMASI (AL)"
                    elif (price - st_line) <= prox:
                        current_state = 'yaklasti_alt'
                        emoji, title = "⚠️", "PST Alt Çizgiye Yaklaştı"

                # Sadece durum değiştiğinde (Yaklaştı -> Temas gibi) mesaj at
                if current_state != last_states[symbol][tf]:
                    if current_state != 'normal':
                        vol_status = "🔥 Yüksek" if row['volume'] > row['vol_avg'] else "⚪ Normal"
                        trend_status = "📈 Boğa" if price > row['ema200'] else "📉 Ayı"
                        
                        msg = (
                            f"{emoji} *{symbol} - {tf.upper()}*\n"
                            f"----------------------------\n"
                            f"📢 *{title}*\n"
                            f"💰 Fiyat: {price}\n"
                            f"📍 PST Çizgisi: {st_line:.2f}\n"
                            f"----------------------------\n"
                            f"🔍 *YARDIMCI ANALİZ:*\n"
                            f"📊 RSI: {rsi:.2f}\n"
                            f"🛣️ Trend (EMA200): {trend_status}\n"
                            f"🌊 Hacim: {vol_status}\n"
                            f"🔘 Bollinger Üst/Alt: {row['bb_upper']:.2f} / {row['bb_lower']:.2f}"
                        )
                        send_telegram_msg(msg)
                    last_states[symbol][tf] = current_state
                
            except Exception as e:
                print(f"Hata: {e}")
            time.sleep(1.5)
    time.sleep(60)
