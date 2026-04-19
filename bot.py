import os
import json
import feedparser
import requests
from firebase_admin import credentials, initialize_app, firestore

# Firebase Bağlantısı
service_account = json.loads(os.getenv('FIREBASE_SERVICE_ACCOUNT'))
cred = credentials.Certificate(service_account)
initialize_app(cred)
db = firestore.client()

def fix_google_image(url):
    # Google'ın verdiği o profil resmi linkini, orijinal görsel linkine zorla çevir
    # Bu yöntem Google'ın gizli görsel servisinin parametresini kullanır
    if "googleusercontent" in url or "google" in url:
        return url.split("=")[0] + "=s0" # Kaliteyi en yükseğe çeker
    return url

def haberleri_islet():
    kaynaklar = [("tr", "TR"), ("en", "US"), ("de", "DE"), ("fr", "FR"), ("es", "ES"), ("it", "IT")]
    
    for dil, ulke in kaynaklar:
        url = f"https://news.google.com/rss?hl={dil}&gl={ulke}&ceid={ulke}:{dil}"
        feed = feedparser.parse(url)
        
        for entry in feed.entries:
            temiz_baslik = entry.title.replace("/", "-").replace(".", "-").replace("[", "").replace("]", "")
            doc_ref = db.collection('haberler').document(temiz_baslik)
            
            # Google'ın RSS içindeki görseli veya yönlendirmesi
            # feedparser entry'sinden resim linkini ayıkla
            gorsel = "https://via.placeholder.com/600x400"
            if hasattr(entry, 'media_content'):
                gorsel = entry.media_content[0]['url']
            elif hasattr(entry, 'links'):
                for link in entry.links:
                    if 'image' in link.get('type', ''):
                        gorsel = link['href']
            
            # Görseli 's0' kalitesine zorla (Google Proxy'sini aşmak için)
            gorsel = fix_google_image(gorsel)
            
            veri = {
                "baslik": entry.title,
                "link": entry.link,
                "gorsel": gorsel,
                "tarih": firestore.SERVER_TIMESTAMP,
                "dil": dil,
                "kategori": "Gündem",
                "kaynak": entry.source.get('title', 'Google News') if 'source' in entry else 'Google News'
            }
            
            doc_ref.set(veri)
            print(f"✅ Yazıldı: {entry.title[:30]}")

if __name__ == "__main__":
    haberleri_islet()
