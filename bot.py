import os
import json
import feedparser
from firebase_admin import credentials, initialize_app, firestore

# Firebase Bağlantısı
service_account = json.loads(os.getenv('FIREBASE_SERVICE_ACCOUNT'))
cred = credentials.Certificate(service_account)
initialize_app(cred)
db = firestore.client()

def haberleri_islet():
    # Haber kaynakları
    kaynaklar = [
        ("tr", "TR"), ("en", "US"), ("de", "DE"), 
        ("fr", "FR"), ("es", "ES"), ("it", "IT")
    ]
    
    for dil, ulke in kaynaklar:
        url = f"https://news.google.com/rss?hl={dil}&gl={ulke}&ceid={ulke}:{dil}"
        feed = feedparser.parse(url)
        
        for entry in feed.entries:
            # 1. Başlığı Firebase ID için güvenli hale getir
            temiz_baslik = entry.title.replace("/", "-").replace(".", "-").replace("[", "").replace("]", "")
            doc_ref = db.collection('haberler').document(temiz_baslik)
            
            # 2. Görsel kontrolü (RSS içinde varsa al, yoksa varsayılan)
            gorsel = "https://via.placeholder.com/600x400"
            if hasattr(entry, 'media_content'):
                gorsel = entry.media_content[0]['url']
            
            # 3. Veriyi hazırla
            veri = {
                "baslik": entry.title,
                "link": entry.link,
                "gorsel": gorsel,
                "tarih": firestore.SERVER_TIMESTAMP,
                "dil": dil,
                "kategori": "Gündem",
                "kaynak": entry.source.get('title', 'Google News') if 'source' in entry else 'Google News'
            }
            
            # 4. Firebase'e kaydet (set() varsa günceller, yoksa oluşturur)
            doc_ref.set(veri)
            print(f"✅ İşlendi: {entry.title[:30]}")

if __name__ == "__main__":
    haberleri_islet()
