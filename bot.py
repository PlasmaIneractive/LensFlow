import os
import json
import feedparser
from firebase_admin import credentials, initialize_app, firestore

# Firebase Bağlantısı
service_account = json.loads(os.getenv('FIREBASE_SERVICE_ACCOUNT'))
cred = credentials.Certificate(service_account)
initialize_app(cred)
db = firestore.client()

# Dil bazlı gerçek RSS kaynakları (Google News yerine)
RSS_KAYNAKLARI = {
    "tr": ["https://www.hurriyet.com.tr/rss/anasayfa", "https://www.sozcu.com.tr/rss/haberler.xml"],
    "en": ["https://feeds.npr.org/1001/rss.xml", "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml"],
    "de": ["https://www.tagesschau.de/xml/rss2/"],
    # Diğer dilleri buraya gerçek RSS linkleriyle ekleyebilirsin
}

def haberleri_islet():
    for dil, urls in RSS_KAYNAKLARI.items():
        for url in urls:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]: # Her kaynaktan 5 haber çek
                
                # Görseli doğrudan 'enclosure' veya 'media_content'ten al
                gorsel = "https://via.placeholder.com/600x400"
                if hasattr(entry, 'enclosures') and entry.enclosures:
                    gorsel = entry.enclosures[0]['url']
                elif hasattr(entry, 'media_content'):
                    gorsel = entry.media_content[0]['url']

                temiz_baslik = entry.title.replace("/", "-").replace(".", "-")
                doc_ref = db.collection('haberler').document(temiz_baslik)
                
                veri = {
                    "baslik": entry.title,
                    "link": entry.link,
                    "gorsel": gorsel,
                    "tarih": firestore.SERVER_TIMESTAMP,
                    "dil": dil,
                    "kategori": "Gündem",
                    "kaynak": entry.source.get('title', 'Haber Sitesi') if 'source' in entry else 'Haber'
                }
                
                doc_ref.set(veri)
                print(f"✅ Gerçek Kaynaktan Alındı: {entry.title[:30]}")

if __name__ == "__main__":
    haberleri_islet()
