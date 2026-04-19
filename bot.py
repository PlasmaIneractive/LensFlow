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

def orijinal_gorseli_cek(url):
    try:
        # İnsan taklidi yapıyoruz
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        }
        # Yönlendirmeleri takip et (Google'dan çıkıp asıl siteye git)
        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        
        # Orijinal haber sitesinin HTML'ini çek
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # En kaliteli görseli bul (og:image en garanti yoldur)
        og_img = soup.find("meta", property="og:image")
        if og_img and og_img.get("content"):
            return og_img["content"]
            
        # Eğer og:image yoksa sayfa içindeki ilk büyük resmi ara
        img = soup.find("img", src=True)
        if img:
            return img["src"]
            
    except Exception as e:
        print(f"Hata: {e}")
    return "https://via.placeholder.com/600x400"

def haberleri_islet():
    kaynaklar = [("tr", "TR"), ("en", "US"), ("de", "DE"), ("fr", "FR"), ("es", "ES"), ("it", "IT")]
    
    for dil, ulke in kaynaklar:
        url = f"https://news.google.com/rss?hl={dil}&gl={ulke}&ceid={ulke}:{dil}"
        feed = feedparser.parse(url)
        
        for entry in feed.entries:
            # Firebase ID'si için temizleme
            temiz_baslik = entry.title.replace("/", "-").replace(".", "-").replace("[", "").replace("]", "")
            doc_ref = db.collection('haberler').document(temiz_baslik)
            
            # Haber zaten varsa atla (Görsellerin güncellenmemesi için temizlik yapıp çalıştırmalısın)
            if not doc_ref.get().exists:
                # Orijinal linke gidip görseli çek
                gorsel = orijinal_gorseli_cek(entry.link)
                
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
                print(f"✅ Başarılı: {entry.title[:30]}... -> {gorsel[:30]}...")

if __name__ == "__main__":
    haberleri_islet()
