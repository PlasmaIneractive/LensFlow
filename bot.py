import os
import json
import asyncio
import feedparser
import aiohttp
import random
import re
from firebase_admin import credentials, initialize_app, firestore

# Firebase Bağlantısı
if 'FIREBASE_CREDENTIALS_JSON' in os.environ:
    service_account = json.loads(os.getenv('FIREBASE_CREDENTIALS_JSON'))
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

async def og_image_cek(session, link, headers):
    """Haber sayfasından og:image meta etiketini çek"""
    try:
        async with session.get(link, headers=headers, timeout=10) as r:
            if r.status == 200:
                html = await r.text()
                # og:image ara
                match = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html)
                if not match:
                    match = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', html)
                if match:
                    return match.group(1).strip()
    except Exception as e:
        print(f"⚠️ og:image çekilemedi ({link[:50]}): {e}")
    return ""

async def haber_isleyici(session, kaynak):
    url = kaynak.get('url')
    kaynak_ismi = kaynak.get('isim')
    if not kaynak_ismi:
        kaynak_ismi = url.split('/')[2].replace('www.', '').split('.')[0].capitalize()

    try:
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

            for entry in feed.entries[:3]:
                baslik = getattr(entry, 'title', 'Başlık Yok')
                link = getattr(entry, 'link', '#')

                doc_id = link.split('/')[-1] or baslik.replace("/", "-")
                doc_ref = db.collection('haberler').document(doc_id)

                # Görsel çıkarma — RSS'ten dene
                gorsel = ""
                if hasattr(entry, 'enclosures') and entry.enclosures:
                    gorsel = entry.enclosures[0].get('url', '')
                elif hasattr(entry, 'media_content') and entry.media_content:
                    gorsel = entry.media_content[0].get('url', '')
                elif hasattr(entry, 'image') and entry.image:
                    gorsel = entry.image.get('href', '')

                # RSS'te görsel yoksa haber sayfasından og:image çek
                if not gorsel and link and link != '#':
                    gorsel = await og_image_cek(session, link, headers)

                if gorsel:
                    print(f"🖼️ Görsel bulundu: {gorsel[:60]}")
                else:
                    print(f"⚠️ Görsel bulunamadı: {baslik[:40]}")

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
    kaynaklar_ref = db.collection('kaynaklar').where('aktif', '==', True).stream()
    RSS_KAYNAKLARI = [doc.to_dict() for doc in kaynaklar_ref]

    print(f"🚀 {len(RSS_KAYNAKLARI)} adet kaynak Firebase'den alındı, başlanıyor...")

    async with aiohttp.ClientSession() as session:
        for i in range(0, len(RSS_KAYNAKLARI), 2):
            tasks = [haber_isleyici(session, k) for k in RSS_KAYNAKLARI[i:i+2]]
            await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
