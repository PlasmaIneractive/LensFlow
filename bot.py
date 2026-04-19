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

ddef gorsel_bul(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 1. Strateji: Sosyal medya meta etiketleri (En garantisi)
        for tag in ["og:image", "twitter:image", "image"]:
            gorsel = soup.find("meta", property=tag) or soup.find("meta", attrs={"name": tag})
            if gorsel and gorsel.get("content"):
                return gorsel["content"]
        
        # 2. Strateji: Eğer meta yoksa, haberin içindeki ilk büyük img tag'ini bul
        images = soup.find_all("img")
        for img in images:
            src = img.get("src")
            if src and len(src) > 20 and not src.endswith(".svg"): # Küçük ikonları ele
                return src if src.startswith("http") else url + src
                
    except Exception as e:
        print(f"Görsel çekme hatası: {e}")
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
