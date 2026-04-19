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

def haberleri_islet():
    kaynaklar = [
        ("tr", "TR"), ("en", "US"), ("de", "DE"), ("fr", "FR"), ("es", "ES"), ("it", "IT")
    ]
    
    for dil, ulke in kaynaklar:
        url = f"https://news.google.com/rss?hl={dil}&gl={ulke}&ceid={ulke}:{dil}"
        feed = feedparser.parse(url)
        
        for entry in feed.entries:
            # 1. Adım: Başlığı temizle (Firebase hatasını önlemek için)
            temiz_baslik = entry.title.replace("/", "-").replace(".", "-").replace("[", "").replace("]", "")
            doc_ref = db.collection('haberler').document(temiz_baslik)
            
            # 2. Adım: Haber zaten var mı kontrol et
            if not doc_ref.get().exists:
                
                # 3. Adım: Görseli RSS içinden al (En garanti yöntem)
                gorsel = "https://via.placeholder.com/600x400" # Varsayılan
                
                # Google News RSS'inde görsel genelde 'media_content' içinde olur
                if hasattr(entry, 'media_content'):
                    gorsel = entry.media_content[0]['url']
                elif hasattr(entry, 'links'):
                    for link in entry.links:
                        if 'image' in link.get('type', ''):
                            gorsel = link['href']
                            break
                
                # 4. Adım: Veriyi hazırla
                veri = {
                    "baslik": entry.title,
                    "link": entry.link,
                    "gorsel": gorsel,
                    "tarih": firestore.SERVER_TIMESTAMP,
                    "dil": dil,
                    "kategori": "Gündem", 
                    "kaynak": entry.source.get('title', 'Google News') if 'source' in entry else 'Google News'
                }
                
                # 5. Adım: Firebase'e yaz
                doc_ref.set(veri)
                print(f"✅ Eklendi: {entry.title} ({dil}) - Görsel: {gorsel[:30]}...")

if __name__ == "__main__":
    haberleri_islet()
