import hmac
import hashlib
import requests
import sys
import re

SECRET = "b771055c82bce0948a9fe4aa3fedc95c0a40cb84ccda96afc4f17c865d7706d9"
API = "https://q2a.solsticestack.ru/api/v1"

HEADERS = {
    "User-Agent": "v1.7.7 Android/30 Xiaomi Mi 9",
    "Accept": "text/plain",
    "Connection": "keep-alive"
}

def get_signature(hwid):
    return hmac.new(SECRET.encode(), hwid.encode(), hashlib.sha256).hexdigest()

def clean_link(link):
    if '?' not in link:
        return link
    
    base, params = link.split('?', 1)
    param_list = params.split('&')
    
    # Оставляем только те параметры, которые не начинаются с alpn
    new_params = [p for p in param_list if not p.startswith('alpn=')]
    
    # Собираем обратно
    return f"{base}?{'&'.join(new_params)}"

def get_configs(hwid):
    sig = get_signature(hwid)
    headers = HEADERS.copy()
    headers["X-Signature"] = sig
    try:
        r = requests.get(f"{API}/sub/{hwid}", headers=headers)
        raw_text = r.text.replace('\\n', '\n').replace('"', '')
        
        # Обрабатываем каждую строку отдельно
        lines = raw_text.splitlines()
        cleaned_lines = [clean_link(line) for line in lines if line.strip()]
        
        return "\n".join(cleaned_lines)
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    hwid = sys.argv[1] if len(sys.argv) > 1 else "testdevice"
    data = get_configs(hwid)
    
    if data:
        with open("configs.txt", "w", encoding="utf-8") as f:
            f.write(data)
        print("Configs cleaned and saved.")
