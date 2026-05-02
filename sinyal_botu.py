import ccxt
import pandas as pd
import pandas_ta as ta
import requests
import time

# --- AYARLAR ---
# Her sembol için takip edilecek özel zaman dilimleri
SYMBOL_CONFIG = {
    "BTC/USDT": {
        "proximity": 100,
        "timeframes": ['1h', '2h', '4h', '1d', '1w']
    },
    "ETH/USDT": {
        "proximity": 5,
        "timeframes": ['2h', '4h', '1d', '1w']
    }
}

TELEGRAM_TOKEN = "8205711200:AAE-76Kui2KTpPBYDeH_ktSzhSRkRTbf9Qo"
CHAT_ID = "5719402713"

# Hafıza sistemi: Her sembol ve her zaman dilimi için ayrı durum takibi
last_states = {
    symbol: {tf: 'normal' for tf in config['timeframes']} 
    for symbol, config in SYMBOL_CONFIG.items()
}

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram Hatası: {e}")

def fetch_data(symbol, timeframe):
    exchange = ccxt.binance()
    # Haftalık (1w) veri için daha fazla mum çekiyoruz
    limit = 200 if timeframe in ['1d', '1w'] else 100
    bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    # Teknik Göstergeler (Bollinger Bantları ve RSI)
    bb = ta.bbands(df['close'], length=20, std=2)
    df['bb_upper'] = bb['BBU_20_2.0']
    df['bb_lower'] = bb['BBL_20_2.0']
    df['rsi'] = ta.rsi(df['close'], length=14)
    
    return df.iloc[-1]

print("🚀 Kişiselleştirilmiş Periyot Botu Başlatıldı...")
send_telegram_msg("🎯 *Kişiselleştirilmiş Takip Başladı!*\n\n*BTC:* 1sa, 2sa, 4sa, Günlük, Haftalık\n*ETH:* 2sa, 4sa, Günlük, Haftalık")

while True:
    for symbol, config in SYMBOL_CONFIG.items():
        for tf in config['timeframes']:
            try:
                row = fetch_data(symbol, tf)
                price = row['close']
                upper = row['bb_upper']
                lower = row['bb_lower']
                rsi = row['rsi']
                prox = config['proximity']
                
                current_state = 'normal'
                emoji = ""
                title = ""

                # KONTROL MANTIĞI
                if price >= upper:
                    current_state = 'temas_ust'
                    emoji, title = "🔴", "ACİL SAT SİNYALİ"
                elif (upper - price) <= prox:
                    current_state = 'yaklasti_ust'
                    emoji, title = "⚠️", "Üst Banda Yaklaştı"
                elif price <= lower:
                    current_state = 'temas_alt'
                    emoji, title = "🟢", "ACİL AL SİNYALİ"
                elif (price - lower) <= prox:
                    current_state = 'yaklasti_alt'
                    emoji, title = "⚠️", "Alt Banda Yaklaştı"

                # Durum Değişimi Kontrolü
                if current_state != last_states[symbol][tf]:
                    if current_state != 'normal':
                        # Haftalık ve Günlük periyotlar için ekstra vurgu yapalım
                        tf_display = tf.replace('1d', 'GÜNLÜK').replace('1w', 'HAFTALIK')
                        msg = (f"{emoji} *{symbol} - {tf_display}*\n"
                               f"----------------------------\n"
                               f"📢 *{title}*\n"
                               f"💰 Fiyat: {price}\n"
                               f"📊 RSI: {rsi:.2f}")
                        send_telegram_msg(msg)
                    
                    last_states[symbol][tf] = current_state
                
            except Exception as e:
                print(f"Hata ({symbol} - {tf}): {e}")
            
            time.sleep(1.5) # Binance API'yi yormayalım

    time.sleep(60) # Her dakika listeyi baştan tara
