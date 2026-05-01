import ccxt
import pandas as pd
import pandas_ta as ta
import requests
import time

# --- BİLGİLERİN ---
TOKEN = "8205711200:AAE-76Kui2KTpPBYDeH_ktSzhSRkRTbf9Qo"
CHAT_ID = "5719402713"

SEMBOL_LISTESI = ['BTC/USDT', 'ETH/USDT']
PERIYOTLAR = ['15m', '30m', '1h', '4h', '1d']

# Strateji Ayarların
ATR_FACTOR = 2.8
ATR_PERIOD = 10

def telegram_gonder(mesaj):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": mesaj}
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram gönderim hatası: {e}")

def sinyal_kontrol():
    # Bağlantıyı her seferinde tazeleyerek ve SPOT piyasaya zorlayarak kuruyoruz
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'spot'} 
    })
    
    for sembol in SEMBOL_LISTESI:
        for periyot in PERIYOTLAR:
            try:
                # Veri çekme
                bars = exchange.fetch_ohlcv(sembol, timeframe=periyot, limit=100)
                if not bars:
                    continue
                
                df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                
                # SuperTrend Hesaplama
                sti = ta.supertrend(df['high'], df['low'], df['close'], length=ATR_PERIOD, multiplier=ATR_FACTOR)
                
                # Sütun isimlerini dinamik yakalayalım (hata payını sıfırlıyoruz)
                line_col = [c for c in sti.columns if 'SUPERT_' in c][0]
                direction_col = [c for c in sti.columns if 'SUPERTd_' in c][0]

                son_fiyat = df['close'].iloc[-1]
                en_yuksek = df['high'].iloc[-1]
                en_dusuk = df['low'].iloc[-1]
                bant_degeri = sti[line_col].iloc[-1]
                yon = sti[direction_col].iloc[-1]

                # --- STRATEJİ KONTROLÜ ---
                # SATIŞ: Trend aşağı (turuncu/-1) ve üst banta temas
                if yon == -1 and en_yuksek >= bant_degeri:
                    msg = f"🚨 SAT SİNYALİ (Üst Bant Teması)\n💰 Varlık: {sembol}\n⏰ Periyot: {periyot}\n💵 Fiyat: {son_fiyat}"
                    telegram_gonder(msg)
                    print(f"Sinyal gönderildi: {sembol} {periyot} SAT")

                # ALIŞ: Trend yukarı (yeşil/1) ve alt banta temas
                elif yon == 1 and en_dusuk <= bant_degeri:
                    msg = f"🚀 AL SİNYALİ (Alt Bant Teması)\n💰 Varlık: {sembol}\n⏰ Periyot: {periyot}\n💵 Fiyat: {son_fiyat}"
                    telegram_gonder(msg)
                    print(f"Sinyal gönderildi: {sembol} {periyot} AL")

            except Exception as e:
                # Hataları daha temiz yazdıralım ki ekran kirlenmesin
                pass
            
            time.sleep(0.2)

# Ana Başlatıcı
print("Bot başlatıldı... Sinyaller Telegram'a düşecek.")
# Çalıştığını anlaman için ilk açılışta mesaj atar
telegram_gonder("🔔 Bot aktif! BTC ve ETH piyasaları izleniyor.")

while True:
    try:
        sinyal_kontrol()
        print(f"Kontrol tamamlandı: {time.strftime('%H:%M:%S')}")
    except Exception as e:
        print(f"Genel döngü hatası: {e}")
    
    time.sleep(60)
