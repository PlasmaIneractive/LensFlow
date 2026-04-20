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

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
]

async def haber_isleyici(session, kaynak):
    try:
        await asyncio.sleep(random.uniform(2, 5))
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        
        async with session.get(kaynak['url'], headers=headers, timeout=30) as response:
            if response.status != 200:
                print(f"⚠️ Hata ({response.status}): {kaynak['url']}")
                return
                
            content = await response.text()
            feed = feedparser.parse(content)
            
            for entry in feed.entries[:5]:
                # Benzersiz ID için linki kullanıyoruz
                doc_id = entry.link.split('/')[-1] or entry.title.replace("/", "-")
                doc_ref = db.collection('haberler').document(doc_id)
                
                gorsel = "https://via.placeholder.com/600x400"
                # RSS içeriğinden görsel çekme mantığı
                if hasattr(entry, 'enclosures') and entry.enclosures: 
                    gorsel = entry.enclosures[0]['url']
                elif hasattr(entry, 'media_content'): 
                    gorsel = entry.media_content[0]['url']
                elif hasattr(entry, 'image'):
                    gorsel = entry.image['href']
                
                veri = {
                    "baslik": entry.title, 
                    "link": entry.link, 
                    "gorsel": gorsel,
                    "tarih": firestore.SERVER_TIMESTAMP, 
                    "dil": kaynak.get('dil', 'en'),
                    "kategori": kaynak.get('kategori', 'Global'), 
                    # Kaynak ismini doğrudan Firebase'deki dokümandan alıyoruz
                    "kaynak": kaynak.get('isim', 'Global News') 
                }
                doc_ref.set(veri, merge=True)
                print(f"✅ Başarılı: {veri['kaynak']} - {entry.title[:30]}")
                
    except Exception as e: 
        print(f"❌ Kritik Hata ({kaynak.get('url')}): {e}")

async def main():
    # Sadece Firebase'den gelen veriyi kullanıyoruz
    kaynaklar_ref = db.collection('kaynaklar').where('aktif', '==', True).stream()
    RSS_KAYNAKLARI = [doc.to_dict() for doc in kaynaklar_ref]
    
    print(f"🚀 {len(RSS_KAYNAKLARI)} global kaynak Firebase'den çekildi, işleniyor...")
    
    async with aiohttp.ClientSession() as session:
        for i in range(0, len(RSS_KAYNAKLARI), 3):
            tasks = [haber_isleyici(session, k) for k in RSS_KAYNAKLARI[i:i+3]]
            await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
