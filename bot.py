import os
import json
import feedparser
import requests
from bs4 import BeautifulSoup
from firebase_admin import credentials, initialize_app, firestore

# Firebase Bağlantısı
service_account = json.loads(os.getenv('FIREBASE_SERVICE_ACCOUNT'))
cred = credentials.Certificate(service_account)
initialize_app(cred)
db = firestore.client()

def haberleri_islet():
    kaynaklar = [("tr", "TR"), ("en", "US"), ("de", "DE"), ("fr", "FR"), ("es", "ES"), ("it", "IT")]
    
    for dil, ulke in kaynaklar:
        url = f"https://news.google.com/rss?hl={dil}&gl={ulke}&ceid={ulke}:{dil}"
        feed = feedparser.parse(url)
        
        for entry in feed.entries:
            temiz_baslik = entry.title.replace("/", "-").replace(".", "-").replace("[", "").replace("]", "")
            doc_ref = db.collection('haberler').document(temiz_baslik)
            
            # --- YENİ GÖRSEL ÇEKME MANTIĞI ---
            gorsel = "https://via.placeholder.com/600x400"
            
            # 1. Öncelik: Summary (HTML Özeti) içindeki <img> etiketini bul
            if hasattr(entry, 'summary'):
                soup = BeautifulSoup(entry.summary, 'html.parser')
                img = soup.find('img')
                if img and img.get('src'):
                    gorsel = img['src']
            
            # 2. Öncelik: Media Content (Eğer varsa)
            if gorsel == "https://via.placeholder.com/600x400" and hasattr(entry, 'media_content'):
                gorsel = entry.media_content[0]['url']
            
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
            print(f"✅ Yazıldı: {entry.title[:30]} | Görsel: {gorsel[:30]}...")

if __name__ == "__main__":
    haberleri_islet()
