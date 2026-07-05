import time
import json
import requests
import os
from bs4 import BeautifulSoup
from datetime import datetime

# =========================
# CONFIG
# =========================

INTERVAL = 600
STATE_FILE = "state.json"

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

SITES = {
    "Feenturm": "https://feenturm.de/collections/pokemon",
    "TCGViert Pokemon": "https://tcgviert.com/collections/pokemon",
    "TCGViert Vorbestellung": "https://tcgviert.com/collections/vorbestellungen/vorbestellungen",
    "Elbenwald": "https://www.elbenwald.de/pokemon/sammelkarten",
    "Tabletop Dragon": "https://www.tabletop-dragon.de/shop_de/trading-card-games/pokemon/vorbestellung.html",
    "Take-It-Shop": "https://take-it-shop.de/search?q=Pokemon"
}

# =========================
# STATE
# =========================

def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

# =========================
# DISCORD
# =========================

def send_discord(shop, title, url):
    try:
        requests.post(
            DISCORD_WEBHOOK,
            json={
                "content": f"""🆕 Neues Pokémon Produkt

🏪 Shop: {shop}
📦 Produkt: {title}
🔗 Link: {url}
🕒 {datetime.now().strftime('%d.%m.%Y %H:%M')}
"""
            },
            timeout=10
        )
    except Exception as e:
        print("Discord Fehler:", e)

# =========================
# FETCH
# =========================

def fetch(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    return r.text, r.status_code

# =========================
# CLEAN
# =========================

def clean(t):
    if not t:
        return ""
    return " ".join(t.split())

# =========================
# REAL PRODUCT FILTER
# =========================

def is_real_product(title, url):
    if not title:
        return False

    title = title.lower()
    url = url.lower()

    bad_keywords = [
        "login",
        "datenschutz",
        "impressum",
        "newsletter",
        "warenkorb",
        "konto",
        "facebook",
        "instagram",
        "tiktok",
        "youtube",
        "startseite",
        "versand",
        "agb",
        "faq",
        "kontakt",
        "zurück"
    ]

    if any(b in title for b in bad_keywords):
        return False

    if len(title) < 8:
        return False

    # muss etwas mit pokemon / tcg / produkt sein
    if not any(x in title for x in ["pokemon", "pokémon", "tcg", "booster", "box", "display", "tin", "deck"]):
        return False

    if "/product" not in url and "pokemon" not in url:
        return False

    return True

# =========================
# PARSER (CLEAN)
# =========================

def parse_generic(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    products = []

    for a in soup.select("a[href]"):
        href = a.get("href")
        if not href:
            continue

        title = clean(a.get_text())

        if href.startswith("/"):
            url = base_url + href.split("?")[0]
        else:
            url = href.split("?")[0]

        if not is_real_product(title, url):
            continue

        products.append((title, url))

    return products

# =========================
# SHOP RUN
# =========================

def run_shop(name, url, state):
    print(f"\n[{name}]")

    html, status = fetch(url)
    print("STATUS:", status)

    if status != 200:
        print("Fehler beim Laden")
        return state

    base_url = "/".join(url.split("/")[:3])

    products = parse_generic(html, base_url)

    print(f"{len(products)} echte Produkte gefunden.")

    known = state.get(name, [])

    known_urls = set()

    for p in known:
        if isinstance(p, dict):
            known_urls.add(p.get("url", ""))
        elif isinstance(p, str):
            known_urls.add(p)

    new_products = []

    for title, url in products:
        if url not in known_urls:
            print("Neues Produkt:", title)

            send_discord(name, title, url)

            new_products.append({
                "title": title,
                "url": url
            })

    state[name] = known + new_products

    return state

# =========================
# MAIN
# =========================

def main():
    print("=" * 60)
    print("Pokemon Multi-Shop Watcher V4 (QUALITY FILTER)")
    print("=" * 60)

    state = load_state()

    while True:
        try:
            for name, url in SITES.items():
                state = run_shop(name, url, state)

            save_state(state)

            print("\nNächster Check in 10 Minuten...")
            print("-" * 60)

            time.sleep(INTERVAL)

        except Exception as e:
            print("GLOBAL ERROR:", e)
            time.sleep(30)

if __name__ == "__main__":
    main()
