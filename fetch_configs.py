#!/usr/bin/env python3

import hmac
import hashlib
import requests
import sys
import ssl
import urllib.request
import json

# ============================================================
# KIKO VPN
# Firebase Remote Config -> BACKEND_PROXY_LIST
# ============================================================

API_KEY = "AIzaSyDAuJ6RLORsVPpmD9cSQByggj5dx2NIUOQ"
APP_ID = "1:701333512151:android:ba3f3f83342a0b5003f592"
PROJECT = "kikovpn-f968d"
PACKAGE = "com.kikovpn.app"

APP_VERSION = "1.50.2.1235"
PLATFORM_VERSION = "34"

# ============================================================
# Секрет для X-Signature
# ============================================================

SECRET = "b771055c82bce0948a9fe4aa3fedc95c0a40cb84ccda96afc4f17c865d7706d9"

# ============================================================
# Firebase Remote Config
# ============================================================

RC_URL = (
    f"https://firebaseremoteconfig.googleapis.com/v1/projects/{PROJECT}"
    f"/namespaces/firebase:fetch?key={API_KEY}"
)

CTX = ssl.create_default_context()

# ============================================================
# Старые рабочие headers для subscription
# ============================================================

HEADERS = {
    "User-Agent": "v1.7.7 Android/30 Xiaomi Mi 9",
    "Accept": "text/plain",
    "Connection": "keep-alive"
}


# ============================================================
# Firebase
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

    req = urllib.request.Request(
        RC_URL,
        data=json.dumps(payload).encode(),
        headers=headers,
        method="POST"
    )

    with urllib.request.urlopen(
        req,
        context=CTX,
        timeout=25
    ) as resp:

        if resp.status != 200:
            raise RuntimeError(
                f"Firebase HTTP {resp.status}"
            )

        data = json.loads(
            resp.read().decode()
        )

    return data.get("entries") or {}


# ============================================================
# Получаем BACKEND_PROXY_LIST
# ============================================================

def pick_api_bases(entries):

    raw = (
        entries.get("BACKEND_PROXY_LIST") or ""
    ).strip()

    bases = []

    for part in raw.split(";"):

        part = part.strip().rstrip("/")

        if part:
            bases.append(part)

    return bases


# ============================================================
# Проверяем backend
# ============================================================

def probe_health(base):

    url = base.rstrip("/") + "/health"

    try:

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent":
                    "KikoVPN/1.50.2.1235 Android",
                "Accept":
                    "application/json"
            }
        )

        with urllib.request.urlopen(
            req,
            context=CTX,
            timeout=12
        ) as resp:

            body = resp.read().decode()

            return (
                resp.status == 200
                and "ok" in body.lower()
            )

    except Exception:
        return False


# ============================================================
# Выбираем API
# ============================================================

def get_api(entries):

    bases = pick_api_bases(entries)

    print("\n=== BACKEND_PROXY_LIST ===")

    if not bases:
        raise RuntimeError(
            "BACKEND_PROXY_LIST пуст"
        )

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

        print(
            "  API_BASE =",
            alive[0]
        )

        if len(alive) > 1:

            print(
                "  fallbacks:",
                alive[1:]
            )

        return alive[0]

    print(
        "\nНет живых backend, "
        "используем первый как fallback:"
    )

    print(
        "  API_BASE =",
        bases[0]
    )

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
# Очистка ссылки
# ============================================================

def clean_link(link):

    if '#' in link:

        base_part, name_part = link.split(
            '#',
            1
        )

        name_suffix = f"#{name_part}"

    else:

        base_part = link
        name_suffix = ""

    if '?' not in base_part:

        return (
            f"{base_part}"
            f"{name_suffix}"
        )

    base, params = base_part.split(
        '?',
        1
    )

    param_list = params.split('&')

    # Оставляем всё кроме alpn=
    new_params = [
        p
        for p in param_list
        if not p.startswith("alpn=")
    ]

    clean_params = (
        f"?{'&'.join(new_params)}"
        if new_params
        else ""
    )

    return (
        f"{base}"
        f"{clean_params}"
        f"{name_suffix}"
    )


# ============================================================
# Получение конфигов
# ============================================================

def get_configs(api_base, hwid):

    sig = get_signature(hwid)

    headers = HEADERS.copy()
    headers["X-Signature"] = sig

    # ВАЖНО:
    # Firebase возвращает базу вида:
    #
    # https://vivocamera.ru/api
    #
    # Старый рабочий API был:
    #
    # https://vivocamera.ru/api/v1
    #
    # Поэтому добавляем /v1 обратно.

    api = api_base.rstrip("/") + "/v1"

    url = f"{api}/sub/{hwid}"

    print("\n=== SUBSCRIPTION ===")
    print("URL:", url)
    print("HWID:", hwid)

    try:

        r = requests.get(
            url,
            headers=headers,
            timeout=20
        )

        print(
            "HTTP:",
            r.status_code
        )

        r.raise_for_status()

        raw_text = (
            r.text
            .replace('\\n', '\n')
            .replace('"', '')
        )

        lines = raw_text.splitlines()

        cleaned_lines = [
            clean_link(line)
            for line in lines
            if line.strip()
        ]

        return "\n".join(
            cleaned_lines
        )

    except Exception as e:

        print(
            f"Error: {e}"
        )

        return None


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

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

    print(
        "\n=== Firebase Remote Config ==="
    )

    try:

        entries = fetch_remote_config()

    except Exception as e:

        print(
            "Firebase error:",
            e
        )

        sys.exit(1)

    for k in sorted(entries):

        v = entries[k]

        v = (
            str(v)
            if len(str(v)) < 120
            else str(v)[:100] + "..."
        )

        print(
            f"  {k}: {v}"
        )

    # --------------------------------------------------------
    # API
    # --------------------------------------------------------

    try:

        api_base = get_api(
            entries
        )

    except Exception as e:

        print(
            "API error:",
            e
        )

        sys.exit(1)

    # --------------------------------------------------------
    # Configs
    # --------------------------------------------------------

    data = get_configs(
        api_base,
        hwid
    )

    if data:

        with open(
            "configs.txt",
            "w",
            encoding="utf-8"
        ) as f:

            f.write(data)

        count = len(
            [
                x
                for x in data.splitlines()
                if x.strip()
            ]
        )

        print(
            "\nConfigs:",
            count
        )

        print(
            "Saved: configs.txt"
        )

    else:

        print(
            "\nКонфиги не получены"
        )
