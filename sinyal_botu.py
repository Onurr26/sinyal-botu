import ccxt
import pandas as pd
import pandas_ta as ta
import requests
import time

# --- AYARLAR ---
SYMBOL_CONFIG = {
    "BTC/USDT": {"proximity": 100},
    "ETH/USDT": {"proximity": 5}
}
TIMEFRAME = '1h'
TELEGRAM_TOKEN = "8205711200:AAE-76Kui2KTpPBYDeH_ktSzhSRkRTbf9Qo"
CHAT_ID = "5719402713"

# Durum takibi için hafıza (Aynı mesajı tekrar atmamak için)
# Durumlar: 'normal', 'yaklasti_ust', 'yaklasti_alt', 'temas_ust', 'temas_alt'
last_states = {symbol: 'normal' for symbol in SYMBOL_CONFIG.keys()}

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram Hatası: {e}")

def fetch_data(symbol):
    exchange = ccxt.binance()
    bars = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=100)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    # İndikatörler
    bb = ta.bbands(df['close'], length=20, std=2)
    df['bb_upper'] = bb['BBU_20_2.0']
    df['bb_lower'] = bb['BBL_20_2.0']
    df['rsi'] = ta.rsi(df['close'], length=14)
    
    return df.iloc[-1]

print("🚀 Bot Bulutta Başlatıldı... Sinyaller İzleniyor.")
send_telegram_msg("🔔 *Bot Aktif!* \nBTC ve ETH için Yakınsama & Temas takibi başladı.")

while True:
    for symbol, config in SYMBOL_CONFIG.items():
        try:
            row = fetch_data(symbol)
            price = row['close']
            upper = row['bb_upper']
            lower = row['bb_lower']
            rsi = row['rsi']
            prox = config['proximity']
            
            current_state = 'normal'
            msg = ""

            # 🔴 SATIŞ BÖLGESİ KONTROLÜ
            if price >= upper:
                current_state = 'temas_ust'
                msg = f"🔴 *ACİL SAT SİNYALİ (Üst Bant)*\n\n💰 Fiyat: {price}\n📊 RSI: {rsi:.2f}\n⚠️ Bant Teması Gerçekleşti!"
            elif (upper - price) <= prox:
                current_state = 'yaklasti_ust'
                msg = f"⚠️ *DİKKAT: Üst Banda Yaklaştı*\n\n💰 Fiyat: {price}\n📏 Mesafe: {upper - price:.2f}\n👀 Hazırlıklı Ol!"

            # 🟢 ALIŞ BÖLGESİ KONTROLÜ
            elif price <= lower:
                current_state = 'temas_alt'
                msg = f"🟢 *ACİL AL SİNYALİ (Alt Bant)*\n\n💰 Fiyat: {price}\n📊 RSI: {rsi:.2f}\n⚠️ Bant Teması Gerçekleşti!"
            elif (price - lower) <= prox:
                current_state = 'yaklasti_alt'
                msg = f"⚠️ *DİKKAT: Alt Banda Yaklaştı*\n\n💰 Fiyat: {price}\n📏 Mesafe: {price - lower:.2f}\n👀 Hazırlıklı Ol!"

            # Sadece durum değiştiğinde mesaj gönder
            if current_state != last_states[symbol]:
                if current_state != 'normal':
                    send_telegram_msg(f"*{symbol}*\n{msg}")
                last_states[symbol] = current_state
                
        except Exception as e:
            print(f"Hata ({symbol}): {e}")

    time.sleep(60) # Her dakika kontrol et
