import os
import json
import asyncio
import feedparser
import aiohttp
import random
from firebase_admin import credentials, initialize_app, firestore

# Firebase Bağlantısı
if 'FIREBASE_SERVICE_ACCOUNT' in os.environ:
    service_account = json.loads(os.getenv('FIREBASE_SERVICE_ACCOUNT'))
    cred = credentials.Certificate(service_account)
else:
    cred = credentials.Certificate('serviceAccountKey.json')
    
initialize_app(cred)
db = firestore.client()

# Tarayıcı imzaları
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
]

async def haber_isleyici(session, kaynak):
    url = kaynak.get('url')
    # Firebase'de isim varsa onu al, yoksa URL'den türet
    kaynak_ismi = kaynak.get('isim')
    if not kaynak_ismi:
        kaynak_ismi = url.split('/')[2].replace('www.', '').split('.')[0].capitalize()
    
    try:
        # Sunucuları yormamak için rastgele bekleme
        await asyncio.sleep(random.uniform(2, 5))
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        
        async with session.get(url, headers=headers, timeout=30) as response:
            if response.status != 200:
                print(f"⚠️ Hata ({response.status}): {url}")
                return
                
            content = await response.text()
            feed = feedparser.parse(content)
            
            if not feed.entries:
                print(f"⚠️ RSS İçeriği Boş: {url}")
                return

            # Her kaynaktan sadece en yeni 3 haberi alarak okuma kotanı koruyoruz
            for entry in feed.entries[:3]:
                baslik = getattr(entry, 'title', 'Başlık Yok')
                link = getattr(entry, 'link', '#')
                
                # Doküman ID'si için linkten türetme
                doc_id = link.split('/')[-1] or baslik.replace("/", "-")
                doc_ref = db.collection('haberler').document(doc_id)
                
                # Görsel çıkarma
                gorsel = "https://via.placeholder.com/600x400"
                if hasattr(entry, 'enclosures') and entry.enclosures: 
                    gorsel = entry.enclosures[0]['url']
                elif hasattr(entry, 'media_content'): 
                    gorsel = entry.media_content[0]['url']
                elif hasattr(entry, 'image'):
                    gorsel = entry.image['href']
                
                veri = {
                    "baslik": baslik, 
                    "link": link, 
                    "gorsel": gorsel,
                    "tarih": firestore.SERVER_TIMESTAMP, 
                    "dil": kaynak.get('dil', 'en'),
                    "kategori": kaynak.get('kategori', 'Global'), 
                    "kaynak": kaynak_ismi
                }
                
                doc_ref.set(veri, merge=True)
                print(f"✅ Başarılı: {kaynak_ismi} - {baslik[:50]}")
                
    except Exception as e: 
        print(f"❌ Kritik Hata ({url}): {e}")

async def main():
    # Firebase'den kaynakları çek (Sadece aktif olanları)
    kaynaklar_ref = db.collection('kaynaklar').where('aktif', '==', True).stream()
    RSS_KAYNAKLARI = [doc.to_dict() for doc in kaynaklar_ref]
    
    print(f"🚀 {len(RSS_KAYNAKLARI)} adet kaynak Firebase'den alındı, başlanıyor...")
    
    async with aiohttp.ClientSession() as session:
        # Kota dostu olması için 2'şerli gruplar halinde işliyoruz
        for i in range(0, len(RSS_KAYNAKLARI), 2):
            tasks = [haber_isleyici(session, k) for k in RSS_KAYNAKLARI[i:i+2]]
            await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
