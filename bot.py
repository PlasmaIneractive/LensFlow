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

def orijinal_sayfadan_gorsel_cek(url):
    try:
        # Gerçek bir tarayıcı taklidi (User-Agent çok önemli)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Referer": "https://www.google.com/"
        }
        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 1. Öncelik: Og:image (Haber sitelerinin paylaşılan görsel meta verisi)
        og_img = soup.find("meta", property="og:image")
        if og_img and og_img.get("content"):
            return og_img["content"]
            
        # 2. Öncelik: Makalenin içindeki ilk büyük resim (Haber gövdesi)
        # Genelde haber resimleri article etiketi içindedir
        article = soup.find('article') or soup.find('main') or soup
        img = article.find('img', src=True)
        if img:
            return img['src']
            
    except Exception as e:
        print(f"Hata oluştu: {e}")
    return "https://via.placeholder.com/600x400"

def haberleri_islet():
    kaynaklar = [("tr", "TR"), ("en", "US"), ("de", "DE"), ("fr", "FR"), ("es", "ES"), ("it", "IT")]
    
    for dil, ulke in kaynaklar:
        url = f"https://news.google.com/rss?hl={dil}&gl={ulke}&ceid={ulke}:{dil}"
        feed = feedparser.parse(url)
        
        for entry in feed.entries[:5]: # Her dilden ilk 5 haber (test için)
            temiz_baslik = entry.title.replace("/", "-").replace(".", "-")
            doc_ref = db.collection('haberler').document(temiz_baslik)
            
            if not doc_ref.get().exists:
                # Orijinal içeriğe git ve görseli çek
                gercek_gorsel = orijinal_sayfadan_gorsel_cek(entry.link)
                
                veri = {
                    "baslik": entry.title,
                    "link": entry.link,
                    "gorsel": gercek_gorsel,
                    "tarih": firestore.SERVER_TIMESTAMP,
                    "dil": dil,
                    "kategori": "Gündem"
                }
                doc_ref.set(veri)
                print(f"✅ Çekildi: {entry.title[:30]}... -> {gercek_gorsel[:30]}...")

if __name__ == "__main__":
    haberleri_islet()
