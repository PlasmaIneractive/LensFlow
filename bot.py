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
    """
    Haberin orijinal sayfasına gider ve meta verilerinden yüksek kaliteli görseli alır.
    """
    try:
        # İnsan gibi davranmak için gerçek tarayıcı başlıkları
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        # Yönlendirmeleri takip ederek asıl siteye ulaş
        response = requests.get(url, headers=headers, timeout=12, allow_redirects=True)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # YÖNTEM: Sosyal medya için paylaşılan özel görseli (og:image) al
            meta_image = soup.find("meta", property="og:image")
            if meta_image and meta_image.get("content"):
                return meta_image["content"]
            
            # YÖNTEM: Alternatif olarak makale içindeki ilk büyük resmi al
            img = soup.find("img", src=True)
            if img:
                return img["src"]
                
    except Exception as e:
        print(f"Görsel çekme hatası: {e}")
        
    return "https://via.placeholder.com/600x400"

def haberleri_islet():
    kaynaklar = [("tr", "TR"), ("en", "US"), ("de", "DE"), ("fr", "FR"), ("es", "ES"), ("it", "IT")]
    
    for dil, ulke in kaynaklar:
        url = f"https://news.google.com/rss?hl={dil}&gl={ulke}&ceid={ulke}:{dil}"
        feed = feedparser.parse(url)
        
        for entry in feed.entries:
            # Firebase ID güvenliği
            temiz_baslik = entry.title.replace("/", "-").replace(".", "-").replace("[", "").replace("]", "")
            doc_ref = db.collection('haberler').document(temiz_baslik)
            
            # Hatalı/Eski verileri temizlemek için burayı if kontrolsüz yazdıralım
            # Böylece her çalışma temiz veriyle güncellenir
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
            print(f"✅ İşlendi: {entry.title[:30]} | Görsel: {gorsel[:30]}...")

if __name__ == "__main__":
    haberleri_islet()
