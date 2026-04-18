import feedparser
import firebase_admin
from firebase_admin import credentials, firestore
import requests
from bs4 import BeautifulSoup
import hashlib

# Firebase Bağlantısı
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

def get_og_image(url):
    """Haberin orijinal görselini linke gidip bulur."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36"
    }
    try:
        response = requests.get(url, timeout=5, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            return og_image["content"]
    except:
        return "https://via.placeholder.com/500x300?text=Görsel+Bulunamadı"
    return "https://via.placeholder.com/500x300?text=Görsel+Bulunamadı"

def haberleri_kaydet(sorgu, dil="tr", ulke="TR"):
    print(f"\n--- {sorgu.upper()} ({ulke}-{dil}) taranıyor ---")
    rss_url = f"https://news.google.com/rss/search?q={sorgu}&hl={dil}&gl={ulke}&ceid={ulke}:{dil}"
    besleme = feedparser.parse(rss_url)
    
    # Tüm haberleri çekmek için döngüyü sınırsız yaptık
    for haber in besleme.entries:
        # MD5 ile benzersiz ID oluştur (Tekilleştirme)
        doc_id = hashlib.md5(haber.link.encode()).hexdigest()
        doc_ref = db.collection("haberler").document(doc_id)
        
        # Eğer haber zaten varsa bir sonrakine geç
        if doc_ref.get().exists:
            continue

        # Görseli çek
        gorsel = get_og_image(haber.link)

        veri = {
            "baslik": haber.title,
            "gorsel": gorsel,
            "tarih": firestore.SERVER_TIMESTAMP,
            "link": haber.link,
            "kaynak": haber.source.get('title', 'Kaynak'),
            "dil": dil,
            "ulke": ulke
        }
        
        doc_ref.set(veri)
        print(f"✅ Eklendi: {haber.title[:40]}...")

# Görevler (Buraya istediğin kadar yeni konu ekleyebilirsin)
if __name__ == "__main__":
    gorevler = [
        ("gastronomi", "tr", "TR"), 
        ("technology", "en", "US"),
        ("yatırım", "tr", "TR")
    ]
    for s, d, u in gorevler:
        haberleri_kaydet(s, d, u)