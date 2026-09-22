#!/usr/bin/env python3

import hmac
import hashlib
import requests
import sys
import json

# ============================================================
# KIKO VPN
# Firebase Remote Config -> BACKEND_PROXY_LIST -> /sub/{hwid}
# ============================================================

API_KEY = "AIzaSyDAuJ6RLORsVPpmD9cSQByggj5dx2NIUOQ"
APP_ID = "1:701333512151:android:ba3f3f83342a0b5003f592"
PROJECT = "kikovpn-f968d"
PACKAGE = "com.kikovpn.app"
APP_VERSION = "1.50.2.1235"
PLATFORM_VERSION = "34"

SECRET = "b771055c82bce0948a9fe4aa3fedc95c0a40cb84ccda96afc4f17c865d7706d9"

RC_URL = (
    f"https://firebaseremoteconfig.googleapis.com/v1/projects/{PROJECT}"
    f"/namespaces/firebase:fetch?key={API_KEY}"
)

HEADERS = {
    "User-Agent": "v1.7.7 Android/30 Xiaomi Mi 9",
    "Accept": "text/plain",
    "Connection": "keep-alive",
}

TIMEOUT = 20


# ============================================================
# Firebase Remote Config
# ============================================================

def fetch_remote_config():
    payload = {
        "appId": APP_ID,
        "appInstanceId": "PROD",
        "packageName": PACKAGE,
        "appVersion": APP_VERSION,
        "platformVersion": PLATFORM_VERSION,
    }

    headers = {
        "User-Agent": "okhttp/4.12.0",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    r = requests.post(
        RC_URL,
        json=payload,
        headers=headers,
        timeout=25,
    )

    r.raise_for_status()

    data = r.json()
    return data.get("entries") or {}


# ============================================================
# Получение backend-ов
# ============================================================

def pick_api_bases(entries):
    raw = (entries.get("BACKEND_PROXY_LIST") or "").strip()

    bases = []

    for part in raw.split(";"):
        part = part.strip().rstrip("/")

        if part:
            bases.append(part)

    return bases


# ============================================================
# Проверка backend
# ============================================================

def probe_health(base):
    health_url = base.rstrip("/") + "/health"

    headers = {
        "User-Agent": "KikoVPN/1.50.2.1235 Android",
        "Accept": "application/json",
    }

    try:
        r = requests.get(
            health_url,
            headers=headers,
            timeout=12,
        )

        return r.status_code == 200 and "ok" in r.text.lower()

    except requests.RequestException:
        return False


def get_api_base(entries):
    bases = pick_api_bases(entries)

    print("\n=== BACKEND_PROXY_LIST ===")

    if not bases:
        raise RuntimeError("BACKEND_PROXY_LIST пуст")

    alive = []

    for base in bases:
        ok = probe_health(base)

        print(
            f"  {'OK' if ok else 'DOWN'}  {base}"
        )

        if ok:
            alive.append(base)

    if alive:
        print("\n=== Актуальный API ===")
        print("  API_BASE =", alive[0])

        if len(alive) > 1:
            print("  fallbacks:", alive[1:])

        return alive[0]

    # fallback — первый backend даже если /health недоступен
    print("\nНет живых backend.")
    print("Используем первый из BACKEND_PROXY_LIST как fallback:")
    print("  API_BASE =", bases[0])

    return bases[0]


# ============================================================
# HMAC
# ============================================================

def get_signature(hwid):
    return hmac.new(
        SECRET.encode(),
        hwid.encode(),
        hashlib.sha256
    ).hexdigest()


# ============================================================
# Очистка конфигов
# ============================================================

def clean_link(link):
    link = link.strip()

    if not link:
        return ""

    if "#" in link:
        base_part, name_part = link.split("#", 1)
        name_suffix = f"#{name_part}"
    else:
        base_part = link
        name_suffix = ""

    if "?" not in base_part:
        return f"{base_part}{name_suffix}"

    base, params = base_part.split("?", 1)

    param_list = params.split("&")

    # Удаляем только alpn=
    new_params = [
        p for p in param_list
        if not p.lower().startswith("alpn=")
    ]

    clean_params = (
        f"?{'&'.join(new_params)}"
        if new_params
        else ""
    )

    return f"{base}{clean_params}{name_suffix}"


# ============================================================
# Получение конфигов
# ============================================================

def get_configs(api_base, hwid):

    sig = get_signature(hwid)

    headers = HEADERS.copy()
    headers["X-Signature"] = sig

    url = f"{api_base.rstrip('/')}/sub/{hwid}"

    print("\n=== SUBSCRIPTION ===")
    print("URL:", url)
    print("HWID:", hwid)

    try:
        r = requests.get(
            url,
            headers=headers,
            timeout=TIMEOUT,
        )

        print("HTTP:", r.status_code)

        r.raise_for_status()

        raw_text = r.text

        # Аналогично старому скрипту
        raw_text = raw_text.replace("\\n", "\n").replace('"', "")

        lines = raw_text.splitlines()

        cleaned_lines = []

        for line in lines:
            line = line.strip()

            if not line:
                continue

            cleaned = clean_link(line)

            if cleaned:
                cleaned_lines.append(cleaned)

        return "\n".join(cleaned_lines)

    except requests.RequestException as e:
        print(f"HTTP Error: {e}")
        return None

    except Exception as e:
        print(f"Error: {e}")
        return None


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print(" KIKO VPN CONFIG FETCHER")
    print("=" * 60)

    hwid = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "testdevice"
    )

    # --------------------------------------------------------
    # Firebase
    # --------------------------------------------------------

    print("\n=== Firebase Remote Config ===")

    try:
        entries = fetch_remote_config()

    except Exception as e:
        print("Firebase error:", e)
        return

    for key in sorted(entries):
        value = entries[key]

        value_str = str(value)

        if len(value_str) > 120:
            value_str = value_str[:100] + "..."

        print(f"  {key}: {value_str}")

    # --------------------------------------------------------
    # Backend
    # --------------------------------------------------------

    try:
        api_base = get_api_base(entries)

    except Exception as e:
        print("\nAPI error:", e)
        return

    # --------------------------------------------------------
    # Subscription
    # --------------------------------------------------------

    data = get_configs(
        api_base,
        hwid
    )

    if not data:
        print("\nКонфиги не получены.")
        return

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    with open(
        "configs.txt",
        "w",
        encoding="utf-8"
    ) as f:
        f.write(data)

    count = len([
        x for x in data.splitlines()
        if x.strip()
    ])

    print("\n" + "=" * 60)
    print("ГОТОВО")
    print("=" * 60)
    print("Configs:", count)
    print("Saved: configs.txt")


if __name__ == "__main__":
    main()
