"""Step 2: local gemma3 (via Ollama) turns each Wikipedia article into a walking-tour stop -> stops.json

Usage: python3 generate_guide.py [max_stops]
"""
import http.client
import json
import sys
import time
import urllib.error
import urllib.request

OLLAMA = "http://localhost:11434/api/generate"
MODEL = "gemma3"

FIELDS = ["name", "built", "tagline", "story", "look_for", "fun_fact"]
CACHE = "data/guide_cache.json"

PROMPT = """You are a friendly heritage tour guide in Perth, Western Australia.
A walker is standing outside "{title}" right now. Using ONLY facts from the article below,
write their stop on the walk. Do not invent dates, names or numbers.

Reply with JSON only, in exactly this shape:
{{
  "name": "short display name of the place",
  "built": "just the year or era it was built, max 4 words, e.g. 1923 or 1850s",
  "tagline": "one catchy line, max 10 words",
  "story": "STRICTLY 50-70 words, spoken to the walker in second person, present tense, as if standing in front of it",
  "look_for": "one specific physical detail they can spot from the street right now",
  "fun_fact": "one surprising fact from the article, max 25 words"
}}

ARTICLE:
{extract}
"""


def ask_gemma(title, extract):
    body = json.dumps({
        "model": MODEL,
        "prompt": PROMPT.format(title=title, extract=extract[:3500]),
        "format": "json",
        "stream": False,
        # small context keeps gemma3 inside a 7 GB laptop's RAM
        "options": {"temperature": 0.3, "num_ctx": 2560, "num_predict": 500},
    }).encode()
    req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=900) as r:
                text = json.load(r)["response"]
        except (ConnectionError, http.client.HTTPException, urllib.error.URLError) as e:
            # on a small laptop Ollama can get OOM-killed; systemd restarts it
            print(f"  Ollama dropped ({e.__class__.__name__}), waiting 15s", flush=True)
            time.sleep(15)
            continue
        try:
            guide = json.loads(text)
            if all(guide.get(k) for k in FIELDS):
                return guide
        except json.JSONDecodeError:
            pass
        open("data/bad_reply.txt", "w").write(text)
        print(f"  bad reply from {MODEL}, retrying ({attempt + 1}/3)", flush=True)
    raise RuntimeError(f"{MODEL} gave no usable reply for {title}")


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    wiki = json.load(open("data/wiki.json"))[:limit]
    try:
        cache = json.load(open(CACHE))
    except FileNotFoundError:
        cache = {}
    stops = []
    for i, w in enumerate(wiki, 1):
        if w["title"] not in cache:  # delete data/guide_cache.json to regenerate everything
            t0 = time.time()
            cache[w["title"]] = ask_gemma(w["title"], w["extract"])
            json.dump(cache, open(CACHE, "w"), indent=2, ensure_ascii=False)
            print(f"[{i}/{len(wiki)}] {w['title']}  ({time.time() - t0:.0f}s)", flush=True)
        guide = {k: cache[w["title"]][k] for k in FIELDS}
        stops.append({
            "n": i,
            "lat": w["lat"],
            "lon": w["lon"],
            "image": w["image"],
            "wiki_url": w["url"],
            **guide,
        })
    with open("stops.json", "w") as f:
        json.dump({"walk": "Station to Swan: Perth Heritage Walk", "model": MODEL, "stops": stops},
                  f, indent=2, ensure_ascii=False)
    print("wrote stops.json")


if __name__ == "__main__":
    main()
