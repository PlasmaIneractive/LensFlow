import os
import json
import asyncio
import feedparser
import aiohttp
from firebase_admin import credentials, initialize_app, firestore

# Firebase Bağlantısı
service_account = json.loads(os.getenv('FIREBASE_SERVICE_ACCOUNT'))
cred = credentials.Certificate(service_account)
initialize_app(cred)
db = firestore.client()

def kaynak_adi_bul(link, entry):
    """Link içerisinden veya RSS verisinden otomatik kaynak adını belirler."""
    # 1. RSS'in kendi verdiği kaynak adını dene
    if hasattr(entry, 'source') and 'title' in entry.source:
        return entry.source['title']
    
    # 2. Link üzerinden eşleştir
    kaynak_haritasi = {
        "sozcu.com.tr": "Sözcü",
        "hurriyet.com.tr": "Hürriyet",
        "sabah.com.tr": "Sabah",
        "milliyet.com.tr": "Milliyet",
        "ntv.com.tr": "NTV",
        "aa.com.tr": "Anadolu Ajansı",
        "haberturk.com": "Habertürk",
        "cumhuriyet.com.tr": "Cumhuriyet",
        "donanimhaber.com": "DonanımHaber"
    }
    
    for domain, isim in kaynak_haritasi.items():
        if domain in link:
            return isim
    return "Haber"

# Modüler Kaynak Listesi
RSS_KAYNAKLARI = [
    {"url": "https://www.hurriyet.com.tr/rss/anasayfa", "kategori": "Gündem", "dil": "tr"},
    {"url": "https://www.sozcu.com.tr/rss/haberler.xml", "kategori": "Gündem", "dil": "tr"},
    # Yüzlerce kaynağını buraya ekleyebilirsin
]

async def haber_isleyici(session, kaynak):
    try:
        async with session.get(kaynak['url'], timeout=10) as response:
            content = await response.text()
            feed = feedparser.parse(content)
            
            for entry in feed.entries[:5]:
                temiz_baslik = entry.title.replace("/", "-").replace(".", "-")
                doc_ref = db.collection('haberler').document(temiz_baslik)
                
                gorsel = "https://via.placeholder.com/600x400"
                if hasattr(entry, 'enclosures') and entry.enclosures:
                    gorsel = entry.enclosures[0]['url']
                elif hasattr(entry, 'media_content'):
                    gorsel = entry.media_content[0]['url']
                
                veri = {
                    "baslik": entry.title,
                    "link": entry.link,
                    "gorsel": gorsel,
                    "tarih": firestore.SERVER_TIMESTAMP,
                    "dil": kaynak['dil'],
                    "kategori": kaynak['kategori'],
                    "kaynak": kaynak_adi_bul(entry.link, entry)
                }
                doc_ref.set(veri)
                print(f"✅ Yazıldı: {veri['kaynak']} - {entry.title[:30]}")
    except Exception as e:
        print(f"Hata ({kaynak['url']}): {e}")

async def main():
    async with aiohttp.ClientSession() as session:
        tasks = [haber_isleyici(session, k) for k in RSS_KAYNAKLARI]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
