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
            
            if not doc_ref.get().exists:
                gorsel = "https://via.placeholder.com/600x400"
                
                # YÖNTEM 1: RSS Özetinin içindeki HTML'i tara (En etkili yöntem)
                if 'summary' in entry:
                    soup = BeautifulSoup(entry.summary, 'html.parser')
                    img_tag = soup.find('img')
                    if img_tag and img_tag.get('src'):
                        gorsel = img_tag['src']
                
                # YÖNTEM 2: Eğer hala boşsa, meta verileri kontrol et
                if gorsel == "https://via.placeholder.com/600x400" and hasattr(entry, 'links'):
                    for link in entry.links:
                        if 'image' in link.get('type', ''):
                            gorsel = link['href']
                            break

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
                print(f"✅ Eklendi: {entry.title} - Görsel: {gorsel[:30]}...")

if __name__ == "__main__":
    haberleri_islet()
