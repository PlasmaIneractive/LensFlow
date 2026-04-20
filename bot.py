import os
import json
import feedparser
from firebase_admin import credentials, initialize_app, firestore

# Firebase Bağlantısı
service_account = json.loads(os.getenv('FIREBASE_SERVICE_ACCOUNT'))
cred = credentials.Certificate(service_account)
initialize_app(cred)
db = firestore.client()

def kaynak_adi_bul(entry, link):
    """Link veya RSS verisinden otomatik kaynak adını belirler."""
    if hasattr(entry, 'source') and 'title' in entry.source:
        return entry.source['title']
    
    # Yeni kaynak eklemek için sadece bu listeyi genişletmen yeterli
    kaynak_haritasi = {
        "sozcu.com.tr": "Sözcü",
        "hurriyet.com.tr": "Hürriyet",
        "ntv.com.tr": "NTV",
        "haberturk.com": "Habertürk",
        "nytimes.com": "New York Times",
        "bbc.com": "BBC",
        "dw.com": "Deutsche Welle"
    }
    
    for domain, isim in kaynak_haritasi.items():
        if domain in link:
            return isim
    return "Haber"

def haberleri_islet():
    # Güncel ve zengin içerikli RSS kaynak listesi
    RSS_KAYNAKLARI = [
        "https://www.hurriyet.com.tr/rss/anasayfa",
        "https://www.sozcu.com.tr/rss/haberler.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
        "https://www.tagesschau.de/xml/rss2/"
    ]
    
    for url in RSS_KAYNAKLARI:
        feed = feedparser.parse(url)
        
        for entry in feed.entries[:10]: # Her kaynaktan en güncel 10 haber
            # Firebase ID için temizleme
            temiz_baslik = entry.title.replace("/", "-").replace(".", "-").replace("[", "").replace("]", "")
            doc_ref = db.collection('haberler').document(temiz_baslik)
            
            # Görseli en garantili yerden, yani 'enclosure' etiketinden al
            gorsel = "https://via.placeholder.com/600x400"
            if hasattr(entry, 'enclosures') and entry.enclosures:
                gorsel = entry.enclosures[0]['url']
            elif hasattr(entry, 'media_content'):
                gorsel = entry.media_content[0]['url']
                
            # Veriyi hikayeleştirerek oluşturuyoruz
            veri = {
                "baslik": entry.title,
                "link": entry.link,
                "gorsel": gorsel,
                "tarih": firestore.SERVER_TIMESTAMP,
                "dil": "tr", # Kaynaklarına göre dil kısmını geliştirebilirsin
                "kategori": "Gündem",
                "kaynak": kaynak_adi_bul(entry, entry.link)
            }
            
            doc_ref.set(veri)
            print(f"✅ İşlendi: {veri['kaynak']} - {entry.title[:30]}...")

if __name__ == "__main__":
    haberleri_islet()
