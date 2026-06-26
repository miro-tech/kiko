import hmac
import hashlib
import requests
import sys

SECRET = "b771055c82bce0948a9fe4aa3fedc95c0a40cb84ccda96afc4f17c865d7706d9"
API = "https://q2a.solsticestack.ru/api/v1"

HEADERS = {
    "User-Agent": "v1.7.7 Android/30 Xiaomi Mi 9",
    "Accept": "text/plain",
    "Connection": "keep-alive"
}

def get_signature(hwid):
    return hmac.new(SECRET.encode(), hwid.encode(), hashlib.sha256).hexdigest()

def get_configs(hwid):
    sig = get_signature(hwid)
    headers = HEADERS.copy()
    headers["X-Signature"] = sig
    try:
        r = requests.get(f"{API}/sub/{hwid}", headers=headers)
        # Если API отдает JSON, то r.text может содержать экранированные \n
        # Если API отдает просто текст, то r.text — это то, что нужно
        return r.text.replace('\\n', '\n').replace('"', '') 
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    hwid = sys.argv[1]
    data = get_configs(hwid)
    
    if data:
        with open("configs.txt", "w", encoding="utf-8") as f:
            f.write(data.strip())
