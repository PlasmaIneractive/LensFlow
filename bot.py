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

def gorsel_bul(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=3)
        soup = BeautifulSoup(response.content, 'html.parser')
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            return og_image["content"]
    except:
        return None
    return None

def haberleri_islet():
    kaynaklar = [
        ("tr", "TR"), ("en", "US"), ("de", "DE"), ("fr", "FR"), ("es", "ES"), ("it", "IT")
    ]
    
    for dil, ulke in kaynaklar:
        url = f"https://news.google.com/rss?hl={dil}&gl={ulke}&ceid={ulke}:{dil}"
        feed = feedparser.parse(url)
        
        for entry in feed.entries:
            doc_ref = db.collection('haberler').document(entry.title)
            
            if not doc_ref.get().exists:
                gorsel = gorsel_bul(entry.link)
                veri = {
                    "baslik": entry.title,
                    "link": entry.link,
                    "gorsel": gorsel if gorsel else "https://via.placeholder.com/600x400",
                    "tarih": firestore.SERVER_TIMESTAMP,
                    "dil": dil,
                    "kaynak": entry.source.get('title', 'Google News')
                }
                doc_ref.set(veri)
                print(f"✅ Eklendi: {entry.title} ({dil})")

if __name__ == "__main__":
    haberleri_islet()
