#!/usr/bin/env python3
"""
Apple UK In-Store Stock Monitor
High-performance retail store inventory checker for Apple products.
Supports multi-colour and multi-storage monitoring simultaneously in a single HTTP/2 request.
When stock is detected, automatically launches Firefox to the checkout page,
plays system audio announcements, and dispatches high-priority push notifications.
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

# Official Apple UK Product Catalog for iPhone Duo
PRODUCT_CATALOG = {
    "MK2D4QN/A": {"name": "iPhone Duo 256GB Star White", "price": "£1,999", "color": "Star White", "storage": "256GB", "url": "https://www.apple.com/uk/shop/product/MK2D4QN/A"},
    "MK2E4QN/A": {"name": "iPhone Duo 256GB Night Sky", "price": "£1,999", "color": "Night Sky", "storage": "256GB", "url": "https://www.apple.com/uk/shop/product/MK2E4QN/A"},
    "MK2F4QN/A": {"name": "iPhone Duo 512GB Star White", "price": "£2,199", "color": "Star White", "storage": "512GB", "url": "https://www.apple.com/uk/shop/product/MK2F4QN/A"},
    "MK2G4QN/A": {"name": "iPhone Duo 512GB Night Sky", "price": "£2,199", "color": "Night Sky", "storage": "512GB", "url": "https://www.apple.com/uk/shop/product/MK2G4QN/A"},
    "MK2H4QN/A": {"name": "iPhone Duo 1TB Star White", "price": "£2,599", "color": "Star White", "storage": "1TB", "url": "https://www.apple.com/uk/shop/product/MK2H4QN/A"},
    "MK2J4QN/A": {"name": "iPhone Duo 1TB Night Sky", "price": "£2,599", "color": "Night Sky", "storage": "1TB", "url": "https://www.apple.com/uk/shop/product/MK2J4QN/A"},
    "MK2K4QN/A": {"name": "iPhone Duo 2TB Star White", "price": "£3,199", "color": "Star White", "storage": "2TB", "url": "https://www.apple.com/uk/shop/product/MK2K4QN/A"},
    "MK2L4QN/A": {"name": "iPhone Duo 2TB Night Sky", "price": "£3,199", "color": "Night Sky", "storage": "2TB", "url": "https://www.apple.com/uk/shop/product/MK2L4QN/A"},
}

DEFAULT_PART_NUMBER = "MK2E4QN/A"
DEFAULT_POSTCODE = "W1B 3AG"  # Central London / Regent Street (Generic Default)
DEFAULT_MAX_DISTANCE_MILES = 50.0
DEFAULT_INTERVAL_SECONDS = 45
FALLBACK_BUY_URL = "https://www.apple.com/uk/shop/buy-iphone/iphone-duo"
FIREFOX_APP_PATH = "/Applications/Firefox.app"
COOKIE_JAR_PATH = "/tmp/apple_stock_cookies.txt"

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:132.0) "
        "Gecko/20100101 Firefox/132.0"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-GB,en;q=0.9",
    "Referer": "https://www.apple.com/uk/shop/buy-iphone/iphone-duo",
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
    buy_url: str = FALLBACK_BUY_URL,
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
        "footer": {"text": "Apple UK Stock Monitor"},
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


def open_in_firefox(url: str):
    """Open product buy page directly in Firefox."""
    print(f"\n🚀 Launching Firefox to: {url}")
    try:
        if os.path.exists(FIREFOX_APP_PATH):
            subprocess.Popen(["open", "-a", FIREFOX_APP_PATH, url])
        else:
            subprocess.Popen(["open", url])
    except Exception as e:
        print(f"⚠️ Could not launch Firefox: {e}")
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


def fetch_fulfillment_data(part_numbers: list, postcode: str) -> dict:
    """
    Fetch availability data for multiple parts simultaneously from Apple's retail stock API.
    Combines parts.0=...&parts.1=... in a single fast HTTP GET request.
    """
    parts_query = "&".join([f"parts.{i}={urllib.parse.quote(p, safe='')}" for i, p in enumerate(part_numbers)])
    formatted_postcode = postcode.strip()

    candidate_urls = [
        f"https://www.apple.com/uk/shop/retail/pickup-message?pl=true&mts.0=regular&{parts_query}&location={urllib.parse.quote_plus(formatted_postcode)}",
        f"https://www.apple.com/uk/shop/retail/pickup-message?pl=true&{parts_query}&location={urllib.parse.quote(formatted_postcode)}",
        f"https://www.apple.com/uk/shop/retail/pickup-message?pl=true&{parts_query}&location={urllib.parse.quote(formatted_postcode.replace(' ', ''))}",
    ]

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
                "-H", f"User-Agent: {BROWSER_HEADERS['User-Agent']}",
                "-H", f"Accept: {BROWSER_HEADERS['Accept']}",
                "-H", f"Accept-Language: {BROWSER_HEADERS['Accept-Language']}",
                "-H", f"Referer: {BROWSER_HEADERS['Referer']}",
                "-H", "Sec-Fetch-Dest: empty",
                "-H", "Sec-Fetch-Mode: cors",
                "-H", "Sec-Fetch-Site: same-origin",
                "-H", f"Priority: {BROWSER_HEADERS['Priority']}",
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

                req = urllib.request.Request(url, headers=BROWSER_HEADERS)
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


def check_availability(part_numbers: list, postcode: str, max_distance: float):
    """
    Check stock for all requested parts across retail stores within distance limit.
    Returns: (in_stock_matches, nearby_stores, all_stores)
    """
    data = fetch_fulfillment_data(part_numbers, postcode)
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
                p_meta = PRODUCT_CATALOG.get(p, {"name": p, "price": "", "url": f"https://www.apple.com/uk/shop/product/{p}"})
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


def resolve_skus(parts_arg: list, color_arg: str, storages_arg: list) -> list:
    """Resolve specific Apple UK SKUs based on CLI or GUI selections."""
    if parts_arg:
        valid_parts = [p for p in parts_arg if p in PRODUCT_CATALOG]
        if valid_parts:
            return valid_parts
        return parts_arg

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
    for sku, info in PRODUCT_CATALOG.items():
        if info["color"] in target_colors and info["storage"] in clean_storages:
            selected.append(sku)

    return selected or [DEFAULT_PART_NUMBER]


def main():
    parser = argparse.ArgumentParser(
        description="Monitor Apple UK Retail Inventory for Apple Products."
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
        default=DEFAULT_POSTCODE,
        help=f"UK Postcode (default: {DEFAULT_POSTCODE})",
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
        help="Test the Firefox browser launch, notification, and Discord push immediately.",
    )
    parser.add_argument(
        "--discord",
        default="",
        help="Discord webhook URL for instant phone push notifications.",
    )
    args = parser.parse_args()

    parts_input = args.parts or ([args.part] if args.part else [])
    monitored_skus = resolve_skus(parts_input, args.color, args.storages)

    first_sku = monitored_skus[0]
    first_meta = PRODUCT_CATALOG.get(first_sku, {"url": FALLBACK_BUY_URL, "name": "iPhone Duo"})

    if args.test_browser:
        print("=" * 65)
        print(" 🧪 TEST MODE: Testing Alerts, Firefox & Discord Push")
        print("=" * 65)
        print("1. Sending desktop notification...")
        notify_mac(
            "Apple Stock Alert [TEST]",
            f"Testing alerts for {len(monitored_skus)} model(s)",
        )
        print("2. Playing alert chime & announcement...")
        play_audio_alert(f"Test alert. Stock monitor is active for {len(monitored_skus)} models.")
        print(f"3. Launching Firefox to: {first_meta['url']}...")
        open_in_firefox(first_meta["url"])

        if args.discord:
            print("4. 📱 Sending test push alert to Discord channel...")
            model_summary = ", ".join([PRODUCT_CATALOG.get(s, {}).get("name", s) for s in monitored_skus])
            send_discord_alert(
                args.discord,
                "TEST ALERT: Apple Multi-Model Monitor Connected",
                f"Your Discord push alerts are active! Monitoring {len(monitored_skus)} model(s):\n• {model_summary}",
                store_name="Apple Store (Test)",
                distance_str="Nearby",
                buy_url=first_meta["url"],
                custom_fields=[
                    {"name": "🎯 Monitored Models", "value": model_summary, "inline": False},
                    {"name": "📍 Search Area", "value": f"{args.postcode} (within {args.distance} miles)", "inline": True},
                    {"name": "⚡ Direct Checkout Link", "value": f"[🛒 Buy on Apple.com]({first_meta['url']})", "inline": False},
                ]
            )

        print("\n✅ Test complete! If Firefox opened and alerts fired, everything is working properly.")
        sys.exit(0)

    print("=" * 65)
    print(" 🍏 Apple UK Stock Monitor — Multi-Model Search")
    print("=" * 65)
    print(f" • Postcode       : {args.postcode}")
    print(f" • Max Radius     : {args.distance} miles")
    print(f" • Check Interval : Every ~{args.interval} seconds")
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
            f"🟢 Stock Monitor Started ({len(monitored_skus)} models)",
            f"Monitoring active near **{args.postcode}** (within {args.distance} miles).\nCheck cadence: every ~{args.interval}s.\n\n**Target Models:**\n" + "\n".join(model_names),
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
                monitored_skus, args.postcode, args.distance
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
                stores_summary = "\n".join(store_lines) if store_lines else f"Scanning stores near {args.postcode}"

                fields = [
                    {"name": "🟢 Status", "value": f"Active & Scanning ({len(monitored_skus)} models)", "inline": True},
                    {"name": "⏱️ Uptime", "value": f"{uptime_str} ({check_count} checks)", "inline": True},
                    {"name": "📍 Target Area", "value": f"{args.postcode} ({args.distance} miles)", "inline": True},
                    {"name": "🎯 Monitored Models", "value": models_str, "inline": False},
                    {"name": "🏬 Monitored Stores", "value": stores_summary, "inline": False},
                    {"name": "⚡ Direct Buy Link", "value": f"[🛒 View Apple Store Page]({FALLBACK_BUY_URL})", "inline": False},
                ]

                print(f"[{now_str}] ⏱️ Dispatching hourly status overview to Discord...")
                send_discord_alert(
                    args.discord,
                    f"Hourly Status Overview (Check #{check_count})",
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
                    open_in_firefox(primary["buy_url"])

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
                        print("\n✅ Product page opened in Firefox. Exiting monitor so you can complete checkout.")
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
