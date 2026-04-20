import os
import json
import asyncio
import feedparser
import aiohttp
from firebase_admin import credentials, initialize_app, firestore

# Firebase Bağlantısı
# GitHub Actions kullanıyorsan secrets üzerinden, yerelde çalışıyorsan dosyadan
if 'FIREBASE_SERVICE_ACCOUNT' in os.environ:
    service_account = json.loads(os.getenv('FIREBASE_SERVICE_ACCOUNT'))
    cred = credentials.Certificate(service_account)
else:
    cred = credentials.Certificate('serviceAccountKey.json')
    
initialize_app(cred)
db = firestore.client()

def kaynak_adi_bul(link, entry):
    if hasattr(entry, 'source') and 'title' in entry.source:
        return entry.source['title']
    
    # Kendi haritanı burada tutmaya devam edebilirsin
    kaynak_haritasi = {
        "hurriyet": "Hürriyet", "sozcu": "Sözcü", "sabah": "Sabah", "milliyet": "Milliyet",
        "cumhuriyet": "Cumhuriyet", "star": "Star", "takvim": "Takvim", "dunya": "Dünya",
        "ntv": "NTV", "cnnturk": "CNN Türk", "haberturk": "Habertürk", "aa.com": "Anadolu Ajansı",
        "donanimhaber": "DonanımHaber", "chip": "Chip"
    }
    for domain, isim in kaynak_haritasi.items():
        if domain in link: return isim
    return "Haber"

def veritabanindan_kaynaklari_yukle():
    """Firebase'den sadece aktif kaynakları çeker."""
    kaynaklar_ref = db.collection('kaynaklar').where('aktif', '==', True).stream()
    return [doc.to_dict() for doc in kaynaklar_ref]

async def haber_isleyici(session, kaynak):
    try:
        async with session.get(kaynak['url'], timeout=15) as response:
            content = await response.text()
            feed = feedparser.parse(content)
            for entry in feed.entries[:5]:
                doc_ref = db.collection('haberler').document(entry.title.replace("/", "-"))
                
                gorsel = "https://via.placeholder.com/600x400"
                if hasattr(entry, 'enclosures') and entry.enclosures: gorsel = entry.enclosures[0]['url']
                elif hasattr(entry, 'media_content'): gorsel = entry.media_content[0]['url']
                
                veri = {
                    "baslik": entry.title, "link": entry.link, "gorsel": gorsel,
                    "tarih": firestore.SERVER_TIMESTAMP, "dil": kaynak.get('dil', 'tr'),
                    "kategori": kaynak.get('kategori', 'Gündem'), "kaynak": kaynak_adi_bul(entry.link, entry)
                }
                doc_ref.set(veri)
                print(f"✅ İşlendi: {veri['kaynak']} - {entry.title[:30]}")
    except Exception as e: print(f"Hata ({kaynak['url']}): {e}")

async def main():
    # Firebase'den listeyi çek
    RSS_KAYNAKLARI = veritabanindan_kaynaklari_yukle()
    print(f"🚀 {len(RSS_KAYNAKLARI)} adet kaynak bulundu, işleniyor...")
    
    async with aiohttp.ClientSession() as session:
        tasks = [haber_isleyici(session, k) for k in RSS_KAYNAKLARI]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
