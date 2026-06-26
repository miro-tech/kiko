import hmac
import hashlib
import requests
import sys

SECRET = "b771055c82bce0948a9fe4aa3fedc95c0a40cb84ccda96afc4f17c865d7706d9"
API = "https://q2a.solsticestack.ru/api/v1"

HEADERS = {
    "User-Agent": "v1.7.7 Android/30 Xiaomi Mi 9",
    "Accept": "text/plain", # Ожидаем текст
    "Connection": "keep-alive"
}

def get_signature(hwid):
    return hmac.new(SECRET.encode(), hwid.encode(), hashlib.sha256).hexdigest()

def get_configs(hwid):
    sig = get_signature(hwid)
    headers = HEADERS.copy()
    headers["X-Signature"] = sig
    try:
        # Используем r.text, так как сервер отдает чистый текст
        r = requests.get(f"{API}/sub/{hwid}", headers=headers)
        return r.text if r.status_code == 200 else None
    except Exception:
        return None

if __name__ == "__main__":
    hwid = sys.argv[1] if len(sys.argv) > 1 else "testdevice"
    output_file = "configs.txt"
    
    data = get_configs(hwid)
    
    if data:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(data)
        print(f"Successfully saved {output_file}")
    else:
        print("Error: Could not fetch configs")
        sys.exit(1)
        
