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
        # Daha gerçekçi bir browser profili
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://www.google.com/'
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        # Eğer site bizi engellediyse veya farklı bir içerik verdiyse
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Site içindeki tüm resimleri analiz et, sadece 200x200'den büyükleri al
        imgs = soup.find_all('img')
        for img in imgs:
            src = img.get('src')
            # Reklam/Logo/İkon filtreleme (küçük resimleri geç)
            if src and len(src) > 50 and ('news' in src or 'photo' in src or 'image' in src):
                return src if src.startswith('http') else url.rsplit('/', 1)[0] + '/' + src
                
    except Exception as e:
        print(f"Hata: {e}")
    return "https://via.placeholder.com/600x400"

def haberleri_islet():
    kaynaklar = [
        ("tr", "TR"), ("en", "US"), ("de", "DE"), ("fr", "FR"), ("es", "ES"), ("it", "IT")
    ]
    
    for dil, ulke in kaynaklar:
        url = f"https://news.google.com/rss?hl={dil}&gl={ulke}&ceid={ulke}:{dil}"
        feed = feedparser.parse(url)
        
        for entry in feed.entries:
            temiz_baslik = entry.title.replace("/", "-").replace(".", "-").replace("[", "").replace("]", "")
            doc_ref = db.collection('haberler').document(temiz_baslik)
            
            if not doc_ref.get().exists:
                gorsel = gorsel_bul(entry.link)
                
                # Kategori sorgusunu iptal ettik, hepsi sabit "Gündem"
                veri = {
                    "baslik": entry.title,
                    "link": entry.link,
                    "gorsel": gorsel if gorsel else "https://via.placeholder.com/600x400",
                    "tarih": firestore.SERVER_TIMESTAMP,
                    "dil": dil,
                    "kategori": "Gündem", 
                    "kaynak": entry.source.get('title', 'Google News') if 'source' in entry else 'Google News'
                }
                
                doc_ref.set(veri)
                print(f"✅ Eklendi: {entry.title} ({dil})")

if __name__ == "__main__":
    haberleri_islet()
