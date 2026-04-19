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
        # Google botu gibi davranarak siteleri kandırıyoruz
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 1. Strateji: Meta etiketleri (En kaliteli görseller burada olur)
        for meta in ["og:image", "twitter:image", "image"]:
            img_tag = soup.find("meta", property=meta) or soup.find("meta", attrs={"name": meta})
            if img_tag and img_tag.get("content"):
                return img_tag["content"]
        
        # 2. Strateji: Sayfa içindeki ilk büyük resim
        images = soup.find_all("img")
        for img in images:
            src = img.get("src")
            if src and not src.startswith("data:") and len(src) > 30: # İkonları ve küçük resimleri atla
                return src if src.startswith("http") else url.rsplit('/', 1)[0] + "/" + src

    except Exception as e:
        print(f"Görsel çekme hatası: {e}")
    return "https://via.placeholder.com/600x400" # Eğer hiç bulunamazsa boş kalsın

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
