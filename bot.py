import os
import json
import feedparser
import requests
from bs4 import BeautifulSoup
from firebase_admin import credentials, initialize_app, firestore

service_account = json.loads(os.getenv('FIREBASE_SERVICE_ACCOUNT'))
cred = credentials.Certificate(service_account)
initialize_app(cred)
db = firestore.client()

def get_real_url(google_url):
    """Google RSS linkini gerçek haber sitesi linkine çevirir."""
    try:
        # Google yönlendirmesini takip etmeden, orijinal haber sitesinin URL'sini yakala
        response = requests.head(google_url, allow_redirects=True, timeout=5)
        return response.url
    except:
        return google_url

def orijinal_gorseli_cek(url):
    try:
        # Gerçek URL'yi al
        real_url = get_real_url(url)
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"}
        
        # Orijinal siteye git
        response = requests.get(real_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Meta görseli al
        og_img = soup.find("meta", property="og:image")
        if og_img and og_img.get("content"):
            return og_img["content"]
            
        return "https://via.placeholder.com/600x400"
    except:
        return "https://via.placeholder.com/600x400"

def haberleri_islet():
    # ... (diğer kısımlar aynı)
    for entry in feed.entries:
        # ... (temiz_baslik işlemleri)
        if not doc_ref.get().exists:
            gorsel = orijinal_gorseli_cek(entry.link)
            # ... (geri kalan veri kaydı)
