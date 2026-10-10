"""Step 3: apply human fact-checks, then bake stops.json into a single self-contained index.html"""
import json

walk = json.load(open("stops.json"))
overrides = json.load(open("overrides.json"))
for stop in walk["stops"]:
    fixes = overrides.get(str(stop["n"]), {})
    stop["name"] = stop["name"].removesuffix(", Perth")  # it's a Perth walk; keep cards tidy
    stop.update(fixes)
    stop["checked"] = sorted(fixes)  # fields a human corrected

html = open("template.html").read()
data = json.dumps(walk, ensure_ascii=False).replace("</", "<\\/")
open("index.html", "w").write(html.replace("/*__STOPS__*/null", data))
fixed = sum(1 for s in walk["stops"] if s["checked"])
print(f"wrote index.html with {len(walk['stops'])} stops ({fixed} fact-checked by hand)")
