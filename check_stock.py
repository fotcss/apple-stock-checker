#!/usr/bin/env python3
"""
Apple In-Store Stock Monitor (UK & US)
High-performance retail store inventory checker for Apple products.
Supports multi-colour and multi-storage monitoring simultaneously in a single HTTP/2 request.
Supports UK (Postcode) and US (ZIP Code) regions.
When stock is detected, automatically launches your chosen browser (Firefox, Safari, Chrome, or Default),
plays system audio announcements, and dispatches high-priority Discord push notifications.
"""

import argparse
import json
import os
import re
import random
import ssl
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import urllib.error

# Official Apple UK Product Catalog (GBP £)
UK_PRODUCT_CATALOG = {
    "MK2D4QN/A": {"name": "iPhone Duo 256GB Star White", "price": "£1,999", "color": "Star White", "storage": "256GB", "url": "https://www.apple.com/uk/shop/product/MK2D4QN/A"},
    "MK2E4QN/A": {"name": "iPhone Duo 256GB Night Sky", "price": "£1,999", "color": "Night Sky", "storage": "256GB", "url": "https://www.apple.com/uk/shop/product/MK2E4QN/A"},
    "MK2F4QN/A": {"name": "iPhone Duo 512GB Star White", "price": "£2,199", "color": "Star White", "storage": "512GB", "url": "https://www.apple.com/uk/shop/product/MK2F4QN/A"},
    "MK2G4QN/A": {"name": "iPhone Duo 512GB Night Sky", "price": "£2,199", "color": "Night Sky", "storage": "512GB", "url": "https://www.apple.com/uk/shop/product/MK2G4QN/A"},
    "MK2H4QN/A": {"name": "iPhone Duo 1TB Star White", "price": "£2,599", "color": "Star White", "storage": "1TB", "url": "https://www.apple.com/uk/shop/product/MK2H4QN/A"},
    "MK2J4QN/A": {"name": "iPhone Duo 1TB Night Sky", "price": "£2,599", "color": "Night Sky", "storage": "1TB", "url": "https://www.apple.com/uk/shop/product/MK2J4QN/A"},
    "MK2K4QN/A": {"name": "iPhone Duo 2TB Star White", "price": "£3,199", "color": "Star White", "storage": "2TB", "url": "https://www.apple.com/uk/shop/product/MK2K4QN/A"},
    "MK2L4QN/A": {"name": "iPhone Duo 2TB Night Sky", "price": "£3,199", "color": "Night Sky", "storage": "2TB", "url": "https://www.apple.com/uk/shop/product/MK2L4QN/A"},
}

# Official Apple US Product Catalog (USD $)
US_PRODUCT_CATALOG = {
    "MK1E4LL/A": {"name": "iPhone Duo 256GB Star White", "price": "$1,999", "color": "Star White", "storage": "256GB", "url": "https://www.apple.com/shop/product/MK1E4LL/A"},
    "MK1F4LL/A": {"name": "iPhone Duo 256GB Night Sky", "price": "$1,999", "color": "Night Sky", "storage": "256GB", "url": "https://www.apple.com/shop/product/MK1F4LL/A"},
    "MK1G4LL/A": {"name": "iPhone Duo 512GB Star White", "price": "$2,199", "color": "Star White", "storage": "512GB", "url": "https://www.apple.com/shop/product/MK1G4LL/A"},
    "MK1H4LL/A": {"name": "iPhone Duo 512GB Night Sky", "price": "$2,199", "color": "Night Sky", "storage": "512GB", "url": "https://www.apple.com/shop/product/MK1H4LL/A"},
    "MK1J4LL/A": {"name": "iPhone Duo 1TB Star White", "price": "$2,599", "color": "Star White", "storage": "1TB", "url": "https://www.apple.com/shop/product/MK1J4LL/A"},
    "MK1L4LL/A": {"name": "iPhone Duo 1TB Night Sky", "price": "$2,599", "color": "Night Sky", "storage": "1TB", "url": "https://www.apple.com/shop/product/MK1L4LL/A"},
    "MK1Q4LL/A": {"name": "iPhone Duo 2TB Star White", "price": "$3,199", "color": "Star White", "storage": "2TB", "url": "https://www.apple.com/shop/product/MK1Q4LL/A"},
    "MK1R4LL/A": {"name": "iPhone Duo 2TB Night Sky", "price": "$3,199", "color": "Night Sky", "storage": "2TB", "url": "https://www.apple.com/shop/product/MK1R4LL/A"},
}

# Unified Catalog Lookup
PRODUCT_CATALOG = {**UK_PRODUCT_CATALOG, **US_PRODUCT_CATALOG}

DEFAULT_POSTCODE_UK = "W1B 3AG"
DEFAULT_ZIP_US = "10001"
DEFAULT_MAX_DISTANCE_MILES = 50.0
DEFAULT_INTERVAL_SECONDS = 45
COOKIE_JAR_PATH = "/tmp/apple_stock_cookies.txt"

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:132.0) "
        "Gecko/20100101 Firefox/132.0"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en-GB;q=0.9,en;q=0.8",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Priority": "u=1, i",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
}


def notify_mac(title: str, message: str, sound: str = "Glass"):
    """Display a native macOS notification banner."""
    safe_title = title.replace('"', '\\"')
    safe_message = message.replace('"', '\\"')
    script = f'display notification "{safe_message}" with title "{safe_title}" sound name "{sound}"'
    try:
        subprocess.run(["osascript", "-e", script], check=False)
    except Exception:
        pass


def send_discord_alert(
    webhook_url: str,
    title: str,
    description: str,
    store_name: str = "",
    distance_str: str = "",
    buy_url: str = "",
    ping_everyone: bool = True,
    color: int = None,
    custom_fields: list = None,
):
    """Send instant push notification to Discord."""
    if not webhook_url or not webhook_url.startswith("https://discord.com/api/webhooks/"):
        return

    content = f"@everyone 🚨 **{title}**" if ping_everyone else f"ℹ️ **{title}**"

    if color is None:
        if "IN STOCK" in title:
            color = 0x2ECC71  # Vibrant Green
        elif "Stop" in title or "Error" in title or "Warning" in title or "Notice" in title:
            color = 0xE67E22  # Orange / Red
        else:
            color = 0x3498DB  # Blue

    embed = {
        "title": "🍏 " + title,
        "description": description,
        "color": color,
        "footer": {"text": "Apple Stock Monitor"},
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    if custom_fields is not None:
        embed["fields"] = custom_fields
    elif "IN STOCK" in title or "TEST" in title:
        embed["url"] = buy_url
        embed["fields"] = [
            {"name": "📦 Target Product", "value": "iPhone Duo", "inline": False},
            {"name": "📍 Store Found", "value": f"{store_name} ({distance_str})" if store_name else "Nearby", "inline": True},
            {"name": "⚡ Direct Checkout", "value": f"[🛒 **CLICK HERE TO BUY NOW ON APPLE STORE**]({buy_url})", "inline": False},
        ]

    payload = {
        "content": content,
        "embeds": [embed],
    }

    try:
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "AppleStockMonitor/1.0"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            pass
    except Exception as e:
        print(f"⚠️ Discord webhook failed: {e}")


def play_audio_alert(message: str):
    """Play alert chime and speak announcement aloud."""
    sound_files = [
        "/System/Library/Sounds/Hero.aiff",
        "/System/Library/Sounds/Glass.aiff",
        "/System/Library/Sounds/Ping.aiff",
    ]
    for sound in sound_files:
        if os.path.exists(sound):
            subprocess.Popen(["afplay", sound])
            break

    try:
        subprocess.Popen(["say", message])
    except Exception:
        pass


def open_browser(url: str, browser: str = "firefox"):
    """Open product buy page in chosen browser (Firefox, Safari, Chrome, or Default)."""
    b = browser.lower().strip()
    print(f"\n🚀 Launching {browser.title()} to: {url}")
    
    cmd = []
    if b == "safari":
        cmd = ["open", "-a", "Safari", url]
    elif "chrome" in b:
        cmd = ["open", "-a", "Google Chrome", url]
    elif "firefox" in b:
        if os.path.exists("/Applications/Firefox.app"):
            cmd = ["open", "-a", "/Applications/Firefox.app", url]
        else:
            cmd = ["open", "-a", "Firefox", url]
    else:
        cmd = ["open", url]

    try:
        subprocess.Popen(cmd)
    except Exception as e:
        print(f"⚠️ Primary launch failed ({e}), opening in default browser...")
        subprocess.Popen(["open", url])


def extract_stores(data: dict) -> list:
    """Safely extract list of retail stores from Apple API response."""
    if not isinstance(data, dict):
        return []
    body = data.get("body", {})
    if not isinstance(body, dict):
        return []

    stores = body.get("stores", [])
    if isinstance(stores, list) and stores:
        return stores

    for key in ["stores", "storeList", "pickupStores"]:
        val = body.get(key)
        if isinstance(val, list) and val:
            return val

    return []


def parse_distance(store: dict) -> float:
    """Extract numeric distance in miles from store record."""
    unit_str = store.get("storeDistanceWithUnit", "")
    if unit_str and isinstance(unit_str, str):
        m = re.search(r"([\d\.]+)", unit_str)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass

    for key in ["storeDistance", "storedistance", "distance", "store_distance"]:
        val = store.get(key)
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            m = re.search(r"([\d\.]+)", val)
            if m:
                return float(m.group(1))

    return 999.0


def fetch_fulfillment_data(part_numbers: list, postcode: str, country: str = "uk") -> dict:
    """
    Fetch availability data for multiple parts simultaneously from Apple's retail stock API.
    Supports UK (/uk/shop/retail/pickup-message) and US (/shop/retail/pickup-message).
    """
    is_us = (country.lower() in ["us", "usa", "united states"])
    base_endpoint = "https://www.apple.com/shop/retail/pickup-message" if is_us else "https://www.apple.com/uk/shop/retail/pickup-message"
    referer = "https://www.apple.com/shop/buy-iphone/iphone-duo" if is_us else "https://www.apple.com/uk/shop/buy-iphone/iphone-duo"

    parts_query = "&".join([f"parts.{i}={urllib.parse.quote(p, safe='')}" for i, p in enumerate(part_numbers)])
    formatted_postcode = postcode.strip()

    candidate_urls = [
        f"{base_endpoint}?pl=true&mts.0=regular&{parts_query}&location={urllib.parse.quote_plus(formatted_postcode)}",
        f"{base_endpoint}?pl=true&{parts_query}&location={urllib.parse.quote(formatted_postcode)}",
        f"{base_endpoint}?pl=true&{parts_query}&location={urllib.parse.quote(formatted_postcode.replace(' ', ''))}",
    ]

    headers = dict(BROWSER_HEADERS)
    headers["Referer"] = referer

    last_error = None

    for url in candidate_urls:
        parsed_data = None

        if os.path.exists("/usr/bin/curl"):
            curl_base_cmd = [
                "/usr/bin/curl",
                "-s",
                "--compressed",
                "--max-time", "25",
                "-c", COOKIE_JAR_PATH,
                "-b", COOKIE_JAR_PATH,
                "-H", f"User-Agent: {headers['User-Agent']}",
                "-H", f"Accept: {headers['Accept']}",
                "-H", f"Accept-Language: {headers['Accept-Language']}",
                "-H", f"Referer: {headers['Referer']}",
                "-H", "Sec-Fetch-Dest: empty",
                "-H", "Sec-Fetch-Mode: cors",
                "-H", "Sec-Fetch-Site: same-origin",
                "-H", f"Priority: {headers['Priority']}",
                "-H", "Cache-Control: no-cache",
                "-w", "\n%{http_code}",
            ]

            for insecure_flag in [[], ["-k"]]:
                try:
                    cmd = curl_base_cmd[:1] + insecure_flag + curl_base_cmd[1:] + [url]
                    res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                    if res.returncode == 0 and res.stdout:
                        parts = res.stdout.strip().rsplit("\n", 1)
                        body = parts[0]
                        status_code = parts[1] if len(parts) > 1 else "200"

                        if status_code == "200" and body:
                            try:
                                candidate = json.loads(body)
                                if "body" in candidate:
                                    parsed_data = candidate
                                    break
                            except json.JSONDecodeError:
                                pass
                        elif status_code in ("403", "429", "541"):
                            last_error = urllib.error.HTTPError(url, int(status_code), f"HTTP {status_code}", {}, None)
                            break
                    elif res.returncode in (35, 60):
                        continue
                except Exception as ex:
                    last_error = ex

        if parsed_data is None:
            try:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=25, context=ssl_context) as response:
                    if response.status == 200:
                        raw_body = response.read().decode("utf-8")
                        candidate = json.loads(raw_body)
                        if "body" in candidate:
                            parsed_data = candidate
                    elif response.status in (403, 429, 541):
                        last_error = urllib.error.HTTPError(url, response.status, f"HTTP {response.status}", {}, None)
            except urllib.error.HTTPError as he:
                last_error = he
            except Exception as ex:
                last_error = ex

        if parsed_data:
            stores = extract_stores(parsed_data)
            if stores:
                return parsed_data

    if parsed_data:
        return parsed_data

    if last_error:
        raise last_error
    raise RuntimeError("Failed to retrieve inventory data from Apple.")


def check_availability(part_numbers: list, postcode: str, max_distance: float, country: str = "uk"):
    """
    Check stock for all requested parts across retail stores within distance limit.
    Returns: (in_stock_matches, nearby_stores, all_stores)
    """
    data = fetch_fulfillment_data(part_numbers, postcode, country)
    stores = extract_stores(data)

    all_stores = []
    in_stock_matches = []

    for store in stores:
        raw_name = store.get("storeName", "Unknown Apple Store")
        city = store.get("city", "")
        if not raw_name.lower().startswith("apple"):
            store_name = f"Apple {raw_name}"
        else:
            store_name = raw_name
        if city and city.lower() not in store_name.lower():
            display_name = f"{store_name} ({city})"
        else:
            display_name = store_name

        distance = parse_distance(store)
        parts_avail = store.get("partsAvailability", {})

        store_parts_status = {}
        store_has_stock = False

        for p in part_numbers:
            p_info = parts_avail.get(p, {})
            pickup_display = p_info.get("pickupDisplay", "").lower()
            selection_enabled = p_info.get("storeSelectionEnabled", False)
            quote = p_info.get("pickupSearchQuote", "")
            if not quote:
                quote = "Pickup unavailable" if pickup_display != "available" else "Available for pickup"

            is_available = (pickup_display == "available") or (selection_enabled is True)
            store_parts_status[p] = {
                "available": is_available,
                "quote": quote,
            }

            if is_available:
                store_has_stock = True
                p_meta = PRODUCT_CATALOG.get(p, {"name": p, "price": "", "url": f"https://www.apple.com/shop/product/{p}"})
                in_stock_matches.append({
                    "store_name": display_name,
                    "distance": distance,
                    "part": p,
                    "product_name": p_meta["name"],
                    "price": p_meta["price"],
                    "buy_url": p_meta["url"],
                    "quote": quote,
                })

        all_stores.append({
            "name": display_name,
            "distance": distance,
            "has_stock": store_has_stock,
            "parts": store_parts_status,
            "city": city,
            "store_number": store.get("storeNumber", ""),
        })

    all_stores.sort(key=lambda s: s["distance"])
    nearby_stores = [s for s in all_stores if s["distance"] <= max_distance]
    nearby_in_stock = [m for m in in_stock_matches if m["distance"] <= max_distance]

    return nearby_in_stock, nearby_stores, all_stores


def resolve_skus(parts_arg: list, color_arg: str, storages_arg: list, country: str = "uk") -> list:
    """Resolve specific Apple SKUs for UK or US based on CLI or GUI selections."""
    if parts_arg:
        valid_parts = [p for p in parts_arg if p in PRODUCT_CATALOG]
        if valid_parts:
            return valid_parts
        return parts_arg

    is_us = (country.lower() in ["us", "usa", "united states"])
    catalog = US_PRODUCT_CATALOG if is_us else UK_PRODUCT_CATALOG

    target_colors = []
    c = (color_arg or "both").lower().replace("-", " ").replace("_", " ")
    if "both" in c or "all" in c:
        target_colors = ["Night Sky", "Star White"]
    elif "white" in c:
        target_colors = ["Star White"]
    elif "night" in c or "sky" in c:
        target_colors = ["Night Sky"]
    else:
        target_colors = ["Night Sky", "Star White"]

    clean_storages = []
    for s in (storages_arg or ["256GB"]):
        s_clean = s.upper().replace(" ", "")
        if "256" in s_clean:
            clean_storages.append("256GB")
        elif "512" in s_clean:
            clean_storages.append("512GB")
        elif "1TB" in s_clean or "1000" in s_clean:
            clean_storages.append("1TB")
        elif "2TB" in s_clean or "2000" in s_clean:
            clean_storages.append("2TB")

    if not clean_storages:
        clean_storages = ["256GB"]

    selected = []
    for sku, info in catalog.items():
        if info["color"] in target_colors and info["storage"] in clean_storages:
            selected.append(sku)

    fallback_sku = "MK1F4LL/A" if is_us else "MK2E4QN/A"
    return selected or [fallback_sku]


def main():
    parser = argparse.ArgumentParser(
        description="Monitor Apple Retail Inventory (UK & US) across multiple models."
    )
    parser.add_argument(
        "--country",
        choices=["uk", "us", "usa"],
        default="uk",
        help="Country / Region to monitor: uk or us (default: uk)",
    )
    parser.add_argument(
        "--browser",
        choices=["firefox", "safari", "chrome", "google-chrome", "default"],
        default="firefox",
        help="Browser to launch upon stock detection: firefox, safari, chrome, default",
    )
    parser.add_argument(
        "--parts",
        nargs="+",
        default=[],
        help="List of Apple SKUs to monitor simultaneously.",
    )
    parser.add_argument(
        "--part",
        default="",
        help="Single Apple SKU (fallback).",
    )
    parser.add_argument(
        "--color",
        default="both",
        help="Colour to monitor: both, night-sky, or star-white.",
    )
    parser.add_argument(
        "--storages",
        nargs="+",
        default=[],
        help="Storages to monitor: 256GB 512GB 1TB 2TB.",
    )
    parser.add_argument(
        "--postcode",
        default="",
        help="Postcode (UK) or ZIP Code (US) to search around.",
    )
    parser.add_argument(
        "--distance",
        type=float,
        default=DEFAULT_MAX_DISTANCE_MILES,
        help=f"Search radius in miles (default: {DEFAULT_MAX_DISTANCE_MILES})",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL_SECONDS,
        help=f"Check interval in seconds (default: {DEFAULT_INTERVAL_SECONDS})",
    )
    parser.add_argument(
        "--keep-monitoring",
        action="store_true",
        help="Continue checking after stock detection instead of exiting.",
    )
    parser.add_argument(
        "--test-browser",
        action="store_true",
        help="Test browser launch, audio alert, and Discord push immediately.",
    )
    parser.add_argument(
        "--discord",
        default="",
        help="Discord webhook URL for instant phone push notifications.",
    )
    args = parser.parse_args()

    country = "us" if args.country in ["us", "usa"] else "uk"
    default_postal = DEFAULT_ZIP_US if country == "us" else DEFAULT_POSTCODE_UK
    postal_code = args.postcode.strip() if args.postcode else default_postal

    parts_input = args.parts or ([args.part] if args.part else [])
    monitored_skus = resolve_skus(parts_input, args.color, args.storages, country)

    first_sku = monitored_skus[0]
    first_meta = PRODUCT_CATALOG.get(first_sku, {"url": "https://www.apple.com", "name": "iPhone Duo"})

    if args.test_browser:
        print("=" * 65)
        print(f" 🧪 TEST MODE: Testing Alerts, Browser ({args.browser.title()}) & Discord")
        print("=" * 65)
        print("1. Sending desktop notification...")
        notify_mac(
            "Apple Stock Alert [TEST]",
            f"Testing alerts for {len(monitored_skus)} model(s) ({country.upper()})",
        )
        print("2. Playing alert chime & announcement...")
        play_audio_alert(f"Test alert. Stock monitor is active for {len(monitored_skus)} models.")
        print(f"3. Launching {args.browser.title()} to: {first_meta['url']}...")
        open_browser(first_meta["url"], args.browser)

        if args.discord:
            print("4. 📱 Sending test push alert to Discord channel...")
            model_summary = ", ".join([PRODUCT_CATALOG.get(s, {}).get("name", s) for s in monitored_skus])
            send_discord_alert(
                args.discord,
                f"TEST ALERT: Apple Monitor Connected ({country.upper()})",
                f"Your Discord push alerts are active!\n• Region: {country.upper()}\n• Browser: {args.browser.title()}\n• Models: {model_summary}",
                store_name="Apple Store (Test)",
                distance_str="Nearby",
                buy_url=first_meta["url"],
                custom_fields=[
                    {"name": "🎯 Monitored Models", "value": model_summary, "inline": False},
                    {"name": "📍 Search Area", "value": f"{postal_code} (within {args.distance} miles)", "inline": True},
                    {"name": "⚡ Direct Checkout Link", "value": f"[🛒 Buy on Apple.com]({first_meta['url']})", "inline": False},
                ]
            )

        print(f"\n✅ Test complete! If {args.browser.title()} opened and alerts fired, everything is working properly.")
        sys.exit(0)

    print("=" * 65)
    print(f" 🍏 Apple Stock Monitor — Multi-Model Search ({country.upper()})")
    print("=" * 65)
    print(f" • Region         : {country.upper()}")
    print(f" • Location       : {postal_code}")
    print(f" • Max Radius     : {args.distance} miles")
    print(f" • Check Interval : Every ~{args.interval} seconds")
    print(f" • Browser        : {args.browser.title()}")
    print(f" • Models ({len(monitored_skus)}) :")
    for s in monitored_skus:
        info = PRODUCT_CATALOG.get(s, {"name": s, "price": ""})
        print(f"    - {info['name']} ({info['price']}) [{s}]")
    print("=" * 65)
    print("Press Ctrl+C at any time to stop monitoring.\n")

    if args.discord:
        model_names = [f"• {PRODUCT_CATALOG.get(s, {}).get('name', s)}" for s in monitored_skus]
        send_discord_alert(
            args.discord,
            f"🟢 Stock Monitor Started ({country.upper()} • {len(monitored_skus)} models)",
            f"Monitoring active near **{postal_code}** (within {args.distance} miles).\nBrowser: **{args.browser.title()}** • Cadence: every ~{args.interval}s.\n\n**Target Models:**\n" + "\n".join(model_names),
            ping_everyone=False,
            color=0x3498DB,
        )

    consecutive_errors = 0
    check_count = 0
    alerted_keys = set()
    start_time = time.time()
    last_hourly_ping = time.time()

    while True:
        check_count += 1
        now_str = time.strftime("%H:%M:%S")

        try:
            in_stock_matches, nearby_stores, all_stores = check_availability(
                monitored_skus, postal_code, args.distance, country
            )
            consecutive_errors = 0

            # Hourly Discord heartbeat summary (@everyone)
            if args.discord and (time.time() - last_hourly_ping >= 3600):
                elapsed_hours = (time.time() - start_time) / 3600.0
                uptime_str = f"{elapsed_hours:.1f} hours" if elapsed_hours >= 1.5 else "1 hour"

                model_names = [PRODUCT_CATALOG.get(p, {}).get("name", p) for p in monitored_skus]
                models_str = "\n".join([f"• {name}" for name in model_names])

                store_lines = []
                for s in nearby_stores[:4]:
                    dist_str = f"~{s['distance']:.1f} mi" if s['distance'] < 900 else "Nearby"
                    store_lines.append(f"• **{s['name']}** ({dist_str}): Scanning {len(monitored_skus)} models")
                stores_summary = "\n".join(store_lines) if store_lines else f"Scanning stores near {postal_code}"

                fallback_url = "https://www.apple.com/shop/buy-iphone" if country == "us" else "https://www.apple.com/uk/shop/buy-iphone"
                fields = [
                    {"name": "🟢 Status", "value": f"Active ({country.upper()} • {len(monitored_skus)} models)", "inline": True},
                    {"name": "⏱️ Uptime", "value": f"{uptime_str} ({check_count} checks)", "inline": True},
                    {"name": "📍 Target Area", "value": f"{postal_code} ({args.distance} miles)", "inline": True},
                    {"name": "🎯 Monitored Models", "value": models_str, "inline": False},
                    {"name": "🏬 Monitored Stores", "value": stores_summary, "inline": False},
                    {"name": "⚡ Direct Buy Link", "value": f"[🛒 View Apple Store Page]({fallback_url})", "inline": False},
                ]

                print(f"[{now_str}] ⏱️ Dispatching hourly status overview to Discord...")
                send_discord_alert(
                    args.discord,
                    f"Hourly Status Overview ({country.upper()} • Check #{check_count})",
                    f"The stock monitor is actively running and scanning {len(monitored_skus)} model(s) every {args.interval}s.",
                    ping_everyone=True,
                    color=0x3498DB,
                    custom_fields=fields,
                )
                last_hourly_ping = time.time()

            if in_stock_matches:
                print(f"[{now_str}] 🟢 IN STOCK DETECTED: {len(in_stock_matches)} match(es) found!")
                for m in in_stock_matches:
                    print(f"   ✅ {m['product_name']} available at {m['store_name']} (~{m['distance']:.1f} mi) — {m['quote']}")

                new_matches = [m for m in in_stock_matches if (m["store_name"], m["part"]) not in alerted_keys]
                if new_matches:
                    primary = new_matches[0]
                    dist_str = f" (~{primary['distance']:.1f} mi)" if primary['distance'] < 900 else ""
                    alert_title = f"🚨 {primary['product_name'].upper()} IN STOCK!"
                    alert_body = f"{primary['store_name']}{dist_str} has pickup stock!"

                    notify_mac(alert_title, alert_body)
                    play_audio_alert(f"{primary['product_name']} is in stock at {primary['store_name']}")
                    open_browser(primary["buy_url"], args.browser)

                    if args.discord:
                        print(f"[{now_str}] 📱 Dispatching Discord @everyone alert for {primary['product_name']}...")
                        send_discord_alert(
                            args.discord,
                            f"🚨 {primary['product_name'].upper()} IN STOCK NOW!",
                            f"🔥 **{primary['store_name']}**{dist_str} has pickup stock right now! Tap the checkout link below.",
                            store_name=primary["store_name"],
                            distance_str=dist_str,
                            buy_url=primary["buy_url"],
                            custom_fields=[
                                {"name": "📦 Model in Stock", "value": f"**{primary['product_name']}**\nPrice: {primary['price']} • SKU: `{primary['part']}`", "inline": False},
                                {"name": "📍 Store Found", "value": f"{primary['store_name']}{dist_str}", "inline": True},
                                {"name": "⚡ Direct Checkout", "value": f"[🛒 **CLICK HERE TO BUY NOW ON APPLE STORE**]({primary['buy_url']})", "inline": False},
                            ]
                        )

                    for m in new_matches:
                        alerted_keys.add((m["store_name"], m["part"]))

                    if not args.keep_monitoring:
                        print(f"\n✅ Product page opened in {args.browser.title()}. Exiting monitor so you can complete checkout.")
                        sys.exit(0)
                else:
                    print(f"[{now_str}] (Already alerted for these matches; continuing checks...)")

            else:
                if nearby_stores:
                    print(f"[{now_str}] Check #{check_count}: Out of stock across {len(nearby_stores)} store(s) within {args.distance} miles ({len(monitored_skus)} models checked):")
                    for s in nearby_stores:
                        dist_str = f"~{s['distance']:.1f} mi" if s['distance'] < 900 else "Nearby"
                        print(f"   ❌ {s['name']} ({dist_str}) — Out of stock")
                elif all_stores:
                    print(f"[{now_str}] Check #{check_count}: Out of stock (Closest stores beyond {args.distance} miles):")
                    for s in all_stores[:3]:
                        dist_str = f"~{s['distance']:.1f} mi" if s['distance'] < 900 else "Unknown dist"
                        print(f"   ℹ️  {s['name']} ({dist_str})")
                else:
                    print(f"[{now_str}] Check #{check_count}: Out of stock. Retrying...")

        except urllib.error.HTTPError as e:
            consecutive_errors += 1
            if e.code == 541:
                print(f"[{now_str}] ⚠️ Apple bot protection challenge (HTTP 541)")
            else:
                print(f"[{now_str}] ⚠️ Apple API HTTP {e.code}: {e.reason}")

            if e.code in (403, 429, 541):
                backoff = min(120, 30 * consecutive_errors)
                print(f"   Cooling down for {backoff} seconds before retrying...")
                if args.discord and consecutive_errors == 1:
                    send_discord_alert(
                        args.discord,
                        "⚠️ Apple Bot Protection Notice",
                        f"Encountered HTTP {e.code}. Cooling down for {backoff}s before retrying automatically.",
                        ping_everyone=False,
                        color=0xE67E22,
                    )
                time.sleep(backoff)
                continue

        except urllib.error.URLError as e:
            consecutive_errors += 1
            print(f"[{now_str}] ⚠️ Network connection issue: {e.reason}")
            if args.discord and consecutive_errors == 2:
                send_discord_alert(
                    args.discord,
                    "⚠️ Network Connection Warning",
                    f"Unable to reach Apple servers: {e.reason}. Retrying automatically...",
                    ping_everyone=False,
                    color=0xE67E22,
                )

        except Exception as e:
            consecutive_errors += 1
            print(f"[{now_str}] ⚠️ Unexpected error: {e}")
            if args.discord and consecutive_errors == 2:
                send_discord_alert(
                    args.discord,
                    "⚠️ Stock Check Warning",
                    f"Unexpected error occurred: {e}. Retrying automatically...",
                    ping_everyone=False,
                    color=0xE74C3C,
                )

        jitter = random.uniform(-3, 3)
        sleep_duration = max(15, args.interval + jitter)
        time.sleep(sleep_duration)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️ Monitoring stopped by user. Goodbye!")
        sys.exit(0)
