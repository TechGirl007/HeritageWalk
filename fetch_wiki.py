"""Step 1: pull facts for each heritage stop from Wikipedia -> data/wiki.json"""
import json
import time
import os
import urllib.error
import urllib.parse
import urllib.request

UA = "PerthHeritageWalk-PoC/0.1 (Hacktoberfest 2026 DEV challenge)"
API = "https://en.wikipedia.org/w/api.php"

# Walk order: Perth Station down to the Swan River
STOPS = [
    "Perth railway station",
    "General Post Office, Perth",
    "Palace Hotel, Perth",
    "London Court",
    "Theatre Royal and Metropole Hotel",
    "Perth Town Hall",
    "Treasury Buildings, Perth",
    "St George's Cathedral, Perth",
    "The Deanery, Perth",
    "Government House, Perth",
    "Old Court House, Perth",
    "Swan Bells",
]


def get(params):
    params = {**params, "format": "json", "formatversion": "2"}
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers={"User-Agent": UA})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 4:
                raise
            wait = int(e.headers.get("Retry-After") or 10 * (attempt + 1))
            print(f"  rate limited, waiting {wait}s")
            time.sleep(wait)


def main():
    data = get({
        "action": "query",
        "titles": "|".join(STOPS),
        "prop": "coordinates|pageimages|info",
        "colimit": "max",
        "pithumbsize": 640,
        "inprop": "url",
        "redirects": 1,
    })
    pages = {p["title"]: p for p in data["query"]["pages"]}
    out = []
    for title in STOPS:
        p = pages.get(title)
        if not p or "coordinates" not in p:
            print("MISSING:", title)
            continue
        c = p["coordinates"][0]
        time.sleep(1.5)  # be polite to the Wikipedia API
        # full-text extracts only come back one page per request
        ex = get({"action": "query", "titles": title, "prop": "extracts", "explaintext": 1})
        p["extract"] = ex["query"]["pages"][0].get("extract", "")
        out.append({
            "title": title,
            "lat": c["lat"],
            "lon": c["lon"],
            "extract": p.get("extract", "")[:6000],
            "image": p.get("thumbnail", {}).get("source"),
            "url": p.get("fullurl"),
        })
        print(f"ok  {title:40} {c['lat']:.5f},{c['lon']:.5f}  {len(p.get('extract',''))} chars  img={'y' if p.get('thumbnail') else 'n'}")
    os.makedirs("data", exist_ok=True)
    with open("data/wiki.json", "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
